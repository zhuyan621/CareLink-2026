# MedQuAD 用药问答独立审核协议｜2026-10-14

本协议的目标是找出当前**英文医学知识检索**面对未参与训练的真实用药问法时的错误，不评估未来糖尿病发病，也不构成临床验证。开发人员不得将锁定集分数用于挑选下一版模型。

## 数据来源与锁定

来源是 [Medication QA / MEDINFO 2019 作者仓库](https://github.com/abachaa/Medication_QA_MedInfo2019) 的 CC BY 4.0 工作簿。论文摘要称 674 对；本机下载文件的 `DrugQA` 工作表实际含 690 个数据行，其中 43 行的问题与较早行完全重复，得到 647 个独立问句。另排除 1 个与此前语料问题完全重复、1 个字符 TF-IDF 相似度达到 0.85 的近重复问句，剩余 645。自动个人信息正则筛查未排除记录，但**不代表已经完成去标识化**；分享题包前仍须人工逐题检查。

对 645 个候选按固定种子与规范化问题计算 SHA-256，取前 250 个为**锁定验收集**，后 100 个为**开发集**。两者没有重复；详细原始问题、来源答案和当前模型预测只保存在本机 `artifacts/medquad_qa_candidate/medication_blind_20261014/`。原始工作簿、题包及个人标注都不进入比赛交付 ZIP；包内仅有聚合计数、来源哈希和选择规则。筛查程序还比对了全部 MedQuAD 原问题、既往 LiveQA/MEDIQA 问题、RQE 训练与验证问句以及 MeQSum 问句；它只能拦截准确重复与明显近重复，不能排除所有语义改写或预训练模型上游数据污染。

这是一份**用药领域**外部切片，不代表全部疾病、护理记录或中文问题。其问句来源与开发集相同；锁定只保证本项目后续不在这 250 题上反复调参。其他领域与中文输入仍需另建独立集。

## 双人审核步骤

1. 启动 CareLink 本机站点后，在统一“交互工作台”向下打开盲评区（`http://127.0.0.1:8511/?view=workspace#review-desk`）；原 `/site/medquad-review` 和 `?view=review` 地址会回到这一区域。离线应急时仍可双击 `tools/medquad_blind_review.html`。输入审核者代号，加载 `development_packet.json`。两位医学背景审核者分别独立标记每题的范围、每条答案的相关性、来源支持和安全性；拒答时再判断拒答是否恰当。审核页面不上传文件，随时可下载当前 JSON 标注并续填。
2. 运行 `python medquad_blind_eval.py check-labels <题包> <审核者A.json> <审核者B.json>` 检查完整性。两人有分歧时，由第三位医学背景人员独立裁决；运行 `python medquad_blind_eval.py score <题包> <A.json> <B.json> --adjudication <裁决者.json>` 生成开发集错误分析。缺少裁决时程序只报告分歧数，不输出性能分数。
3. 仅使用开发集分析失分原因、构造正确答案与难负例、训练候选；不得查看 250 题锁定集的标注结果或汇总分数。
4. 候选模型与拒答阈值冻结后，让两位审核者对锁定集当前版和候选版**隐藏版本身份**地审核实际返回结果。全部分歧裁决完成后，才进行一次最终比较。若候选返回新答案，不能把旧版标注机械套用到新答案。

目前两套题包的状态是**等待人工审核**，没有“医学准确率”或“泛化提升”的新结果。自动生成的候选答案只是待审核材料，不是黄金标签。标注应避免把“来源支持”与“现行指南正确性”混为一谈；旧来源可能过时，不确定时必须标“不确定”。

## 预先冻结的晋级门槛

主指标：锁定集中、人工判定“属于范围”的问题，其首条答案同时被判为“充分回答、来源支持、未见明显风险”的比例。候选须相较当前版至少提高 **5 个百分点**，且按问题配对重采样所得提升的 95% 区间下界大于 0。附加门槛：前三条中至少一条满足同样条件的比例不得下降；被标为潜在不安全的返回问题数不得增加；错误拒答数不得增加。必须同时报告每种问句类型的样本数和结果，不以少数子群的偶然波动单独作提升宣称。

250 题可能不足以验证罕见安全事件。若范围外题数很少，拒答表现只能标记“证据不足”，不得按 0 错误写成安全。上述门槛是本项目研究晋级规则，不是医学器械性能标准。参照 [FDA 对测试集独立性的解释](https://www.fda.gov/science-research/artificial-intelligence-and-medical-products/fda-digital-health-and-artificial-intelligence-glossary-educational-resource) 和 [WHO 对医疗 AI 外部验证的建议](https://www.who.int/news/item/19-10-2023-who-outlines-considerations-for-regulation-of-artificial-intelligence-for-health) 管理证据边界。

## 文件与复现

代码 `medquad_blind_eval.py`；本机离线审核页 `tools/medquad_blind_review.html`。聚合的锁定集清单为 `artifacts/medquad_qa/blind_eval_manifest_20261014.json`，开发集清单为 `artifacts/medquad_qa/medication_development_manifest_20261014.json`。独立题包是本机研究文件，不在 ZIP；新同事需要题包时应由团队在完成隐私复核后通过受控渠道提供，不应从网页自动下载。
