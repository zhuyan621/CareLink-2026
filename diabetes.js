/* A real, input-driven future-risk calculation, separate from acute screening. */
(() => {
  const workbench = document.querySelector("#workspace-view .workbench");
  if (!workbench) return;
  const section = document.createElement("section");
  section.className = "diabetes-studio";
  section.id = "diabetes-studio";
  section.setAttribute("aria-labelledby", "diabetes-heading");
  section.innerHTML = `
    <div class="diabetes-head"><div><span>LONGITUDINAL RISK / INDEPENDENT MODULE</span><h2 id="diabetes-heading">未来糖尿病风险，<br><em>现在输入，现场计算。</em></h2><p>与上方急性照护交接筛查是两条独立链路。这里计算已发表的 Framingham 8 年新发糖尿病评分；每次结果只来自刚提交的数值，不读取案例库或 medNo.22 问答。</p></div><div class="diabetes-horizon"><b>08</b><span>YEARS / 研究随访时间窗</span></div></div>
    <div class="diabetes-grid"><form id="diabetes-form" class="diabetes-form"><div class="diabetes-panel-top"><span>01 / BASELINE INPUT</span><small>基线信息 · 本页不保存</small></div>
      <div class="diabetes-fields">
        <label>是否已确诊糖尿病？<select name="known_diabetes" required><option value="">请选择</option><option value="false">否</option><option value="true">是（本评分不适用）</option></select></label>
        <label>生物学性别（用于 HDL 阈值）<select name="sex" required><option value="">请选择</option><option value="male">男</option><option value="female">女</option></select></label>
        <label>BMI <small>kg/m²</small><input name="bmi" type="number" min="15" max="55" step="0.1" required placeholder="例如 24.5"></label>
        <label>收缩压 <small>mmHg</small><input name="systolic_bp" type="number" min="70" max="250" step="1" required placeholder="例如 125"></label>
        <label>舒张压 <small>mmHg</small><input name="diastolic_bp" type="number" min="40" max="150" step="1" required placeholder="例如 78"></label>
        <label>空腹血糖 <small>mmol/L</small><input name="fasting_glucose_mmol_l" type="number" min="2.5" max="30" step="0.01" required placeholder="例如 5.4"></label>
        <label>HDL-C <small>mmol/L</small><input name="hdl_mmol_l" type="number" min="0.2" max="4" step="0.01" required placeholder="例如 1.3"></label>
        <label>甘油三酯 <small>mmol/L</small><input name="triglycerides_mmol_l" type="number" min="0.2" max="20" step="0.01" required placeholder="例如 1.5"></label>
      </div><div class="diabetes-checks"><label><input name="parental_diabetes" type="checkbox">父亲或母亲患糖尿病</label><label><input name="bp_medication" type="checkbox">正在接受降压治疗</label></div>
      <button type="submit" id="diabetes-run">计算 8 年风险 <span>↗</span></button><p class="diabetes-unit-note">请填真实测量单位。若已确诊糖尿病，本评分不适用；空腹血糖达到原研究的基线排除阈值时系统会拒绝计算。</p>
    </form><div class="diabetes-result" id="diabetes-result" role="status" aria-live="polite"><div class="diabetes-result-idle"><span>02 / LIVE CALCULATION</span><strong>等待输入。</strong><p>提交后显示实际得分、研究队列对应的 8 年风险区间，以及每个因素的贡献。</p><div class="diabetes-signal" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div></div></div></div>
    <div class="diabetes-boundary"><div><b>DATA ≠ TEMPLATE</b><p>上方 8 年结果是发表规则，不是预置病例；另有公开 NAGALA 随访队列训练的 3 年 MAPFM 研究权重，走独立接口。</p></div><div><b>GENERALIZABILITY</b><p>8 年规则来自美国队列，3 年研究权重来自日本队列；两者均未在中国目标照护人群外部验证或校准。</p></div><div><b>INPUT BOUNDARY</b><p>心率、血氧、体温、呼吸频率未进入这两种未来糖尿病计算；不可声称它们已预测未来糖尿病。</p></div></div>
    <a class="diabetes-source" href="https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/486842" target="_blank" rel="noopener noreferrer">研究来源 · Wilson 等，2007，Table 6 ↗</a>`;
  workbench.insertAdjacentElement("afterend", section);
  if (window.location.hash === "#diabetes-studio") {
    requestAnimationFrame(() => section.scrollIntoView({ block: "start", behavior: "instant" }));
  }
  const flags = document.querySelector("#workspace-view .workspace-hero-flags");
  if (flags) {
    const jump = document.createElement("a");
    jump.className = "diabetes-jump";
    jump.href = "#diabetes-studio";
    jump.textContent = "独立模块 · 未来糖尿病风险 ↘";
    flags.append(jump);
  }

  const form = section.querySelector("#diabetes-form");
  const output = section.querySelector("#diabetes-result");
  const button = section.querySelector("#diabetes-run");
  const idle = output.innerHTML;
  let activeRequest = 0;

  form.addEventListener("input", () => {
    activeRequest += 1;
    output.innerHTML = idle;
  });

  function showError(message) {
    output.replaceChildren();
    const block = document.createElement("div");
    block.className = "diabetes-error";
    const label = document.createElement("span");
    label.textContent = "CALCULATION STOPPED / 未生成风险";
    const body = document.createElement("p");
    body.textContent = message;
    block.append(label, body);
    output.append(block);
  }

  function showResult(data) {
    output.replaceChildren();
    const heading = document.createElement("div");
    heading.className = "diabetes-result-heading";
    heading.innerHTML = `<span>02 / ACTUAL CALCULATION</span><small>FRAMINGHAM OFFSPRING · TABLE 6</small>`;
    const hero = document.createElement("div");
    hero.className = "diabetes-risk-hero";
    const label = document.createElement("span");
    label.textContent = "研究队列 8 年风险";
    const value = document.createElement("strong");
    value.textContent = data.risk_text;
    const score = document.createElement("small");
    score.textContent = `评分 ${data.score} 分 · 不是个人诊断`;
    hero.append(label, value, score);
    const meter = document.createElement("div");
    meter.className = "diabetes-meter";
    meter.setAttribute("aria-label", `风险评分 ${data.score} 分`);
    const fill = document.createElement("span");
    fill.style.width = `${Math.min(100, data.score / 30 * 100)}%`;
    meter.append(fill);
    const factors = document.createElement("div");
    factors.className = "diabetes-factors";
    const title = document.createElement("h3");
    title.textContent = "逐项计分 / 可复核";
    factors.append(title);
    data.factors.forEach((item) => {
      const row = document.createElement("div");
      const name = document.createElement("span");
      name.textContent = item.name;
      const points = document.createElement("b");
      points.textContent = `+${item.points}`;
      if (item.points) row.className = "is-positive";
      row.append(name, points);
      factors.append(row);
    });
    const note = document.createElement("p");
    note.className = "diabetes-result-note";
    note.textContent = "仅代表发表研究中相同评分群体的估计。该模型未在 CareLink 目标中国照护人群校准，不能据此进行诊断或治疗决定。";
    output.append(heading, hero, meter, factors, note);
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const serial = ++activeRequest;
    const values = new FormData(form);
    const payload = {
      known_diabetes: values.get("known_diabetes") === "true",
      sex: values.get("sex"),
      bmi: Number(values.get("bmi")),
      systolic_bp: Number(values.get("systolic_bp")),
      diastolic_bp: Number(values.get("diastolic_bp")),
      fasting_glucose_mmol_l: Number(values.get("fasting_glucose_mmol_l")),
      hdl_mmol_l: Number(values.get("hdl_mmol_l")),
      triglycerides_mmol_l: Number(values.get("triglycerides_mmol_l")),
      parental_diabetes: values.has("parental_diabetes"),
      bp_medication: values.has("bp_medication"),
    };
    button.disabled = true;
    button.firstChild.textContent = "正在计算… ";
    try {
      const response = await fetch("/risk/diabetes-8y", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (serial !== activeRequest) return;
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "输入不符合发表模型的要求。请核对数值和单位。");
      if (data.model !== "framingham_offspring_table_6" || data.horizon_years !== 8 || data.system_extension !== "mapfm_chronic_risk_v2" || data.original_mapfm_model_used_for_this_probability !== false) throw new Error("后端模型版本不匹配，结果未展示。");
      showResult(data);
      window.dispatchEvent(new Event("careguard:chronic-risk-computed"));
    } catch (error) {
      if (serial === activeRequest) showError(error.message || "无法连接本地计算服务。");
    } finally {
      button.disabled = false;
      button.firstChild.textContent = "计算 8 年风险 ";
    }
  });
})();
