/* Detailed technical copy checked against the current implementation. */
window.CareGuardArchitectureDetails = Object.freeze({
  Perception: {
    title: "把现场记录，变成可读取的上下文。",
    purpose: "保留文字、测量值和输入模态之间的关系，为后面的检索与推理准备统一表示。",
    steps: [
      ["拼接实际输入", "合并问题原文、预处理生成的 clinical_text，以及化验项目的名称、数值、单位和异常标记。空字段跳过，已有内容进入同一段上下文。"],
      ["构建特征表示", "文本交给 semantic_embedding；可选图像读取像素描述或外部预计算特征。图像缺失时用零向量记录，避免编造视觉内容。"],
      ["融合并记录模态", "有图像时按文本 0.80、图像 0.20 组合，再做归一化；同时返回是否消费临床文本、化验条目数、图像来源等元数据。"]
    ],
    before: ["网页 / 预处理器", "交接文本、单次体征、可选化验与图像"],
    after: ["RAA 与协作引擎", "编码上下文参与检索策略比较，并与后续蒸馏上下文融合"],
    cooperation: "调用由 HeterogeneousMultiAgentEcosystem 组织。Perception 输出 context_vector，Topology 记录向 RAA 传递的问题摘要和向量维度。",
    example: {context: "合成交接记录，用于解释输入流转。", input: "“夜间突发胸痛，伴大汗；已呼叫负责人。”加上 HR 112、SpO₂ 91%、RR 25。", processing: "预处理器把体征编入 clinical_text；感知模块将其与原始叙述一起编码。", output: "context_vector、text_vector，以及 clinical_text_consumed 等模态记录。"},
    scope: "默认实现是 RealPerceptionAgent。图像能力限于实际输入描述与特征接入；工程保留的旧模拟编码类不是当前默认类。"
  },
  RAA: {
    title: "让推理先有材料可以核对。",
    purpose: "在知识索引中寻找与当前问题相关的资料，并记录为什么采用某种检索策略。",
    steps: [
      ["形成候选资料", "Mixed-RAG 合并词面与稠密检索，Rerank-RAG 对候选重新排序；FAISS 是否启用取决于依赖与配置。"],
      ["适配问题复杂度", "Adaptive-RAG 计算查询不确定性；较高时扩大检索并兼顾主题多样性，较低时使用较快的混合检索。"],
      ["比较质量与成本", "协作引擎比较检索策略与 DMA 决策模式的收益、成本，记录选定策略、轮数、文档数量、相关度和耗时。"]
    ],
    before: ["Perception / 协作引擎", "问题文本与编码上下文，检索参数和当前知识索引"],
    after: ["Fusion", "主检索、重排、自适应检索产生的候选资料批次"],
    cooperation: "原始协作链还会引入可用的人工资料和近期来源资料。RAA 的候选只是起点，后续仍由 Fusion 去重、Verification 核查出处。MedQuAD 网页问答另走独立索引。",
    example: {context: "同一条合成胸痛交接的资料检索。", input: "当前问题文本、编码上下文与本次 top_k 配置。", processing: "比较 mixed、rerank、adaptive 的候选，保存所选策略及检索元数据。", output: "候选文档的 ID、主题、内容与相关度；最终可显示来源数由核验结果决定。"},
    scope: "检索相关度只用于资料匹配。检索不到或没有资料通过后续核验时，动态来源可以为 0。"
  },
  Fusion: {
    title: "把多路检索，整理成一份上下文。",
    purpose: "避免重复材料反复占据上下文，同时把需要进一步核查的差异显式记录下来。",
    steps: [
      ["合并与排序", "展开多个文档批次，先按相似度排序。启用三源融合时，上游先整理人工、近期来源和检索资料，再交给本模块。"],
      ["识别重复与差异", "相同文档 ID 或 SimHash 汉明距离接近的内容会去重；对部分高排名、不同主题的条目记录距离较大的候选冲突。"],
      ["生成融合摘要", "按主题平均相关度与单篇相关度重新组织资料，输出输入数、去重数、冲突数和候选冲突记录。"]
    ],
    before: ["RAA / 三源资料整理", "多路候选资料与可用的人工、近期来源条目"],
    after: ["Verification 与蒸馏模块", "去重文档、融合摘要、候选冲突条目"],
    cooperation: "Verification 会根据融合摘要提高部分候选冲突资料的核查门槛。时序分支可用时，fuse_with_tfa 还可组织 DMA、TFA 与风险检索的综合输出。",
    example: {context: "假设三个检索策略返回了同一条资料。", input: "mixed、rerank、adaptive 的多个批次中出现相同 doc_id。", processing: "合并时保留一个条目，记录删掉的重复数量，再检查高排名资料之间的差异。", output: "fused_docs 与 input_docs、dedup_removed、conflicts 等摘要字段。"},
    scope: "当前冲突检测基于主题与内容指纹，是需要核查的工程信号，不是自动理解并裁定医学观点真伪。"
  },
  Verification: {
    title: "问清出处，再决定资料是否进入推理。",
    purpose: "把来源可追溯性、时间信息和基础风险信号转成可检查的接受或拒绝记录。",
    steps: [
      ["检查来源身份", "读取 PubMed 标识、DOI、来源网址、检索时间或人工审核者标识；结合基础文本风险信号计算可追溯性分数。"],
      ["检查时效与候选冲突", "核对文档更新时间与配置的有效期。融合阶段标出的候选冲突会使核查更严格，并保留相应记录。"],
      ["返回可追踪的判定", "输出接受列表、拒绝数量、拒绝原因与总体核验状态。没有文档通过时，协作引擎明确记录 evidence_unavailable。"]
    ],
    before: ["Fusion", "去重文档与候选冲突摘要"],
    after: ["DMA / Consensus", "核验后的上下文，以及独立的核验状态与原因"],
    cooperation: "通过的资料才进入后续上下文蒸馏与 DMA 推理；核验摘要也交给 Consensus。TFA 分支另有 verify_tfa_report 检查可用性与报告一致性。",
    example: {context: "假设一条候选资料没有可追溯的来源信息。", input: "候选内容与缺失的 DOI、PMID 或来源元数据。", processing: "按当前门槛计算来源分数，并核对更新时间。", output: "接受或拒绝记录，以及 stale、fact_score_low 等代码原因；页面动态来源数随实际结果显示。"},
    scope: "代码字段 fact_score 在当前实现中衡量来源与可核查信号，不能读作疾病判断的正确率。"
  },
  DMA: {
    title: "结合记录和资料，执行本次推理。",
    purpose: "调用本机推理后端，把当前输入和可用来源组织成结构化候选输出，记录实际执行状态。",
    steps: [
      ["接收本次上下文", "接口接收问题、上下文向量与核验资料。协作引擎已完成融合与蒸馏；当前 Ollama 请求主要由问题文本与资料文本构成。"],
      ["调用本地生成", "优先通过本机 HTTP 接口调用配置的 Ollama 模型，解析结构化返回，并记录 ollama_local_http 与生成验证标记。"],
      ["校准字段并处理异常", "处理内部评分与复核标记；若后端失败且配置允许，则转入旧路径并标记降级。结果继续接受监测、共识门控和网页展示层处理。"]
    ],
    before: ["Verification / 蒸馏模块", "问题、已核验资料与融合后的上下文"],
    after: ["TFA / Consensus / 展示层", "候选推理输出、实际后端、内部评分与复核标记"],
    cooperation: "Maintenance 检查异常输出；TFA 时序分支可读取 DMA 上下文；Consensus 汇总其结果。CareLink 展示层进一步把输出组织为可人工复核的交接线索。",
    example: {context: "合成记录在本机推理服务在线时运行。", input: "交接文本、单次体征编成的临床文本，以及本次通过核验的资料。", processing: "实际发起 Ollama 请求，解析返回并标记运行后端。", output: "dma_backend、ollama_generation_verified 与本次候选结果；临床标签不会直接成为网页疾病概率。"},
    scope: "DMA 的 confidence 是内部评分。未来三年糖尿病研究概率由 TFA 专用权重计算，两者用途与输入不同。"
  },
  TFA: {
    title: "把结局、时间窗和权重对应起来。",
    purpose: "为明确的研究预测任务提供计算入口。当前已训练并开放的结局是未来三年新发糖尿病。",
    steps: [
      ["核对任务与基线", "糖尿病路径要求基线无糖尿病，并提供年龄、BMI、空腹血糖、收缩压、甘油三酯。输入缺失、矛盾或超出训练观察范围时停止计算。"],
      ["运行研究权重", "校验检查点和训练报告，按训练均值、尺度标准化五项特征；经过任务输入适配层、共享基线编码器与对应结局头得到输出。"],
      ["返回三年研究估计", "使用保存的 Platt 参数校准后返回 1095 天研究估计、权重指纹与任务信息。未匹配验证的旧时序接口保持不可用状态。"]
    ],
    before: ["自然语言解析 / 基线表单", "明确的糖尿病基线状态、五项特征与单位"],
    after: ["研究预测结果区", "research_probability、horizon_days、checkpoint_sha256 等字段"],
    cooperation: "api.py 通过 attach_to_tfa 将 forecast_prospective 绑定到已有 TFA 实例。这个入口直接运行研究头；护理交接的 forecast 时序分支和 MedQuAD 问答各有独立路径。",
    example: {context: "三年新发糖尿病的合成基线输入。", input: "基线未患糖尿病；50 岁，BMI 25，空腹血糖 5.3 mmol/L，收缩压 125 mmHg，甘油三酯 1.2 mmol/L。", processing: "核对任务、单位与训练范围，标准化后运行检查点并校准输出。", output: "返回三年研究估计及权重 SHA-256；具体百分比由工作台本次实际计算显示。"},
    scope: "现有研究权重使用公开 NAGALA 纵向队列，只完成内部验证。单次心率、血氧、体温、呼吸频率不属于这项研究模型的输入。"
  },
  Consensus: {
    title: "把分歧和不确定性，交给明确的接管流程。",
    purpose: "对多模块输出执行分层规则，形成可追踪的升级原因与人工复核要求。",
    steps: [
      ["先检查强制接管", "若 DMA 要求人工、出现严重冲突、风险达到特定条件，或 TFA 缺少有效投票资格，则进入强制人工分支。"],
      ["执行否决与常规门控", "未被强制接管的结果继续检查 DMA 否决条件，再按评分和风险组合进入后续分支，记录票项、权重、层级和原因。"],
      ["通过就绪性检查", "协作引擎再执行 readiness gate；当前临床验证条件未满足时维持人工接管。网页上的复核决定由使用者明确填写并导出。"]
    ],
    before: ["DMA / Verification / 可用 TFA", "推理结果、核验摘要、风险可用性与高风险标记"],
    after: ["HITL / CareLink 复核区", "门控层级、升级原因、人工复核要求与审计上下文"],
    cooperation: "共识模块是工程内的决策规则，不是多位医生投票。HITL 管理与网页复核承接人工处理；最终 readiness gate 还会限制自动批准。",
    example: {context: "合成演示中勾选“强制高风险人工复核”。", input: "本次结果携带高风险标记，连同推理与核验摘要进入门控。", processing: "系统保留接管原因，由展示层给出 P1 并要求填写人工复核说明。", output: "requires_human_review 与复核入口；由复核人员完成决定，之后才能导出本次审计。"},
    scope: "算法内部的 approved 字段还受就绪性检查约束；不能用内部投票结果宣称系统获准进行自动临床决策。"
  },
  Privacy: {
    title: "保护模块消息，并约束反馈更新。",
    purpose: "为进程内的智能体消息提供认证加密，并为可选反馈梯度提供裁剪和加噪操作。",
    steps: [
      ["准备会话密钥", "从显式参数或配置的环境密钥读取 AES 密钥；没有持久密钥时生成临时会话密钥。密钥不会放进网页展示。"],
      ["认证加密与校验", "每条消息生成随机 nonce，通过 AES-GCM 加密；解密时校验认证信息。Topology 记录加密状态与字段名，避免在其消息记录里直接保留原文。"],
      ["处理反馈梯度", "在调用反馈保护方法时，先限制梯度范数再叠加噪声。该操作属于反馈更新路径，不会因一次普通页面筛查而自动训练所有模块。"]
    ],
    before: ["Topology / 可选反馈更新", "序列化消息内容，或待处理的数值梯度"],
    after: ["消息路由 / 反馈调用方", "加密消息、解密校验结果与处理后的梯度"],
    cooperation: "Topology 在启用隐私配置时调用加密与解密接口；审计原文的去标识化另由脱敏模块负责，网页还有独立的个人标识格式预检。",
    example: {context: "Perception 向 RAA 传递一条进程内消息。", input: "消息字段包含问题摘要与 context_dim。", processing: "内容序列化后使用 AES-GCM 处理，接收校验通过后返回可追踪状态。", output: "encrypted=true 与 field_names 等消息记录；网页不显示密钥或密文内容。"},
    scope: "当前没有形式化差分隐私预算核算。消息加密、审计脱敏、网页输入检查是三个不同的工程环节。"
  },
  Maintenance: {
    title: "让模块异常，有状态可查。",
    purpose: "围绕已注册模块的心跳和输出做轻量运行检查，为协作引擎保留异常记录。",
    steps: [
      ["登记并检查心跳", "登记模块实例；任务开始时比较最后心跳与超时配置，读取模块是否已经标记为 faulty。"],
      ["标记异常输出", "检查空输出、无效数值及缺失或异常的 confidence；发现问题后增加计数并将对应模块标为故障。"],
      ["提供状态恢复入口", "restart_or_replace 会重置已注册对象的健康状态与心跳。实际任务异常的降级调用由独立的 DegradationManager 负责。"]
    ],
    before: ["全部注册模块 / 协作引擎", "模块实例、最后心跳时间与本次输出"],
    after: ["运行状态与降级处理", "alerts、isolated_agents、abnormal_outputs 等统计"],
    cooperation: "协作引擎开始执行时调用 monitor，DMA 返回后调用 detect_abnormal_output。它记录模块故障状态，降级管理器负责在受保护调用失败时提供替代结果。",
    example: {context: "假设某模块返回空结果。", input: "模块名与 output=None。", processing: "异常检测增加计数，将模块记为 abnormal_output，并更新故障状态。", output: "异常统计与隔离状态，供运行核查；不会把空返回显示成成功完成。"},
    scope: "当前恢复方法重置的是进程内对象状态；它不是已部署的跨机器自动重启平台，也不保证服务持续在线。"
  },
  Topology: {
    title: "给每一次模块传递，记录一条路径。",
    purpose: "管理节点、邻居、星型或网状连接，以及消息是否存在可投递路径。",
    steps: [
      ["注册节点与连接", "注册十个模块和 HITL 节点。star 围绕配置的中心节点构建连接，mesh 为不同节点建立直接连接。"],
      ["计算并记录路径", "发送消息时检查发送者和接收者的关系；星型中的两个外围节点经中心中转。启用隐私时同步调用 Privacy。"],
      ["处理未连通消息", "没有路径的消息进入重试队列并增加失败计数；retry_disconnected 会重新查路，更新重试次数与投递状态。"]
    ],
    before: ["各模块 / 协作引擎", "发送者、接收者、字段载荷与当前拓扑配置"],
    after: ["接收模块与通信记录", "route_path、delivered、retry_count 与路由统计"],
    cooperation: "协作流程在 Perception→RAA、RAA→Fusion、Verification→DMA 等阶段记录消息。Privacy 提供消息保护；Maintenance 独立观察模块健康状态。",
    example: {context: "星型配置下，两个外围模块需要通信。", input: "sender=Perception、receiver=RAA，以及一条字段载荷。", processing: "如果两者没有直连，则经过配置的中心节点生成路由路径；没有可用路径则入队。", output: "形如“发送者 → 中心 → 接收者”的 route_path，以及 delivered 或待重试状态。"},
    scope: "这是当前 Python 进程内的逻辑路由和投递状态管理，并未据此部署独立的网络智能体服务集群。"
  }
});
