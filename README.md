# 安护智链 CareLink — 2026 数媒创赛软件应用版

当前产品品牌统一为 **CareLink**，新版 ZIP 根目录为 `CareLink_2026`。`careguard_*.py`、浏览器事件、已有案例存储键与 JSON schema 保留原技术名称以兼容既有数据；原始 MAPFM 快照与历史报告保持原貌。本机开发目录仍为 `CareGuard_2026`，与新版解压目录名称不同，但启动入口相同。

新同事第一次拿到交付包，请先双击阅读 [记事本快速版](打开网页_新同事先看这个.txt)，按步骤解压、安装依赖并启动本机网页；需要完整的模型准备和故障排查时，阅读 [详细启动指南](START_HERE_新同事打开网页.md)。不要直接打开 `careguard_web/index.html`，网页必须由本机服务连接工程接口。

> 建议申报：**自主选题｜移动与网络应用开发类**  
> 核心定位：面向养老机构交接班的多智能体风险筛查、循证核验、人工复核与审计平台。  
> 使用边界：科研与竞赛演示原型，不替代医生或护理专业人员。

参赛前先阅读 [本届作品增量核验表](COMPETITION_DELTA.md)：历史获奖项目与当前 CareLink 的实质差异仍须由团队对照原始参赛包核验；本文件和网站不能自行证明参赛资格。

前瞻神经研究接口保留训练输入范围检查与内部测试重抽样区间。另新增 [MedQuAD 全量来源问答](docs/MEDQUAD_QA.md)：逐 XML 核查官方压缩包，全部 47,441 个问题参与词汇/IDF 拟合，其中有答案的 16,407 条进入本地回答索引；问答与疾病发病预测严格分开。

工作台现在有互不混用的三条研究路径：[8 年新发糖尿病发表规则](docs/DIABETES_PREDICTION.md)、3 年新发糖尿病 MAPFM TFA 神经研究头，以及 [MedQuAD 原文问答检索](docs/MEDQUAD_QA.md)。前者是现场计算的确定性规则；第二项使用真实开放 NAGALA 随访队列训练的新增研究权重，非最初历史包原有权重；第三项融合 TF-IDF 与预训练语义编码器，并附独立 LiveQA 不完整标注问法测试，不是 MAPFM 微调，更不能从问答预测未来糖尿病。糖尿病足网页和对外接口已从本版移除；原始历史工程快照不被改写。所有功能未经目标人群外部临床验证，不用于临床决策。

问答泛化的后续验收见 [自然问法与上线门禁](docs/MEDQUAD_ROBUSTNESS.md)：新候选在封存题退步，未替换现有排序；这份否定结果也进入网页状态与交付审计。

另以 [MEDIQA 2019 官方问答集做外部核验](docs/MEDQUAD_MEDIQA2019.md)：严格对齐的 52 道题上，当前版已知答案 Top-1 / Top-3 分别为 22/52、32/52。答案字段候选把 Top-3 提到 35/52，却使 Top-1 降到 21/52，未通过预设上线门槛，线上排序保持原版。这些是部分正例检索，不是完整答案准确率或临床验证。

## 参赛演示快速启动

完整压缩包的网页／代码地图、打包边界与人工核验事项见 [交付包总览](SUBMISSION_PACKAGE_OVERVIEW.md)；最初 MAPFM 工程的独立源码快照及排除的本机环境见 [原工程快照说明](ORIGINAL_PACKAGE_SNAPSHOT.md)；现场流程见 [三分钟演示稿](DEMO_3_MIN.md)。可先运行 `python start_demo.py --check` 检查依赖、605 行数据与 Ollama 可达性，再用 `python start_demo.py` 启动本机网站。`python package_competition.py` 会在 `releases/` 生成带 SHA-256 清单的完整交付 ZIP，不覆盖旧包。

推荐使用独立产品前端（页面、工作台与筛查 API 在同一本机地址，不依赖外部字体或前端构建服务）：

```powershell
python -m uvicorn careguard_site:app --host 127.0.0.1 --port 8511
```

打开 `http://127.0.0.1:8511/` 查看产品首页；`?view=workspace&case=chest`、`?view=workspace&case=stroke`、`?view=workspace&case=change` 可直达对应合成案例，`?view=evidence` 展示带时间戳的本机证据快照。首页和信号地图的 Canvas 粒子仅作合成案例的信息流示意，不表示实时推理结果；动画可暂停，也会遵循系统的减少动态效果设置。新增的医学观察视觉层展示合成案例 HR / SpO₂ / RR，并把首页快速选择、工作台案例及图谱选点联动起来；动态节律线是数学绘制的图形示意，不是实测心电、设备数据或医学判断。筛查按钮调用同源 `/screening/engineering`：用户填写的单次体征先由原始 MAPFM CSV 预处理器解析，再作为当前模型的临床文本输入进入原始多智能体引擎，页面显示本次解析数量、源代码一致性与实际推理后端；不是前端伪造结果，也不伪称单次输入具有时序预测。源码逐文件对照与实际调用路径见 [工程合并核查](ENGINE_SOURCE_MERGE.md)，本地可运行 `python careguard_engineering_smoke.py --require-ollama`，或访问 `/engineering/status` 核对指纹。工作台会对常见个人标识格式做提交前提示，并显示本次请求执行轨迹；证据页另设当前浏览器会话核验板，与历史快照分开。格式检测不能替代人工脱敏，刷新会清空会话状态。人工复核与审计 JSON 在浏览器内完成；“加入我们”是独立且明确同意后才向外发送的联系表单。此入口目前仅供本机预览，尚未公开部署。

“交互工作台”现在合并自然语言问答、三年新发糖尿病研究估计、MedQuAD 来源检索与独立人工盲评（`?view=workspace#medical-language-studio`，盲评区为 `#review-desk`）。明确且完整的中文／英文基线信息才会调用 MAPFM TFA 已训练权重；普通英文医学知识问答只检索来源，不输出疾病概率。缺项、冲突、其他疾病或其他时间范围均不伪造概率；这项输入适配不能证明模型已跨人群泛化，详见 [自然语言工作台说明](docs/MEDICAL_LANGUAGE_WORKSPACE.md)。原 `/site/medquad-review` 与 `?view=review` 地址回到同一工作台盲评区。审核者自行从本机选择题包，页面内标注并导出 JSON，私有原始题包不会被网站公开或上传。单文件离线备份仍保留在 `tools/medquad_blind_review.html`，流程见 [独立盲评说明](docs/MEDQUAD_BLIND_EVAL_20261014.md)。

首页和工作台现在有六个可载入的合成演示案例：前三个为项目预置情境，后三个从 `demo_assets/sample_vitals.csv` 的三个单次体征行构建信息缺口练习，可通过 `?view=workspace&case=baseline`、`?view=workspace&case=recheck`、`?view=workspace&case=context` 直达。每个新增案例都标明来源；样本行没有患者身份、症状或时序关联，不能当作真实病例或诊断依据。案例卡采用毛玻璃材质，仍保持文字与来源可读。

首页的“原始问题”展台接入 `medNo.22.csv`，支持英文主题／问题检索、主题筛选和逐条查看来源。该数据集包含 605 条医学问答，**不是患者病例库**；页面默认精选六条养老照护相关的问题，展示原始 ID、问题和有限回答摘录。接口 `/site/dataset/questions` 直接读取本地 CSV；历史问答可能过时或具有美国语境，不参与工作台筛查，也不代表现行临床指南。

`?view=lab` 打开可操作的三维研究图谱：81 个由三个预置案例生成的合成输入变体、80 个按当前门控代码枚举的规则状态，以及 12 个素材／代码／测试／缺口来源节点。每个可操作数据中心周围增加确定性视觉粒子，形成高密度粒子场；全局密度滑块只改变粒子显示，不增加数据量。三张图均支持旋转、缩放、筛选、精确选点和 CSV 导出；选点可载入工作台输入或跳转对应证据与材料。坐标定义、生成公式、来源和不能推出的结论记录于 [RESEARCH_LAB_METHOD.md](RESEARCH_LAB_METHOD.md)。图中没有真实患者样本或临床准确率。

`?view=join` 是项目合作联系页面。三张照片来自项目历史路演材料，仅作档案展示；页面介绍可核对的项目部分与合作流程，表单的参与方向提示和字数会实时更新。表单不收集患者资料。邮件投递走服务端 `/site/join`，固定收件人为 `yuanjiegu52@gmail.com`，不会把密钥暴露给浏览器；未配置通道时页面会禁用发送并明确显示“尚未配置”，不会假装投递成功。可任选以下一种配置后重启网站进程：

```powershell
# 方案 A：Resend。发件地址需满足邮件服务商的域名验证要求。
$env:CAREGUARD_MAIL_FROM = 'CareLink <team@your-verified-domain.example>'
$env:CAREGUARD_RESEND_API_KEY = '<在本机环境变量中填写真实密钥>'

# 方案 B：SMTP（不用 Resend 时选择；端口可为 465 或 587）。
$env:CAREGUARD_MAIL_FROM = 'CareLink <team@your-domain.example>'
$env:CAREGUARD_SMTP_HOST = 'smtp.your-provider.example'
$env:CAREGUARD_SMTP_PORT = '465'
$env:CAREGUARD_SMTP_USER = '<账号>'
$env:CAREGUARD_SMTP_PASSWORD = '<应用密码>'
```

不要将密钥写入源码、提交到版本库或贴到聊天中。`GET /site/join/status` 可检查通道是否已配置；返回 `ready: true` 只代表配置完整，不能替代真实收件测试。当前表单只在邮件服务确认接收后显示成功，未本地保存申请人信息。

旧版 Streamlit 页面仍保留作兼容和备份：

```powershell
streamlit run careguard_app.py
```

在当前电脑上，可直接用原项目的已安装环境启动：

```powershell
cd 'C:\Users\Lenovo\Documents\ChatGPT\数媒\CareGuard_2026'
& 'C:\Users\Lenovo\Desktop\MAPFM_medical_AI_repaired_complete\.venv\Scripts\python.exe' -m streamlit run careguard_app.py --server.port 8510
```

浏览器打开 `http://localhost:8510/` 查看旧版 Streamlit 产品介绍页；现场操作可直接进入 `http://localhost:8510/?focus=workspace`，真实性与使用边界可直接进入 `http://localhost:8510/?focus=boundary`。这三个入口都在本机运行，不是公开部署地址。若本机 Ollama 不可达，界面会明确显示降级状态并隔离诊断标签；这不影响合成案例的演示流程。

首页还提供交接班情境拆解、三个合成案例、系统协作链和证据边界说明。点击案例卡会打开工作台并载入对应输入；可直接使用 `?focus=workspace&case=chest`、`?focus=workspace&case=stroke` 或 `?focus=workspace&case=change`。案例卡是静态情境介绍，不代表实时模型输出。

答辩前建议在同一环境运行 `python careguard_smoke.py --require-ollama`，并查看“真实性证据板”的最近自检时间。此脚本仅使用合成案例，不保存护理原文。

比赛专用入口不需要登录，内置合成案例，提供人工复核、浏览器本地交接摘要 TXT 和审计 JSON 导出。交接摘要只在本次实际筛查和复核之后出现；输入变化会使它失效。详细升级说明见 [COMPETITION_UPGRADE.md](COMPETITION_UPGRADE.md)，主张与证据边界见 [EVIDENCE_MATRIX.md](EVIDENCE_MATRIX.md)。

---

# 旧版 MAPFM 科研框架说明（不代表本次参赛已验证能力）

以下为原项目历史文档，含设计目标与研究性表述；请勿将其全部视为本次比赛已交付功能或临床有效性证据。参赛主张以 [EVIDENCE_MATRIX.md](EVIDENCE_MATRIX.md) 为准。

## MAPFM — Heterogeneous Multi-Agent Medical AI Ecosystem

MAPFM (Multi-Agent Perception-Fusion Medical) 是一个**异构多智能体医疗 AI 临床决策支持系统**，模拟从患者问诊输入到诊断输出、风险评估、人工审核、共识投票的完整临床辅助决策流程。

## Architecture

```
Patient Query
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│ Stage 1  Perception Agent                                     │
│           Text encoder + Image ViT patching → Cross-Attention  │
│           Fusion → Context Vector                              │
└──────────────────────┬───────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ Stage 2  RAA (Retrieval Augmented Agent)                      │
│           ┌─ Mixed-RAG:   TF-IDF + MiniLM/FAISS fusion        │
│           ├─ Rerank-RAG:  + similarity + recency + authority   │
│           └─ Adaptive-RAG: uncertainty-gated deep/shallow      │
│           Nash Game-Theoretic strategy selection with DMA      │
└──────────────────────┬───────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ Stage 3  Tri-Source Fusion → Knowledge Fusion → Verification  │
│           Human(0.95) + Authoritative(0.90) + Retrieval(0.75) │
│           SimHash dedup + conflict detection + fact-checking   │
└──────────────────────┬───────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ Stage 4  DMA (Decision Making Agent)                          │
│           Primary:  Ollama Llama3:8b (local LLM)              │
│           Fallback: TF-IDF centroid + retrieval + lexical     │
│           Platt scaling calibration + disease disambiguation   │
└──────────────────────┬───────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ Stage 5  TFA (Temporal Foreseeing Agent)                      │
│           MedTsLLM-v1.5 / Heuristic TCN+LSTM+Transformer      │
│           Short(24h) / Mid(30d) / Long(12m) risk windows      │
│           DMA-confidence-aware calibration                    │
└──────────────────────┬───────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ Stage 6  HITL (Human-in-the-Loop)                             │
│           DMA low confidence / TFA critical risk / conflicts  │
│           Interactive review → Model & retrieval updates      │
└──────────────────────┬───────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ Stage 7  Hierarchical Consensus + Comprehensive Answer        │
│           FORCE_HITL → DMA_VETO → NORMAL_VOTE (3-layer)      │
│           DMA(2票) + TFA(1票) + Verification(1票)             │
└──────────────────────┬───────────────────────────────────────┘
                       ▼
                 Final Report
```

## Agents

网页技术架构：打开 `http://127.0.0.1:8511/?view=home#mapfm-architecture`，可点选以下十个工程模块，并切换护理交接、3 年糖尿病研究预测和 MedQuAD 来源问答路径。每个模块展示当前默认实现的职责、输入、输出与代码方法；结构图是调用关系说明，实际运行状态见工作台。

详细技术手册位于同页 `#architecture-handbook`：十个模块分别有三步执行机制、上下游协作关系和合成数据流示例；前后箭头可连续阅读。实现范围在当前模块下集中说明，正文与架构图选择同步更新。

| Agent | Role | Key Capability |
|---|---|---|
| **Perception** | 多模态感知编码 | RealPerceptionAgent：实际输入的确定性特征与可选预计算特征；旧模拟类仍保留 |
| **RAA** | 检索增强 | 3 RAG strategies, FAISS dense index, game-theoretic selection |
| **DMA** | 诊断决策 | Ollama Llama3:8b primary + legacy fallback, Platt calibration |
| **TFA** | 时序研究预测 | 旧时序分支按任务验证可用性；新增 forecast_prospective 接入 3 年糖尿病研究权重 |
| **Fusion** | 知识融合去重 | SimHash dedup, conflict detection, area consensus |
| **Verification** | 来源核验 | 来源身份、可追溯标识、时间与基础风险信号；不作为医学真值判定 |
| **Consensus** | 层次化共识 | 3-layer voting: FORCE_HITL → DMA_VETO → NORMAL_VOTE |
| **Privacy** | 隐私与传输 | 默认 AES-GCM 认证加密；反馈梯度裁剪加噪，无形式化隐私预算保证 |
| **Maintenance** | 健康监控 | Heartbeat, fault isolation, abnormal output detection |
| **Topology** | 通信拓扑 | Star/Mesh routing, encrypted messaging, retry queue |

## Integrated Modules

| Module | Function |
|---|---|
| `OnlineKnowledgeBaseManager` | Dynamic KB with TF-IDF + FAISS dual index, authoritative crawl simulation |
| `TriSourceKnowledgeFusion` | Weighted fusion of human/authoritative/retrieval knowledge sources |
| `KnowledgeDistillationEngine` | Compress verified docs into context vectors + distilled text |
| `HumanInTheLoopManager` | 3-level HITL: autonomous → intervention → parameter update |
| `ContrastiveRetrievalUpdater` | Positive/negative sample contrastive feedback for retrieval weights |
| `ContinuousLearningLoop` | Online learning triggered at ≥10 feedback records |
| `DegradationManager` | 4-level graceful degradation with automatic `safe_call` fallback |

## Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) (optional, for LLM inference)

### Setup

```bash
# Clone and enter the project
cd MAPFM_medical_AI_repaired_complete

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Pull the LLM model (optional — legacy fallback works without it)
ollama pull llama3:8b
```

### Run Demo

```bash
python mapfm_ecosystem_repaired.py
```

This runs 8 collaborative tasks on random test samples, prints per-task diagnostics (DMA, RAA, TFA, Fusion, Consensus, HITL), then executes ablation, robustness, data-scale adaptability, and common-vs-rare disease experiments.

### Run FastAPI Server

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

### Run Tests

```bash
pytest -q
```

## Configuration

All hard-coded parameters are externalized into `SystemConfig` and `EcosystemConfig` dataclasses. Override via `config.yaml`:

```yaml
random_seed: 42
confidence_threshold: 0.62
ollama_model_name: "llama3:8b"
ollama_timeout_seconds: 10.0
enable_tfa: true
enable_hitl: true
enable_consensus: true
consensus_threshold: 0.667
nash_max_rounds: 6
# ... 60+ configurable parameters
```

Key configuration groups:
- **Model**: `ollama_model_name`, `ollama_temperature`, `ollama_num_ctx`
- **Thresholds**: `confidence_threshold`, `retrieval_relevance_threshold`, `high_risk_tfa_threshold`
- **Weights**: `dma_centroid_weight`, `dma_retrieval_weight`, `dma_lexical_weight`, `dma_tfa_weight`
- **Feature flags**: `enable_tfa`, `enable_hitl`, `enable_consensus`, `enable_multimodal`, `enable_privacy`

## Experiments

The system includes four built-in experiment suites:

| Experiment | Description |
|---|---|
| **Ablation** | Full ecosystem vs. no-HITL / no-TFA / no-Multimodal |
| **Noise Robustness** | Performance at 0% / 10% / 30% keyword masking noise |
| **Data-Scale Adaptability** | Accuracy vs. training data fraction (20%–100%) |
| **Common vs. Rare** | F1 disparity between high-prevalence and low-prevalence diseases |

## File Structure

```
├── mapfm_ecosystem_repaired.py   # Main ecosystem (~4650 lines)
├── utils.py                      # Embedding, SimHash, tokenization, etc.
├── exceptions.py                 # MAPFMException hierarchy (6 subclasses)
├── logging_config.py             # Structured Loguru logging
├── config_loader.py              # YAML config with hot-reload
├── desensitizer.py               # PII masking
├── audit_logger.py               # JSONL audit trail
├── traceability.py               # Decision trace persistence
├── redis_bus.py                  # Optional Redis message queue
├── api.py                        # FastAPI REST endpoints
├── config.yaml                   # Deployable configuration defaults
├── requirements.txt              # Python dependencies
├── tests/
│   ├── test_dma.py               # DMA fallback contract test
│   ├── test_retrieval.py         # Retrieval strategy tests
│   ├── test_utils.py             # Utility function tests
│   └── test_exceptions.py        # Exception hierarchy tests
├── examples/
│   └── run_single_request.py     # Single-request example
├── original/                     # Original source archive
└── logs/                         # Runtime logs
```

## Design Principles

### LLM + Traditional ML Hybrid
DMA runs Llama3:8b as the primary inference engine. When Ollama is unreachable, the system falls back to a deterministic TF-IDF centroid + retrieval-weighted classifier — no external dependency required at runtime.

### Graceful Degradation
Every component call is wrapped via `DegradationManager.safe_call()`. Single-point failures (Ollama crash, FAISS index corruption, TFA timeout) trigger automatic fallbacks; the pipeline continues with reduced functionality rather than aborting.

### Safety by Design
- **3-layer consensus voting** prevents over-reliance on any single agent
- **HITL** triggers on low confidence, critical risk, verification conflicts, or TFA-diagnosis divergence
- **Platt scaling** calibrates LLM confidence against empirical correctness
- **Chinese risk labels and recommendations** for clinical readability

### Privacy-Aware
Inter-agent messages use authenticated AES-GCM by default. Feedback gradients are clipped and receive noise (`secure_gradient_noise_std`); without a privacy accountant this is not a formal differential-privacy guarantee. PII desensitization runs on every query before audit logging. The legacy simulated XOR class remains available for historical compatibility.

### Research-Ready
Configurable experiment suites (ablation, robustness, adaptability, common-vs-rare), structured request tracing with correlation IDs, per-stage latency logging, and JSONL audit trails make the system suitable for medical AI research and simulation.

## Compatibility Notes

- **Ollama** is the preferred DMA runtime. Set `allow_dma_legacy_fallback=true` (default) for offline environments.
- **MiniLM** (`sentence-transformers/all-MiniLM-L6-v2`) is lazy-loaded. Falls back to deterministic hash embeddings if unavailable.
- **FAISS** is optional — dense retrieval falls back to NumPy dot-product scan.
- The original source from `GU YUANJIE.docx` is preserved in `original/`.
- `# === MODIFIED:` annotations mark all changes from the original code.
