"use strict";

// Decorative, deterministic Canvas rendering. It never visualizes model output.
(() => {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const fields = [];
  let motionEnabled = !reducedMotion.matches;
  let frameHandle = 0;
  let lastFrame = 0;
  const palettes = {
    hero: { line: [151, 246, 190], spark: [218, 255, 145], dust: [145, 242, 211], glow: [183, 255, 162] },
    atlas: { line: [144, 238, 195], spark: [218, 255, 145], dust: [145, 242, 211], glow: [183, 255, 162] },
    research: { line: [194, 158, 230], spark: [235, 180, 206], dust: [168, 232, 209], glow: [224, 174, 255] },
    workspace: { line: [175, 149, 224], spark: [229, 179, 241], dust: [160, 226, 223], glow: [225, 183, 255] },
    evidence: { line: [221, 164, 201], spark: [255, 202, 158], dust: [158, 221, 224], glow: [255, 196, 211] },
  };

  function randomGenerator(seed) {
    let value = seed >>> 0;
    return () => {
      value = (1664525 * value + 1013904223) >>> 0;
      return value / 4294967296;
    };
  }

  function createField(canvas, kind, count, seed) {
    const context = canvas.getContext("2d", { alpha: true });
    if (!context) return null;
    const field = {
      canvas, context, kind, count, random: randomGenerator(seed),
      nodes: [], width: 0, height: 0, pointer: null, visible: false,
    };
    const surface = canvas.parentElement;
    surface.addEventListener("pointermove", (event) => {
      if (event.pointerType === "touch") return;
      const bounds = canvas.getBoundingClientRect();
      field.pointer = { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
      if (!motionEnabled) draw(field);
    }, { passive: true });
    surface.addEventListener("pointerleave", () => {
      field.pointer = null;
      if (!motionEnabled) draw(field);
    });
    new ResizeObserver(() => resize(field)).observe(canvas);
    const observer = new IntersectionObserver((entries) => {
      field.visible = entries[0]?.isIntersecting || false;
      if (field.visible) {
        resize(field);
        schedule();
      }
    }, { threshold: 0.01 });
    observer.observe(canvas);
    resize(field);
    return field;
  }

  function makeNode(field) {
    const { random, width, height } = field;
    return {
      x: random() * width,
      y: random() * height,
      vx: (random() - 0.5) * (field.kind === "hero" ? 0.42 : 0.32),
      vy: (random() - 0.5) * (field.kind === "hero" ? 0.42 : 0.32),
      radius: random() > 0.9 ? 2.1 : 0.7 + random() * 0.9,
      phase: random() * Math.PI * 2,
      accent: random() > 0.84,
      depth: 0.45 + random() * 0.95,
    };
  }

  function resize(field) {
    const bounds = field.canvas.getBoundingClientRect();
    const width = Math.round(bounds.width);
    const height = Math.round(bounds.height);
    if (width < 2 || height < 2) return;
    if (width === field.width && height === field.height) return;
    const priorWidth = field.width;
    const priorHeight = field.height;
    field.width = width;
    field.height = height;
    const ratio = Math.min(window.devicePixelRatio || 1, 1.75);
    field.canvas.width = Math.round(width * ratio);
    field.canvas.height = Math.round(height * ratio);
    field.context.setTransform(ratio, 0, 0, ratio, 0, 0);
    if (!field.nodes.length) {
      field.nodes = Array.from({ length: field.count }, () => makeNode(field));
    } else {
      for (const point of field.nodes) {
        point.x *= width / priorWidth;
        point.y *= height / priorHeight;
      }
    }
    draw(field);
  }

  function draw(field) {
    const { context, width, height, nodes, pointer, kind } = field;
    if (!width || !height) return;
    context.clearRect(0, 0, width, height);
    const palette = palettes[kind] || palettes.hero;
    const reach = kind === "hero" ? 124 : kind === "atlas" ? 112 : 132;
    const baseOpacity = kind === "hero" ? 0.3 : 0.26;

    if (pointer && motionEnabled) {
      const halo = context.createRadialGradient(pointer.x, pointer.y, 0, pointer.x, pointer.y, 200);
      halo.addColorStop(0, `rgba(${palette.glow.join(",")},0.17)`);
      halo.addColorStop(1, `rgba(${palette.glow.join(",")},0)`);
      context.fillStyle = halo;
      context.fillRect(pointer.x - 200, pointer.y - 200, 400, 400);
    }

    // Sparse orbital guides give the field depth without encoding any medical state.
    context.save();
    context.translate(width * (kind === "hero" ? 0.76 : 0.54), height * 0.5);
    context.rotate(-0.3);
    context.strokeStyle = `rgba(${palette.line.join(",")},0.08)`;
    context.lineWidth = 1;
    for (const scale of [0.22, 0.35, 0.5]) {
      context.beginPath();
      context.ellipse(0, 0, width * scale, height * scale * 0.62, 0, 0, Math.PI * 2);
      context.stroke();
    }
    context.restore();

    context.lineWidth = 0.75;
    for (let i = 0; i < nodes.length; i += 1) {
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j += 1) {
        const b = nodes[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const distance2 = dx * dx + dy * dy;
        if (distance2 > reach * reach) continue;
        const opacity = (1 - Math.sqrt(distance2) / reach) * baseOpacity;
        context.strokeStyle = `rgba(${palette.line.join(",")},${opacity.toFixed(3)})`;
        context.beginPath();
        context.moveTo(a.x, a.y);
        context.lineTo(b.x, b.y);
        context.stroke();
      }
    }

    for (const point of nodes) {
      const brightness = (0.42 + Math.sin(point.phase) * 0.18) * point.depth;
      context.fillStyle = point.accent
        ? `rgba(${palette.spark.join(",")},${brightness.toFixed(3)})`
        : `rgba(${palette.dust.join(",")},${brightness.toFixed(3)})`;
      if (point.accent) {
        context.shadowColor = `rgb(${palette.spark.join(",")})`;
        context.shadowBlur = 13 * point.depth;
      }
      context.beginPath();
      context.arc(point.x, point.y, point.radius * point.depth, 0, Math.PI * 2);
      context.fill();
      context.shadowBlur = 0;
      if (point.accent && motionEnabled) {
        context.strokeStyle = `rgba(${palette.spark.join(",")},0.11)`;
        context.lineWidth = 0.65;
        context.beginPath();
        context.moveTo(point.x, point.y);
        context.lineTo(point.x - point.vx * 22, point.y - point.vy * 22);
        context.stroke();
      }
    }

    if (pointer && motionEnabled) {
      for (const point of nodes) {
        const dx = point.x - pointer.x;
        const dy = point.y - pointer.y;
        const distance = Math.hypot(dx, dy);
        if (distance > 155) continue;
        context.strokeStyle = `rgba(${palette.glow.join(",")},${(0.22 * (1 - distance / 155)).toFixed(3)})`;
        context.beginPath();
        context.moveTo(pointer.x, pointer.y);
        context.lineTo(point.x, point.y);
        context.stroke();
      }
    }

    if (kind === "atlas") {
      const centerX = width * 0.5;
      const centerY = height * 0.5;
      const satellite = nodes.slice(0, 4);
      for (const point of satellite) {
        context.strokeStyle = "rgba(214,255,151,0.14)";
        context.setLineDash([3, 7]);
        context.beginPath();
        context.moveTo(centerX, centerY);
        context.lineTo(point.x, point.y);
        context.stroke();
      }
      context.setLineDash([]);
    }
  }

  function advance(field) {
    const { width, height, pointer } = field;
    for (const point of field.nodes) {
      if (pointer) {
        const dx = point.x - pointer.x;
        const dy = point.y - pointer.y;
        const distance2 = dx * dx + dy * dy;
        if (distance2 < 150 * 150 && distance2 > 1) {
          const force = (1 - Math.sqrt(distance2) / 150) * 0.18;
          point.x += (dx / Math.sqrt(distance2)) * force;
          point.y += (dy / Math.sqrt(distance2)) * force;
        }
      }
      point.x += point.vx * point.depth;
      point.y += point.vy * point.depth;
      point.phase += 0.018;
      if (point.x < -5) point.x = width + 5;
      if (point.x > width + 5) point.x = -5;
      if (point.y < -5) point.y = height + 5;
      if (point.y > height + 5) point.y = -5;
    }
    draw(field);
  }

  function schedule() {
    if (frameHandle || !motionEnabled || document.hidden || !fields.some((field) => field.visible)) return;
    frameHandle = requestAnimationFrame(tick);
  }

  function tick(time) {
    frameHandle = 0;
    if (!motionEnabled || document.hidden) return;
    if (time - lastFrame >= 32) {
      for (const field of fields) if (field.visible) advance(field);
      lastFrame = time;
    }
    schedule();
  }

  function updateControls() {
    document.querySelectorAll("[data-motion-toggle]").forEach((button) => {
      button.setAttribute("aria-pressed", String(motionEnabled));
      button.setAttribute("aria-label", motionEnabled ? "暂停粒子动画" : "启用粒子动画");
      button.querySelector(".motion-icon").textContent = motionEnabled ? "Ⅱ" : "▶";
      button.querySelector(".motion-label").textContent = motionEnabled ? "暂停动态" : "启用动态";
    });
  }

  function setMotion(enabled) {
    motionEnabled = Boolean(enabled);
    if (!motionEnabled && frameHandle) {
      cancelAnimationFrame(frameHandle);
      frameHandle = 0;
    }
    updateControls();
    for (const field of fields) draw(field);
    schedule();
  }

  const scenes = [
    ["hero-particles", "hero", 152, 2211],
    ["research-particles", "research", 110, 4317],
    ["atlas-particles", "atlas", 122, 5119],
    ["workspace-particles", "workspace", 92, 7721],
    ["evidence-particles", "evidence", 92, 8831],
  ];
  for (const [id, kind, count, seed] of scenes) {
    const canvas = document.getElementById(id);
    const field = canvas && createField(canvas, kind, count, seed);
    if (field) fields.push(field);
  }
  document.querySelectorAll("[data-motion-toggle]").forEach((button) => {
    button.addEventListener("click", () => setMotion(!motionEnabled));
  });
  reducedMotion.addEventListener("change", (event) => setMotion(!event.matches));
  document.addEventListener("visibilitychange", schedule);
  document.addEventListener("careguard:viewchange", () => {
    for (const field of fields) resize(field);
    schedule();
  });
  updateControls();
  schedule();
})();
