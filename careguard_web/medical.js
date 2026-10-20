/* Decorative observation rhythm. This is not sampled ECG, sensor input, or a diagnosis. */
(() => {
  "use strict";
  const canvases = [...document.querySelectorAll(".medical-wave")];
  if (!canvases.length) return;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const fields = canvases.map((canvas) => ({ canvas, ctx: canvas.getContext("2d"), visible: false, width: 0, height: 0 }));
  let enabled = !reducedMotion.matches;
  let frame = 0;

  function gaussian(x, center, spread) {
    const distance = (x - center) / spread;
    return Math.exp(-distance * distance);
  }

  function rhythm(position) {
    const phase = ((position % 1) + 1) % 1;
    return Math.sin(phase * Math.PI * 2) * 0.016
      - gaussian(phase, 0.17, 0.029) * 0.085
      + gaussian(phase, 0.277, 0.011) * 0.19
      - gaussian(phase, 0.303, 0.009) * 0.56
      + gaussian(phase, 0.337, 0.018) * 0.13
      - gaussian(phase, 0.63, 0.067) * 0.085;
  }

  function size(field) {
    const rect = field.canvas.getBoundingClientRect();
    const width = Math.round(rect.width);
    const height = Math.round(rect.height);
    if (!width || !height) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    if (width === field.width && height === field.height && field.canvas.width === Math.round(width * ratio)) return;
    field.width = width;
    field.height = height;
    field.canvas.width = Math.round(width * ratio);
    field.canvas.height = Math.round(height * ratio);
    field.ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  }

  function draw(field, now) {
    size(field);
    const { canvas, ctx, width: w, height: h } = field;
    if (!w || !h) return;
    ctx.clearRect(0, 0, w, h);
    ctx.save();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(212, 230, 223, .095)";
    const step = h < 90 ? 22 : 30;
    for (let x = 0; x <= w; x += step) {
      ctx.beginPath(); ctx.moveTo(x + .5, 0); ctx.lineTo(x + .5, h); ctx.stroke();
    }
    for (let y = 0; y <= h; y += step) {
      ctx.beginPath(); ctx.moveTo(0, y + .5); ctx.lineTo(w, y + .5); ctx.stroke();
    }
    const baseline = h * .56;
    ctx.strokeStyle = "rgba(221, 233, 223, .17)";
    ctx.beginPath(); ctx.moveTo(0, baseline + .5); ctx.lineTo(w, baseline + .5); ctx.stroke();

    const rate = Math.max(48, Math.min(150, Number(canvas.dataset.medicalRate) || 72));
    const period = Math.max(92, Math.min(170, 160 - (rate - 60) * .58));
    const shift = enabled ? (now * .028) % period : 0;
    const amplitude = h * (h < 90 ? .7 : .65);
    ctx.beginPath();
    for (let x = 0; x <= w + 2; x += 2) {
      const y = baseline + rhythm((x + shift) / period) * amplitude;
      if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = getComputedStyle(canvas).getPropertyValue("--medical-line").trim() || "#bfe0cc";
    ctx.lineWidth = h < 90 ? 1.45 : 1.9;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.stroke();

    const scanX = enabled ? (now * .055) % w : w * .63;
    const band = ctx.createLinearGradient(scanX - 45, 0, scanX + 20, 0);
    band.addColorStop(0, "rgba(223, 241, 230, 0)");
    band.addColorStop(.77, "rgba(223, 241, 230, .055)");
    band.addColorStop(1, "rgba(223, 241, 230, 0)");
    ctx.fillStyle = band;
    ctx.fillRect(Math.max(0, scanX - 45), 0, 65, h);
    ctx.fillStyle = "rgba(228, 238, 231, .72)";
    ctx.fillRect(Math.round(scanX), 0, 1, 7);
    ctx.fillRect(Math.round(scanX), h - 7, 1, 7);
    ctx.restore();
  }

  function schedule() {
    if (frame || !enabled || document.hidden || !fields.some((field) => field.visible)) return;
    frame = requestAnimationFrame(tick);
  }

  function tick(now) {
    frame = 0;
    if (!enabled || document.hidden) return;
    for (const field of fields) if (field.visible) draw(field, now);
    schedule();
  }

  function syncMotion() {
    const toggle = document.querySelector("[data-motion-toggle]");
    enabled = !reducedMotion.matches && (!toggle || toggle.getAttribute("aria-pressed") === "true");
    if (!enabled && frame) { cancelAnimationFrame(frame); frame = 0; }
    for (const field of fields) draw(field, enabled ? performance.now() : 0);
    schedule();
  }

  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      const field = fields.find((item) => item.canvas === entry.target);
      if (field) { field.visible = entry.isIntersecting; if (field.visible) draw(field, performance.now()); }
    }
    schedule();
  }, { rootMargin: "60px" });
  fields.forEach((field) => observer.observe(field.canvas));
  const resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const field = fields.find((item) => item.canvas === entry.target);
      if (field) draw(field, performance.now());
    }
  });
  fields.forEach((field) => resizeObserver.observe(field.canvas));
  document.querySelectorAll("[data-motion-toggle]").forEach((button) => button.addEventListener("click", syncMotion));
  reducedMotion.addEventListener("change", syncMotion);
  document.addEventListener("visibilitychange", schedule);
  document.addEventListener("careguard:viewchange", () => { fields.forEach((field) => draw(field, performance.now())); schedule(); });
  syncMotion();
})();
