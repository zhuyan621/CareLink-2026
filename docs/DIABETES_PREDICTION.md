# 未来糖尿病风险模块：实现与边界

## 当前可运行内容

工作台下方的“未来糖尿病风险”是独立于原有 MAPFM 急性照护筛查的功能。用户先确认是否已确诊糖尿病，再输入当前基线的 BMI、血压、空腹血糖、HDL-C、甘油三酯、父母糖尿病史和降压治疗状态，网页 POST 到 `/risk/diabetes-8y`。后端每次现场计算逐项得分，并返回已发表研究对应的 **8 年新发糖尿病风险档位**。修改输入会清除旧结果；已确诊或空腹血糖达到研究的基线糖尿病排除阈值时不输出风险。

这是真正运行的、可复核的**发表队列风险评分**，不是预先写好的病例结论；但它也**不是 MAPFM 神经模型**。同一工作台新增了另一个独立的 **3 年 NAGALA/MAPFM TFA 神经研究栏**，其权重来自公开真实随访队列，不与本 8 年规则混算。两种风险数值均不应被解释为中国照护对象的精确个人概率。

## 方法与出处

- Wilson PWF 等，*Prediction of Incident Diabetes Mellitus in Middle-aged Adults: The Framingham Offspring Study*，Archives of Internal Medicine，2007，Table 6：<https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/486842>。
- 原研究对基线无糖尿病者做后续随访，Table 6 将临床变量转换成积分及 8 年风险档位。本实现逐项复现表中 7 个计分条件与风险查表，不自行拟合系数、不用 medNo.22.csv 训练。
- 输入采用中国常见的 mmol/L 单位，计算时转成原表的 mg/dL：葡萄糖×18.0182，HDL-C×38.67，甘油三酯×88.57。血压保持 mmHg，BMI 保持 kg/m²。边界测试见 `tests/test_diabetes_risk.py`。
- 低分组原表只给出 `≤3%`，最高分组给出 `>35%`；界面保留区间符号，不捏造一个精确百分比。

## 适用范围和不适用范围

1. 原研究人群为美国 Framingham Offspring 队列，未在 CareLink 目标中国照护人群做外部验证或校准。不能宣称临床有效、用于分诊或治疗。
2. 已确诊糖尿病者不适用“未来新发”风险；空腹血糖达到原研究基线排除阈值的输入会被拒绝。其他异常化验值也应由专业人员结合完整临床信息评估。
3. 上方工作台的心率、血氧、体温、呼吸频率不在本评分中，不能说它们已经用于预测未来糖尿病。该评分所用的是血压及代谢相关基线变量。
4. 本页不持久化该表格输入，浏览器只向本机 `127.0.0.1` 服务发送本次计算参数。部署到非本机环境前需另做隐私、安全和合规评估。

## 复现

```powershell
python -m pytest -q tests/test_diabetes_risk.py
python start_demo.py --port 8511
```

打开 <http://127.0.0.1:8511/?view=workspace#diabetes-studio>。例如选择“未确诊”、男、BMI 31、血压 132/80 mmHg、空腹血糖 6.0 mmol/L、HDL-C 0.8 mmol/L、甘油三酯 2.0 mmol/L、父母患病、未服降压药，应该返回 28 分、`>35%`。此例仅用于核对计分，不是患者案例。

## 后续中国队列模型所需工作

中国 Rich Healthcare [Dryad 队列](https://datadryad.org/dataset/doi:10.5061/dryad.ft8750v)的原始工作簿下载仍被官方反机器人验证阻挡，**未用于训练**。为取得真实训练数据，已使用另一个公开的[日本 NAGALA 随访队列](https://datadryad.org/dataset/doi:10.5061/dryad.8q0p192)训练 3 年 MAPFM TFA 研究头；它不是中国人群模型，也不改变本页 8 年 Framingham 规则。具体样本、性能、限制和复现流程见 [双结局神经升级](MAPFM_PROSPECTIVE_NEURAL.md)。

取得原始纵向数据后，下一步须：核验文件哈希及字段；只用基线变量训练；明确 3 年事件与提前失访的删失处理；按个体和地点分离训练/验证集；报告区分度、校准、净获益和分人群误差；完成独立外部验证与临床审查后再讨论实际使用。严禁把末次随访血糖或随访结局作为输入特征。
