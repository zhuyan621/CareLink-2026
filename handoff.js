/* A browser-local, non-clinical handover summary for reviewed demo inputs. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.CareGuardHandoff = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  const clean = (value) => String(value ?? "").trim();
  const count = (value) => Number.isFinite(Number(value)) ? Math.max(0, Math.trunc(Number(value))) : 0;

  function build(record, screening, review) {
    if (!record || !screening || review?.status !== "completed") {
      throw new Error("必须先完成本次筛查与人工复核");
    }
    if (!clean(record.title) || !clean(record.note) || !clean(review.decision)) {
      throw new Error("交接摘要缺少必要输入或人工决定");
    }
    if (screening.priority?.code === "P1" &&
        (clean(review.decision).includes("常规观察") || !clean(review.notes))) {
      throw new Error("P1 交接摘要不得自动放行，且必须保留人工复核说明");
    }
    return {
      title: clean(record.title),
      eventTime: clean(record.eventTime).replace("T", " ") || "未填写",
      note: clean(record.note),
      observedChange: clean(record.observedChange) || "未填写",
      actionTaken: clean(record.actionTaken) || "未填写",
      vitals: {
        heartRate: clean(record.heartRate), spo2: clean(record.spo2),
        temperature: clean(record.temperature), respiratoryRate: clean(record.respiratoryRate),
      },
      requestId: clean(screening.request_id) || "未提供",
      priority: clean(screening.priority?.code) || "未确认",
      clue: clean(screening.observed_clue) || "未能可靠归类",
      engine: clean(screening.engine_label) || "状态未确认",
      dynamicEvidence: count(screening.evidence_count),
      offlineReferences: count(screening.reference_count),
      reviewer: clean(review.reviewer) || "未署名",
      decision: clean(review.decision),
      reviewNotes: clean(review.notes) || "未填写",
      reviewedAt: clean(review.reviewed_at) || "未提供",
    };
  }

  function toText(packet) {
    return [
      "安护智链 CareLink｜合成演示交接摘要",
      "仅供科研与竞赛演示；不是病历、诊断、医嘱或临床交接凭证。",
      "",
      `案例：${packet.title}`,
      `发生时间：${packet.eventTime}`,
      `护理交接记录：${packet.note}`,
      `观察到的变化：${packet.observedChange}`,
      `已采取措施 / 待交接事项：${packet.actionTaken}`,
      `演示体征：HR ${packet.vitals.heartRate} 次/分；SpO₂ ${packet.vitals.spo2}%；体温 ${packet.vitals.temperature}℃；RR ${packet.vitals.respiratoryRate} 次/分`,
      "",
      `本次请求：${packet.requestId}`,
      `演示优先级线索：${packet.priority}；${packet.clue}`,
      `实际链路：${packet.engine}`,
      `来源状态：动态核验 ${packet.dynamicEvidence} 条；人工整理的离线参考 ${packet.offlineReferences} 条`,
      "动态来源为零时不得把离线参考称作本次动态证据。",
      "",
      `人工复核人：${packet.reviewer}`,
      `人工决定：${packet.decision}`,
      `复核说明：${packet.reviewNotes}`,
      `复核时间：${packet.reviewedAt}`,
      "",
      "请仅使用合成或充分脱敏的演示内容。最终判断由具备资质的专业人员负责。",
    ].join("\n");
  }

  return { build, toText };
});
