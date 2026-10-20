"""Traceable PubMed evidence ingestion via the official NCBI E-utilities API.

Only records actually returned by NCBI are emitted.  Network failures produce an
empty result and an explicit error; the module never fabricates literature.
"""
from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests


NCBI_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class PubMedFetchReport:
    query: str
    requested: int
    documents: List[Dict[str, Any]] = field(default_factory=list)
    pmids: List[str] = field(default_factory=list)
    error: Optional[str] = None
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _node_text(node: Optional[ET.Element]) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def _article_date(article: ET.Element) -> datetime:
    candidates = [
        article.find(".//ArticleDate"),
        article.find(".//JournalIssue/PubDate"),
        article.find(".//DateCompleted"),
    ]
    month_map = {
        name: index for index, name in enumerate(
            ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        )
    }
    for node in candidates:
        if node is None:
            continue
        try:
            year = int(_node_text(node.find("Year")) or datetime.utcnow().year)
            raw_month = _node_text(node.find("Month")) or "1"
            month = int(raw_month) if raw_month.isdigit() else month_map.get(raw_month[:3].title(), 1)
            day = int(_node_text(node.find("Day")) or 1)
            return datetime(year, max(1, min(month, 12)), max(1, min(day, 28)))
        except (TypeError, ValueError):
            continue
    return datetime.utcnow()


class PubMedEvidenceClient:
    """Small, rate-limited client for ESearch + EFetch.

    NCBI asks API users to provide a tool name and e-mail.  Both may be supplied
    through MAPFM_NCBI_TOOL / MAPFM_NCBI_EMAIL; an API key may be supplied through
    NCBI_API_KEY.  The no-key path is conservatively limited to 3 requests/second.
    """

    def __init__(
        self,
        *,
        email: Optional[str] = None,
        tool: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 20.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.email = email or os.getenv("MAPFM_NCBI_EMAIL", "")
        self.tool = tool or os.getenv("MAPFM_NCBI_TOOL", "mapfm-competition-research")
        self.api_key = api_key or os.getenv("NCBI_API_KEY", "")
        self.timeout = timeout
        self.session = session or requests.Session()
        self._last_request = 0.0
        self.last_report: Optional[PubMedFetchReport] = None

    def _request(self, endpoint: str, params: Dict[str, Any]) -> requests.Response:
        minimum_gap = 0.11 if self.api_key else 0.35
        remaining = minimum_gap - (time.monotonic() - self._last_request)
        if remaining > 0:
            time.sleep(remaining)
        common = {"db": "pubmed", "tool": self.tool}
        if self.email:
            common["email"] = self.email
        if self.api_key:
            common["api_key"] = self.api_key
        response = self.session.get(
            f"{NCBI_EUTILS}/{endpoint}",
            params={**common, **params},
            timeout=self.timeout,
            headers={"User-Agent": f"{self.tool}/1.0 ({self.email or 'email-not-configured'})"},
        )
        self._last_request = time.monotonic()
        response.raise_for_status()
        return response

    def search(self, query: str, max_results: int = 5) -> PubMedFetchReport:
        max_results = max(1, min(int(max_results), 20))
        report = PubMedFetchReport(query=query, requested=max_results)
        try:
            search = self._request(
                "esearch.fcgi",
                {"term": query, "retmax": max_results, "retmode": "json", "sort": "pub date"},
            ).json()
            pmids = [str(value) for value in search.get("esearchresult", {}).get("idlist", [])]
            report.pmids = pmids
            if not pmids:
                self.last_report = report
                return report
            root = ET.fromstring(
                self._request("efetch.fcgi", {"id": ",".join(pmids), "retmode": "xml"}).content
            )
            for article in root.findall(".//PubmedArticle"):
                pmid = _node_text(article.find(".//MedlineCitation/PMID"))
                title = _node_text(article.find(".//Article/ArticleTitle"))
                abstract = " ".join(
                    _node_text(node) for node in article.findall(".//Article/Abstract/AbstractText")
                ).strip()
                journal = _node_text(article.find(".//Article/Journal/Title"))
                publication_date = _article_date(article)
                doi = ""
                for identifier in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
                    if identifier.attrib.get("IdType") == "doi":
                        doi = _node_text(identifier)
                        break
                if not pmid or not title:
                    continue
                report.documents.append(
                    {
                        "question": title,
                        "answer": abstract or f"PubMed record: {title}",
                        "source": "PubMed",
                        "last_updated": publication_date,
                        "doc_weight": 1.0,
                        "metadata": {
                            "pmid": pmid,
                            "doi": doi,
                            "journal": journal,
                            "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                            "retrieved_at": report.fetched_at,
                            "retrieval_query": query,
                            "provenance_verified": True,
                            "content_type": "title_and_abstract" if abstract else "title_only",
                        },
                    }
                )
        except Exception as exc:  # explicit failure, never synthetic fallback
            report.error = f"{type(exc).__name__}: {exc}"
            report.documents = []
        self.last_report = report
        return report
