# 安护智链 CareLink｜MedQuAD 版完整交付包总览

本压缩包面向 **2026 数媒创赛本机演示与代码核查**，不是公开部署包或临床产品。解压后进入 `CareLink_2026` 根目录；零基础启动见 [新同事指南](START_HERE_新同事打开网页.md)。

| 路径 | 现场动作 | 实际方法 | 不能宣称 |
| --- | --- | --- | --- |
| 养老照护交接工作台 | 输入合成交接与单次体征、运行筛查、人工复核 | 原 MAPFM 预处理与多智能体研究引擎 | 临床诊断或自动分诊 |
| 未来糖尿病 | 输入代谢及基线指标 | 8 年发表规则；另有 NAGALA 训练的 3 年 TFA 研究扩展 | MedQuAD 问答训练出了发病预测 |
| MedQuAD 医学问答 | 输入英文知识问题、查看来源答案 | 官方 XML 全量清点，47,441 个问题拟合 TF-IDF 词汇/IDF，16,407 条有答案问答进入词面及预训练语义检索索引；附 LiveQA 和 MEDIQA 2019 外部问法审计 | 原始 MAPFM 神经权重已用 MedQuAD 微调，或答案是现行指南 |

糖尿病足页面、风险评分和图像分割对外接口已从本版移除。旧源码与报告在本机工作目录保留作历史恢复，但不进入新版交付 ZIP；`original_engine_package/` 是独立原工程快照，为溯源保持不变。MAPFM 现有糖尿病研究检查点内部曾按双头结构保存，第二头未受训练且不会作为本版产品功能开放。

## 文件地图

| 路径 | 作用 |
| --- | --- |
| `careguard_web/` | 产品首页、统一交互工作台（自然语言、三年糖尿病研究估计、来源问答和盲评）、证据板、三维研究图谱、加入我们。 |
| `careguard_web/architecture.js`、`careguard_web/architecture.css`、`careguard_web/architecture-details.js` | 首页十智能体技术架构：三条路径、十模块点选、代码对应、执行机制、协作关系与合成示例。 |
| `careguard_site.py`、`api.py` | 同源网页和真实计算接口；`/mapfm/medquad-qa/ask` 是问答检索。 |
| `medquad_official_master.zip` | 作者官方 GitHub `master` 完整归档，原始 XML 和许可证。 |
| `medquad_qa.py`、`train_medquad_qa.py`、`build_medquad_semantic.py`、`medquad_generalization.py` | 解析、计数、拟合、语义索引、外部问法评测、哈希核验及检索。 |
| `artifacts/medquad_qa/` | TF-IDF 模型、语义编码器及向量索引、16,407 条有答案记录、训练与三类问法评测聚合报告；均可核验。 |
| `docs/MEDQUAD_QA.md`、`docs/MEDQUAD_ROBUSTNESS.md`、`docs/MEDQUAD_MEDIQA2019.md` | 训练范围、版权空答案、自然问法及官方外部问答核验、被拒绝的候选方案和模型边界。 |
| `mapfm_ecosystem_repaired.py`、`mapfm_utils/`、`original_engine_package/` | 当前 MAPFM 运行代码和 225 文件独立历史快照。 |
| `mapfm_prospective_neural.py`、`artifacts/prospective_neural/` | 3 年新发糖尿病研究权重与内部验证报告；原始患者级数据不随包分发。 |
| `medNo.22.csv`、`demo_assets/` | 原 605 条医学问答索引和合成体征，不是患者案例。 |
| `tests/`、`PACKAGE_MANIFEST.json` | 自动化测试及逐文件哈希清单。 |

官方 MedQuAD README 标称 47,457 对问答；本版下载的官方 `master` 压缩包逐 XML 解析得到 47,441 对，全部问题参与无监督统计拟合，其中 31,034 对没有答案，16,407 对有答案并进入回答索引。三个 MedlinePlus 子集答案由上游因版权主动移除，不会由本项目抓取、补写或拿空答案当监督标签。来源：[作者仓库](https://github.com/abachaa/MedQuAD)、[论文](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-019-3119-4)。许可为 CC BY 4.0，须保留署名与原始许可。

## 快速启动与核查

```powershell
python -m pip install -r requirements.txt
python start_demo.py --check
python start_demo.py
```

打开 `http://127.0.0.1:8511/?view=workspace#medquad-studio`；输入 `What is diabetes?` 或改写问法可以实际调用本机词面+语义融合检索。`GET /mapfm/medquad-qa/status` 核对来源、模型和语义索引哈希。交接大模型演示仍需另行启动 Ollama；MedQuAD 检索和糖尿病研究权重不依赖 Ollama。整包打包脚本会重新解析官方 XML、核对模型及记录哈希，拒绝不一致的交付包。外部问法离线评测的已标注相关答案前三名命中率从 38.67% 提升至 60.00%（38 道可对齐题、排重后 75 种问法；评分不完整，非临床准确率，未模拟在线同 URL 去重）。

新增的另一批 80 条自然问法进一步检验上线稳定性：38 条封存题上当前版已知原文答案 Top-3 命中率为 42.11%。一个开发集略优的排序候选在封存集降至 36.84%，故**没有上线**；网页与包内 `robustness_audit.json` 如实披露。不要把旧版 60.00% 单独称为通用准确率。外部镜像原始个人健康叙事不随包转发，复现需按文档从公开来源另取。

另用 [官方 MEDIQA 2019 问答集](docs/MEDQUAD_MEDIQA2019.md) 严格对齐 52 道外部题目：当前版已知答案 Top-1 为 22/52、Top-3 为 32/52。答案字段候选 Top-3 上升至 35/52，但 Top-1 降至 21/52，未通过预设上线门槛；进一步“锁住第一名”方案在旧自然问法上也退步。候选均未接入网页实际检索，`mediqa2019_audit.json` 和状态接口如实区分当前版与被拒绝方案。

2026-10-14 又用官方 RQE 和 MeQSum 做三项训练／重排实验，均未通过预设门槛，因此**线上模型未更换，也不能宣称泛化能力已经提高**。结果、数据隔离和复现实验代码见 [最新泛化核查](docs/MEDQUAD_GENERALIZATION_20261014.md)；交付包只包含聚合审计 JSON，不包含失败候选权重或外部原始问题工作簿。

下一步的[独立审核协议](docs/MEDQUAD_BLIND_EVAL_20261014.md)已建立：新的公开用药问答来源经去重筛查后，固定 100 题开发集与 250 题锁定集，并提供本机离线双人标注页面。**两套题包尚未由医学人员审核，暂无新的答案质量分数。** 原始题目和模型回答不进入交付 ZIP；公开包仅包含抽样规则、来源哈希、待审核状态与复现工具。

## 提交前还需人工完成

1. 核对赛事正式类别、历史项目增量及团队贡献证据。
2. 审查全部项目照片、肖像、论文、第三方数据及模型的公开传播授权。
3. 不要把内部测试指标、检索词面相似度或演示优先级包装成临床有效性。
