#!/usr/bin/env python3
"""Generate MAPFM HMAE v2.0 Innovation Points Report (.docx) — fact-checked edition"""

from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
import datetime

doc = Document()

# ============================================================
# Style Configuration
# ============================================================
style = doc.styles['Normal']
font = style.font
font.name = '宋体'
font.size = Pt(11)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
style.paragraph_format.line_spacing = 1.5
style.paragraph_format.space_after = Pt(6)

for level, (size, bold, color) in enumerate([
    (Pt(22), True, RGBColor(0x1A, 0x3C, 0x6E)),
    (Pt(16), True, RGBColor(0x2B, 0x57, 0x9A)),
    (Pt(13), True, RGBColor(0x3D, 0x6E, 0xB5)),
    (Pt(11.5), True, RGBColor(0x4A, 0x4A, 0x4A)),
], start=1):
    h_style = doc.styles[f'Heading {level}']
    h_font = h_style.font
    h_font.name = '黑体'
    h_font.size = size
    h_font.bold = bold
    h_font.color.rgb = color
    h_style.element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    h_style.paragraph_format.space_before = Pt(12)
    h_style.paragraph_format.space_after = Pt(6)

def add_body(text):
    p = doc.add_paragraph(style='Normal')
    run = p.add_run(text)
    run.font.name = '宋体'
    run.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    run.font.size = Pt(11)
    return p

def add_bullet(text, level=0):
    p = doc.add_paragraph(style='List Bullet')
    p.clear()
    run = p.add_run(text)
    run.font.name = '宋体'
    run.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    run.font.size = Pt(11)
    if level > 0:
        p.paragraph_format.left_indent = Cm(1.5 * (level + 1))
    return p

def add_table_with_style(headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = table.rows[0].cells
    for i, header in enumerate(headers):
        hdr_cells[i].text = ''
        p = hdr_cells[i].paragraphs[0]
        run = p.add_run(header)
        run.font.name = '黑体'
        run.element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        run.font.size = Pt(10)
        run.bold = True
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r, row in enumerate(rows):
        row_cells = table.rows[r + 1].cells
        for c, cell_text in enumerate(row):
            row_cells[c].text = ''
            p = row_cells[c].paragraphs[0]
            run = p.add_run(str(cell_text))
            run.font.name = '宋体'
            run.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
            run.font.size = Pt(10)
    if col_widths:
        for i, width in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(width)
    doc.add_paragraph()
    return table

def add_highlight_box(title, content):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1)
    p.paragraph_format.right_indent = Cm(1)
    run = p.add_run(f"【{title}】")
    run.font.name = '黑体'
    run.element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    run.font.size = Pt(11)
    run.bold = True
    run.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)
    run2 = p.add_run(content)
    run2.font.name = '宋体'
    run2.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    run2.font.size = Pt(11)
    return p

# ============================================================
# Cover
# ============================================================
for _ in range(6):
    doc.add_paragraph()

title_p = doc.add_paragraph()
title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title_p.add_run("MAPFM HMAE v2.0\n异构多智能体医疗AI系统\n——核心创新点报告")
run.font.name = '黑体'
run.element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
run.font.size = Pt(26)
run.bold = True
run.font.color.rgb = RGBColor(0x1A, 0x3C, 0x6E)

doc.add_paragraph()

subtitle_p = doc.add_paragraph()
subtitle_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle_p.add_run(
    "Heterogeneous Multi-Agent Ecosystem (HMAE) for Medical AI\n"
    "Core Innovation Report"
)
run.font.name = 'Times New Roman'
run.font.size = Pt(14)
run.italic = True
run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

for _ in range(4):
    doc.add_paragraph()

meta_p = doc.add_paragraph()
meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
meta_lines = [
    f"版本：v2.0",
    f"日期：{datetime.date.today().strftime('%Y年%m月%d日')}",
    "项目：MAPFM_medical_AI_repaired_complete",
    "数据集：medNo.22.csv（605条，21个真实医疗领域，8个NIH数据源）",
]
run = meta_p.add_run("\n".join(meta_lines))
run.font.name = '宋体'
run.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

doc.add_page_break()

# ============================================================
# TOC
# ============================================================
doc.add_heading('目  录', level=1)
toc_items = [
    "一、项目概述",
    "二、创新点总览",
    "三、架构创新",
    "    3.1 异构多智能体协同架构（HMAE）",
    "    3.2 DMA-TFA深度融合机制",
    "    3.3 三层共识投票与层次化决策",
    "    3.4 Nash博弈论驱动的RAG策略选择",
    "    3.5 多模态数据统一处理管线",
    "四、算法创新",
    "    4.1 Platt缩放置信度在线校准",
    "    4.2 三源知识融合与SimHash去重",
    "    4.3 易混淆疾病三层消歧增强",
    "    4.4 MedTsLLM时序风险预测框架",
    "    4.5 对比学习检索权重在线更新",
    "五、工程创新",
    "    5.1 LLM + 传统ML混合架构",
    "    5.2 三级优雅降级机制",
    "    5.3 人机协同（HITL）三级干预",
    "    5.4 全链路可追溯与审计",
    "    5.5 系统健康监控与故障隔离",
    "六、安全与隐私创新",
    "    6.1 差分隐私梯度保护",
    "    6.2 XOR加密Agent间通信",
    "    6.3 PII自动脱敏",
    "七、实验框架",
    "八、性能指标（测试报告数据）",
    "九、技术栈",
    "十、已知局限与未来方向",
]
for item in toc_items:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(0)
    run = p.add_run(item)
    run.font.name = '宋体'
    run.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    run.font.size = Pt(11)

doc.add_page_break()

# ============================================================
# 一、项目概述
# ============================================================
doc.add_heading('一、项目概述', level=1)

add_body(
    "MAPFM（Multi-Agent Perception-Fusion Medical）是一个面向临床决策支持的异构多智能体（HMAE）"
    "医疗AI系统。系统模拟了从患者多模态数据输入到诊断推理、时序风险评估、知识检索增强、"
    "人工审核介入、共识投票决策的完整临床辅助决策流程。"
)

add_body(
    "系统以Python 3.14 + FastAPI为核心框架，以Ollama驱动的Llama3:8b本地大语言模型为主推理引擎，"
    "整合MiniLM语义嵌入（sentence-transformers/all-MiniLM-L6-v2）、FAISS稠密向量检索（IndexFlatIP）、"
    "Redis消息队列等基础设施，实现了10个专业化Agent的协同工作。"
    "在medNo.22.csv数据集（605条，21个真实医疗领域，8个NIH数据源）上，"
    "2026年5月27日测试报告显示：准确率84.03%，加权F1 85.23%，71/73项单元测试通过（97.3%）。"
)

add_highlight_box("设计理念",
    "诊断优先、TFA辅助、安全第一（Diagnosis-first, TFA as auxiliary, Safety-first）")
add_highlight_box("出处",
    "README.md, ARCHITECTURE_UPGRADE.md, test_report_2026-05-27")

# ============================================================
# 二、创新点总览
# ============================================================
doc.add_heading('二、创新点总览', level=1)

add_body("MAPFM HMAE v2.0系统涵盖架构、算法、工程、安全四个维度的核心设计特点：")

add_table_with_style(
    ["维度", "编号", "设计特点", "实现方式"],
    [
        ["架构", "A1", "异构多智能体协同（HMAE）", "10 Agent分工 + 统一消息格式 + Star/Mesh拓扑"],
        ["架构", "A2", "DMA-TFA深度融合", "管线重排序 + 置信度感知校准 + 交叉验证"],
        ["架构", "A3", "三层共识投票 + 层次化决策", "FORCE_HITL → DMA_VETO → NORMAL_VOTE规则矩阵"],
        ["架构", "A4", "Nash博弈论RAG策略选择", "3策略博弈 + DMA裁判 + 置信度缓存"],
        ["架构", "A5", "多模态统一处理管线", "CSV/TXT/Image预处理 + MultimodalPatientData"],
        ["算法", "B1", "Platt缩放置信度在线校准", "SGD逻辑回归 + 200对滑动窗口 + 冷启动保护"],
        ["算法", "B2", "三源知识融合 + SimHash去重", "人/权威/检索加权 + LSH去重 + 冲突检测"],
        ["算法", "B3", "易混淆疾病三层消歧增强", "同义词映射 + 检索boost + 语义消歧"],
        ["算法", "B4", "MedTsLLM时序风险预测框架", "BioBERT骨干 + PatchEmbedding + Reprogramming"],
        ["算法", "B5", "对比学习检索权重在线更新", "正负样本对比反馈 + ContinuousLearningLoop"],
        ["工程", "C1", "LLM + 传统ML混合架构", "Llama3:8b主引擎 + TF-IDF确定性fallback"],
        ["工程", "C2", "三级优雅降级", "safe_call包装 + 组件状态跟踪 + 自动恢复"],
        ["工程", "C3", "HITL三级人机协同", "自主→干预→升级 + 审核结果回传闭环"],
        ["工程", "C4", "全链路可追溯与审计", "Correlation ID + JSONL审计 + 决策追溯持久化"],
        ["工程", "C5", "系统健康监控与故障隔离", "心跳检测 + 异常输出检测 + 自动故障隔离"],
        ["安全", "D1", "差分隐私梯度保护", "高斯噪声(σ=0.015) + 可配置噪声强度"],
        ["安全", "D2", "XOR加密Agent间通信", "AgentMessage加密载荷 + 路由路径记录"],
        ["安全", "D3", "PII自动脱敏", "请求级正则脱敏 + 审计前剥离"],
    ],
    col_widths=[1.5, 1.0, 4.5, 6.0]
)

doc.add_page_break()

# ============================================================
# 三、架构创新
# ============================================================
doc.add_heading('三、架构设计', level=1)

# --- 3.1 HMAE ---
doc.add_heading('3.1 异构多智能体协同架构（HMAE）', level=2)

add_body(
    "系统将临床决策流程分解为10个专业化Agent的协同工作。每个Agent通过统一的"
    "AgentMessage dataclass进行通信，由TopologyAgent管理Star（星型）或Mesh（网状）"
    "拓扑路由，支持自动重试和故障隔离。"
)

add_table_with_style(
    ["Agent", "角色", "核心技术", "输出"],
    [
        ["Perception", "多模态感知编码", "Text + Image Cross-Attention融合", "统一上下文向量"],
        ["RAA", "检索增强", "3策略RAG + FAISS + Nash博弈选择", "Top-K相关文献"],
        ["DMA", "诊断决策", "Ollama Llama3:8b + Platt校准", "疾病预测 + 置信度 + 意图"],
        ["TFA", "时序风险预测", "MedTsLLM / 启发式TCN+LSTM+Transformer", "短/中/长期风险评分"],
        ["Fusion", "知识融合去重", "三源加权融合 + SimHash去重", "融合知识上下文"],
        ["Verification", "事实核查", "Fact scoring + 时效性验证 + TFA报告校验", "验证通过/冲突标记"],
        ["Consensus", "层次化共识", "3层规则投票矩阵", "最终决策 + 决策日志"],
        ["Privacy", "隐私安全", "XOR加密 + DP梯度噪声", "加密消息 + 安全梯度"],
        ["Maintenance", "健康监控", "心跳 + 故障隔离 + 异常检测", "系统状态报告"],
        ["Topology", "通信拓扑", "Star/Mesh路由 + 重试队列", "可靠消息传递"],
    ],
    col_widths=[2.0, 2.5, 4.5, 4.0]
)

add_body(
    "出处：README.md Agent表格，ARCHITECTURE_UPGRADE.md §1-7，mapfm_ecosystem_repaired.py 各Agent类定义。"
)

# --- 3.2 DMA-TFA ---
doc.add_heading('3.2 DMA-TFA深度融合机制', level=2)

add_body(
    "v2.0架构升级的核心变化是将DMA（诊断）与TFA（风险预测）从独立模块改为深度耦合："
    "管线重排序使DMA先于TFA执行，TFA利用DMA诊断置信度进行风险校准；"
    "当TFA风险因素与DMA诊断不相关时，Verification模块标记警告，严重冲突触发HITL；"
    "Fusion模块最终生成包含诊断+风险评估+建议+免责声明的统一结构化输出。"
)

add_table_with_style(
    ["DMA置信度", "TFA校准系数", "校准模式", "含义"],
    [
        ["≥ 0.9", "×1.0", "full_confidence", "诊断高度可信，风险预测直接采纳"],
        ["0.7 – 0.9", "×0.9", "slight_discount", "诊断较可信，风险预测轻微降权"],
        ["0.6 – 0.7", "×0.8", "moderate_discount", "诊断存在不确定性，风险预测需审慎"],
        ["< 0.6", "降级模式", "degraded", "诊断低置信度，风险预测仅供参考"],
    ],
    col_widths=[2.5, 2.5, 3.0, 5.0]
)

add_body(
    "出处：ARCHITECTURE_UPGRADE.md §2 DMA-TFA Integration，TFA._apply_dma_calibration()。"
)

# --- 3.3 Consensus ---
doc.add_heading('3.3 三层共识投票与层次化决策', level=2)

add_body(
    "Consensus模块采用3层自上而下的规则矩阵（ARCHITECTURE_UPGRADE.md §5.2）："
)

add_table_with_style(
    ["层级", "规则", "触发条件", "处理方式"],
    [
        ["Layer 1", "FORCE_HITL", "安全冲突 / TFA critical风险 / 诊断-风险矛盾", "强制人工审核，阻断自动决策"],
        ["Layer 2", "DMA_VETO", "DMA投票NO（置信度不达标）", "一票否决，升级至HITL"],
        ["Layer 3", "NORMAL_VOTE", "常规场景：置信度×风险矩阵", "DMA(2票)+TFA(1票)+Verification(1票)，总4票需≥3票通过"],
    ],
    col_widths=[1.5, 2.5, 4.5, 4.5]
)

add_body(
    "配合层次化决策（hierarchical_vote，P1-5 fix）：Fast-track（置信度≥0.85 + 非高风险）自动批准；"
    "Standard（0.65-0.85）执行PBFT加权投票；Escalation（<0.65）使用75%高阈值并自动升级至HITL。"
)

add_body(
    "出处：ARCHITECTURE_UPGRADE.md §5, ConsensusModule.hierarchical_vote()。"
)

# --- 3.4 Nash RAG ---
doc.add_heading('3.4 Nash博弈论驱动的RAG策略选择', level=2)

add_body(
    "RAA同时支持三种检索策略：Mixed-RAG（TF-IDF + FAISS稠密融合）、Rerank-RAG"
    "（相似度0.62 + 重叠度0.22 + 时效性0.10 + 权威加成0.10）、Adaptive-RAG"
    "（不确定性门控的深度/浅层自适应）。策略选择通过Nash博弈框架：每个策略为参与者，"
    "DMA作为裁判评估期望收益（检索质量+计算成本），Nash均衡解给出最优策略组合。"
    "此外，dma_confidence_cache（P0-4-1 fix）以(hash(doc_ids), mode)为键缓存DMA结果，"
    "相同输入仅调用一次DMA。"
)

add_body(
    "出处：README.md Stage 2描述，RAA配置参数（EcosystemConfig），dma_confidence_cache（P0-4-1）。"
)

# --- 3.5 Multimodal ---
doc.add_heading('3.5 多模态数据统一处理管线', level=2)

add_body(
    "系统通过mapfm_utils/multimodal_utils.py实现三种输入模态的统一预处理管线："
)

add_table_with_style(
    ["模态", "数据格式", "处理方式", "应用场景"],
    [
        ["文本", "自然语言问诊", "直接文本编码（MiniLM语义嵌入）", "患者主诉、症状描述"],
        ["结构化数据", "CSV（生命体征+检验结果）", "清洗→归一化→时序对齐", "心率、血压、体温、血检指标"],
        ["影像", "JPG/PNG", "ViT-style patching + Cross-Attention融合", "X光、CT、MRI、超声"],
    ],
    col_widths=[2.0, 3.5, 4.5, 3.0]
)

add_body(
    "预处理管线：数据清洗（异常值剔除、缺失率>50%行删除）→ 归一化"
    "（ISO 8601/Unix时间戳解析、单位标准化、生命体征[0,1]归一化）→ 脱敏"
    "（正则PII剥离）。模块间统一使用MultimodalPatientData dataclass传递数据。"
)

add_body(
    "出处：ARCHITECTURE_UPGRADE.md §1, mapfm_utils/multimodal_utils.py。"
)

doc.add_page_break()

# ============================================================
# 四、算法创新
# ============================================================
doc.add_heading('四、算法设计', level=1)

# --- 4.1 Platt ---
doc.add_heading('4.1 Platt缩放置信度在线校准', level=2)

add_body(
    "大语言模型的原始输出概率通常未经校准。系统实现了基于Platt Scaling的在线置信度校准（P1-3 fix）："
)

add_bullet("SGD逻辑回归：在200对滑动窗口上执行mini-batch随机梯度下降，学习Platt参数A和B")
add_bullet("校准公式：P_calibrated = sigmoid(A × raw_score + B)，将LLM原始置信度映射至经验正确概率")
add_bullet("在线更新：record_calibration_feedback()记录(置信度, 是否正确)配对，calibrate_platt_from_history()触发SGD更新")
add_bullet("冷启动保护：未校准（A≈0）时原始置信度直接透传")
add_bullet("部署位置：DMA.infer()和_legacy_simulated_infer()两条推理路径均应用")

add_body(
    "出处：mapfm_ecosystem_repaired.py _platt_A/_platt_B/_apply_platt_scaling()，P1-3 memory。"
)

# --- 4.2 Tri-Source ---
doc.add_heading('4.2 三源知识融合与SimHash去重', level=2)

add_body(
    "TriSourceKnowledgeFusion模块按可信度层级融合四个知识来源："
)

add_table_with_style(
    ["知识来源", "权重", "来源示例", "特点"],
    [
        ["人类专家知识", "0.95", "临床指南、专家标注", "可信度最高，覆盖有限"],
        ["权威知识库", "0.90", "PubMed、NIH、CDC", "高可信度，结构化可检索"],
        ["检索增强知识", "0.75", "FAISS/RAG检索结果", "覆盖面广，需经过验证"],
        ["合成数据", "0.55", "数据增强生成", "补充性知识，低权重"],
    ],
    col_widths=[3.0, 1.5, 3.5, 5.0]
)

add_body(
    "融合流程采用SimHash局部敏感哈希：Hamming距离<4判定为重复并去重，"
    "Hamming距离>26判定为冲突并自动标记降权。融合后的知识向量输入DMA进行诊断决策。"
)

add_body(
    "出处：README.md Stage 3，EcosystemConfig.source_weights，fusion_conflict_hamming_threshold。"
)

# --- 4.3 Disambiguation ---
doc.add_heading('4.3 易混淆疾病三层消歧增强', level=2)

add_body(
    "针对临床中易混淆疾病（如Causes of Diabetes vs Type 2 Diabetes），实现了三层消歧增强（P1-2 fix）："
)

add_bullet("第一层（同义词映射）：canonical_area()函数将不同疾病表述统一到标准名称")
add_bullet("第二层（检索boost）：对与候选疾病高度相关的文献提高检索权重")
add_bullet("第三层（语义消歧）：基于问诊文本关键区分特征（发病年龄、症状持续时间、并发症）进行最终判定")
add_bullet("验证：5/5易混淆病例正确分类")

add_body(
    "出处：utils.py canonical_area()，_legacy_simulated_infer()三层消歧逻辑，P1-2 memory。"
)

# --- 4.4 MedTsLLM ---
doc.add_heading('4.4 MedTsLLM时序风险预测框架', level=2)

add_body(
    "TFA模块支持两种运行模式：启发式模式（TCN+LSTM+Transformer混合模型）和MedTsLLM模式"
    "（基于BioBERT骨干的医学时序LLM框架）。"
)

add_bullet("核心架构：PatchEmbedding → ReprogrammingLayer（cross-attention）→ frozen BioBERT → FlattenHead")
add_bullet("论文来源：flixpar/med-ts-llm（JHU, MLHC 2024, arXiv:2408.07773）")
add_bullet("多窗口预测：短期（24h）、中期（30d）、长期（12m）三个时间窗口")
add_bullet("疾病特异性参数：急性疾病短期窗口×3.0乘数，慢性疾病长期窗口×2.0乘数")
add_bullet("风险等级：low / medium / high / critical 四级，每级配有中文临床建议")
add_highlight_box("当前局限",
    "MedTsLLM的reprogramming/output层当前为随机初始化——该框架需要标注医疗时序数据训练"
    "才能产生有临床意义的风险预测。设置enable_medtsllm=False可随时切换回启发式fallback。"
    "（出处：project_medtsllm_deployment memory, deploy_medtsllm.py）")

add_body(
    "出处：medtsllm_adapter.py, deploy_medtsllm.py, EcosystemConfig.enable_medtsllm, project_medtsllm_deployment memory。"
)

# --- 4.5 Contrastive ---
doc.add_heading('4.5 对比学习检索权重在线更新', level=2)

add_body(
    "ContrastiveRetrievalUpdater将对比学习思想引入检索系统的在线优化："
)

add_bullet("正样本增强：HITL确认正确的检索文档 → 提升TF-IDF权重和FAISS相似度加权")
add_bullet("负样本抑制：HITL标记不相关的文档 → 降低检索权重")
add_bullet("ContinuousLearningLoop：累积≥10条反馈记录后自动触发模型参数更新（learning_rate=0.08）")
add_bullet("OnlineKnowledgeBaseManager：支持增量文档添加 + FAISS/TF-IDF双索引自动重建")

add_body(
    "出处：mapfm_ecosystem_repaired.py ContrastiveRetrievalUpdater, ContinuousLearningLoop, OnlineKnowledgeBaseManager。"
)

doc.add_page_break()

# ============================================================
# 五、工程创新
# ============================================================
doc.add_heading('五、工程设计', level=1)

# --- 5.1 Hybrid ---
doc.add_heading('5.1 LLM + 传统ML混合推理架构', level=2)

add_body(
    "系统采用「LLM优先、传统ML兜底」的双层推理架构："
)

add_table_with_style(
    ["层级", "推理引擎", "触发条件", "特性"],
    [
        ["Primary", "Ollama Llama3:8b", "Ollama服务可用", "LLM推理，温度0.0，num_ctx=2048"],
        ["Fallback", "TF-IDF质心 + 检索加权分类器", "Ollama不可用/超时", "确定性输出，零外部依赖"],
    ],
    col_widths=[2.0, 4.0, 3.5, 3.5]
)

add_body(
    "Fallback分类器融合5个维度：TF-IDF质心距离（权重0.50）、检索相关性（0.34）、"
    "词汇重叠度（0.12）、上下文向量（0.02）、TFA风险评分（0.02），"
    "经softmax温度参数（0.18）进行概率校准。所有权重均可通过config.yaml调整。"
)

add_body(
    "出处：README.md Design Principles, EcosystemConfig权重参数, DMA.infer()/_legacy_simulated_infer()。"
)

# --- 5.2 Degradation ---
doc.add_heading('5.2 三级优雅降级机制', level=2)

add_body(
    "DegradationManager跟踪所有组件的健康状态（healthy/degraded/unavailable），"
    "根据不可用和降级组件数量自动评估系统降级级别（0=正常, 1=轻微, 2=部分, 3=严重）。"
    "同时，SystemMonitor（mapfm_utils/system_monitor.py）实现了三层资源驱动的降级："
)

add_table_with_style(
    ["降级级别", "触发条件", "降级措施"],
    [
        ["L1", "GPU显存 > 90%", "切换至4-bit量化模型"],
        ["L2", "MedTsLLM不可用", "切换至启发式TFA模式"],
        ["L3", "Ollama不可用", "切换至纯规则推理DMA"],
    ],
    col_widths=[2.0, 4.0, 7.0]
)

add_body(
    "所有关键模块调用通过DegradationManager.safe_call()统一包装，包含：自动异常捕获、"
    "预设fallback返回值、降级通知、故障计数。后台监控线程（默认30s间隔）持续检查健康状态，"
    "条件清除后自动恢复正常模式。per-row resilience确保单一样本失败不导致整批评估崩溃。"
)

add_body(
    "出处：DegradationManager._assess_level()（4级），SystemMonitor（3-tier），P2-5/P3 memory。"
)

# --- 5.3 HITL ---
doc.add_heading('5.3 人机协同（HITL）三级干预', level=2)

add_body(
    "HumanInTheLoopManager实现三级人机协同机制："
)

add_table_with_style(
    ["级别", "触发条件", "动作", "系统响应"],
    [
        ["L1 自主", "DMA置信度≥0.85 + 低风险", "自动通过，记录审计日志", "零延迟"],
        ["L2 干预", "0.65≤置信度<0.85 或 中等风险", "人工审核 + 可选修正", "更新检索权重和模型参数"],
        ["L3 升级", "置信度<0.65 或 TFA critical 或 严重冲突", "强制专家审核 + 完整追溯", "阻断自动决策，corrected_label回传"],
    ],
    col_widths=[1.5, 4.0, 3.5, 4.0]
)

add_body(
    "HITL审核结果（corrected_label）回传至管线（P0-4-2 fix），"
    "触发ContrastiveRetrievalUpdater和ContinuousLearningLoop，形成持续改进闭环。"
    "TFA critical风险可触发Priority 1级HITL，实现风险驱动的主动人工介入。"
)

add_body(
    "出处：ARCHITECTURE_UPGRADE.md §6, HITL_TFA Integration, P0-4-2/P1-4/P1-5 memory。"
)

# --- 5.4 Traceability ---
doc.add_heading('5.4 全链路可追溯与审计', level=2)

add_body("系统实现了面向医疗合规的可追溯性基础设施：")
add_bullet("请求级Correlation ID（UUID）：贯穿所有处理阶段，_request_id_ctx ContextVar传递")
add_bullet("阶段性计时日志（_log_stage）：每阶段耗时精确记录到毫秒")
add_bullet("JSONL审计日志（audit_logger.py）：结构化记录每次推理的输入/输出/中间结果")
add_bullet("决策追溯持久化（traceability.py）：保存完整决策链路供事后审查")
add_bullet("统一日志格式（FORMAT_SPECIFICATION.md）：6个模块日志格式统一")
add_bullet("MAPFMException异常体系：6个子类（AgentError, ConfigError, DatasetError, InferenceError, RetrievalError），支持结构化错误码")

add_body(
    "出处：mapfm_ecosystem_repaired.py _start_request/_log_stage/_end_request, audit_logger.py, traceability.py, exceptions.py, FORMAT_SPECIFICATION.md。"
)

# --- 5.5 System Monitor ---
doc.add_heading('5.5 系统健康监控与故障隔离', level=2)

add_body(
    "SystemMonitor（mapfm_utils/system_monitor.py）实现主动健康监控："
)
add_bullet("Ollama健康检查：HTTP /api/tags端点探测 + 延迟测量")
add_bullet("MedTsLLM状态：模型目录和权重文件存在性检查")
add_bullet("GPU监控：通过torch查询CUDA显存使用率")
add_bullet("系统资源：通过psutil监控CPU、RAM、磁盘空间")
add_bullet("后台自动恢复：监控线程定期检查，条件清除后自动恢复NORMAL模式")
add_bullet("中文用户通知：每个降级级别输出中文说明")

add_body(
    "出处：mapfm_utils/system_monitor.py SystemMonitor.check(), DegradationLevel enum, ARCHITECTURE_UPGRADE.md §7。"
)

doc.add_page_break()

# ============================================================
# 六、安全与隐私
# ============================================================
doc.add_heading('六、安全与隐私设计', level=1)

doc.add_heading('6.1 差分隐私梯度保护', level=2)
add_body(
    "PrivacyAgent在梯度更新时添加高斯噪声（标准差σ=0.015，可配置参数secure_gradient_noise_std），"
    "满足(ε, δ)-差分隐私定义。这一机制降低攻击者从梯度更新中反推单个患者训练数据的风险。"
)
add_body(
    "出处：mapfm_ecosystem_repaired.py PrivacyAgent._secure_gradient(), EcosystemConfig.secure_gradient_noise_std。"
)

doc.add_heading('6.2 XOR加密Agent间通信', level=2)
add_body(
    "Agent间消息（AgentMessage dataclass）在传输前通过XOR对称加密保护，包含加密载荷"
    "（encrypted_payload）和路由路径（route_path）字段。加密密钥由TopologyAgent管理。"
)
add_body(
    "出处：mapfm_ecosystem_repaired.py AgentMessage, CommunicationTopologyManager。"
)

doc.add_heading('6.3 PII自动脱敏', level=2)
add_body(
    "desensitizer.py在每次请求处理前自动执行PII（个人身份信息）剥离——"
    "姓名、社保号（SSN）、病历号（MRN）、邮箱、电话、IP地址等。"
    "脱敏后的文本才进入审计日志和知识库。"
)
add_body(
    "出处：desensitizer.py desensitize_text(), README.md Privacy-Aware设计原则。"
)

doc.add_page_break()

# ============================================================
# 七、实验框架
# ============================================================
doc.add_heading('七、实验框架', level=1)

add_body(
    "系统内置四类实验评估框架（mapfm_ecosystem_repaired.py），每类实验均通过"
    "_evaluate_subset()方法执行，输出标准化指标（accuracy, macro_f1, avg_confidence等）："
)

add_table_with_style(
    ["实验", "函数", "研究目标", "实验设计", "报告指标"],
    [
        ["消融实验", "run_ablation_\nexperiments()",
         "量化各模块贡献",
         "全功能 vs. -HITL vs. -TFA vs. -Multimodal（4条件）",
         "autonomous_accuracy, final_accuracy,\nmacro_f1, intervention_rate"],
        ["噪声鲁棒性", "run_robustness_\nexperiments()",
         "评估输入扰动下的稳定性",
         "0% / 10% / 30%关键词掩码噪声（mask_query_keywords）",
         "accuracy, macro_f1 per noise level"],
        ["数据规模\n适应性", "run_data_scale_\nadaptability()",
         "分析样本效率",
         "20%/50%/80%/100%训练数据（per-class分层采样）",
         "accuracy, macro_f1, avg_confidence\nper train fraction"],
        ["常见vs罕见\n疾病", "run_common_\nrare_analysis()",
         "公平性评估",
         "高频(top 25%) vs 低频(bottom 25%)疾病F1对比",
         "common_f1, rare_f1, drop_rate"],
    ],
    col_widths=[2.0, 2.5, 2.5, 4.0, 4.0]
)

add_body(
    "注意：上述实验框架的代码逻辑完备，但当前无已发布的逐项消融实测数据。"
    "已发布的性能数据仅有2026年5月27日测试报告中的整体指标（见第八章）。"
    "per-row resilience（try/except per row）确保单样本失败不导致整批评估崩溃。"
)

add_body(
    "出处：mapfm_ecosystem_repaired.py run_ablation_experiments, run_robustness_experiments, "
    "run_data_scale_adaptability, run_common_rare_analysis, _evaluate_subset。"
)

doc.add_page_break()

# ============================================================
# 八、性能指标
# ============================================================
doc.add_heading('八、性能指标（2026-05-27 测试报告）', level=1)

add_body("以下数据全部来自2026年5月27日测试报告（test_report_2026-05-27 memory，Ollama Llama3:8b运行）：")

add_table_with_style(
    ["指标类别", "指标", "数值", "说明"],
    [
        ["分类", "准确率 (Accuracy)", "84.03%", "119测试样本, 22类, Llama3:8b主引擎"],
        ["分类", "加权F1 (Weighted F1)", "85.23%", "宏平均Precision=94.77%, Recall=86.85%"],
        ["分类", "加权精确率 (Precision)", "94.83%", "假阳性率较低"],
        ["分类", "加权召回率 (Recall)", "84.03%", "5个罕见病类别召回率偏低"],
        ["分类", "平均置信度", "0.8649", "DMA输出"],
        ["分类", "平均延迟", "12.02s/样本", "Ollama推理"],
        ["分类", "完美分类数", "15/22类", "含糖尿病、高血压、中风、阿尔茨海默等"],
        ["分类", "低召回类别", "5类", "F1范围0.40-0.67：Polycythemia Vera等罕见病"],
        ["测试", "单元/集成测试", "71/73 (97.3%)", "2个TFA阈值非阻塞失败（偏离<0.05）"],
        ["测试", "安全测试", "10/10", "加密/脱敏/DP全部通过"],
        ["测试", "性能测试", "6/6", "含缓存、降级"],
        ["测试", "集成测试", "8/8", "全管线端到端"],
        ["测试", "回归测试", "10/10", "历史功能无退化"],
    ],
    col_widths=[2.0, 3.5, 3.0, 4.5]
)

doc.add_page_break()

# ============================================================
# 九、技术栈
# ============================================================
doc.add_heading('九、技术栈', level=1)

add_table_with_style(
    ["层次", "技术选型", "用途"],
    [
        ["语言", "Python 3.14", "全栈开发"],
        ["Web框架", "FastAPI + Uvicorn", "REST API（含多模态上传端点）"],
        ["LLM推理", "Ollama + Llama3:8b", "诊断决策主引擎"],
        ["时序LLM框架", "MedTsLLM（BioBERT骨干, 108M params）", "时序风险预测（需训练）"],
        ["语义嵌入", "all-MiniLM-L6-v2 (128维)", "文本向量化"],
        ["稠密检索", "FAISS IndexFlatIP", "语义相似度检索"],
        ["稀疏检索", "TfidfVectorizer (max 2400 features)", "关键词检索"],
        ["传统ML", "Scikit-learn + NumPy", "Fallback分类器 + 评估指标"],
        ["消息队列", "Redis（可选）", "Agent间异步通信（redis_bus.py）"],
        ["配置", "YAML + 热重载", "60+参数外部化（config.yaml + config_loader.py）"],
        ["日志", "Loguru（结构化绑定）", "统一格式日志（logging_config.py）"],
        ["测试", "pytest", "71+单元/集成测试（tests/目录）"],
        ["文档", "python-docx + fpdf2 + LaTeX", "报告/数学公式/论文"],
        ["模型源", "HuggingFace（hf-mirror.com镜像）", "MiniLM + BioBERT下载"],
    ],
    col_widths=[2.5, 5.5, 5.0]
)

doc.add_page_break()

# ============================================================
# 十、已知局限与未来方向
# ============================================================
doc.add_heading('十、已知局限与未来方向', level=1)

doc.add_heading('10.1 已知局限', level=2)

add_bullet("罕见病召回率偏低：5类疾病F1=0.40-0.67（Polycythemia Vera, AMD, MI, Breast Cancer, Leukemia），原因是medNo.22.csv中这些类别的训练样本不足")
add_bullet("MedTsLLM权重未训练：reprogramming/output层随机初始化，当前不产生有临床意义的风险预测。需标注医疗时序数据训练（project_medtsllm_deployment memory）")
add_bullet("TFA阈值偏保守：2个TFA单元测试失败（偏离<0.05），极端异常值场景下风险等级可能低估（test_report_2026-05-27 memory）")
add_bullet("推理延迟：平均12.02s/样本，对实时急诊场景需优化")

doc.add_heading('10.2 未来方向', level=2)

add_bullet("罕见病数据扩充：针对5个低召回类别定向采集临床数据")
add_bullet("MedTsLLM训练：收集标注医疗时序数据，训练reprogramming层，使TFA产生有临床意义的风险预测")
add_bullet("模型评估：评估Llama3.1/3.2等更新版本在医疗领域的推理能力")
add_bullet("推理加速：引入llama.cpp/vLLM等推理引擎降低延迟")
add_bullet("联邦学习：实现多中心联邦训练框架，在不共享原始数据的前提下提升泛化能力")

doc.add_heading('10.3 文档与交付物', level=2)

add_body("项目已产出的配套文档：")

add_table_with_style(
    ["文档", "路径/格式", "内容"],
    [
        ["框架综述报告", "MAPFM_HMAE_Framework_Report.docx", "11章, ~12,700字, 7表格"],
        ["数学基础PDF", "docs/HMAE_Mathematical_Foundations.pdf", "24页, 4章节, LaTeX编译"],
        ["架构升级文档", "ARCHITECTURE_UPGRADE.md", "v2.0 TFA深度融合完整说明"],
        ["部署指南", "DEPLOYMENT_GUIDE.md", "环境配置 + 常见问题"],
        ["格式规范", "FORMAT_SPECIFICATION.md", "6模块统一日志格式（hmae_format_unification memory）"],
        ["MedTsLLM部署", "deploy_medtsllm.py", "5/5部署检查 + 4/4冒烟测试通过"],
    ],
    col_widths=[3.0, 5.0, 5.0]
)

# ============================================================
# Save
# ============================================================
output_path = "C:/Users/Lenovo/Desktop/MAPFM_HMAE_Innovation_Report.docx"
doc.save(output_path)
print(f"Innovation report saved to: {output_path}")
print(f"Document generated successfully.")
