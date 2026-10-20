# MedQuAD 未见问法泛化升级核查｜2026-10-12

本次升级的是网页“来源问答”检索，不是未来糖尿病发病预测。原 MAPFM 主体、NAGALA 3 年糖尿病研究头和 8 年发表规则未借用 MedQuAD 问答数据重训。

## 运行链路

`POST /mapfm/medquad-qa/ask` 先用全量问题拟合的词/字 TF-IDF，另用本地预训练 MiniLM 语义编码器检索 16,407 条有答案问题，等权融合排序并按三重门槛拒答。结果只返回原始英文来源答案及 URL，不生成新的医学内容。语义编码器权重未在 MedQuAD 上微调；其作用是提供问法改写的语义表示，而非疾病预测。整包携带编码器权重和向量索引，不依赖首次启动时访问外网。

## 可复核证据

- 数据来源：作者 [MedQuAD](https://github.com/abachaa/MedQuAD) 和 [LiveQA 2017 医疗测试](https://github.com/abachaa/LiveQA_MedicalTask_TREC2017)，两者原仓库均声明 CC BY 4.0；语义编码器 [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) 为 Apache-2.0。
- 独立 LiveQA 有 104 道题，附于 MedQuAD 的 2,479 条人工评分回答中，565 条可通过问题、URL、答案前缀严格对齐到本机索引；38 道题有至少一条可对齐的 3/4 分答案。
- 原始与摘要问法合计 76 个；排除 1 个与训练问题完全相同的问法后，75 个未重复问法进入测试。在线阈值的离线近似：已标注相关答案前三名命中率从词面模型的 **38.67%** 到融合模型的 **60.00%**。原始问题、摘要问题两个分组均改善，但样本很小，不能据此保证跨机构、人群或疾病的泛化。
- 测试只对部分答案评分，未标注答案不能当作错误；打分规则曾被用于选择融合与门槛，因此这不是锁定模型后的全新盲测，也没有临床专家终点评估。预训练语义编码器的上游数据与 LiveQA 是否重叠未知。
- 明显非医学提问（自行车、面包、足球比分）拒答测试通过；这只是有限的越界测试，不覆盖所有风险提问。

复核文件：`medquad_generalization.py`、`artifacts/medquad_qa/generalization_benchmark.json`、`artifacts/medquad_qa/liveqa_test_questions.xml`、`artifacts/medquad_qa/semantic/semantic_report.json`。包生成器逐项检查来源、编码器、索引和评测数据的 SHA-256。网页“工作台 / MedQuAD 来源问答”显示有限的可对齐测试口径，不把相关度标为医学置信度。

## 后续仍需

1. 冻结当前权重、阈值和评测代码；另找未参与方案选择的新测试集，并做临床专业人员盲评、错误类型审查及不同疾病/来源分层分析。
2. 为未来糖尿病发病预测模型另行做跨机构、跨时间的外部验证、校准及亚组评估。MedQuAD 问答的改进不能证明这一预测头泛化。
3. 不将本系统用于诊断、用药或临床决策。
