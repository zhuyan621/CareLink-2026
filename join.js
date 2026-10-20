/* Join page: crisp bitmap headline and same-origin, consent-based email form. */
(() => {
  "use strict";
  const canvas = document.querySelector("#join-pixel-title");
  const form = document.querySelector("#join-form");
  if (!canvas || !form) return;

  const glyphs = {
    "A":["01110","10001","10001","11111","10001","10001","10001"],
    "C":["01111","10000","10000","10000","10000","10000","01111"],
    "D":["11110","10001","10001","10001","10001","10001","11110"],
    "E":["11111","10000","10000","11110","10000","10000","11111"],
    "G":["01111","10000","10000","10111","10001","10001","01111"],
    "I":["11111","00100","00100","00100","00100","00100","11111"],
    "J":["00111","00010","00010","00010","10010","10010","01100"],
    "K":["10001","10010","10100","11000","10100","10010","10001"],
    "L":["10000","10000","10000","10000","10000","10000","11111"],
    "N":["10001","11001","10101","10101","10011","10001","10001"],
    "O":["01110","10001","10001","10001","10001","10001","01110"],
    "R":["11110","10001","10001","11110","10100","10010","10001"],
    "S":["01111","10000","10000","01110","00001","00001","11110"],
    "U":["10001","10001","10001","10001","10001","10001","01110"],
    "0":["01110","10001","10011","10101","11001","10001","01110"],
    "2":["01110","10001","00001","00010","00100","01000","11111"],
    "5":["11111","10000","11110","00001","00001","10001","01110"],
    "6":["00110","01000","10000","11110","10001","10001","01110"],
    ":":["00000","00100","00100","00000","00100","00100","00000"],
    ".":["00000","00000","00000","00000","00000","01100","01100"],
    "-":["00000","00000","00000","11111","00000","00000","00000"],
    " ":["00000","00000","00000","00000","00000","00000","00000"],
  };
  const lines = ["JOIN US :", "CARELINK", "2025-2026."];
  canvas.width = 72;
  canvas.height = 32;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  lines.forEach((line, lineIndex) => {
    const startX = Math.floor((canvas.width - (line.length * 6 - 1)) / 2);
    for (let i = 0; i < line.length; i++) {
      const glyph = glyphs[line[i]] || glyphs[" "];
      ctx.fillStyle = lineIndex === 2 ? "#e7aa8a" : "#f2f0e9";
      glyph.forEach((row, y) => [...row].forEach((pixel, x) => {
        if (pixel === "1") ctx.fillRect(startX + i * 6 + x, lineIndex * 11 + y, 1, 1);
      }));
    }
  });

  const status = document.querySelector("#join-form-status");
  const submit = document.querySelector("#join-submit");
  const fallback = document.querySelector("#join-mail-fallback");
  const trackSelect = document.querySelector("#join-track");
  const trackPreview = document.querySelector("#join-track-preview");
  const message = document.querySelector("#join-message");
  const messageCount = document.querySelector("#join-message-count");
  const trackNotes = {
    "产品与交互设计": "可先查看交互工作台：场景、执行轨迹与人工接管都需要更清晰的使用体验。",
    "前端与创意技术": "可先操作三维研究图谱：让复杂信息既可感知，也能被精确选点与核对。",
    "后端与 AI 工程": "可先查看证据与边界：运行链路、来源状态与失败降级都需要可靠实现。",
    "照护场景研究": "可先查看六个合成案例：需要更好的问题定义，也需要明确真实场景验证的缺口。",
    "医学与合规咨询": "可先阅读证据与边界：原型用途、人工责任与未验证项必须被明确表达。",
    "机构或项目合作": "可先查看产品概览与证据页：请在介绍中写明合作目标及可验证的范围。",
    "其他合作": "请在介绍中写明你关注的问题、可贡献的经验与希望如何协作。",
  };
  function updateBrief() {
    trackPreview.textContent = trackNotes[trackSelect.value] || "选择一个参与方向后，这里会提示你可以先查看的项目部分。";
    messageCount.textContent = `想法内容 ${message.value.length} / 2000 字`;
  }
  trackSelect.addEventListener("change", updateBrief);
  message.addEventListener("input", updateBrief);
  updateBrief();
  let deliveryReady = false;
  const setStatus = (message, state = "idle") => {
    status.textContent = message;
    status.dataset.state = state;
  };
  async function checkDelivery() {
    try {
      const response = await fetch("/site/join/status", { cache: "no-store" });
      const data = await response.json();
      deliveryReady = Boolean(response.ok && data.ready);
      submit.disabled = !deliveryReady;
      fallback.hidden = deliveryReady;
      setStatus(deliveryReady ? "邮件通道已就绪。提交后会显示服务端回执。" : "邮件通道尚未配置；为避免误报，暂不开放提交。", deliveryReady ? "ready" : "error");
    } catch (_) {
      submit.disabled = true;
      fallback.hidden = false;
      setStatus("无法核验邮件通道，请检查本机服务。", "error");
    }
  }
  checkDelivery();

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!deliveryReady) { setStatus("邮件通道未就绪，未发送任何信息。", "error"); return; }
    const fields = [...form.querySelectorAll("input,select,textarea")];
    fields.forEach((field) => field.removeAttribute("aria-invalid"));
    if (!form.checkValidity()) {
      const first = fields.find((field) => !field.checkValidity());
      if (first) { first.setAttribute("aria-invalid", "true"); first.focus(); first.reportValidity(); }
      setStatus("请补全带 * 的项目并检查邮箱、网址格式。", "error");
      return;
    }
    const values = Object.fromEntries(new FormData(form).entries());
    values.consent = document.querySelector("#join-consent").checked;
    submit.disabled = true;
    setStatus("正在提交，请勿重复发送…");
    try {
      const response = await fetch("/site/join", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values), signal: AbortSignal.timeout(16000),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "提交未成功，请稍后重试。");
      form.reset();
      updateBrief();
      setStatus("邮件服务已接收你的合作意向。我们会通过你留下的邮箱联系；这不代表邮件已抵达收件箱。", "success");
    } catch (error) {
      fallback.hidden = false;
      setStatus(error.name === "TimeoutError" ? "连接超时，无法确认是否已发送，请勿立刻重复提交。" : error.message || "提交失败，未收到服务端回执。", "error");
    } finally {
      submit.disabled = !deliveryReady;
    }
  });
})();
