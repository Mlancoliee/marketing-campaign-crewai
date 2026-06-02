export type Locale = "zh" | "en"

export type Phase = "start" | "discovery" | "planning" | "integration" | "content" | "finalize"

export type AgentId = "chief_strategist" | "market_analyst" | "brand_creative_director" | "channel_planner" | "copywriter"

export type CardType = "audience" | "brand_creative" | "channel_plan" | "strategy" | "copywriting"

export type ActionType = "confirm" | "redo" | "rollback" | "finish"

export interface Action {
  id: string
  label: string
  type: ActionType
  target?: "brand" | "channel" | "all"
}

export interface SSEEvent {
  type: string
  phase?: Phase
  progress?: number
  agent?: AgentId
  lane?: "brand" | "channel"
  content?: string
  card?: CardType
  data?: Record<string, unknown>
  actions?: Action[]
  message?: string
  from?: string
  lanes?: string[]
  suggestions?: string[]
}

export interface ChatMessage {
  role: AgentId | "user"
  content: string
  phase: Phase
}

export interface CardData {
  audience: { content: string } | null
  brand_creative: { creatives: Record<string, unknown>[] } | null
  channel_plan: { plan: Record<string, unknown> } | null
  strategy: { content: string } | null
  copywriting: { content: Record<string, unknown> } | null
}

export interface HistoryItem {
  id: string
  campaignName: string
  timestamp: number
  phase: Phase
}

export interface AppState {
  phase: Phase
  progress: number
  locale: Locale
  conversationId: string
  streaming: boolean
  activeAgents: { agent: AgentId; lane?: string }[]
  pendingActions: Action[]
  statusMessage: string
  cards: CardData
  messages: ChatMessage[]
  parallelActive: boolean
  suggestions: string[]
  finalDocument: string
  reconciliationNotes: string
}

export type AppAction =
  | { type: "RESET" }
  | { type: "SET_LOCALE"; locale: Locale }
  | { type: "SET_CONVERSATION_ID"; id: string }
  | { type: "PHASE_CHANGE"; phase: Phase; progress: number }
  | { type: "AGENT_START"; agent: AgentId; lane?: string }
  | { type: "CHUNK"; agent: AgentId; content: string; lane?: string }
  | { type: "AGENT_END"; agent: AgentId; lane?: string }
  | { type: "CARD_UPDATE"; card: CardType; data: Record<string, unknown> }
  | { type: "ACTIONS"; actions: Action[] }
  | { type: "STATUS"; message: string }
  | { type: "PARALLEL_START"; lanes: string[] }
  | { type: "PARALLEL_END" }
  | { type: "CLEAR_CARD"; card: CardType }
  | { type: "ADD_MESSAGE"; message: ChatMessage }
  | { type: "STREAMING_START" }
  | { type: "STREAMING_END" }
  | { type: "DONE" }
  | { type: "ERROR"; message: string }
  | { type: "RESTORE"; state: Partial<AppState> }
  | { type: "SUGGESTIONS"; suggestions: string[] }
  | { type: "CLEAR_FINAL_DOC" }
  | { type: "SET_RECONCILIATION"; notes: string }
