import { useCallback, useRef } from "react"
import type { AppAction, SSEEvent, Locale } from "../types"

interface SendOptions {
  message?: string
  skip_discovery?: boolean
  card_action?: {
    target: "brand" | "channel"
    type: "confirm" | "redo" | "keep_old"
    selected_index?: number
    feedback?: string
    previous_data?: Record<string, unknown>
  }
  phase_action?: {
    type: "confirm" | "redo" | "rollback" | "keep_old"
    feedback?: string
  }
  iteration_feedback?: string
  finish?: boolean
  campaign_name?: string
  campaign_brief?: string
  locale?: Locale
}

export function useSSE(dispatch: React.Dispatch<AppAction>) {
  const conversationIdRef = useRef<string>("")
  const abortRef = useRef<AbortController | null>(null)

  const setConversationId = useCallback((id: string) => {
    conversationIdRef.current = id
    dispatch({ type: "SET_CONVERSATION_ID", id })
  }, [dispatch])

  const send = useCallback(async (options: SendOptions = {}) => {
    // Abort previous request if any
    if (abortRef.current) {
      abortRef.current.abort()
    }

    const controller = new AbortController()
    abortRef.current = controller

    dispatch({ type: "STREAMING_START" })

    try {
      const body: Record<string, unknown> = {
        action: "send",
        conversation_id: conversationIdRef.current || undefined,
        ...options,
      }

      // 线上 Makers 平台需要 makers-conversation-id header
      const convId = conversationIdRef.current || crypto.randomUUID()
      if (!conversationIdRef.current) {
        conversationIdRef.current = convId
      }

      const response = await fetch("/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "makers-conversation-id": convId,
        },
        body: JSON.stringify({ ...body, conversation_id: convId }),
        signal: controller.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error("No response body")

      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6).trim()
            if (!data || data === "[DONE]") continue

            try {
              const event: SSEEvent = JSON.parse(data)
              handleEvent(event)
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }

      // Process remaining buffer
      if (buffer.startsWith("data: ")) {
        const data = buffer.slice(6).trim()
        if (data && data !== "[DONE]") {
          try {
            const event: SSEEvent = JSON.parse(data)
            handleEvent(event)
          } catch {
            // Skip
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return
      dispatch({ type: "ERROR", message: err instanceof Error ? err.message : "Unknown error" })
    } finally {
      // 只有当前 controller 仍是活跃的才 dispatch STREAMING_END
      // （如果被新请求 abort 了，abortRef 已经指向新 controller）
      if (abortRef.current === controller) {
        dispatch({ type: "STREAMING_END" })
        abortRef.current = null
      }
    }
  }, [dispatch])

  const loadHistory = useCallback(async (id?: string) => {
    const cid = id || conversationIdRef.current
    if (!cid) return

    try {
      // 优先调用 cloud-function /history（独立于 agent 进程）
      let response = await fetch("/history", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "makers-conversation-id": cid,
        },
        body: JSON.stringify({ conversation_id: cid }),
      })

      // 如果 /history 不可用（404），回退到 agent /stream
      if (!response.ok) {
        response = await fetch("/stream", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "makers-conversation-id": cid,
          },
          body: JSON.stringify({ action: "history", conversation_id: cid }),
        })
      }

      if (!response.ok) return

      const data = await response.json()

      if (data.current_phase && data.current_phase !== "start") {
        conversationIdRef.current = cid
        dispatch({ type: "SET_CONVERSATION_ID", id: cid })
        dispatch({
          type: "RESTORE",
          state: {
            phase: data.current_phase,
            conversationId: cid,
            cards: data.cards || {},
            messages: (data.chat_history || []).map((m: { role: string; content: string; phase?: string }) => {
              let content = m.content
              if (content.includes("[SUGGEST")) {
                content = content.split("[SUGGEST")[0].trim()
              }
              return { role: m.role, content, phase: m.phase || data.current_phase }
            }),
          },
        })
      } else {
        dispatch({ type: "STATUS", message: "会话已过期，请新建" })
      }
    } catch {
      dispatch({ type: "STATUS", message: "加载失败" })
    }
  }, [dispatch])

  const abort = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
  }, [])

  function handleEvent(event: SSEEvent) {
    switch (event.type) {
      case "conversation_id":
        if (event.data?.id) {
          setConversationId(event.data.id as string)
        }
        break

      case "phase_change":
        if (event.phase) {
          dispatch({ type: "PHASE_CHANGE", phase: event.phase, progress: event.progress ?? 0 })
        }
        break

      case "agent_start":
        if (event.agent) {
          dispatch({ type: "AGENT_START", agent: event.agent, lane: event.lane })
        }
        break

      case "chunk":
        if (event.agent && event.content) {
          dispatch({ type: "CHUNK", agent: event.agent, content: event.content, lane: event.lane })
        }
        break

      case "agent_end":
        if (event.agent) {
          dispatch({ type: "AGENT_END", agent: event.agent, lane: event.lane })
        }
        break

      case "card_update":
        if (event.card && event.data) {
          dispatch({ type: "CARD_UPDATE", card: event.card, data: event.data })
        }
        break

      case "actions":
        if (event.actions) {
          dispatch({ type: "ACTIONS", actions: event.actions })
        }
        break

      case "status":
        if (event.message) {
          dispatch({ type: "STATUS", message: event.message })
        }
        break

      case "parallel_start":
        if (event.lanes) {
          dispatch({ type: "PARALLEL_START", lanes: event.lanes })
        }
        break

      case "parallel_end":
        dispatch({ type: "PARALLEL_END" })
        break

      case "suggestions":
        if (event.suggestions) {
          dispatch({ type: "SUGGESTIONS", suggestions: event.suggestions })
        }
        break

      case "message":
        if (event.content && event.from) {
          dispatch({
            type: "ADD_MESSAGE",
            message: {
              role: event.from as "market_analyst" | "user",
              content: event.content,
              phase: event.phase || "discovery",
            },
          })
        }
        break

      case "done":
        dispatch({ type: "DONE" })
        break

      case "error":
        dispatch({ type: "ERROR", message: event.message || "Unknown error" })
        break
    }
  }

  return { send, loadHistory, abort, setConversationId, conversationIdRef }
}
