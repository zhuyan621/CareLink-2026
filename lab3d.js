/* Canvas perspective scatterplots: a true rotatable 3D projection, no remote libraries. */
(() => {
  "use strict";
  const data = window.CareGuardLabData;
  if (!data) return;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const $ = (selector) => document.querySelector(selector);
  const node = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = String(text);
    return element;
  };
  const hash = (value) => [...String(value)].reduce((seed, char) => Math.imul(seed ^ char.charCodeAt(0), 16777619) >>> 0, 2166136261);
  const random = (seed) => {
    let state = seed >>> 0;
    return () => ((state = Math.imul(state, 1664525) + 1013904223 >>> 0) / 4294967296);
  };

  const configs = {
    observation: { points: data.observationPoints(), ranges: [[80, 126], [88, 98], [16, 29]], axes: ["HR", "SpO₂", "RR"], defaultId: "chest-0-0-0" },
    gate: { points: data.gatePoints(), ranges: [[0, 4], [0, 1], [0, 7]], axes: ["冲突", "急性", "门控"], defaultId: "gate-0-0-0" },
    source: { points: data.sourcePoints(), ranges: [[-0.25, 3.25], [-0.4, 4.4], [-0.2, 3.2]], axes: ["层级", "类型", "范围"], defaultId: "module-design" },
  };

  class Scatter3D {
    constructor(key, config) {
      this.key = key;
      this.points = config.points;
      this.ranges = config.ranges;
      this.axes = config.axes;
      this.canvas = $(`#lab-canvas-${key}`);
      this.ctx = this.canvas.getContext("2d");
      this.selectBox = $(`#lab-select-${key}`);
      this.detail = $(`#lab-detail-${key}`);
      this.count = $(`#lab-count-${key}`);
      this.primary = $(`#lab-primary-${key}`);
      this.exportPanel = node("div", "lab-export-preview");
      this.exportPanel.hidden = true;
      this.exportNote = node("p");
      this.exportText = node("textarea");
      this.exportText.readOnly = true;
      this.exportText.rows = 6;
      this.exportText.setAttribute("aria-label", `${key} CSV 数据预览，可选择并复制`);
      this.exportPanel.append(this.exportNote, this.exportText);
      this.primary.closest(".lab-action-row").after(this.exportPanel);
      this.filter = "all";
      this.selected = this.points.find((point) => point.id === config.defaultId) || this.points[0];
      this.visiblePoints = this.points.slice();
      this.motes = this.makeMotes();
      this.visibleMotes = this.motes;
      this.edges = this.makeEdges();
      this.phase = 0;
      this.density = 100;
      const spaceRandom = random(hash(`ambient-${key}`));
      this.ambient = Array.from({ length: 240 }, () => ({
        coordinates: [(spaceRandom() - .5) * 3.2, (spaceRandom() - .5) * 3.1, (spaceRandom() - .5) * 3.2],
        phase: spaceRandom() * 7, alpha: .13 + spaceRandom() * .34, radius: .45 + spaceRandom() * 1.1,
      }));
      this.projected = [];
      this.yaw = -0.68; this.pitch = 0.33; this.zoom = 1;
      this.playing = !reducedMotion.matches;
      this.hovered = null; this.drag = null; this.intersecting = false;
      this.width = 0; this.height = 0;
      this.populateSelect(); this.bind(); this.updateDetail(); this.updateCameraLabel();
      if ("ResizeObserver" in window) new ResizeObserver(() => this.resize()).observe(this.canvas);
    }

    populateSelect() {
      this.selectBox.replaceChildren(...this.visiblePoints.map((point) => {
        const option = node("option", "", this.optionLabel(point));
        option.value = point.id; return option;
      }));
      if (this.selected && this.visiblePoints.includes(this.selected)) this.selectBox.value = this.selected.id;
    }

    optionLabel(point) {
      if (this.key === "observation") return `${point.title} · ${point.heartRate} / ${point.spo2}% / ${point.respiratoryRate}`;
      if (this.key === "gate") return `${point.code} · 冲突${point.conflicts} / 急性${Number(point.acute)} / 门控${point.gateBits}`;
      return point.title;
    }

    bind() {
      this.selectBox.addEventListener("change", () => this.select(this.points.find((point) => point.id === this.selectBox.value)));
      this.primary.addEventListener("click", () => this.runPrimary());
      this.canvas.addEventListener("pointerdown", (event) => {
        this.drag = { x: event.clientX, y: event.clientY, moved: false };
        this.canvas.setPointerCapture(event.pointerId);
      });
      this.canvas.addEventListener("pointermove", (event) => {
        if (this.drag) {
          const dx = event.clientX - this.drag.x, dy = event.clientY - this.drag.y;
          if (Math.abs(dx) + Math.abs(dy) > 3) this.drag.moved = true;
          this.yaw += dx * 0.008; this.pitch = Math.max(-1.25, Math.min(1.25, this.pitch + dy * 0.008));
          this.drag.x = event.clientX; this.drag.y = event.clientY;
          this.playing = false; this.updateCameraLabel(); this.draw();
        } else {
          this.hovered = this.pick(event);
          this.canvas.style.cursor = this.hovered ? "pointer" : "grab";
          this.canvas.title = this.hovered ? this.optionLabel(this.hovered) : "拖动旋转；点选散点查看详情";
          this.draw();
        }
      });
      this.canvas.addEventListener("pointerup", (event) => {
        if (this.drag && !this.drag.moved) this.select(this.pick(event));
        this.drag = null;
      });
      this.canvas.addEventListener("pointercancel", () => { this.drag = null; });
      this.canvas.addEventListener("pointerleave", () => { if (!this.drag) { this.hovered = null; this.draw(); } });
      this.canvas.addEventListener("wheel", (event) => {
        event.preventDefault(); this.zoomBy(event.deltaY < 0 ? 0.11 : -0.11);
      }, { passive: false });
      this.canvas.addEventListener("keydown", (event) => {
        if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "+", "=", "-", "Enter"].includes(event.key)) event.preventDefault();
        if (event.key === "ArrowLeft") this.yaw -= 0.13;
        if (event.key === "ArrowRight") this.yaw += 0.13;
        if (event.key === "ArrowUp") this.pitch = Math.min(1.25, this.pitch + 0.13);
        if (event.key === "ArrowDown") this.pitch = Math.max(-1.25, this.pitch - 0.13);
        if (event.key === "+" || event.key === "=") this.zoomBy(0.11);
        if (event.key === "-") this.zoomBy(-0.11);
        if (event.key === "Enter") this.select(this.hovered || this.selected);
        this.playing = false; this.updateCameraLabel(); this.draw();
      });
    }

    resize() {
      const rect = this.canvas.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.width = rect.width; this.height = rect.height;
      this.canvas.width = Math.round(rect.width * dpr); this.canvas.height = Math.round(rect.height * dpr);
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.draw();
    }

    normalize(point) {
      return ["x", "y", "z"].map((axis, index) => {
        const [min, max] = this.ranges[index];
        return ((point[`plot${axis.toUpperCase()}`] ?? point[axis]) - min) / (max - min) * 2 - 1;
      });
    }

    makeMotes() {
      const count = this.key === "source" ? 72 : 23;
      return this.points.flatMap((point) => {
        const seeded = random(hash(point.id));
        const base = this.normalize(point);
        return Array.from({ length: count }, (_, index) => {
          const azimuth = seeded() * Math.PI * 2;
          const elevation = (seeded() - .5) * Math.PI;
          const radius = .045 + Math.pow(seeded(), .7) * (this.key === "source" ? .32 : .19);
          return {
            point, base, index, angle: azimuth, elevation, radius,
            phase: seeded() * Math.PI * 2, size: .55 + seeded() * 1.6,
            alpha: .16 + seeded() * .55,
          };
        });
      });
    }

    makeEdges() {
      if (this.key === "source") return [];
      const edges = [];
      for (let i = 0; i < this.points.length; i++) for (let j = i + 1; j < this.points.length; j++) {
        const a = this.points[i], b = this.points[j];
        if (this.key === "observation") {
          if (a.caseId !== b.caseId) continue;
          const delta = [Math.abs(a.heartRate - b.heartRate) / 12, Math.abs(a.spo2 - b.spo2) / 3, Math.abs(a.respiratoryRate - b.respiratoryRate) / 4];
          if (delta.reduce((sum, value) => sum + value, 0) !== 1) continue;
        } else {
          const changes = [Math.abs(a.conflicts - b.conflicts), Number(a.acute !== b.acute), Number(a.highRisk !== b.highRisk), Number(a.hitl !== b.hitl), Number(a.consensusApproved !== b.consensusApproved)];
          if (changes.reduce((sum, value) => sum + value, 0) !== 1) continue;
        }
        edges.push([a, b]);
      }
      return edges;
    }

    project(coordinates) {
      const [x, y, z] = coordinates;
      const cy = Math.cos(this.yaw), sy = Math.sin(this.yaw);
      const cp = Math.cos(this.pitch), sp = Math.sin(this.pitch);
      const rx = x * cy + z * sy;
      const rz = -x * sy + z * cy;
      const ry = y * cp - rz * sp;
      const depth = y * sp + rz * cp;
      const perspective = 3.8 / (4.5 - depth * 0.55);
      const scale = Math.min(this.width, this.height) * 0.31 * this.zoom * perspective;
      return { x: this.width * 0.5 + rx * scale, y: this.height * 0.53 - ry * scale, depth };
    }

    pick(event) {
      const rect = this.canvas.getBoundingClientRect();
      const x = event.clientX - rect.left, y = event.clientY - rect.top;
      return this.projected.filter((entry) => Math.hypot(entry.x - x, entry.y - y) < 13)
        .sort((a, b) => b.depth - a.depth)[0]?.point || null;
    }

    select(point) {
      if (!point) return;
      this.selected = point; this.selectBox.value = point.id;
      this.updateDetail(); this.draw();
    }

    setFilter(filter) {
      this.filter = filter; this.updateVisible();
    }

    updateVisible() {
      const maxOrder = Number($("#lab-range-input").value);
      const zeroOnly = $("#lab-zero-conflict").checked;
      this.visiblePoints = this.points.filter((point) => {
        if (this.filter !== "all" && point.group !== this.filter) return false;
        if (this.key === "observation" && Object.values(point.offsets).filter((value) => value !== 0).length > maxOrder) return false;
        if (this.key === "gate" && zeroOnly && point.conflicts !== 0) return false;
        return true;
      });
      const visible = new Set(this.visiblePoints);
      this.visibleMotes = this.motes.filter((mote) => visible.has(mote.point));
      if (!this.visiblePoints.includes(this.selected)) this.selected = this.visiblePoints[0] || null;
      this.count.textContent = `${this.visiblePoints.length} 个${this.key === "gate" ? "状态" : this.key === "source" ? "节点" : "点"}`;
      this.populateSelect(); this.updateDetail(); this.draw();
    }

    zoomBy(delta) { this.zoom = Math.max(0.63, Math.min(1.8, this.zoom + delta)); this.draw(); }
    resetCamera() { this.yaw = -0.68; this.pitch = 0.33; this.zoom = 1; this.draw(); }
    toggleMotion() { this.playing = !this.playing && !reducedMotion.matches; this.updateCameraLabel(); }
    updateCameraLabel() { $(`[data-lab-camera="${this.key}:toggle"]`).textContent = this.playing ? "暂停粒子流" : "开启粒子流"; }

    draw() {
      if (!this.width || !this.height || $("#lab-view").hidden) return;
      const ctx = this.ctx, w = this.width, h = this.height;
      ctx.clearRect(0, 0, w, h);
      const bg = ctx.createRadialGradient(w * 0.52, h * 0.43, 8, w * 0.5, h * 0.5, h * 0.88);
      bg.addColorStop(0, this.key === "gate" ? "#292538" : this.key === "source" ? "#193139" : "#282d3d");
      bg.addColorStop(.54, "#171a25"); bg.addColorStop(1, "#0d111b");
      ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
      const ambientColor = this.key === "source" ? "#a4d9ce" : this.key === "gate" ? "#c1a5da" : "#e4bdd6";
      for (const dust of this.ambient) {
        const p = this.project(dust.coordinates);
        if (p.x < 0 || p.x > w || p.y < 0 || p.y > h) continue;
        const shimmer = this.playing ? .76 + .24 * Math.sin(this.phase * 1.6 + dust.phase) : 1;
        ctx.globalAlpha = dust.alpha * shimmer;
        ctx.fillStyle = ambientColor;
        ctx.fillRect(p.x, p.y, dust.radius, dust.radius);
      }
      ctx.globalAlpha = 1;
      ctx.save(); ctx.lineWidth = 1;
      for (let i = 0; i <= 4; i++) {
        const t = -1 + i * 0.5;
        this.segment([-1, -1, t], [1, -1, t], "#c5b5d21b");
        this.segment([t, -1, -1], [t, -1, 1], "#c5b5d21b");
      }
      for (const y of [-1, 1]) for (const z of [-1, 1]) this.segment([-1, y, z], [1, y, z], "#c9bdda35");
      for (const x of [-1, 1]) for (const z of [-1, 1]) this.segment([x, -1, z], [x, 1, z], "#c9bdda35");
      for (const x of [-1, 1]) for (const y of [-1, 1]) this.segment([x, y, -1], [x, y, 1], "#c9bdda35");
      [[this.axes[0], [1.22, -1, -1]], [this.axes[1], [-1, 1.2, -1]], [this.axes[2], [-1, -1, 1.22]]].forEach(([label, pos]) => {
        const p = this.project(pos); ctx.fillStyle = "#d6d2e7"; ctx.font = "700 12px system-ui, sans-serif"; ctx.fillText(label, p.x - 7, p.y);
      });
      ctx.restore();

      const visible = new Set(this.visiblePoints);
      ctx.save(); ctx.lineWidth = .75;
      for (const [a, b] of this.edges) {
        if (!visible.has(a) || !visible.has(b)) continue;
        const p = this.project(this.normalize(a)), q = this.project(this.normalize(b));
        const highlight = a === this.selected || b === this.selected;
        ctx.strokeStyle = highlight ? "#e1b8c459" : this.key === "gate" ? "#afa7d02a" : "#a6b3d626";
        ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
      }
      ctx.restore();

      ctx.save(); ctx.globalCompositeOperation = "screen";
      const stride = Math.ceil(100 / this.density) * (w < 560 ? 2 : 1);
      for (let i = 0; i < this.visibleMotes.length; i += stride) {
        const mote = this.visibleMotes[i];
        const drift = this.playing ? this.phase * (.28 + mote.index % 5 * .055) : 0;
        const angle = mote.angle + drift;
        const orbit = mote.radius * (1 + .075 * Math.sin(this.phase + mote.phase));
        const p = this.project([
          mote.base[0] + Math.cos(angle) * Math.cos(mote.elevation) * orbit,
          mote.base[1] + Math.sin(mote.elevation + drift * .23) * orbit,
          mote.base[2] + Math.sin(angle) * Math.cos(mote.elevation) * orbit,
        ]);
        if (p.x < 0 || p.x > w || p.y < 0 || p.y > h) continue;
        const isSelected = mote.point === this.selected;
        ctx.globalAlpha = mote.alpha * (isSelected ? .94 : .55) * Math.max(.55, Math.min(1, .84 + p.depth * .08));
        ctx.fillStyle = mote.point.color;
        const size = mote.size * (isSelected ? 1.25 : 1);
        ctx.fillRect(p.x, p.y, size, size);
      }
      ctx.restore();

      this.projected = this.visiblePoints.map((point) => ({ point, ...this.project(this.normalize(point)) }))
        .sort((a, b) => a.depth - b.depth);
      for (const entry of this.projected) {
        const radius = 3.1 + (entry.depth + 1.7) * 0.72;
        const selected = entry.point === this.selected, hovered = entry.point === this.hovered;
        ctx.globalAlpha = Math.max(0.62, Math.min(1, 0.8 + entry.depth * 0.08));
        ctx.fillStyle = entry.point.color;
        ctx.shadowBlur = selected ? 17 : hovered ? 10 : 4;
        ctx.shadowColor = entry.point.color;
        ctx.beginPath(); ctx.arc(entry.x, entry.y, selected ? radius + 2 : hovered ? radius + 1.2 : radius, 0, Math.PI * 2); ctx.fill();
        if (selected) { ctx.shadowBlur = 0; ctx.strokeStyle = "#f1edf5"; ctx.lineWidth = 1.15; ctx.beginPath(); ctx.arc(entry.x, entry.y, radius + 8, 0, Math.PI * 2); ctx.stroke(); }
      }
      ctx.globalAlpha = 1; ctx.shadowBlur = 0;
      ctx.fillStyle = "#c9c6d66e"; ctx.font = "italic 13px Georgia, serif";
      ctx.fillText("CARELINK / DATA CENTERS + VISUAL PARTICLES", 18, h - 19);
    }

    segment(a, b, color) {
      const p = this.project(a), q = this.project(b);
      this.ctx.strokeStyle = color; this.ctx.beginPath(); this.ctx.moveTo(p.x, p.y); this.ctx.lineTo(q.x, q.y); this.ctx.stroke();
    }

    updateDetail() {
      const point = this.selected;
      this.detail.replaceChildren();
      if (!point) {
        if (this.key === "observation") {
          for (const id of ["lab-monitor-hr", "lab-monitor-spo2", "lab-monitor-rr"]) document.getElementById(id).textContent = "—";
        }
        this.detail.append(node("p", "", "当前筛选下没有点。")); this.primary.disabled = true; return;
      }
      this.primary.disabled = false;
      if (this.key === "observation") {
        document.getElementById("lab-monitor-hr").textContent = String(point.heartRate);
        document.getElementById("lab-monitor-spo2").textContent = `${point.spo2}%`;
        document.getElementById("lab-monitor-rr").textContent = String(point.respiratoryRate);
        document.getElementById("lab-medical-wave").dataset.medicalRate = point.heartRate;
        this.detail.append(node("span", "lab-detail-overline", point.central ? "BASE / 原始合成案例中心点" : "PERTURBATION / 合成扰动点"));
        this.detail.append(node("h3", "", point.title));
        this.detail.append(node("p", "", `心率 ${point.heartRate} 次/分 · 血氧 ${point.spo2}% · 呼吸 ${point.respiratoryRate} 次/分`));
        this.detail.append(node("small", "", `相对中心偏移：心率 ${point.offsets.heartRate >= 0 ? "+" : ""}${point.offsets.heartRate}，血氧 ${point.offsets.spo2 >= 0 ? "+" : ""}${point.offsets.spo2}，呼吸 ${point.offsets.respiratoryRate >= 0 ? "+" : ""}${point.offsets.respiratoryRate}。载入后仍需手动运行，不能把这个点当作筛查结果。`));
        this.primary.textContent = "载入此合成变体 ↗";
      } else if (this.key === "gate") {
        this.detail.append(node("span", "lab-detail-overline", "EXACT CODE BRANCH / 规则状态"));
        this.detail.append(node("h3", "", `${point.code} · ${point.code === "P1" ? "立即人工复核" : point.code === "P2" ? "优先人工复核" : "常规复核"}`));
        this.detail.append(node("p", "", `严重冲突 ${point.conflicts} · 急性线索 ${point.acute ? "是" : "否"} · 强制高风险 ${point.highRisk ? "是" : "否"}`));
        this.detail.append(node("small", "", `人工触发 ${point.hitl ? "是" : "否"}；共识 ${point.consensusApproved ? "通过" : "未通过"}；门控编码 ${point.gateBits}。该点由代码条件枚举，不是一次模型运行。`));
        this.primary.textContent = "查看人工门控证据 ↗";
      } else {
        this.detail.append(node("span", "lab-detail-overline", `${point.group.toUpperCase()} / PROJECT SOURCE`));
        if (point.image) { const image = node("img", "lab-detail-image"); image.src = point.image; image.alt = point.title; this.detail.append(image); }
        this.detail.append(node("h3", "", point.title));
        this.detail.append(node("p", "", `来源：${point.source}`));
        this.detail.append(node("small", "", point.boundary));
        if (point.id === "session") {
          const session = window.CareGuardSite?.getSessionSummary();
          this.detail.append(node("small", "lab-detail-live", session ? `当前会话 ${session.requestId} · ${session.engine} · ${session.priority} · ${session.evidenceCount} 条动态来源` : "当前浏览器会话尚未运行；此节点不冒充已生成的结果。"));
        }
        this.primary.textContent = point.id === "session" ? "查看当前会话 ↗" : point.image && !point.materialKey ? "查看完整工程示意 ↗" : "查看对应设计或证据 ↗";
      }
    }

    runPrimary() {
      const point = this.selected, site = window.CareGuardSite;
      if (!point || !site) return;
      if (this.key === "observation") site.loadLabVariant(point);
      else if (this.key === "gate") site.openClaim(3);
      else if (point.id === "session") site.openSession();
      else if (point.materialKey) site.openMaterial(point.materialKey);
      else if (Number.isInteger(point.claimIndex)) site.openClaim(point.claimIndex);
      else if (point.image) window.open(point.image, "_blank", "noopener,noreferrer");
    }

    exportCsv() {
      const columns = this.key === "observation" ? ["id", "caseId", "heartRate", "spo2", "respiratoryRate", "temperature", "central"]
        : this.key === "gate" ? ["id", "conflicts", "acute", "highRisk", "hitl", "consensusApproved", "gateBits", "code"]
          : ["id", "title", "group", "x", "y", "z", "source", "boundary"];
      const quote = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
      const rows = [columns.map(quote).join(","), ...this.visiblePoints.map((point) => columns.map((column) => quote(point[column])).join(","))];
      const csv = rows.join("\r\n");
      this.exportText.value = csv;
      this.exportNote.textContent = `已生成 ${this.visiblePoints.length} 条当前筛选记录。若浏览器未保存文件，可从下框复制完整 CSV。`;
      this.exportPanel.hidden = false;
      const url = URL.createObjectURL(new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" }));
      const link = node("a"); link.href = url; link.download = `carelink_${this.key}_research_only.csv`;
      document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  }

  const plots = Object.fromEntries(Object.entries(configs).map(([key, config]) => [key, new Scatter3D(key, config)]));
  $("#lab-density-input").addEventListener("input", (event) => {
    const density = Number(event.currentTarget.value);
    $("#lab-density-value").textContent = `${density}%`;
    Object.values(plots).forEach((plot) => { plot.density = density; plot.draw(); });
  });
  $("#lab-range-input").addEventListener("input", () => { $("#lab-range-value").textContent = `≤ ${$("#lab-range-input").value}`; plots.observation.updateVisible(); });
  $("#lab-zero-conflict").addEventListener("change", () => plots.gate.updateVisible());
  document.addEventListener("click", (event) => {
    const filter = event.target.closest("[data-lab-filter]");
    if (filter) {
      const [key, value] = filter.dataset.labFilter.split(":");
      if (plots[key]) {
        document.querySelectorAll(`[data-lab-filter^="${key}:"]`).forEach((button) => button.classList.toggle("is-active", button === filter));
        plots[key].setFilter(value);
      }
      return;
    }
    const camera = event.target.closest("[data-lab-camera]");
    if (camera) {
      const [key, action] = camera.dataset.labCamera.split(":");
      const plot = plots[key]; if (!plot) return;
      if (action === "toggle") plot.toggleMotion();
      else if (action === "reset") plot.resetCamera();
      else plot.zoomBy(action === "in" ? 0.12 : -0.12);
      return;
    }
    const exporter = event.target.closest("[data-lab-export]");
    if (exporter) plots[exporter.dataset.labExport]?.exportCsv();
  });
  const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
    const key = entry.target.dataset.labPlot; if (plots[key]) plots[key].intersecting = entry.isIntersecting;
  }), { rootMargin: "200px" });
  document.querySelectorAll("[data-lab-plot]").forEach((element) => observer.observe(element));
  document.addEventListener("careguard:viewchange", () => {
    if (!$("#lab-view").hidden) requestAnimationFrame(() => Object.values(plots).forEach((plot) => { plot.resize(); if (plot.key === "source") plot.updateDetail(); }));
  });
  reducedMotion.addEventListener("change", () => {
    if (reducedMotion.matches) Object.values(plots).forEach((plot) => { plot.playing = false; plot.updateCameraLabel(); });
  });
  let previous = performance.now();
  function frame(now) {
    const elapsed = Math.min(now - previous, 40); previous = now;
    if (!$("#lab-view").hidden && !document.hidden) {
      Object.values(plots).forEach((plot) => {
        if (!plot.intersecting) return;
        if (plot.playing && !reducedMotion.matches) {
          plot.yaw += elapsed * 0.00013;
          plot.phase += elapsed * 0.0007;
          plot.draw();
        }
      });
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  if (!$("#lab-view").hidden) requestAnimationFrame(() => Object.values(plots).forEach((plot) => plot.resize()));
})();
