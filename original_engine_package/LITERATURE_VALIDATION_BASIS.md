# MAPFM 竞赛升级版：文献依据与实现边界

## 项目定位

本版本定位为“面向免陪照护场景的可追溯多智能体临床风险辅助决策研究系统”。它可以用于科研、流程演示与前瞻性验证设计，不能替代医生诊断，也不能在缺少外部验证时自动放行临床建议。

## 文献审视后作出的关键纠偏

1. **MedTsLLM 不再被冒充为 24 h/30 d/12 m 恶化风险模型。** 原论文和官方代码的主要任务是 ECG/呼吸波形的语义分割、边界检测和异常检测；论文中的重编程层及任务头需要训练。当前项目没有对应结局标签和合格检查点，因此 TFA 只做输入信号质量摘要并撤销投票权。只有配置任务为 `clinical_deterioration_risk`、包含完整训练层且声明校准/外部验证的检查点后，适配器才允许输出。

2. **影像输入真实进入管线，但不宣称影像诊断。** 系统读取上传文件的实际像素，并形成可审计的灰度/梯度描述符用于传输和融合测试。BiomedCLIP 证明大规模医学图文预训练可用于医学表征，但任何具体诊断任务仍需独立训练与验证，所以当前元数据明确标记 `image_interpretation_validated=false`。

3. **动态知识更新只接受真实 PubMed 记录。** 新客户端使用 NCBI ESearch + EFetch，保存 PMID、DOI、期刊、原始链接、检索式和检索时间。网络失败返回错误和零文献，不再生成“最新权威知识”句子。

4. **“事实核验”改为可证实的来源核验。** 代码仅判断来源标识、可追溯链接、时间和危险措辞，不再声称自动判定医学观点真假。输出固定声明 `provenance_freshness_and_safety_signals_not_claim_truth`。

5. **评估遵循组级隔离和透明报告。** TRIPOD+AI 要求透明报告数据来源、开发/评估过程和模型性能；FUTURE-AI 强调可信、可部署与全生命周期治理。因此本项目按患者 ID（若存在）或规范化问题文本分组切分，重复问题不得跨集合。

## 当前数据审计

- 规范化后：591 行、22 类。
- 新分割：训练 475 行、测试 116 行。
- 训练/测试规范化问题组重叠：0。
- 测试集中仍有 109/116（93.97%）问题直接包含疾病标签。

因此 `medNo.22.csv` 只能作为医学知识问答/软件回归数据，不能支撑“临床诊断准确率”主张。代码在训练语料中默认屏蔽精确标签词，并强制同时报告“原始问题”和“标签词屏蔽压力测试”结果；二者都不等于外部临床验证。

## 已落实的工程修复

| 原问题 | 当前处理 |
|---|---|
| 默认绑定模拟感知/验证/隐私/LoRA | 默认切换为真实输入感知、来源核验、AES-GCM；反馈校准如实命名 |
| 图像、检验、临床文本未进入推理 | 实际像素、检验项和临床文本均进入感知；文本/检验进入后续检索与决策输入 |
| 随机 MedTsLLM 头输出风险 | 无合格检查点即阻断概率输出；禁止 query-hash 合成时序 |
| 伪造在线文献 | 改用 NCBI E-utilities；失败时不回退到假文献 |
| 随机行切分导致泄漏 | 改为 patient/question group split，自动审计零组重叠 |
| “LoRA”实际只改偏置 | 运行时更名为反馈校准；新增独立 `train_lora.py` 执行真实 PEFT LoRA |
| 固定密钥 XOR | AES-GCM、每条消息新 nonce、环境密钥或临时会话密钥；篡改检测已测试 |
| 人工审核按钮不闭环 | 新增审核持久化 JSONL 与出队方法 |
| 缺依赖 | 增加 multipart、Streamlit、Plotly、cryptography；LoRA 依赖独立文件 |
| API/仪表盘忽略 YAML | 两个入口均从项目目录加载 `config.yaml` |
| 消息拓扑装饰化 | 7 个阶段转换均实际路由，敏感载荷只在消息对象保留加密版本 |
| 未验证结果可能自动通过 | 临床就绪门最终覆盖共识；缺外部验证工件时一律 `research_only` |
| 内置明文账号 | 删除内置密码，改为环境变量/PBKDF2-HMAC-SHA256 |

## 竞赛前必须补齐、但不能靠代码伪造的内容

1. 明确一个临床结局，例如“住院老年患者未来 24 h 跌倒/压疮风险”，不要同时宣称 22 类诊断和三时间尺度预后。
2. 获得带患者级 ID、时间戳、结局定义和伦理/脱敏说明的数据；按患者和时间外切分。
3. 预注册主要终点和亚组；报告 AUROC、AUPRC、敏感度、特异度、Brier 分数、校准截距/斜率和决策曲线。
4. 在独立医院/时间段做外部验证，并记录失败案例、缺失数据、分布漂移和人工接管率。
5. 由临床负责人签署验证工件后再考虑打开临床门；修改 JSON 文件本身不等同于审批。

## 主要依据

- MedTsLLM paper: https://arxiv.org/abs/2408.07773
- MedTsLLM official repository: https://github.com/flixpar/med-ts-llm
- BiomedCLIP: https://arxiv.org/abs/2303.00915
- Microsoft Research BiomedCLIP page: https://www.microsoft.com/en-us/research/publication/biomedclip-a-multimodal-biomedical-foundation-model-pretrained-from-fifteen-million-scientific-image-text-pairs/
- TRIPOD+AI: https://www.bmj.com/content/385/bmj-2023-078378
- FUTURE-AI: https://www.bmj.com/content/388/bmj-2024-081554.long
- MedRAG/MIRAGE: https://arxiv.org/abs/2402.13178
- NCBI E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- NCBI API overview: https://www.ncbi.nlm.nih.gov/home/develop/api/
- Calibration tutorial: https://pubmed.ncbi.nlm.nih.gov/32106284/
- NIST AES-GCM (SP 800-38D): https://csrc.nist.gov/pubs/sp/800/38/d/final

