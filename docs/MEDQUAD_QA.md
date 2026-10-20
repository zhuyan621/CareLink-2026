# MedQuAD 全量来源问答训练与使用边界

## 数据和许可

官方来源是 [Asma Ben Abacha 的 MedQuAD 仓库](https://github.com/abachaa/MedQuAD)，本项目保存其 `master` 完整压缩包 `medquad_official_master.zip`，SHA-256 为 `45aeef400844f3551a7862c3378cc9edf72818ef09d6c1d400f227207ee5179d`。原仓库将数据标注为 CC BY 4.0，引用：Ben Abacha A, Demner-Fushman D. A Question-Entailment Approach to Question Answering. *BMC Bioinformatics*. 2019;20:511. DOI: [10.1186/s12859-019-3119-4](https://doi.org/10.1186/s12859-019-3119-4)。完整原始许可证及 README 在压缩包内。

本机逐 XML 解析 `11,274` 个文档、`47,441` 个 QAPair；无 XML 解析错误、无空问题。官方 README 称 `47,457` 对，与此 `master` 快照的可解析数量相差 16 对，故页面与报告只使用本机可复核的数量，不把官方概数冒充本机实数。

| 计数 | 数量 | 处理 |
| --- | ---: | --- |
| 原始问答条目 | 47,441 | 全部逐条检查 |
| 有答案条目 | 16,407 | 全部参与模型拟合和原文索引 |
| 空答案条目 | 31,034 | 记入核查，不提供监督答案 |

其中 `ADAM` 17,348、`MPlusDrugs` 12,889、`MPlusHerbsSupplements` 792 条均无答案；另有 GARD 的 5 条空答案。官方 README 明确：前三个 MedlinePlus 子集因版权移除了答案。本项目不爬取或臆造被移除内容。`medNo.22.csv` 的 605 条索引是最初工程保留的另一份资料，不重复算入 MedQuAD 训练数。

## 已训练模型

`python train_medquad_qa.py` 使用**全部 47,441 个英文问题**拟合词级和字符级 TF-IDF 词汇及逆文档频率，再把其中 **16,407 条有原始答案**的问题向量化并建立回答索引；空答案问题只参与无监督统计拟合，绝不作为伪答案监督。另用 [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) 预训练语义编码器（Apache-2.0）为这 16,407 个问题建立向量索引。在线检索以 50% 词面分数、50% 语义分数融合，并要求融合分数 ≥0.32、语义 ≥0.40、词面 ≥0.08，否则拒答。最多返回三条不同 URL 的原文答案。该语义编码器**没有在 MedQuAD 上继续训练权重**，也不是原始 MAPFM 神经网络。`match_score` 是检索排序分数，**不是**医学可信度或诊断概率。

包中已含 TF-IDF 模型、语义编码器及向量索引；新同事无需重训或下载模型。若要重建 TF-IDF，请指定空目录：

```powershell
python train_medquad_qa.py --source medquad_official_master.zip --output artifacts/medquad_qa_new
```

语义索引的离线重建脚本是 `build_medquad_semantic.py`，需提供本机已有的 MiniLM 模型目录并指定新的空目标目录，脚本拒绝覆盖已存在索引。`medquad_generalization.py` 复核 LiveQA 测试，原始试题保存在 `artifacts/medquad_qa/liveqa_test_questions.xml`，评价报告在 `artifacts/medquad_qa/generalization_benchmark.json`，均与交付包一起保存。测试来源按作者说明为 CC BY 4.0，见 [LiveQA 原仓库](https://github.com/abachaa/LiveQA_MedicalTask_TREC2017)。

## 未见问法测试与泛化边界

作者的独立 LiveQA 测试有 104 道题，MedQuAD 压缩包附 2,479 条人工评分回答。我们只把**规范化问题、原始 URL、答案前缀完全对齐**的 565 条评分映射至本机索引；其中 38 道题至少有一条被评为 3/4 分的已对齐答案。对这 38 题的原始问法和人工摘要问法分别检索，排除与原 MedQuAD 问题完全重复的 1 个问法后共 75 个问法。比较已标注相关答案在前三名出现的比例：原词面阈值方案为 **38.67%**，50/50 融合与保守拒答门槛为 **60.00%**。这项离线指标采用索引原始排序和阈值，未模拟在线页面的同 URL 去重和近分答案优先规则；两种方法用同一规则，仍不是完整线上端到端评估。它是**不完整标注集合的已知相关答案命中率**，不是总体正确率、精确率、疾病预测泛化率或临床安全性证明。38 题过少，分数权重和门槛也参考了此测试集；预训练编码器的上游数据是否覆盖 LiveQA 未知。尚需另一套未参与选择的外部数据与人工盲评。

对“修自行车链”“烤面包”“查足球比分”等明显非医学问题做了拒答冒烟检查。它们不能穷尽未知问题；面对缺乏证据或个体诊疗问题，系统仍可能检索到仅表面相关的历史答案。部署时需保留来源与免责声明。

后续又增加了 80 个来自另一批公开自然语言医疗问句的开发／封存测试。候选排序在开发集略有收益，但封存集明显退步，因此**未替换当前线上排序**。参见 [自然问法与上线门禁](MEDQUAD_ROBUSTNESS.md)；不能把旧 LiveQA 的 60.00% 或本轮开发集数值单独包装成“泛化能力强”。

再用官方 MEDIQA 2019 QA 测试集做了严格答案原文对齐核验：52 道可评题中，当前线上版已知答案 Top-1 / Top-3 分别命中 22 / 32 道。答案字段候选虽提高 Top-3，但降低 Top-1，因此仍未部署。具体口径与不完整标注边界见 [MEDIQA 2019 外部问法核验](MEDQUAD_MEDIQA2019.md)。

网页调用 `GET /mapfm/medquad-qa/status` 与 `POST /mapfm/medquad-qa/ask`。输入示例：

```json
{"question":"What is diabetes?","top_k":3}
```

回答携带原始问题、原始答案、来源机构、源 URL、融合检索分数及分项分数、数据 SHA-256。由于 MedQuAD 是历史英文公众健康资料，来源页可能迁移或过时；回答不是中国现行指南或临床建议。已有上述外部问法测试，但**尚无充分的临床人工评估**。

## 与 MAPFM 糖尿病预测的关系

MedQuAD 没有患者基线、随访时长和未来发病标签，不能训练或验证未来糖尿病风险。网站上 3 年新发糖尿病研究权重仍来自开放 NAGALA 纵向队列，是挂接在原 MAPFM TFA 上的另一套研究扩展，绝非本次 MedQuAD 训练成果；8 年规则评分又是独立发表公式。本次移除糖尿病足的产品页面和对外接口，未改写原始历史工程快照。
