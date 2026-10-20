/* Reproducible, non-clinical data for the CareLink interactive research atlas. */
(function (root) {
  "use strict";

  const CASE_SEEDS = [
    { id: "chest", title: "夜间突发胸痛", heartRate: 112, spo2: 91, respiratoryRate: 25, temperature: 36.8, color: "#d9fa99" },
    { id: "stroke", title: "疑似卒中表现", heartRate: 96, spo2: 95, respiratoryRate: 20, temperature: 36.6, color: "#d5a8ef" },
    { id: "change", title: "慢病状态变化", heartRate: 102, spo2: 93, respiratoryRate: 23, temperature: 36.7, color: "#f3b49a" },
  ];

  function observationPoints() {
    const points = [];
    for (const seed of CASE_SEEDS) {
      for (const dh of [-12, 0, 12]) {
        for (const ds of [-3, 0, 3]) {
          for (const dr of [-4, 0, 4]) {
            const heartRate = seed.heartRate + dh;
            const spo2 = seed.spo2 + ds;
            const respiratoryRate = seed.respiratoryRate + dr;
            points.push({
              id: `${seed.id}-${dh}-${ds}-${dr}`, group: seed.id, caseId: seed.id,
              title: seed.title, color: seed.color, x: heartRate, y: spo2, z: respiratoryRate,
              heartRate, spo2, respiratoryRate, temperature: seed.temperature,
              central: dh === 0 && ds === 0 && dr === 0,
              offsets: { heartRate: dh, spo2: ds, respiratoryRate: dr },
            });
          }
        }
      }
    }
    return points;
  }

  // Mirrors careguard_presenter._priority for the five displayed Boolean/ordinal inputs.
  // This enumerates logic states, not people, outcomes, probabilities, or model accuracy.
  function gatePriority({ conflicts, acute, highRisk, hitl, consensusApproved }) {
    if (acute || highRisk || conflicts > 0) return "P1";
    if (hitl || !consensusApproved) return "P2";
    return "P3";
  }

  function gatePoints() {
    const points = [];
    for (let conflicts = 0; conflicts <= 4; conflicts++) {
      for (const acute of [false, true]) {
        for (const highRisk of [false, true]) {
          for (const hitl of [false, true]) {
            for (const consensusApproved of [false, true]) {
              const code = gatePriority({ conflicts, acute, highRisk, hitl, consensusApproved });
              const gateBits = Number(highRisk) * 4 + Number(hitl) * 2 + Number(!consensusApproved);
              points.push({
                id: `gate-${conflicts}-${Number(acute)}-${gateBits}`, group: code,
                title: `${code} · 冲突 ${conflicts} / 急性 ${acute ? "是" : "否"} / 门控 ${gateBits}`,
                x: conflicts, y: Number(acute), z: gateBits,
                conflicts, acute, highRisk, hitl, consensusApproved, gateBits, code,
                color: code === "P1" ? "#fa9f88" : code === "P2" ? "#e9d18f" : "#aee2bc",
              });
            }
          }
        }
      }
    }
    return points;
  }

  const SOURCE_ITEMS = [
    { id: "field-visit", title: "历史走访照片", group: "archive", x: 0, y: 0, z: 0, materialKey: "visit", image: "/assets/archive/field-visit.jpeg", source: "11+智弈护晓.zip / 路演图片", boundary: "能说明曾开展走访；不能推出当前部署或临床效果。" },
    { id: "legacy-ui", title: "旧版界面档案", group: "archive", x: 0, y: 2, z: 0, materialKey: "interface", image: "/assets/archive/legacy-interface.jpeg", source: "11+智弈护晓.zip / 路演图片", boundary: "只能说明设计演进，不代表当前功能清单。" },
    { id: "shwid-cover", title: "SHWID 2025 论文集封面", group: "archive", x: 1, y: 1, z: 0, image: "/assets/research/shwid-2025-cover.png", source: "素材(3).zip / 论文扫描件", boundary: "说明材料来源与年份，不证明本版软件效果。" },
    { id: "shwid-contents", title: "论文集目录 · MAPFM / 212", group: "archive", x: 1, y: 1, z: 0, image: "/assets/research/shwid-2025-contents.png", source: "素材(3).zip / 论文扫描件", boundary: "证明目录列有 MAPFM 论文，不证明临床有效性。" },
    { id: "mapfm-paper", title: "MAPFM 论文首页", group: "archive", x: 1, y: 1, z: 0, materialKey: "paper", image: "/assets/research/mapfm-paper-first-page.png", source: "素材(3).zip / 论文扫描件", boundary: "说明多智能体检索增强的研究路径，不等于当前产品已验证。" },
    { id: "screening-api", title: "当前 /screening 接口", group: "build", x: 3, y: 3, z: 1, claimIndex: 0, source: "api.py", boundary: "证明存在可调用软件接口，不证明诊断准确率。" },
    { id: "presenter", title: "分层输出与门控代码", group: "build", x: 3, y: 3, z: 1, claimIndex: 0, source: "careguard_presenter.py", boundary: "证明实现了显示规则与人工门控，不证明临床决策正确。" },
    { id: "human-gate", title: "人工复核与审计导出", group: "build", x: 3, y: 3, z: 2, claimIndex: 3, source: "careguard_presenter.py / tests/test_careguard_presenter.py", boundary: "测试覆盖流程行为，不替代专业判断。" },
    { id: "pytest", title: "自动化测试快照", group: "test", x: 3, y: 4, z: 2, claimIndex: 0, source: "artifacts/competition/careguard_pytest_latest.xml", boundary: "带时间戳的软件测试快照，不是实时监测。" },
    { id: "smoke", title: "合成案例自检快照", group: "test", x: 3, y: 4, z: 2, claimIndex: 1, source: "artifacts/competition/careguard_live_smoke_latest.json", boundary: "历史 Ollama 自检不保证此刻仍在线。" },
    { id: "session", title: "当前浏览器会话", group: "runtime", x: 3, y: 4, z: 1, source: "工作台本次 /screening 响应", boundary: "需现场运行才有状态；刷新浏览器即清空。" },
    { id: "clinical-gap", title: "外部临床验证缺口", group: "gap", x: 3, y: 4, z: 3, claimIndex: 5, source: "尚无可展示的独立外部验证", boundary: "明确未验证，不可把软件测试和历史研究升级为临床结论。" },
  ];

  function sourcePoints() {
    const counts = new Map();
    return SOURCE_ITEMS.map((item) => {
      const cell = `${item.x}-${item.y}-${item.z}`;
      const index = counts.get(cell) || 0;
      counts.set(cell, index + 1);
      return { ...item, plotX: item.x + ((index % 3) - 1) * 0.11, plotY: item.y + (Math.floor(index / 3) - 0.5) * 0.11, plotZ: item.z, color: { archive: "#c9afea", build: "#a9e1c4", test: "#d9fa99", runtime: "#89baf0", gap: "#f2a391" }[item.group] };
    });
  }

  const api = { CASE_SEEDS, SOURCE_ITEMS, observationPoints, gatePriority, gatePoints, sourcePoints };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.CareGuardLabData = api;
})(typeof window !== "undefined" ? window : null);
