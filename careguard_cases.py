"""Synthetic, non-identifiable cases shared by the UI and live smoke check."""

from __future__ import annotations

from typing import Any, Dict


SAMPLE_CASES: Dict[str, Dict[str, Any]] = {
    "夜间突发胸痛": {
        "note": "82岁男性，夜间突发持续性胸部压榨感，向左臂放射，伴大汗、恶心和呼吸困难。护理员已停止活动并呼叫值班负责人。",
        "vitals": {"heart_rate": 112, "spo2": 91, "temperature": 36.8, "respiratory_rate": 25},
        "force_high_risk": True,
    },
    "疑似卒中表现": {
        "note": "76岁女性，晨间巡视发现突然口角歪斜、言语含糊，右侧上肢无力，症状约20分钟前出现。",
        "vitals": {"heart_rate": 96, "spo2": 95, "temperature": 36.6, "respiratory_rate": 20},
        "force_high_risk": True,
    },
    "慢病状态变化": {
        "note": "79岁男性，近三日活动后气促加重，双下肢水肿，夜间需垫高枕头入睡，较平日乏力。",
        "vitals": {"heart_rate": 102, "spo2": 93, "temperature": 36.7, "respiratory_rate": 23},
        "force_high_risk": False,
    },
    "夜班单次记录": {
        "note": "合成体征样本 21:00 的单次记录，未附现场主诉或处置描述。此案例用于演示交接信息待补全，不代表真实患者。",
        "vitals": {"heart_rate": 86, "spo2": 96, "temperature": 36.7, "respiratory_rate": 18},
        "force_high_risk": False,
        "source": "demo_assets/sample_vitals.csv:2",
    },
    "复测语境待核对": {
        "note": "合成体征样本 21:05 的单次记录。与表中其他时间点不推定属于同一人；需要人工核对测量条件和观察描述。",
        "vitals": {"heart_rate": 94, "spo2": 95, "temperature": 36.7, "respiratory_rate": 20},
        "force_high_risk": False,
        "source": "demo_assets/sample_vitals.csv:3",
    },
    "交接信息缺口": {
        "note": "合成体征样本 21:10 的单次记录，缺少症状、采集条件和已采取措施。请人工补全；单次数值不能给出诊断。",
        "vitals": {"heart_rate": 103, "spo2": 93, "temperature": 36.8, "respiratory_rate": 23},
        "force_high_risk": False,
        "source": "demo_assets/sample_vitals.csv:4",
    },
}


def clinical_text_for_case(case: Dict[str, Any]) -> str:
    """Add structured vital signs without inventing a longitudinal time series."""
    vitals = case["vitals"]
    return (
        f'{case["note"]}\n生命体征：心率 {vitals["heart_rate"]} 次/分，'
        f'血氧 {vitals["spo2"]}%，体温 {vitals["temperature"]}℃，'
        f'呼吸 {vitals["respiratory_rate"]} 次/分。'
    )
