# MedQuAD 泛化迭代核查｜2026-10-14

结论：**本轮没有证实泛化提升，三项候选均拒绝上线**。网页和接口继续使用既有 16,407 条有答案问答的词面＋预训练语义融合检索；本轮训练过的神经编码器只留在本机实验目录，不作为线上模型，也不是 MAPFM 未来糖尿病预测权重。

## 数据与隔离

- [官方 MEDIQA 2019 RQE](https://github.com/abachaa/MEDIQA2019/tree/master/MEDIQA_Task2_RQE)：仅用 train 与 validation 做问题蕴含开发实验；`test` 未用于本轮比较。其标签说明两个问题的语义关系，不等于 MedQuAD 的答案正确性标签。该验证集中正例 FAQ 几乎不能对齐到本项目的有答案 MedQuAD 索引，因此不能把 RQE 分数直接当作在线问答命中率。
- [官方 MeQSum](https://github.com/abachaa/MeQSum)：原始 1,000 对消费者长问题与人工摘要；先排除与既有外部问答测试问题及 MedQuAD 原问题的重合，再按问题哈希固定划分为 755 训练、172 开发。摘要任务也不是答案相关性判断。
- 原先的 80 道 LiveQA 自然问法和 52 道 MEDIQA 2019 严格对齐问答**已在此前迭代暴露**，本轮只用作回归门槛，不将其称为全新独立测试。原始叙事、MeQSum 工作簿、RQE XML 和失败候选权重不进入比赛交付包。

## 预设门槛与结果

| 候选 | 本轮开发结果 | 决定 |
| --- | --- | --- |
| RQE 10 特征分类器 | 302 对验证，AUROC 0.8579、平均精确率 0.7558；原语义余弦 0.8931、0.8257 | 两项均退步，拒绝 |
| RQE 正例微调 MiniLM | 3,180 对非相同正例训练；验证 AUROC 0.8904、平均精确率 0.8200；预设要求 AUROC 至少增加 0.01 且平均精确率不降 | 未过门槛，拒绝；封存 RQE test 未触碰 |
| MeQSum 摘要微调 MiniLM | 172 对摘要检索 Top-1 0.9651→0.9651；旧 LiveQA 80 题已知答案 Top-3 35→34，旧 MEDIQA 52 题 Top-1 22→21 | 未达预设摘要 Top-1 +0.05 及问答无回退门槛，拒绝 |

MeQSum 基线摘要 Top-1 已达 96.51%，原先预设的五个百分点提升门槛事实上有明显天花板问题；即使另看问答回归，候选依然出现退步。个别子指标改善（例如 MEDIQA Top-3 32→33）不能掩盖第一名和另一组 Top-3 的回退。以上分数是**已知答案检索/问句匹配**，不是医学正确率、安全性或临床有效性。

可复现代码在根目录 `medquad_rqe_trial.py`、`train_medquad_rqe_encoder.py`、`medquad_rqe_encoder_eval.py`、`train_medquad_meqsum_encoder.py`、`medquad_meqsum_eval.py`、`medquad_meqsum_qa_trial.py`；聚合审计见 `artifacts/medquad_qa/generalization_20261014.json`。需自行按原仓库许可下载官方数据并保留来源署名；候选目录 `artifacts/medquad_qa_candidate/` 是本机研究记录，不在 ZIP 内。

下一步真正提高泛化，需要新的、去标识化、独立采集的真实英文用户问题，由医学背景标注者对**答案相关性、事实正确性、危险性与拒答是否恰当**分别判定；按照来源、疾病、问句类型和时间分层，先锁定验证集及晋级门槛，再训练和一次性验收。未经这一步，不能宣称模型已经更会回答或能用于临床。
