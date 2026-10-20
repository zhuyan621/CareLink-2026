/* Full-source MedQuAD retrieval; source answers, no generative diagnosis. */
(() => {
  const anchor = document.querySelector("#prospective-neural-lab") || document.querySelector("#diabetes-studio");
  if (!anchor) return;
  const section = document.createElement("section");
  section.className = "medquad-studio";
  section.id = "medquad-studio";
  section.innerHTML = `
    <div class="medquad-atmosphere" aria-hidden="true"><i></i><i></i><i></i></div>
    <div class="medquad-inner">
      <div class="medquad-header"><span>03 / MEDICAL KNOWLEDGE · COMPLETE SOURCE AUDIT</span><div class="medquad-title-line"><h2>让问答，<br><em>回到来源。</em></h2><div class="medquad-bigtype" aria-hidden="true">MQ<span>47k</span></div></div><p>使用官方 MedQuAD 全量 XML 逐条核查，拟合英文医学问答检索模型。输入英文问题，现场检索原始答案与 NIH 来源链接；它不推算未来发病，也不替代诊断。</p></div>
      <div class="medquad-counts"><div><b id="mq-all">—</b><span>全部问题 · 参与词汇拟合</span></div><div><b id="mq-trained">—</b><span>有答案 · 进入回答索引</span></div><div><b id="mq-empty">—</b><span>官方移除 / 空答案 · 未伪造</span></div><div><b id="mq-state">读取中</b><span>本机模型与数据校验</span></div></div>
      <div class="medquad-console"><form id="mq-form"><div class="medquad-panel-top"><span>01 / ASK THE SOURCE</span><small>ENGLISH · NO PATIENT DATA</small></div><label for="mq-query">输入英文医学知识问题</label><textarea id="mq-query" minlength="5" maxlength="500" required placeholder="What is diabetes?" spellcheck="false"></textarea><div class="medquad-form-foot"><span>请勿输入姓名、病历号或可识别个人信息。</span><button type="submit" disabled>检索原始问答 ↗</button></div></form><div class="medquad-results" id="mq-results" role="status" aria-live="polite"><div class="medquad-results-head"><span>02 / ATTRIBUTED ANSWERS</span><b>等待输入</b></div><p class="medquad-empty">这里只显示与问题匹配的原始来源回答。没有足够匹配时明确拒答，不生成编造内容。</p></div></div>
      <div class="medquad-bottom"><p>官方 README 宣称 47,457 对；本机下载的 master 快照逐 XML 解析为 47,441 对，其中 31,034 对答案为空。全部问题参与词汇与 IDF 拟合；16,407 条有原始答案的记录进入回答索引。检索融合词面模型与预训练语义编码器；后者并未在 MedQuAD 上微调，也不是 MAPFM。<span id="mq-evaluation">独立问法测试加载中。</span><span id="mq-robustness"></span><span id="mq-mediqa"></span><span id="mq-latest"></span><span id="mq-blind"></span>这些是部分标注的检索命中率，不是医学准确率或临床验证。</p><div class="medquad-bottom-links"><a class="medquad-review-jump" href="#review-desk">继续在工作台进行医学问答盲评 ↘</a><a href="https://github.com/abachaa/MEDIQA2019/tree/master/MEDIQA_Task3_QA" target="_blank" rel="noopener noreferrer">官方 MEDIQA 2019 问答集 ↗</a></div></div>
    </div>`;
  anchor.insertAdjacentElement("afterend", section);
  const auditCopy = section.querySelector(".medquad-bottom > p");
  if (auditCopy) {
    const auditDetails = document.createElement("details");
    auditDetails.className = "medquad-audit-details";
    const summary = document.createElement("summary");
    summary.textContent = "查看训练数据与泛化核验明细";
    auditCopy.replaceWith(auditDetails);
    auditDetails.append(summary, auditCopy);
  }
  const flags = document.querySelector("#workspace-view .workspace-hero-flags");
  if (flags) {
    const link = document.createElement("a");
    link.href = "#medquad-studio";
    link.className = "medquad-jump";
    link.textContent = "MedQuAD · 全量来源问答 ↘";
    flags.append(link);
  }
  const form = section.querySelector("#mq-form");
  const button = form.querySelector("button");
  const results = section.querySelector("#mq-results");
  const state = section.querySelector("#mq-state");
  fetch("/mapfm/medquad-qa/status", {cache: "no-store"}).then(r => r.json()).then(data => {
    if (!data.ready) throw new Error(data.reason || "模型不可用");
    section.querySelector("#mq-all").textContent = data.qa_pairs_total.toLocaleString();
    if (data.vocabulary_fitted_questions !== data.qa_pairs_total) throw new Error("全量问题拟合数量不匹配");
    section.querySelector("#mq-trained").textContent = data.indexed_pairs.toLocaleString();
    section.querySelector("#mq-empty").textContent = data.answerless_pairs.toLocaleString();
    state.textContent = "HYBRID READY";
    const evaluation = section.querySelector("#mq-evaluation");
    if (data.external_evaluable_questions && data.known_relevant_at_3_lexical != null && data.known_relevant_at_3_hybrid != null) {
      evaluation.textContent = `独立 LiveQA 中 ${data.external_evaluable_questions} 道可对齐题目、两种问法的已标注相关答案 Top-3 命中率：${(100 * data.known_relevant_at_3_lexical).toFixed(1)}% → ${(100 * data.known_relevant_at_3_hybrid).toFixed(1)}%（仅部分答案有标签）。`;
    }
    if (data.natural_query_holdout_count && data.natural_query_known_answer_at_3 != null) {
      section.querySelector("#mq-robustness").textContent = `另用 ${data.natural_query_holdout_count} 条封存自然问法验收：当前版已知原文答案 Top-3 命中率 ${(100 * data.natural_query_known_answer_at_3).toFixed(1)}%；一项开发集表现更好的排序改动在封存集退步，已拒绝上线。`;
    }
    if (data.mediqa2019_evaluable_questions && data.mediqa2019_baseline_known_answer_at_3 != null) {
      section.querySelector("#mq-mediqa").textContent = `官方 MEDIQA 2019 严格对齐的 ${data.mediqa2019_evaluable_questions} 道题中，当前版已知答案 Top-1 / Top-3 为 ${(100 * data.mediqa2019_baseline_known_answer_at_1).toFixed(1)}% / ${(100 * data.mediqa2019_baseline_known_answer_at_3).toFixed(1)}%；答案字段候选虽提高 Top-3，但使 Top-1 退步，未部署。`;
    }
    if (data.latest_generalization_baseline_retained && data.latest_generalization_candidates_rejected === 3) {
      section.querySelector("#mq-latest").textContent = ` ${data.latest_generalization_audit_date} 的 RQE / MeQSum 三项泛化候选均未通过回归门槛，线上仍为原版；本轮没有证实泛化提升。`;
    }
    if (data.blind_evaluation_locked_questions === 250 && data.blind_evaluation_development_questions === 100) {
      section.querySelector("#mq-blind").textContent = " 新建的 100 题开发集与 250 题锁定用药问答集等待医学人员双人审核；尚无新的质量分数。";
    }
    button.disabled = false;
  }).catch(error => { state.textContent = "未就绪"; results.querySelector(".medquad-empty").textContent = error.message; });
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (!form.reportValidity() || button.disabled) return;
    const question = section.querySelector("#mq-query").value.trim();
    button.disabled = true;
    results.replaceChildren();
    const working = document.createElement("p"); working.className = "medquad-empty"; working.textContent = "正在本机检索有来源的答案…"; results.append(working);
    try {
      const response = await fetch("/mapfm/medquad-qa/ask", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({question, top_k: 3})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "检索失败");
      results.replaceChildren();
      const head = document.createElement("div"); head.className = "medquad-results-head";
      const label = document.createElement("span"); label.textContent = "02 / ATTRIBUTED ANSWERS";
      const count = document.createElement("b"); count.textContent = data.matches.length ? `${data.matches.length} 条来源` : "拒答";
      head.append(label, count); results.append(head);
      if (!data.matches.length) { const p = document.createElement("p"); p.className = "medquad-empty"; p.textContent = "没有达到检索阈值的答案。请换用英文疾病或症状关键词；系统不会编造回答。"; results.append(p); return; }
      data.matches.forEach((item, index) => {
        const card = document.createElement("article");
        const small = document.createElement("span"); small.textContent = `${String(index + 1).padStart(2, "0")} / ${item.source} · 融合检索相关度 ${item.match_score.toFixed(2)}（非医学置信度）`;
        const title = document.createElement("h3"); title.textContent = item.question;
        const answer = document.createElement("p"); answer.textContent = item.answer;
        card.append(small, title, answer);
        if (/^https:\/\//.test(item.source_url)) { const source = document.createElement("a"); source.href = item.source_url; source.target = "_blank"; source.rel = "noopener noreferrer"; source.textContent = "查看原始来源 ↗"; card.append(source); }
        results.append(card);
      });
    } catch (error) { results.replaceChildren(); const p = document.createElement("p"); p.className = "medquad-empty"; p.textContent = error.message || "本机接口不可用"; results.append(p); }
    finally { button.disabled = false; }
  });
})();
