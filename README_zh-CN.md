# Marketing Campaign Planner

基于 CrewAI 多智能体框架的 AI 营销活动策划系统，通过交互式分阶段对话引导用户完成端到端的营销方案策划。

**框架:** CrewAI · **分类:** 营销策划 · **语言:** Python

[![部署到 EdgeOne Makers](https://cdnstatic.tencentcs.com/edgeone/pages/deploy.svg)](https://console.cloud.tencent.com/edgeone/makers/new?template=crewai-marketing-campaign&from=within&fromAgent=1&agentLang=python)

## 概述

本模板实现了一个基于 CrewAI Flows 和 React 前端的全栈营销活动策划 Agent。系统引导用户经历结构化的 5 阶段工作流 —— 从需求调研到最终内容交付 —— 使用专业 AI Crew 协作产出品牌创意、渠道策略和整合营销方案。每个阶段都内置人机协作反馈机制，用户可在推进前对输出内容进行迭代修改。

- 多阶段编排：需求调研、方案策划（品牌+渠道并行）、策略整合、内容产出、方案定稿
- 每个阶段均支持人机协作，通过 CrewAI `@human_feedback` 装饰器实现确认、重做、回退操作
- 实时 SSE 流式输出 Agent 推理过程和结构化卡片内容
- 会话持久化 + 粘性路由 —— 对话可跨实例重启恢复
- 分支操作（重做品牌、重做渠道、返回上一步）在主流程外独立处理，不重启 Flow

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `AI_GATEWAY_API_KEY` | 是 | 模型网关 API Key。使用 Makers Models API Key，或任何 OpenAI 兼容的供应商密钥。 |
| `AI_GATEWAY_BASE_URL` | 是 | 网关基础 URL。Makers Models 使用 `https://ai-gateway.edgeone.link/v1`。 |
| `AI_GATEWAY_MODEL` | 否 | 模型 ID。默认为 `@makers/deepseek-v4-flash`。 |

本模板遵循 OpenAI 兼容标准 —— 可指向 Makers Models 或任何兼容的模型供应商。

### 如何获取 AI_GATEWAY_API_KEY

1. 打开 [Makers 控制台](https://console.cloud.tencent.com/edgeone/makers)
2. 登录并开通 Makers
3. 进入 **Makers → 模型 → API Key**，创建一个密钥
4. 将密钥填入 `AI_GATEWAY_API_KEY`

内置模型免费但有速率限制，适合开发和验证。生产环境建议绑定自有供应商密钥（BYOK）。

## 本地开发

### 前置条件

- Node.js >= 18
- Python >= 3.11

### 命令

```bash
# 安装前端依赖
npm install

# 安装 Python Agent 依赖
pip install -r requirements.txt

# 复制环境变量文件
cp .env.example .env
# 填写 AI_GATEWAY_API_KEY 和 AI_GATEWAY_BASE_URL

# 启动本地开发（前端 + Agent + Cloud Functions 同时运行）
edgeone makers dev
```

开发服务器同时运行 Vite 前端、CrewAI Agent（`agents/stream.py`）和 Cloud Functions。访问 `http://localhost:8088` 查看应用，`http://localhost:8080/agent-metrics` 查看可观测面板。

## 项目结构

```
.
├── agents/                          # CrewAI Agent 运行时（Python）
│   ├── stream.py                    # POST /stream — SSE 流式主入口
│   ├── _lib/
│   │   ├── flow.py                  # MarketingCampaignFlow（5步编排）
│   │   ├── persistence.py           # 进程内 FlowPersistence + 外部存储同步
│   │   ├── feedback_provider.py     # 人机反馈 Provider 桥接
│   │   ├── llm.py                   # LLM 初始化工具
│   │   └── logger.py               # 结构化日志
│   └── _crews/
│       ├── agents.yaml              # 共享 Agent 定义
│       ├── discovery_crew/          # 市场分析师 — 受众与洞察问答
│       ├── brand_creative_crew/     # 品牌创意总监 — 视觉与信息架构
│       ├── channel_planning_crew/   # 渠道策划师 — 媒体组合与预算
│       ├── integration_crew/        # 策略总监 — 统一方案整合
│       └── content_crew/            # 文案专家 — 最终内容产出
├── cloud-functions/                 # 辅助 HTTP 端点（Python）
│   ├── history.py                   # POST /history — 加载会话历史
│   ├── delete.py                    # POST /delete — 删除会话
│   └── requirements.txt
├── src/                             # React + TypeScript 前端
│   ├── App.tsx                      # 主应用 + 状态管理
│   ├── components/
│   │   ├── cards/                   # 结构化输出卡片（品牌、渠道等）
│   │   ├── views/                   # 阶段视图（调研、策划等）
│   │   ├── Header.tsx               # 导航 + 语言切换
│   │   ├── PhaseProgress.tsx        # 5阶段进度指示器
│   │   ├── InputBar.tsx             # 带建议的聊天输入框
│   │   ├── StartPanel.tsx           # 活动简介输入面板
│   │   └── HistoryPanel.tsx         # 会话历史侧边栏
│   ├── hooks/
│   │   ├── useSSE.ts               # SSE 流消费 Hook
│   │   └── useHistory.ts           # 会话历史 Hook
│   ├── i18n.ts                      # 国际化（中/英）
│   ├── types/index.ts               # TypeScript 类型定义
│   └── utils/export.ts              # Markdown 导出工具
├── edgeone.json                     # EdgeOne Pages 配置
├── package.json                     # 前端依赖与脚本
├── requirements.txt                 # Python 依赖（crewai[litellm,tools]）
└── vite.config.ts                   # Vite + React + TailwindCSS 配置
```

## 工作原理

### 会话模式与粘性路由

每个对话通过 `conversation_id` 标识。前端在每次请求中通过 `Makers-Conversation-Id` HTTP Header 发送此 ID。EdgeOne Agent 运行时使用粘性路由将对话固定到特定实例，确保内存中的 Flow 状态（暂停/恢复上下文）在请求间可访问。冷启动或实例迁移时，挂起状态通过 `load_pending_from_store()` 从持久化存储恢复。

### 工作流阶段

`MarketingCampaignFlow` 类（`agents/_lib/flow.py`）使用 CrewAI 的 `@start`、`@listen`、`@router` 装饰器编排 5 步顺序工作流：

```
需求调研 → 方案策划 → 策略整合 → 内容产出 → 方案定稿
```

1. **需求调研** — `DiscoveryCrew`（市场分析师）迭代提问（最多 4 轮）收集活动目标、目标受众和市场背景。每轮通过 `@human_feedback` 暂停并等待用户输入。当分析师检测到信息充足时，输出 `[READY]` 标记自动推进。

2. **方案策划** — 两个 Crew ：
   - `BrandCreativeCrew` — 生成品牌定位、视觉方向和信息框架
   - `ChannelPlanningCrew` — 产出媒体渠道组合、预算分配和排期策略
   
   两者输出以结构化卡片呈现，用户可独立确认或重做。

3. **策略整合** — `IntegrationCrew` 将品牌和渠道输出合并为统一、连贯的营销战役策略文档。

4. **内容产出** — `ContentCrew` 基于整合策略生成最终文案交付物（标题、正文、CTA、社交媒体变体）。

5. **方案定稿** — 汇总完整营销方案，提供全文档生成、修改迭代和 Markdown 导出功能。

### 人机协作

每个阶段边界使用 CrewAI 的 `@human_feedback` 装饰器配合自定义 `FeedbackProvider`。Flow 在每个 Crew 输出后暂停，通过 `card_update` 事件将结果流式推送到前端，等待用户操作：

- **确认** — 接受并推进到下一阶段
- **重做** — 重新生成当前阶段输出（带新旧对比视图）
- **返回** — 回退到之前的阶段（不丢失下游数据）

分支操作（`redo_brand`、`redo_channel`、`rollback`）由 `stream.py` 的 handler 层拦截，直接调用 Crew，不经过主 Flow 路由。

### Crew 与角色

| Crew | Agent 角色 | 职责 |
|------|-----------|------|
| `DiscoveryCrew` | 市场分析师 | 结构化问答提取活动需求 |
| `BrandCreativeCrew` | 品牌创意总监 | 品牌定位、视觉识别、信息架构 |
| `ChannelPlanningCrew` | 渠道策划师 | 媒体组合、预算分配、排期 |
| `IntegrationCrew` | 策略总监 | 整合所有输入为统一策略 |
| `ContentCrew` | 文案专家 | 最终交付内容产出 |

### 关键路由

| 方法 | 路径 | 处理器 | 说明 |
|------|------|--------|------|
| POST | `/stream` | `agents/stream.py` | Agent 主入口 — SSE 流式、kickoff/resume |
| POST | `/history` | `cloud-functions/history.py` | 加载会话消息和阶段状态 |
| POST | `/delete` | `cloud-functions/delete.py` | 删除会话 |

### Conversation ID 传递

1. 前端在每次请求中发送 `Makers-Conversation-Id` Header
2. 首次请求（无 ID）时，运行时生成新 `conversation_id` 并通过 SSE 流返回 `conversation_id` 事件
3. 后续请求携带此 ID 以恢复同一 Flow 实例
4. 粘性路由确保请求到达持有内存 Flow 状态的同一实例
5. 实例重启时，`persistence.py` 从 `context.store` 恢复挂起的 `HumanFeedbackPending` 上下文

### 运行时配置（edgeone.json）

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "agents": {
    "framework": "crewai",
    "dir": "agents",
  }
}
```

| 字段 | 值 | 用途 |
|------|------|------|
| `agents.framework` | `crewai` | 指示运行时加载 CrewAI Agent 处理器 |
| `agents.dir` | `agents` | 包含 `stream.py` 和 Crew 定义的目录 |
| `buildCommand` | `npm run build` | Vite 前端生产构建 |
| `outputDirectory` | `dist` | 与 Agent 一起提供的静态资源 |

## 相关资源

- [EdgeOne Makers Agents 文档](https://cloud.tencent.com/document/product/1552/132759)
- [Makers 快速开始](https://cloud.tencent.com/document/product/1552/132786)
- [Makers Models](https://cloud.tencent.com/document/product/1552/132748)

## 许可证

MIT
