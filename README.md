# Marketing Campaign Planner - EdgeOne Makers Agent Template

AI-powered marketing campaign planning workbench with multi-agent collaboration, structured card-based workflows, and real-time streaming output.

Built on [EdgeOne Makers](https://edgeone.ai/makers) + [CrewAI](https://crewai.com/) + Python.

## Deploy
[![Deploy to EdgeOne Makers](https://cdnstatic.tencentcs.com/edgeone/pages/deploy.svg)](https://console.cloud.tencent.com/edgeone/makers/new?template=crewai-marketing-campaign&from=within&fromAgent=1&agentLang=python)

## Features

### Core Planning Pipeline
- **Market Research (Discovery)** — AI analyst interviews user to understand campaign goals, audience, budget
- **Parallel Planning** — Brand creative + channel strategy generated simultaneously
- **Strategy Integration** — Chief strategist synthesizes all inputs into unified plan
- **Content Creation** — Copywriter produces headlines, body, CTAs, social variants
- **Plan Finalization** — Full structured document generation with conflict resolution

### Agent Features
- **5-Agent Team** — Chief Strategist, Market Analyst, Creative Director, Channel Planner, Copywriter
- **Real-time Streaming** — Token-by-token output via CrewAI event bus + SSE
- **Human-in-the-Loop** — Card-based interactions: confirm, redo with comparison, rollback
- **Redo Comparison** — Side-by-side old/new version comparison with animated transitions
- **Cross-stage Rollback** — Go back to any previous stage without losing data
- **Smart Suggestions** — AI-generated reply suggestions during research phase
- **Persistent Storage** — `context.store` for cross-restart session recovery

### Other
- **Export** — Download complete plan as Markdown file
- **History** — Session list with localStorage index + platform Blob storage
- **Bilingual** — Chinese / English toggle
- **Responsive** — Sticky navigation, accordion views, smooth animations

## Project Structure

```
crewai-marketing-campaign-python/
├── agents/                         # Python Agent Backend
│   ├── stream.py                   # Main SSE handler (kickoff + resume)
│   ├── _lib/
│   │   ├── state.py                # CampaignState (Pydantic)
│   │   ├── flow.py                 # MarketingCampaignFlow (CrewAI Flow)
│   │   ├── llm.py                  # LLM configuration
│   │   ├── feedback_provider.py    # Pause/resume mechanism
│   │   ├── persistence.py          # In-memory state store
│   │   └── logger.py
│   └── _crews/
│       ├── agents.yaml             # 5 agent definitions
│       ├── discovery_crew/         # Market research crew
│       ├── brand_creative_crew/    # Brand & creative crew
│       ├── channel_planning_crew/  # Channel strategy crew
│       ├── integration_crew/       # Strategy integration crew
│       └── content_crew/           # Copywriting crew
├── src/                            # React Frontend
│   ├── App.tsx                     # Main app + state management (useReducer)
│   ├── hooks/
│   │   ├── useSSE.ts              # SSE streaming hook
│   │   └── useHistory.ts          # localStorage history utility
│   ├── components/
│   │   ├── Header.tsx             # Logo + locale + history + new
│   │   ├── PhaseProgress.tsx      # 5-phase progress bar
│   │   ├── StatusBar.tsx          # Agent status notifications
│   │   ├── InputBar.tsx           # Chat input with prefill
│   │   ├── StartPanel.tsx         # Campaign name + brief input
│   │   ├── HistoryPanel.tsx       # Session history sidebar
│   │   ├── views/
│   │   │   ├── DiscoveryView.tsx  # Q&A chat + suggestions
│   │   │   ├── PlanningView.tsx   # Single-column cards + comparison
│   │   │   ├── IntegrationView.tsx
│   │   │   ├── ContentView.tsx
│   │   │   └── FinalizeView.tsx   # Overview + full document + edit
│   │   └── cards/
│   │       ├── BaseCard.tsx       # Reusable card shell
│   │       ├── CompareCards.tsx   # Side-by-side comparison
│   │       ├── BrandCreativeCard.tsx
│   │       ├── ChannelPlanCard.tsx
│   │       ├── StrategyCard.tsx
│   │       └── CopywritingCard.tsx
│   ├── utils/export.ts           # Markdown export utility
│   ├── styles/index.css          # Design system (Flat Design)
│   ├── types/index.ts            # TypeScript types
│   └── i18n.ts                   # Chinese/English translations
├── edgeone.json                   # EdgeOne deployment config
├── package.json                   # Frontend dependencies
├── requirements.txt               # Python dependencies
└── vite.config.ts                 # Vite + React + TailwindCSS
```

## Quick Start

```bash
# Install frontend dependencies
npm install

# Configure environment variables
cp .env.example .env
# Edit .env with your AI Gateway credentials

# Local development
edgeone makers dev
```

Visit http://localhost:8088

## Workflow

```
Discovery → Planning (parallel) → Integration → Content → Finalize
   │              │                    │            │          │
   │   Brand Creative + Channel    Strategy     Copywriting   │
   │   Strategy (side by side)    Integration                  │
   │                                                           │
   └─── AI interviews user ──────── Cards with ─── Full plan ─┘
        to understand needs         confirm/redo    document
                                    + comparison    generation
```

### Phase Details

| Phase | Agent | User Interaction |
|-------|-------|-----------------|
| **Discovery** | Market Analyst | Q&A with AI suggestions, skip when ready |
| **Planning** | Creative Director + Channel Planner | Review cards, confirm or redo with comparison |
| **Integration** | Chief Strategist | Confirm, redo, or rollback to planning |
| **Content** | Copywriter | Confirm, redo, or rollback to integration |
| **Finalize** | Chief Strategist | Generate full document, edit via chat, export |

## API Endpoint

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/stream` | POST | All interactions (kickoff, resume, history) | SSE / JSON |

### Request Protocol

```json
{
  "action": "send" | "history",
  "conversation_id": "uuid",
  "locale": "zh" | "en",
  "campaign_name": "...",
  "campaign_brief": "...",
  "message": "...",
  "skip_discovery": true,
  "card_action": { "target": "brand"|"channel", "type": "confirm"|"redo"|"keep_old" },
  "phase_action": { "type": "confirm"|"redo"|"rollback"|"keep_old" },
  "iteration_feedback": "..."
}
```

### SSE Event Types

```
conversation_id — Session ID assignment
phase_change    — Switch frontend view
agent_start/end — Agent activity indicators
chunk           — Streaming text content
card_update     — Card data update
message         — Complete message (discovery)
suggestions     — AI reply suggestions
actions         — Available action buttons
status          — Status bar notification
done            — Stream complete
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AI_GATEWAY_API_KEY` | Yes | AI Gateway API Key |
| `AI_GATEWAY_BASE_URL` | Yes | AI Gateway Base URL |

## Recommended Models

Default: `openai/@makers/deepseek-v4-flash` (streaming) + `openai/deepseek-v4-flash` (routing).

| Model | Best For |
|-------|---------|
| `@makers/deepseek-v4-flash` | **Recommended** — Fast, good at structured output |
| `@makers/minimax-m2.7` | General purpose |

## Tech Stack

- **Frontend**: React 19 + Vite 8 + TailwindCSS 4 + TypeScript
- **Agent**: [CrewAI](https://crewai.com/) 1.14+ (Python, Flow + multi-Crew)
- **LLM**: [LiteLLM](https://github.com/BerriAI/litellm) (OpenAI-compatible)
- **Storage**: `context.store` (platform Blob storage) + in-memory state
- **Deployment**: [EdgeOne Makers](https://edgeone.ai/makers)

## Design System

- **Style**: Flat Design
- **Primary**: `#7C3AED` (Purple)
- **CTA**: `#F97316` (Orange)
- **Typography**: Poppins (headings) + Open Sans (body)

## Deployment

```bash
edgeone makers deploy
```

## License

MIT
