# -*- coding: utf-8 -*-
# 智弈护晓 DawnGuard 医疗 → 养老 全站换词脚本
import io, sys

path = r"C:\Users\Lenovo\Desktop\MAPFM_medical_AI_repaired_complete\docs\index.html"

with open(path, 'r', encoding='utf-8', newline='') as f:
    t = f.read()

orig = t

# 按顺序替换：先替换更长的/更具体的短语，再替换通用词
repl = [
    # ===== 品牌名 =====
    ('智医算', '智养算'),

    # ===== 标题 / meta =====
    ('多智能体医疗免陪照护AI机器人', '多智能体智慧养老照护AI机器人'),
    ('医疗免陪照护AI机器人', '智慧养老照护AI机器人'),
    ('非接触式数字化免陪病房方案。已落地济南5家医院，ACM论文见刊。',
     '非接触式数字化智慧养老方案。已落地济南5家养老院/社区诊所，ACM论文见刊。'),
    ('数字化免陪病房方案', '数字化智慧养老照护方案'),
    ('医疗文本分类精确率81.95%', '养老照护文本分类精确率81.95%'),
    ('医疗AI,免陪照护,多智能体,MAPFM,护理机器人,智能医疗,大模型,RAG',
     '养老AI,智慧照护,多智能体,MAPFM,护理机器人,智慧养老,大模型,RAG'),
    ('🏥', '🏡'),

    # ===== 图标 =====
    ('fa-hospital-user', 'fa-hand-holding-heart'),
    ('fa-hospital', 'fa-home'),
    ('fa-stethoscope', 'fa-home'),

    # ===== 具体短语（先于通用词）=====
    ('医疗健康机器人', '智慧养老机器人'),
    ('全球医疗健康机器人', '全球智慧养老机器人'),
    ('AI 医疗算法', 'AI 养老照护算法'),
    ('医疗算法', '养老照护算法'),
    ('AI 医疗', 'AI 养老'),
    ('医疗AI', '养老AI'),
    ('智能医疗', '智慧养老'),
    ('医疗RAG', '养老照护RAG'),
    ('医疗 RAG 知识引擎', '养老照护 RAG 知识引擎'),
    ('医疗知识引擎', '照护知识引擎'),
    ('医疗知识图谱', '照护知识图谱'),
    ('医疗文本', '照护文本'),
    ('医疗场景', '养老场景'),
    ('医疗决策', '照护决策'),
    ('医疗大模型', '养老照护大模型'),
    ('医疗私有模型', '养老照护私有模型'),
    ('医疗专业工具', '照护专业工具'),
    ('医疗工具连接器', '照护工具连接器'),
    ('医疗应用', '养老应用'),
    ('医疗 IT', '照护 IT'),
    ('医疗信息系统', '养老信息系统'),
    ('医疗合规', '养老照护合规'),
    ('医疗纠纷', '照护纠纷'),
    ('医疗责任', '照护责任'),
    ('医疗巨头', '养老机器人巨头'),
    ('医疗行业', '养老行业'),
    ('医疗NLP', '养老NLP'),
    ('医疗年度', '养老年度'),
    ('医疗数据', '健康数据'),
    ('医疗照护困境', '养老照护困境'),
    ('医疗机器人产业', '养老照护机器人产业'),
    ('医疗机器人', '养老照护机器人'),
    ('医疗康复展', '康复养老展'),
    ('医疗平权', '养老平权'),
    ('医疗器械质量管理体系认证', '照护设备质量管理体系认证'),
    ('医疗器械', '照护设备'),
    ('二类医疗器械', '二类养老照护设备'),
    ('二类器械', '照护设备'),
    ('器械注册', '设备注册'),
    ('NMPA二类医疗器械注册认证', 'NMPA养老照护设备注册认证'),
    ('进入医保准入目录', '进入长护险准入目录'),
    ('医保', '长护险'),

    # ===== 医院 / 三甲 / 机构 =====
    ('济南复大肿瘤医院', '济南复大康养中心'),
    ('三甲·肿瘤特护', '大型·失能特护'),
    ('济南华圣医院', '济南华圣养老院'),
    ('肿瘤患者', '失能长者'),
    ('医院信息系统', '机构信息系统'),
    ('自主调用 HIS/LIS/PACS 等医院信息系统，实现医疗 IT 全链路打通',
     '自主调用养老管理/监测/评估等机构信息系统，实现照护 IT 全链路打通'),
    ('自主调用 HIS/LIS/PACS，MCP 标准化对接', '自主调用养老管理系统，MCP 标准化对接'),
    ('HIS/EMR', '养老管理系统'),
    ('HIS 无缝对接', '养老管理平台无缝对接'),
    ('HIS 联通', '养老管理系统联通'),
    ('HIS接口联调', '养老管理系统接口联调'),
    ('HIS无缝', '系统无缝'),
    ('HIS', '养老管理系统'),
    ('三甲核心院区', '高端养老机构核心床位'),
    ('三甲标配', '大型机构标配'),
    ('三甲800元/床', '大型机构800元/床'),
    ('三甲标杆', '大型机构标杆'),
    ('三甲医院', '大型养老机构'),
    ('三甲', '大型养老机构'),
    ('5家医院60+床位', '5家养老机构60+床位'),
    ('5 家医院/康养机构', '5 家养老/康养机构'),
    ('5家医院·60+床位', '5家养老机构·60+床位'),
    ('50+医院', '50+养老机构'),
    ('50+ 医院', '50+ 养老机构'),
    ('15+医院', '15+养老机构'),
    ('15+ 医院', '15+ 养老机构'),
    ('15+ 三甲医院', '15+ 大型养老机构'),
    ('3家医院', '3家养老机构'),
    ('3 家医院', '3 家养老机构'),
    ('医院/康养机构落地', '养老/康养机构落地'),
    ('医院联合试点', '养老机构联合试点'),
    ('医院运维台账', '养老机构运维台账'),
    ('医院采购决策', '养老机构采购决策'),
    ('医院信任危机', '机构信任危机'),
    ('医院管理层需求', '养老机构管理层需求'),
    ('医院试点合作', '养老机构试点合作'),
    ('医院临床试点合作', '养老院照护试点合作'),
    ('医院现场交流', '机构现场交流'),
    ('医院主任合影', '机构负责人合影'),
    ('试点医院', '试点养老机构'),
    ('第一试点医院', '第一试点养老机构'),
    ('医院', '养老院'),

    # ===== 医学 / 临床 / 医护 =====
    ('齐鲁医学院', '护理与康复学院'),
    ('医学循证基础', '循证照护基础'),
    ('循证医学证据链', '循证照护证据链'),
    ('循证医学', '循证照护'),
    ('医学库', '照护知识库'),
    ('医学大模型', '养老大模型'),
    ('临床医学', '老年照护'),
    ('医学文献', '照护文献'),
    ('医学', '照护'),

    ('临床医护', '养老照护'),
    ('临床对接', '机构对接'),
    ('临床高危', '养老高危'),
    ('临床验证网络', '落地验证网络'),
    ('临床验证端', '落地验证端'),
    ('临床验证', '落地验证'),
    ('Clinical Validations', 'Pilot Validations'),
    ('临床试点', '落地试点'),
    ('临床数据', '照护数据'),
    ('临床', '照护'),

    ('注册护士缺口', '专业护理员缺口'),
    ('将护士从繁重', '将护理员从繁重'),
    ('护士站', '护理站'),
    ('护士长', '护理部主任'),
    ('护士', '护理员'),

    ('家庭医生', '社区健康管家'),
    ('专家医生', '照护专家'),
    ('医生', '照护专家'),

    ('医嘱', '照护指令'),
    ('医患', '长者'),

    # ===== 患者 / 病房 / 住院 =====
    ('慢性病患者', '失能/半失能长者'),
    ('患者', '长者'),
    ('免陪病房方案', '智慧养老照护方案'),
    ('示范病房', '示范床位'),
    ('特护病房', '特护床位'),
    ('病房照护场景', '养老床位照护场景'),
    ('病房物理环境', '照护床位物理环境'),
    ('病房级', '床位级'),
    ('不出病房', '不出床位'),
    ('失能病房的人工智能曙光', '失能长者的智慧养老曙光'),
    ('病房管理效能', '照护管理效能'),
    ('病房', '床位'),
    ('一人住院，全家受累', '一人失能，全家失衡'),
    ('长期住院', '长期入住'),
    ('住院', '入住'),

    # ===== 疾病 / 病情 / 病 =====
    ('并发症', '健康风险'),
    ('病情初筛', '健康风险初筛'),
    ('病历', '健康档案'),
    ('慢性病', '慢病'),
    ('慢病数据', '长者健康数据'),
    ('罕见病', '失能风险'),
    ('病床', '床位'),
    ('病种', '风险场景'),
    ('疾病预测', '健康风险预测'),
    ('疾病', '健康风险'),

    # ===== 机构名称（社区卫生中心 → 社区养老）=====
    ('潍坊经开卫生中心', '潍坊经开社区养老服务中心'),
    ('沂城街道卫生中心', '沂城街道社区养老中心'),

    # ===== 其他 =====
    ('国家卫健委', '民政部门'),
    ('国家多部委', '民政部门'),
    ('卫健委', '民政部门'),
    ('Clinical Pilot', 'Elderly Care Pilot'),
    ('Medical Text', 'Medical Text'),  # 论文标题保留（真实 DOI）
    ('PubMed、UpToDate', '照护规范库、老年医学文献库'),
    ('PubMed、UpToDate 及院内知识库', '照护规范库、老年医学文献库及机构知识库'),
    ('PubMed', '照护规范库'),
    ('UpToDate', '老年医学文献库'),
    ('Meditron-7B 与 Llama-3 医疗私有模型', 'Llama-3 等养老照护私有模型'),
    ('Meditron-7B/ Llama-3', 'Llama-3 等养老照护模型'),
    ('Meditron-7B', 'Llama-3'),
    ('人工智能医疗展', '人工智能养老展'),
    ('中国国际医疗器械博览会 (CMEF)、医疗康复展', '中国国际养老福祉博览会、康复辅具展'),
    ('人工智能+医疗', '人工智能+养老'),
    ('医疗', '养老'),
]

not_found = []
for old, new in repl:
    if old == new:
        continue
    n = t.count(old)
    if n == 0:
        not_found.append(old)
    t = t.replace(old, new)

# ===== 疾病预测表格 → 健康风险场景（结构化重写）=====
rows = [
    ('01', '跌倒风险（Fall Risk）', '失能/半失能照护区', 'high'),
    ('02', '压疮 / 压力性损伤（Pressure Injury）', '长期卧床照护区', 'high'),
    ('03', '阿尔茨海默病（Alzheimer\'s Disease）', '失智照护专区', 'high'),
    ('04', '脑卒中后遗症（Stroke Sequelae）', '康复照护区', 'high'),
    ('05', '帕金森病（Parkinson\'s Disease）', '失能照护区', 'mid'),
    ('06', '慢性心力衰竭（Chronic Heart Failure）', '慢病管理区', 'high'),
    ('07', '冠心病（Coronary Heart Disease）', '慢病管理区', 'high'),
    ('08', '高血压（Hypertension）', '慢病管理区', 'prev'),
    ('09', '2 型糖尿病（Type 2 Diabetes）', '慢病管理区', 'mid'),
    ('10', '慢性阻塞性肺疾病（COPD）', '呼吸照护区', 'mid'),
    ('11', '吞咽障碍 / 呛咳（Dysphagia）', '饮食照护区', 'high'),
    ('12', '营养不良 / 肌少症（Sarcopenia）', '营养照护区', 'mid'),
    ('13', '骨质疏松 / 骨折风险（Osteoporosis）', '康复照护区', 'prev'),
    ('14', '尿失禁（Urinary Incontinence）', '基础照护区', 'mid'),
    ('15', '便秘（Constipation）', '基础照护区', 'prev'),
    ('16', '睡眠障碍（Sleep Disorder）', '夜间照护区', 'mid'),
    ('17', '老年抑郁（Geriatric Depression）', '心理照护区', 'mid'),
    ('18', '慢性疼痛（Chronic Pain）', '疼痛照护区', 'mid'),
    ('19', '认知障碍走失风险（Wandering）', '失智照护专区', 'high'),
    ('20', '呼吸道感染 / 坠积性肺炎（Pneumonia）', '呼吸照护区', 'high'),
]

def badge(level):
    if level == 'high':
        return '<span class="px-2 py-1 bg-danger/20 text-danger text-xs rounded-full font-bold">高危</span>'
    if level == 'mid':
        return '<span class="px-2 py-1 bg-yellow-500/20 text-yellow-500 text-xs rounded-full font-bold">中危</span>'
    return '<span class="px-2 py-1 bg-secondary/20 text-secondary text-xs rounded-full font-bold">预防</span>'

tbody_rows = []
for num, name, scene, level in rows:
    tbody_rows.append(
        '                        <tr class="hover:bg-white/5 transition-colors">\n'
        f'                            <td class="p-5 text-center font-tech text-primary">{num}</td>\n'
        f'                            <td class="p-5 font-bold text-white">{name}</td>\n'
        f'                            <td class="p-5">{scene}</td>\n'
        f'                            <td class="p-5 text-center">{badge(level)}</td>\n'
        '                        </tr>'
    )
tbody = '\n'.join(tbody_rows)

new_section = '''    <section id="disease" class="py-32 bg-[#050B1A] relative reveal">
        <div class="max-w-7xl mx-auto px-6">
            <div class="text-center mb-20">
                <span class="text-primary font-bold tracking-[0.5em] text-xs uppercase block mb-4 font-tech">Health Risk Prediction</span>
                <h2 class="text-4xl md:text-5xl font-black text-white mb-6">MAPFM 训练/测试集 <span class="text-gradient">核心健康风险场景</span></h2>
                <div class="w-24 h-1 bg-gradient-to-r from-primary to-accent mx-auto rounded-full mb-8"></div>
                <p class="text-slate-400 max-w-3xl mx-auto">基于多智能体协同与跨模态数据融合，精准识别长者健康风险，持续获取数据，风险有时间窗口</p>
            </div>

            <div class="overflow-x-auto hide-scroll rounded-[2rem] border border-white/10 shadow-2xl bg-white/5">
                <table class="w-full text-left border-collapse min-w-[600px]">
                    <thead>
                        <tr class="bg-white/10 text-white text-sm tracking-wider">
                            <th class="p-5 font-bold w-16 text-center">序号</th>
                            <th class="p-5 font-bold">核心健康风险</th>
                            <th class="p-5 font-bold">覆盖照护场景</th>
                            <th class="p-5 font-bold text-center">预警级别</th>
                        </tr>
                    </thead>
                    <tbody class="text-sm text-slate-300 divide-y divide-white/5">
''' + tbody + '''
                    </tbody>
                </table>
            </div>
            <p class="text-center text-xs text-slate-500 mt-6"><i class="fas fa-info-circle mr-1"></i> 基于实验室标注数据与养老试点反馈，覆盖 20 大高频健康风险场景</p>
        </div>
    </section>'''

# 用 index 定位并替换整个 disease section
start = t.index('<section id="disease"')
end = t.index('</section>', start) + len('</section>')
t = t[:start] + new_section + t[end:]

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(t)

print("=== 替换完成 ===")
print("原文件长度:", len(orig), "字符")
print("新文件长度:", len(t), "字符")
print("未命中的替换词（0 次）:")
for s in not_found:
    print("  -", s)
