"""Auditable diabetes-risk rule extension alongside the original MAPFM core."""

from __future__ import annotations

import threading
import time

from diabetes_risk import DiabetesRiskInput, ExistingDiabetesEvaluation, calculate_diabetes_risk
from mapfm_ecosystem_repaired import BaseAgent, HeterogeneousMultiAgentEcosystem


AGENT_NAME = "ChronicRiskRules"


class ChronicRiskRuleAgent(BaseAgent):
    """Deterministic MAPFM-compatible rule agent, not a trained MAPFM model."""

    def __init__(self) -> None:
        super().__init__(AGENT_NAME)
        self._lock = threading.Lock()
        self.last_task: str | None = None

    def _calculate(self, task: str, item: object, calculator) -> dict:
        started = time.perf_counter()
        with self._lock:
            self.total_calls += 1
            self.heartbeat()
            self.last_task = task
        try:
            result = calculator(item)
        except ExistingDiabetesEvaluation:
            # A correctly rejected out-of-scope patient is not an agent fault.
            with self._lock:
                self.record_runtime(started)
            raise
        except Exception:
            with self._lock:
                self.mark_failure()
                self.record_runtime(started)
            raise
        with self._lock:
            self.record_runtime(started)
        return result | {
            "system_extension": "mapfm_chronic_risk_v2",
            "mapfm_agent": AGENT_NAME,
            "task": task,
            "integration_mode": "registered_deterministic_rule_agent_not_original_mapfm_model",
            "original_mapfm_model_used_for_this_probability": False,
            "execution_trace": [
                {"stage": "eligibility", "status": "passed"},
                {"stage": "published_rule_calculation", "status": "completed", "model": result["model"]},
                {"stage": "source_and_limitations", "status": "attached"},
                {"stage": "human_review", "status": "required"},
            ],
        }

    def diabetes(self, item: DiabetesRiskInput) -> dict:
        return self._calculate("incident_diabetes", item, calculate_diabetes_risk)

    def safe_status(self) -> dict:
        """Agent health only; never expose patient inputs or results."""
        with self._lock:
            state = self.get_status()
            return {"name": state["name"], "status": state["status"],
                    "total_calls": state["total_calls"], "failures": state["failures"],
                    "last_runtime_seconds": state["last_runtime_seconds"], "last_task": self.last_task}


_AGENT = ChronicRiskRuleAgent()


def attach_to_ecosystem(ecosystem: HeterogeneousMultiAgentEcosystem) -> None:
    """Register the extension in original MAPFM maintenance and topology.

    This does not send chronic-risk values to the original LLM or repurpose its
    acute-care disease labels. Registration is idempotent.
    """
    ecosystem.maintenance_agent.register(_AGENT)
    ecosystem.topology_manager.register_node(_AGENT.name)
    ecosystem.chronic_risk_agent = _AGENT


def agent_status() -> dict:
    return _AGENT.safe_status()


def predict_diabetes_onset(item: DiabetesRiskInput) -> dict:
    return _AGENT.diabetes(item)


def capabilities() -> dict:
    return {
        "system_extension": "mapfm_chronic_risk_v2",
        "original_mapfm_core_modified": False,
        "agent": AGENT_NAME,
        "integration_mode": "registered_deterministic_rule_agent_not_original_mapfm_model",
        "pathways": [
            {"task": "incident_diabetes", "endpoint": "/risk/diabetes-8y", "horizon_years": 8,
             "population": "baseline_without_diabetes", "method": "published_framingham_score"},
        ],
        "clinical_use_allowed": False,
        "note": "仅提供未来糖尿病发表规则；MedQuAD 医学问答不是纵向结局数据。",
    }
