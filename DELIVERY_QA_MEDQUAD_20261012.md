# CareGuard MedQuAD 版交付核查｜2026-10-12

> 本文记录当日第一版 TF-IDF 交付状态；当前融合语义检索、未见问法评测和新完整包请见 `DELIVERY_QA_MEDQUAD_GENERALIZATION_20261012.md`。下文“尚无独立测试”等只属于旧版历史状态。

## 已完成

- 从作者官方 MedQuAD 仓库取得完整 `master` 原始 ZIP，保存原始 README 和 CC BY 4.0 许可。
- 解析 11,274 个 XML 文档，得到 47,441 条 QAPair；**全部 47,441 个问题参与 TF-IDF 词汇/IDF 拟合**，16,407 条有答案记录进入回答索引，31,034 条空答案未伪造。官方 README 标称 47,457 对，和本机可解析快照相差 16 对，已在网页与文档如实揭示。
- 训练/核查文件：`artifacts/medquad_qa/medquad_retrieval.joblib`、`answer_records.jsonl`、`training_report.json`。来源 ZIP、模型和记录均附 SHA-256；打包前会重新解析来源并核验数量和哈希。
- 工作台新增独立来源问答区，现场输入英文问题调用 `/mapfm/medquad-qa/ask`，仅显示原文、来源及词面相似度；无足够匹配则拒答。浏览器用 `What is diabetes?` 实测 3 条带来源结果。
- 从当前网页和 OpenAPI 移除糖尿病足风险、图像分割入口；新版交付 ZIP 排除对应旧源码、权重、数据和旧报告。原始 MAPFM 历史快照保留原样。
- 原有 8 年糖尿病发表规则及 3 年 NAGALA 训练的 TFA 研究头保持独立可用。MedQuAD 不参与两者的发病概率计算。

## 本机核查

| 项目 | 结果 |
| --- | --- |
| 官方来源 ZIP SHA-256 | `45aeef400844f3551a7862c3378cc9edf72818ef09d6c1d400f227207ee5179d` |
| 检索模型 SHA-256 | `863f88d54398aabe3494495c0fb2f7ba9610d4969fc02a910ecefd076d30f960` |
| 有答案索引 SHA-256 | `8f97b47a63130cd531fac5c62cea4cb4bf012840c391116705259c7e3c9cff8c` |
| 页面真实调用 | 本机 8511：状态 200、问答 200，糖尿病足 API 不在 OpenAPI |
| 浏览器视觉 | [MedQuAD 工作台截图](artifacts/site-qa/medquad-studio-20261012.png) |
| 自动化测试 | 最终全套 `166 passed`、0 失败、3 项依赖警告；JUnit 见 `artifacts/competition/careguard_pytest_latest.xml` |

## 尚未完成 / 不得宣称

此模型是完整可用有答案数据拟合的**统计问答检索器**，不是原始 MAPFM 神经模型的参数微调；没有独立问答质量评估，也没有临床外部验证。问答数据无患者级未来发病标签，不能用于训练未来糖尿病发病预测。原文可能过时或仅适用美国公众健康语境。比赛展示时应保留这些边界与来源署名。
