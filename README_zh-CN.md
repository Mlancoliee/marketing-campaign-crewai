# 营销活动策划 - EdgeOne Makers Agent 模板

AI 驱动的营销活动策划工作台，支持多 Agent 协作、结构化卡片工作流、实时流式输出。

基于 [EdgeOne Makers](https://edgeone.ai/makers) + [CrewAI](https://crewai.com/) + Python 构建。

## 部署
[![使用 EdgeOne Makers 部署](https://cdnstatic.tencentcs.com/edgeone/pages/deploy.svg)](https://console.cloud.tencent.com/edgeone/makers/new?template=crewai-marketing-campaign&from=within&fromAgent=1&agentLang=python)

## 功能特性

### 核心策划流程
- **市场调研** — AI 分析师访谈用户，收集目标受众、卖点、预算等关键信息
- **并行策划** — 品牌创意 + 渠道策略同时生成，互不阻塞
- **策略整合** — 策略总监综合所有模块，输出统一方案
- **内容产出** — 文案专家产出标题、正文、CTA、社媒变体
- **方案定稿** — 生成完整结构化营销方案文档，自动检测冲突

### Agent 特性
- **5 人 Agent 团队** — 策略总监、市场分析师、品牌创意总监、渠道策划师、文案专家
- **真正的流式输出** — 通过 CrewAI 事件总线 + SSE 逐 token 推送
- **人机互动** — 卡片操作：确认、重做对比、跨阶段回退
- **重做对比模式** — 新旧方案并排对比，动画过渡，一键选择
- **跨阶段回退** — 可返回任意前序阶段，不丢失已有数据
- **智能推荐回答** — 调研阶段 AI 生成相关回答建议
- **持久化存储** — `context.store` 平台 Blob 存储，跨重启恢复

### 其他功能
- **导出方案** — 下载完整方案为 Markdown 文件
- **历史记录** — localStorage 索引 + 平台 Blob 持久化
- **双语支持** — 中文 / English 一键切换
- **响应式设计** — Sticky 导航、手风琴视图、流畅动画

## 项目结构

```
crewai-marketing-campaign-python/
├── agents/                         # Python Agent 后端
│   ├── stream.py                   # 主 SSE 处理器（kickoff + resume）
│   ├── _lib/
│   │   ├── state.py                # CampaignState（Pydantic）
│   │   ├── flow.py                 # MarketingCampaignFlow（CrewAI Flow）
│   │   ├── llm.py                  # LLM 配置
│   │   ├── feedback_provider.py    # 暂停/恢复机制
│   │   ├── persistence.py          # 进程内存状态存储
│   │   └── logger.py
│   └── _crews/
│       ├── agents.yaml             # 5 个 Agent 定义
│       ├── discovery_crew/         # 市场调研 Crew
│       ├── brand_creative_crew/    # 品牌创意 Crew
│       ├── channel_planning_crew/  # 渠道策划 Crew
│       ├── integration_crew/       # 策略整合 Crew
│       └── content_crew/           # 内容产出 Crew
├── src/                            # React 前端
│   ├── App.tsx                     # 主应用 + 状态管理（useReducer）
│   ├── hooks/
│   │   ├── useSSE.ts              # SSE 流式通信 hook
│   │   └── useHistory.ts          # localStorage 历史工具
│   ├── components/
│   │   ├── Header.tsx             # Logo + 语言切换 + 历史 + 新建
│   │   ├── PhaseProgress.tsx      # 5 阶段进度条
│   │   ├── StatusBar.tsx          # Agent 状态通知栏
│   │   ├── InputBar.tsx           # 输入框（支持推荐填充）
│   │   ├── StartPanel.tsx         # 活动名称 + 简要描述
│   │   ├── HistoryPanel.tsx       # 历史记录侧边栏
│   │   ├── views/
│   │   │   ├── DiscoveryView.tsx  # 对话问答 + 推荐按钮
│   │   │   ├── PlanningView.tsx   # 单列卡片 + 对比模式
│   │   │   ├── IntegrationView.tsx
│   │   │   ├── ContentView.tsx
│   │   │   └── FinalizeView.tsx   # 方案总览 + 完整文档 + 修改
│   │   └── cards/
│   │       ├── BaseCard.tsx       # 通用卡片外壳
│   │       ├── CompareCards.tsx   # 并排对比组件
│   │       ├── BrandCreativeCard.tsx
│   │       ├── ChannelPlanCard.tsx
│   │       ├── StrategyCard.tsx
│   │       └── CopywritingCard.tsx
│   ├── utils/export.ts           # Markdown 导出工具
│   ├── styles/index.css          # 设计系统（Flat Design）
│   ├── types/index.ts            # TypeScript 类型
│   └── i18n.ts                   # 中英文翻译
├── edgeone.json                   # EdgeOne 部署配置
├── package.json                   # 前端依赖
├── requirements.txt               # Python 依赖
└── vite.config.ts                 # Vite + React + TailwindCSS
```

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 填入你的 AI Gateway 配置：

```env
AI_GATEWAY_API_KEY=your-api-key
AI_GATEWAY_BASE_URL=your-gateway-url
```

### 3. 本地开发

```bash
edgeone makers dev
```

访问 http://localhost:8088

### 4. 部署

```bash
edgeone makers deploy
```

## 工作流程

```
市场调研 → 方案策划（并行） → 策略整合 → 内容产出 → 方案定稿
   │              │                │          │          │
   │   品牌创意 + 渠道策略      策略总监     文案专家     │
   │   （单列展示）              整合                     │
   │                                                     │
   └── AI 访谈收集需求 ──── 卡片确认/重做 ── 完整方案 ───┘
                             + 对比模式      文档生成
```

### 各阶段说明

| 阶段 | 负责 Agent | 用户交互 |
|------|-----------|---------|
| **市场调研** | 市场分析师 | 问答对话 + AI 推荐回答，信息够了可跳过 |
| **方案策划** | 创意总监 + 渠道策划师 | 查看卡片，确认或重做（支持对比） |
| **策略整合** | 策略总监 | 确认、重做或回退到策划阶段 |
| **内容产出** | 文案专家 | 确认、重做或回退到整合阶段 |
| **方案定稿** | 策略总监 | 生成完整文档，基于文档修改，导出 |

## 接口协议

| 端点 | 方法 | 说明 | 响应格式 |
|------|------|------|----------|
| `/stream` | POST | 所有交互（启动、恢复、历史） | SSE / JSON |

### 请求格式

```json
{
  "action": "send" | "history",
  "conversation_id": "uuid",
  "locale": "zh" | "en",
  "campaign_name": "活动名称",
  "campaign_brief": "简要描述",
  "message": "用户回答",
  "skip_discovery": true,
  "card_action": { "target": "brand"|"channel", "type": "confirm"|"redo"|"keep_old" },
  "phase_action": { "type": "confirm"|"redo"|"rollback"|"keep_old" },
  "iteration_feedback": "修改意见"
}
```

### SSE 事件类型

```
conversation_id — 会话 ID
phase_change    — 切换前端视图
agent_start/end — Agent 活动指示器
chunk           — 流式文本内容
card_update     — 卡片数据更新
message         — 完整消息（调研阶段）
suggestions     — AI 推荐回答
actions         — 可用操作按钮
status          — 状态栏通知
done            — 流结束
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `AI_GATEWAY_API_KEY` | 是 | AI Gateway API Key |
| `AI_GATEWAY_BASE_URL` | 是 | AI Gateway Base URL |

## 使用模型

默认：`openai/@makers/deepseek-v4-flash`（流式）+ `openai/deepseek-v4-flash`（路由判断）。

| 模型 | 推荐场景 |
|------|---------|
| `@makers/deepseek-v4-flash` | **推荐** — 响应快、结构化输出好 |
| `@makers/minimax-m2.7` | 通用 |

## 技术栈

- **前端**: React 19 + Vite 8 + TailwindCSS 4 + TypeScript
- **Agent**: [CrewAI](https://crewai.com/) 1.14+（Python，Flow + 多 Crew 协作）
- **LLM**: [LiteLLM](https://github.com/BerriAI/litellm)（OpenAI 兼容接口）
- **存储**: `context.store`（平台 Blob 存储）+ 进程内存
- **部署**: [EdgeOne Makers](https://edgeone.ai/makers)

## 设计系统

- **风格**: Flat Design
- **主色**: `#7C3AED`（紫色）
- **CTA**: `#F97316`（橙色）
- **字体**: Poppins（标题）+ Open Sans（正文）

## License

MIT
