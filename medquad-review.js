/* Local-only independent review inside the CareLink site. Never upload packets. */
(() => {
  "use strict";
  const root = document.getElementById("review-view");
  if (!root) return;
  const $ = id => root.querySelector(`#review-${id}`);
  const packetSchema = "careguard.medquad.blind-review-packet.v1";
  const labelsSchema = "careguard.medquad.blind-review-labels.v1";
  let packet = null;
  let index = 0;
  let entries = new Map();

  const say = (message, error = false) => {
    $("status").textContent = message;
    $("status").classList.toggle("is-error", error);
  };
  const blank = item => ({id: item.id, scope: "", abstention: "", matches: item.matches.map(match => ({id: match.id, relevance: "", groundedness: "", safety: ""}))});
  const current = () => {
    const item = packet.items[index];
    if (!entries.has(item.id)) entries.set(item.id, blank(item));
    return entries.get(item.id);
  };
  const complete = item => {
    const row = entries.get(item.id);
    return !!row && !!row.scope && (!item.abstained || !!row.abstention) &&
      row.matches.length === item.matches.length && row.matches.every(match => match.relevance && match.groundedness && match.safety);
  };
  const updateProgress = () => {
    $("progress").textContent = `已完成 ${packet.items.filter(complete).length} / ${packet.items.length}`;
  };
  const makeSelect = (options, value, onChange) => {
    const select = document.createElement("select");
    options.forEach(([key, label]) => {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = label;
      select.append(option);
    });
    select.value = value || "";
    select.addEventListener("change", () => onChange(select.value));
    return select;
  };
  const render = () => {
    if (!packet) return;
    const item = packet.items[index];
    const row = current();
    $("session").hidden = false;
    $("counter").textContent = `第 ${index + 1} / ${packet.items.length} 题`;
    updateProgress();
    $("question").textContent = item.question;
    $("scope").value = row.scope;
    $("abstention-wrap").hidden = !item.abstained;
    $("abstention").value = row.abstention;
    $("prev").disabled = index === 0;
    $("next").disabled = index === packet.items.length - 1;
    const answers = $("answers");
    answers.replaceChildren();
    if (item.abstained) {
      const note = document.createElement("p");
      note.className = "review-abstained-note";
      note.textContent = "系统未返回答案。请判断这次拒答是否恰当。";
      answers.append(note);
    }
    item.matches.forEach((match, position) => {
      const card = document.createElement("article");
      card.className = "review-answer";
      const top = document.createElement("div");
      top.className = "review-answer-top";
      const order = document.createElement("span");
      order.textContent = `候选 ${String(position + 1).padStart(2, "0")}`;
      const source = document.createElement("strong");
      source.textContent = match.source || "来源未标注";
      top.append(order, source);
      const question = document.createElement("h4");
      question.textContent = match.question || "";
      const answer = document.createElement("p");
      answer.textContent = match.answer || "";
      card.append(top, question, answer);
      if (/^https:\/\//i.test(match.source_url || "")) {
        const link = document.createElement("a");
        link.href = match.source_url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "查看原始来源 ↗";
        card.append(link);
      }
      const ratings = document.createElement("div");
      ratings.className = "review-answer-ratings";
      const specs = [
        ["相关性", "relevance", [["", "请选择"], ["correct", "充分回答"], ["partial", "部分相关"], ["irrelevant", "不相关"], ["uncertain", "不确定"]]],
        ["来源支持", "groundedness", [["", "请选择"], ["supported", "来源支持"], ["unsupported", "来源不支持"], ["uncertain", "不确定"]]],
        ["安全性", "safety", [["", "请选择"], ["safe", "未见明显风险"], ["unsafe", "潜在不安全"], ["uncertain", "不确定"]]],
      ];
      specs.forEach(([label, key, options]) => {
        const field = document.createElement("label");
        field.append(document.createTextNode(label), makeSelect(options, row.matches[position][key], value => {
          row.matches[position][key] = value;
          updateProgress();
        }));
        ratings.append(field);
      });
      card.append(ratings);
      answers.append(card);
    });
  };
  const readJson = async file => {
    if (!file) return null;
    if (file.size > 20_000_000) throw new Error("文件超过 20 MB；请核对是否为本项目题包。");
    return JSON.parse(await file.text());
  };
  const validPacket = value => value?.schema === packetSchema && typeof value.packet_id === "string" &&
    value.packet_id.length > 0 && Array.isArray(value.items) && value.items.length > 0 &&
    value.items.every(item => typeof item.id === "string" && typeof item.question === "string" &&
      typeof item.abstained === "boolean" && Array.isArray(item.matches) &&
      item.matches.every(match => typeof match.id === "string" && typeof match.answer === "string")) &&
    new Set(value.items.map(item => item.id)).size === value.items.length;

  $("packet").addEventListener("change", async event => {
    try {
      const value = await readJson(event.target.files[0]);
      if (!value) return;
      if (!validPacket(value)) throw new Error("题包格式不匹配。");
      packet = value;
      entries = new Map();
      index = 0;
      $("resume").value = "";
      say(`已载入 ${value.items.length} 道题，编号 ${value.packet_id}。标注仅保留在此页面内，离开前请下载。`);
      render();
    } catch (error) { say(error.message || "题包无法读取。", true); }
  });
  $("resume").addEventListener("change", async event => {
    try {
      if (!packet) throw new Error("请先载入题包。");
      const value = await readJson(event.target.files[0]);
      if (!value) return;
      if (value.schema !== labelsSchema || value.packet_id !== packet.packet_id || !Array.isArray(value.entries)) throw new Error("标注文件与题包不匹配。");
      const byId = new Map(value.entries.map(row => [row.id, row]));
      const restored = new Map();
      packet.items.forEach(item => {
        const row = byId.get(item.id);
        if (!row) return;
        if (!Array.isArray(row.matches) || row.matches.length !== item.matches.length ||
            row.matches.some((match, i) => match.id !== item.matches[i].id)) throw new Error("已有标注的答案顺序与题包不匹配。");
        restored.set(item.id, row);
      });
      entries = restored;
      $("reviewer").value = typeof value.reviewer_id === "string" ? value.reviewer_id.slice(0, 60) : "";
      say("已恢复本机标注进度；请继续独立审核。");
      render();
    } catch (error) { say(error.message || "标注无法读取。", true); }
  });
  $("scope").addEventListener("change", event => { current().scope = event.target.value; updateProgress(); });
  $("abstention").addEventListener("change", event => { current().abstention = event.target.value; updateProgress(); });
  $("prev").addEventListener("click", () => { if (index > 0) { index--; render(); $("session").scrollIntoView({block: "start"}); } });
  $("next").addEventListener("click", () => { if (index < packet.items.length - 1) { index++; render(); $("session").scrollIntoView({block: "start"}); } });
  $("download").addEventListener("click", () => {
    if (!packet) return;
    const reviewer = $("reviewer").value.trim();
    if (!reviewer) { say("请先填写审核者代号。", true); $("reviewer").focus(); return; }
    const labels = {schema: labelsSchema, packet_id: packet.packet_id, reviewer_id: reviewer,
      entries: packet.items.map(item => entries.get(item.id) || blank(item))};
    const url = URL.createObjectURL(new Blob([JSON.stringify(labels, null, 2)], {type: "application/json"}));
    const link = document.createElement("a");
    link.href = url;
    link.download = `medquad-review-${reviewer.replace(/[^A-Za-z0-9_-]/g, "_")}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    say(`已导出 ${packet.items.filter(complete).length} / ${packet.items.length} 道完整标注；可稍后续填。`);
  });
})();
