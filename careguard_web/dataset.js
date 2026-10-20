"use strict";

// Source medical Q&A, not patient cases. Pagination preserves original CSV IDs.
(() => {
  const list = document.querySelector("#dataset-list");
  if (!list) return;
  const search = document.querySelector("#dataset-search");
  const area = document.querySelector("#dataset-area");
  const count = document.querySelector("#dataset-count");
  const prev = document.querySelector("#dataset-prev");
  const next = document.querySelector("#dataset-next");
  const pageInput = document.querySelector("#dataset-page");
  const pageTotal = document.querySelector("#dataset-page-total");
  const pageForm = document.querySelector("#dataset-page-form");
  const PAGE_SIZE = 24;
  let currentPage = 0;
  let matched = 0;
  let requestSerial = 0;
  let detailSerial = 0;
  let timer;

  function clearDetail() {
    ++detailSerial;
    document.querySelector("#dataset-id").textContent = "ROW / —";
    document.querySelector("#dataset-detail-area").textContent = "SOURCE RECORD";
    document.querySelector("#dataset-question").textContent = "请选择一条原始问答";
    document.querySelector("#dataset-answer").textContent = "调整检索词或主题后，在左侧选择记录查看完整原文。";
    document.querySelector("#dataset-source").textContent = "SOURCE / medNo.22.csv";
  }

  async function selectQuestion(item, userInitiated = false) {
    const serial = ++detailSerial;
    document.querySelector("#dataset-id").textContent = `ROW / ${item.id}`;
    document.querySelector("#dataset-detail-area").textContent = item.area;
    document.querySelector("#dataset-question").textContent = item.question;
    document.querySelector("#dataset-answer").textContent = "正在读取完整原始回答…";
    document.querySelector("#dataset-source").textContent = `SOURCE / ${item.source} · medNo.22.csv`;
    list.querySelectorAll(".dataset-row").forEach((button) => {
      const selected = Number(button.dataset.id) === item.id;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    try {
      const response = await fetch(`/site/dataset/questions/${item.id}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const full = await response.json();
      if (serial === detailSerial) document.querySelector("#dataset-answer").textContent = full.answer || "原始回答为空。";
    } catch (_error) {
      if (serial === detailSerial) document.querySelector("#dataset-answer").textContent = "完整回答暂时无法读取，请使用下方原始 CSV 核对。";
    }
    if (userInitiated && window.matchMedia("(max-width: 900px)").matches) {
      const motion = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth";
      document.querySelector(".dataset-detail").scrollIntoView({ behavior: motion, block: "start" });
    }
  }

  function renderRows(items) {
    list.replaceChildren();
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "dataset-empty";
      empty.textContent = "没有匹配的问题。可尝试英文主题词或原始 ID，例如 stroke、#381。";
      list.append(empty);
      clearDetail();
      return;
    }
    items.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "dataset-row";
      button.dataset.id = String(item.id);
      button.setAttribute("aria-pressed", "false");
      const code = document.createElement("span");
      code.className = "dataset-row-id";
      code.textContent = `#${item.id}`;
      const main = document.createElement("span");
      main.className = "dataset-row-main";
      const topic = document.createElement("small");
      topic.textContent = item.area;
      const question = document.createElement("strong");
      question.textContent = item.question;
      main.append(topic, question);
      const arrow = document.createElement("span");
      arrow.className = "dataset-row-arrow";
      arrow.setAttribute("aria-hidden", "true");
      arrow.textContent = "↗";
      button.append(code, main, arrow);
      button.addEventListener("click", () => selectQuestion(item, true));
      list.append(button);
    });
    selectQuestion(items[0]);
  }

  function updatePager() {
    const pages = Math.max(1, Math.ceil(matched / PAGE_SIZE));
    pageInput.value = String(currentPage + 1);
    pageInput.max = String(pages);
    pageTotal.textContent = `/ ${pages} 页`;
    prev.disabled = currentPage === 0;
    next.disabled = currentPage >= pages - 1 || matched === 0;
    pageInput.disabled = matched === 0;
    pageForm.querySelector("#dataset-go").disabled = matched === 0;
  }

  async function load(page = 0) {
    const serial = ++requestSerial;
    const q = search.value.trim();
    const topic = area.value;
    const offset = page * PAGE_SIZE;
    const params = new URLSearchParams({ q, area: topic, offset: String(offset), limit: String(PAGE_SIZE) });
    list.textContent = "正在读取原始问答索引…";
    try {
      const response = await fetch(`/site/dataset/questions?${params.toString()}`, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (serial !== requestSerial) return;
      matched = data.matched;
      const pages = Math.max(1, Math.ceil(matched / PAGE_SIZE));
      if (page >= pages) { load(pages - 1); return; }
      currentPage = page;
      renderRows(data.items);
      list.scrollTop = 0;
      count.textContent = `显示 ${data.items.length ? offset + 1 : 0}–${offset + data.items.length} / 匹配 ${matched} · 全库 ${data.total_rows}`;
      updatePager();
    } catch (_error) {
      if (serial !== requestSerial) return;
      list.textContent = "问答索引暂时无法读取，请检查本地站点服务。";
      count.textContent = "读取失败";
      matched = 0;
      currentPage = 0;
      updatePager();
      clearDetail();
    }
  }

  search.addEventListener("input", () => {
    clearTimeout(timer);
    if (/^#\d+$/.test(search.value.trim())) area.value = "";
    timer = setTimeout(() => load(0), 220);
  });
  area.addEventListener("change", () => load(0));
  prev.addEventListener("click", () => load(Math.max(0, currentPage - 1)));
  next.addEventListener("click", () => load(currentPage + 1));
  pageForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const pages = Math.max(1, Math.ceil(matched / PAGE_SIZE));
    const page = Number(pageInput.value);
    if (!Number.isInteger(page) || page < 1 || page > pages) {
      pageInput.value = String(currentPage + 1);
      pageInput.focus();
      return;
    }
    load(page - 1);
  });
  fetch("/site/dataset/manifest").then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }).then((manifest) => {
    const status = document.querySelector("#dataset-manifest");
    status.textContent = `已核对 ${manifest.total_rows} / ${manifest.unique_ids} 条唯一记录 · ${manifest.topic_count} 个主题`;
    for (const topic of manifest.topics) {
      const option = document.createElement("option");
      option.value = topic.area;
      option.textContent = `${topic.area} (${topic.count})`;
      area.append(option);
    }
  }).catch(() => {
    document.querySelector("#dataset-manifest").textContent = "数据清单暂不可读；请核对原始 CSV。";
  });
  load();
})();
