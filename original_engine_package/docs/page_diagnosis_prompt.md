# MAPFM 诊断演示页生成 Prompt

> 用途：喂给 LLM（Gemini / Claude 等）生成 `dashboard/pages/page_diagnosis.py`。
> 目标：为 MAPFM HMAE 医学多智能体系统做一个"诊断演示页"，用于 iCAN 大赛现场答辩演示。
> 设计来源：参考 `ai-doctor`（多医生会诊面板）+ `AI-disease-predictor`（症状诊断结果页）两个开源项目的布局。

---

## 0. 任务目标

在现有 Streamlit 暗色科幻风控制面板（`dashboard/`）中，新增一个页面 `dashboard/pages/page_diagnosis.py`，作为**首页/核心演示页**。页面要让评委在 30 秒内看懂"这系统怎么看病"：输入症状 → 多个 AI 智能体流水线会诊 → 输出诊断结论。

要求：复用现有主题，只新增本页，不改动 `theme.py` / `components.py` 的既有代码。

---

## 1. 技术栈与约束

- **框架**：Streamlit（Python），必须用 `st.` API，不要用 React/Vue/HTML 组件库。
- **主题**：已存在的暗色科幻主题，通过 `dashboard.theme.inject_dark_theme()` 注入。本页**不需要**重复注入。
- **后端**：调用 `eco.diagnose(query)` 获取诊断结果（`eco` 是 `HeterogeneousMultiAgentEcosystem` 实例，由页面父级传入）。
- **图表**：用 `plotly.graph_objects`（项目已用，见 `dashboard/theme.py` 的 `configure_plotly_dark`）。
- **现有组件**：`dashboard/components.py` 提供 `neon_metric_card / section_header / info_bar` 等，可复用。
- **渲染函数签名**：与现有页面一致 —— `def render(eco, config, dataset, monitor) -> None:`（参考 `pages/page_overview.py`）。

---

## 2. 现有主题资源（必须复用，颜色不得另造）

### 2.1 颜色系统（来自 `dashboard/theme.py` 的 `COLORS`）

| 用途 | 值 |
|---|---|
| 页面背景 | `#0a0a14` |
| 面板背景 | `rgba(12,18,35,0.85)` |
| 卡片背景 | `rgba(16,24,48,0.75)` |
| 输入框背景 | `rgba(20,30,55,0.7)` |
| 主霓虹色（青） | `#00f5ff` |
| 洋红 | `#ff00e5` |
| 紫 | `#7c3aed` |
| 成功绿 | `#00ff88` |
| 警告黄 | `#ffaa00` |
| 危险红 | `#ff3344` |
| 正文 | `#e0e0ff` |
| 次要文字 | `#7a8ba8` |
| 弱文字 | `#4a5578` |

### 2.2 图表调色板 `CHART_PALETTE`

```
#00f5ff, #ff00e5, #7c3aed, #00ff88, #ffaa00, #ff3344, #3b82f6, #ff8c00
```

### 2.3 现成 CSS class（可直接在 `st.markdown(..., unsafe_allow_html=True)` 里用）

- `.glass-panel` —— 玻璃拟态面板
- `.section-header` —— 带渐变下划线的区块标题
- `.info-box info / success / warning / error` —— 带左侧色条的信息框
- `.status-badge status-healthy / status-degraded / status-offline / status-unknown` —— 状态徽章
- `.pulse-dot dot-green / dot-yellow / dot-red / dot-gray` —— 脉冲状态圆点
- `.neon-text-cyan / magenta / green / danger` —— 霓虹发光文字

---

## 3. 页面整体结构（三区块，自上而下）

页面用 `st.container()` 或直接顺序渲染，从上到下三个区块：

```
┌──────────────────────────────────────────────────────────┐
│ 区块A：输入区  症状chips + 主诉textarea + 化验单上传 + [开始诊断] │
├──────────────────────────────────────────────────────────┤
│ 区块B：会诊过程区  各智能体按流水线发言 + 阶段/轮次 + 投票事件       │
├──────────────────────────────────────────────────────────┤
│ 区块C：结果区  主诊断+置信度 | 风险分级 | 鉴别诊断图 | 建议         │
└──────────────────────────────────────────────────────────┘
```

- 初始状态：只显示区块A，B、C 隐藏。
- 点击「开始诊断」后：显示区块B（会诊过程逐条滚动出现），完成后显示区块C。
- 所有状态存在 `st.session_state`，键名前缀统一用 `dx_`（避免与其他页冲突）。

---

## 4. 区块A：输入区（抄 AI-disease-predictor 的 SymptomForm）

### 4.1 布局

放在一个 `.glass-panel` 内，从上到下：

1. **标题**：用 `.section-header` 显示「患者信息」。
2. **症状多选网格**：`st.multiselect` 或自绘 chips。若用 multiselect，症状列表取 `dataset` 里真实症状列（若取不到，用一组通用常见症状兜底：发热、咳嗽、头痛、乏力、胸痛、腹痛、恶心、眩晕）。要求：
   - 选中的症状以彩色 pill/chip 显示（复用主题色）。
   - 至少选 1 个或填 1 句主诉才能提交，否则 `st.warning` 提示。
3. **主诉文本框**：`st.text_area`，占位符「请描述您的主要症状与不适，例如：持续三天高热、干咳、乏力…」。
4. **化验单/报告上传**（可选）：`st.file_uploader`，accept 图片与文本，接已有 multimodal 能力；若未上传则跳过。
5. **提交按钮**：`st.button("开始诊断", type="primary", use_container_width=True)`。点击后进入 loading 状态（按钮 disable + spinner）。

### 4.2 交互要求

- 提交时清空旧结果（`dx_history = []`、`dx_result = None`）。
- 提交后不要立即显示结果，先进入区块B（会诊过程）。

---

## 5. 区块B：会诊过程区（抄 ai-doctor 的 DiscussionPanel + ChatDisplay + StatusPanel + VoteTally）

这是**本页的核心卖点**，也是评委最看的部分：把多智能体的"讨论/投票"过程可视化。

### 5.1 阶段状态机（必须实现）

```
setup → discussion → voting → finished
```

- `setup`：尚未开始（初始）。
- `discussion`：各智能体按流水线顺序"发言"。
- `voting`：共识投票阶段（DMA/TFA/Verification 投标签）。
- `finished`：会诊结束，进入结果区。

阶段存于 `st.session_state.dx_phase`。顶部用一条控制条显示当前阶段文案：
- `setup` → 「准备中」
- `discussion` → 「讨论中」
- `voting` → 「评估中」
- `finished` → 「已结束」

控制条右侧放一个**轮次/进度指示**（`dx_round`，从 1 递增）。

### 5.2 消息类型与渲染（抄 ChatDisplay.vue 的 5 种消息）

`dx_history` 是一个 list，每条消息是一个 dict，含 `type` 字段。五种类型：

| type | 含义 | 视觉 |
|---|---|---|
| `system` | 系统提示（如"会诊开始"） | 居中、弱色小字（`text_dim`） |
| `agent` | 某个智能体发言 | 左侧：圆形头像(缩写) + 该 agent 专属色气泡 + agent 名 + 正文 |
| `patient` | 患者补充 | 右侧气泡，青色系 |
| `vote` | 投票/标注事件 | 居中橙色徽章条「A 标注 B：原因」 |
| `hilt` | 人工介入(HITL)触发 | 黄色警示条，高亮 |

**渲染方式**：不能用 Streamlit 原生 chat（会重排），用 `st.markdown` 手写 HTML/CSS 逐条渲染，或 `st.container` + 自定义样式。每条消息左/右对齐、气泡圆角、agent 配色。

### 5.3 智能体配色（抄 ai-doctor 的 doctorPalette 思想）

给每个智能体一个**固定、可区分**的颜色，取自 `CHART_PALETTE`，按 agent 名 hash 或按固定映射。建议映射：

| 智能体 | 中文 | 颜色 |
|---|---|---|
| Perception | 感知 | `#00f5ff` 青 |
| RAA | 检索增强分析 | `#ff00e5` 洋红 |
| DMA | 诊断多智能体 | `#7c3aed` 紫 |
| TFA | 可信度融合 | `#00ff88` 绿 |
| Fusion | 融合 | `#ffaa00` 黄 |
| Verification | 验证 | `#ff3344` 红 |
| Consensus | 共识 | `#ff8c00` 橙 |

> 注：以代码里 `eco` 实际的 agent 列表为准，按顺序从 `CHART_PALETTE` 取色；不足则循环。每个 agent 气泡的边框色 = 该 agent 色，底色 = 该 agent 色的 12% 透明度，名字色 = 该 agent 色。

### 5.4 侧栏状态面板（抄 StatusPanel.vue）

在会诊过程区右侧（`st.columns([3,1])`）放一个状态面板：

1. **阶段 / 当前轮次**：两个 `neon_metric_card`。
2. **智能体列表**（抄 DoctorList）：每个 agent 一行，左侧 agent 名（当前正在发言的 agent 用其专属色 + 脉冲圆点 `.pulse-dot dot-green`），右侧状态徽章 `.status-badge`（在席/已发言/待发言）。
3. **投票统计**（抄 VoteTally）：`voting` 阶段显示一个表：智能体 → 得票数；下方列出投票详情「X → Y：原因」。

### 5.5 逐条滚动与打字机效果

- 会诊消息应**逐条出现**（模拟实时发言），用 `st.empty()` + `time.sleep()` 逐条 append 并 `st.rerun()`，或一次性渲染后用 CSS `animation: fadeInUp 0.25s` 实现淡入。
- 若用逐条实时渲染，每条 agent 消息间隔约 0.4–0.8 秒，营造"多智能体在思考"的演示感。

---

## 6. 区块C：结果区（抄 AI-disease-predictor 的 PredictionResult）

会诊 `finished` 后显示。两栏布局 `st.columns([2,1])`。

### 6.1 左栏（占 2/3），从上到下：

1. **主诊断卡片**（抄 Primary Prediction）：
   - 小标题「主诊断」。
   - 诊断名大字（`st.markdown` 用 `neon-text-cyan` 放大）。
   - 置信度进度条：`st.progress(confidence)` 或自绘条形，右侧显示百分比。
2. **风险分级警示条**（抄 medical-mcp-agent 的急诊横幅，是 MAPFM 独有加分项）：
   - 根据 TFA 风险等级（low/medium/high/critical）显示一条 `.info-box`：
     - low → `.info-box success` 「低风险」
     - medium → `.info-box warning` 「中风险」
     - high → `.info-box warning` 「高风险，建议人工复核」
     - critical → `.info-box error` 「危急，已触发人工介入(HITL)」
3. **推理说明**（抄 Explanation）：一段正文，解释为什么得出该诊断。
4. **关键症状**（抄 Key Symptoms）：绿色 chips/pills 列表，标注影响诊断的主要症状。
5. **注意事项**（抄 Precautions）：`st.markdown` 无序列表。
6. **建议**（抄 Treatment）：`st.markdown` 无序列表。

### 6.2 右栏（占 1/3）：

**鉴别诊断置信度分布图**（抄 Confidence Distribution）：
- `plotly` 水平条形图（`orientation='h'`），X 轴 0–100%（或 0–1）。
- 数据 = 主诊断 + 鉴别诊断，按置信度从高到低排序。
- 用 `configure_plotly_dark(fig)` 套暗色主题，bar 色用 `#3b82f6` 或主霓虹色。
- 高度约 300px。

### 6.3 底部免责声明（必须有，医疗合规）

结果区底部固定一条弱色小字（`text_dim`，居中）：

> 「本系统为辅助决策工具，诊断结果仅供参考，不替代执业医师诊断。身体不适请及时就医。」

---

## 7. 数据流与 session_state 规范

```
点击[开始诊断]
  → dx_phase = "discussion"
  → 逐条 push agent 消息到 dx_history（Perception→RAA→DMA→TFA→Fusion→Verification）
  → dx_phase = "voting"，push 投票消息（DMA 2票 / TFA 1票 / Verification 1票，阈值 3）
  → 是否达阈值？否 → 触发 HITL 消息(push type=hilt)
  → dx_phase = "finished"，调 eco.diagnose(query) 拿到结果存 dx_result
  → 渲染区块C
```

session_state 键（统一 `dx_` 前缀）：

| 键 | 类型 | 含义 |
|---|---|---|
| `dx_phase` | str | setup/discussion/voting/finished |
| `dx_history` | list[dict] | 会诊消息流 |
| `dx_round` | int | 当前轮次 |
| `dx_result` | dict/None | `eco.diagnose()` 返回值 |
| `dx_input` | dict | 症状/主诉/上传文件 |

**关键注意**：`eco.diagnose()` 的真实返回结构**需要先读代码确认字段名**（不要猜）。在没确认前，结果区字段用"从 `dx_result` 里取对应键、取不到则显示占位符"—"—"的防御式写法。

---

## 8. 视觉规范总结

- 圆角：面板 12px，卡片 10px，按钮 8px。
- 字体：沿用主题的 `'Segoe UI', 'Microsoft YaHei', 'Courier New', monospace`。
- 间距：区块间 `st.divider()` 或 margin；卡片内 padding 1.2rem。
- 动画：消息淡入 `fadeInUp 0.25s`；脉冲圆点 `pulse-dot-glow`。
- 所有颜色从 `COLORS` / `CHART_PALETTE` 取，**禁止**另造新的主题色。

---

## 9. 输出要求

1. 输出**单个 Python 文件** `dashboard/pages/page_diagnosis.py`。
2. 函数签名 `def render(eco, config, dataset, monitor) -> None:`，风格与 `pages/page_overview.py` 一致。
3. 中文注释、中文界面文案，变量命名沿用项目 snake_case。
4. 健壮性：`eco` / `dataset` / `monitor` 为 `None` 时不崩溃，降级显示占位。
5. 不要 import 未安装的第三方库（仅 streamlit / plotly / 项目内模块 / numpy / pandas）。
6. 先给出 `eco.diagnose()` 返回结构的假设字段表，再据此写结果区映射代码，并附"若字段名不符如何改"的说明。

---

## 附：两个参考项目的关键源文件（可自行 Clone 对照）

- ai-doctor：`src/components/ChatDisplay.vue`、`DiscussionPanel.vue`、`StatusPanel.vue`、`VoteTally.vue`、`DoctorList.vue`
- AI-disease-predictor：`components/PredictionResult.tsx`、`SymptomForm.tsx`、`types.ts`、`App.tsx`
