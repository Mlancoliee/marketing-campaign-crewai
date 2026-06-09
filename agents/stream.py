"""POST /stream — 营销活动策划 Agent 主入口 (SSE streaming)

架构：
- 主流程（discovery → planning → integration → content → finalize）
  由 MarketingCampaignFlow 管理，使用 @human_feedback 暂停/恢复
- 分支操作（redo_brand / redo_channel / rollback 等）
  由 handler 层拦截，直接调用 Crew，不进 Flow
"""

import asyncio

from crewai.flow.async_feedback.types import HumanFeedbackPending
from crewai.types.streaming import FlowStreamingOutput, StreamChunkType
from crewai.utilities.streaming import (
    create_async_chunk_generator,
    create_streaming_state,
    register_cleanup,
    signal_end,
    signal_error,
)

from agents._lib.flow import MarketingCampaignFlow, CampaignState, bind_collapse_llm, _crew_text
from agents._lib.llm import init_llm
from agents._lib.logger import make_logger
from agents._lib.persistence import (
    get_persistence, has_pending, load_pending_from_store, sync_pending_to_store,
)

# Crew imports for branch actions
from agents._crews.brand_creative_crew.brand_creative_crew import BrandCreativeCrew
from agents._crews.channel_planning_crew.channel_planning_crew import ChannelPlanningCrew
from agents._crews.integration_crew.integration_crew import IntegrationCrew
from agents._crews.content_crew.content_crew import ContentCrew

log = make_logger("Handler")


# ─── Streaming resume wrapper ────────────────────────────────────────

async def _stream_resume(flow, feedback: str) -> FlowStreamingOutput:
    """Wrap resume_async in streaming infrastructure.

    CrewAI's resume_async() doesn't return a streaming iterator, but the
    underlying Crew still emits LLMStreamChunkEvent to the event bus.
    This helper subscribes to those events — same pattern as kickoff_async.
    """
    result_holder: list = []
    task_info = {"index": 0, "name": "", "id": "", "agent_role": "", "agent_id": ""}
    state = create_streaming_state(task_info, result_holder, use_async=True)
    output_holder: list = []

    async def run():
        try:
            result = await flow.resume_async(feedback)
            result_holder.append(result)
        except Exception as e:
            if isinstance(e, HumanFeedbackPending):
                result_holder.append(e)
            else:
                signal_error(state, e, is_async=True)
        finally:
            signal_end(state, is_async=True)

    streaming = FlowStreamingOutput(
        async_iterator=create_async_chunk_generator(state, run, output_holder)
    )
    register_cleanup(streaming, state)
    output_holder.append(streaming)
    return streaming


# ─── Branch action detection ─────────────────────────────────────────

BRANCH_ACTIONS = {
    "rollback_to_planning", "rollback_to_integration", "rollback_to_content",
}


def _parse_action(message: str) -> tuple[str, str]:
    """Parse ACTION:xxx|feedback=yyy from message. Returns (action, feedback)."""
    if not message.startswith("ACTION:"):
        return "", message
    parts = message[7:].split("|", 1)
    action = parts[0].strip()
    feedback = ""
    if len(parts) > 1 and "=" in parts[1]:
        feedback = parts[1].split("=", 1)[1].strip()
    return action, feedback


def _is_branch_action(message: str) -> bool:
    """Check if this message is a branch action that should bypass Flow."""
    if message.startswith("ACTION:"):
        action, _ = _parse_action(message)
        return action in BRANCH_ACTIONS
    return False


# ─── Main handler ────────────────────────────────────────────────────

async def handler(context):
    """POST /stream — conversation turn (streaming)."""
    conversation_id = getattr(context, "conversation_id", None)
    body = context.request.body or {}

    # Parse user input — support both text message and structured phase_action
    user_message = (
        body.get("message")
        or body.get("user_message")
        or body.get("campaign_brief")
        or ""
    ).strip()
    campaign_name = body.get("campaign_name", "")
    locale = body.get("locale", "zh")
    action = body.get("action", "send")
    phase_action = body.get("phase_action")  # e.g., {"type": "confirm"}
    card_action = body.get("card_action")    # e.g., {"target": "brand", "type": "redo", "feedback": "..."}
    iteration_feedback = body.get("iteration_feedback", "")  # e.g., "预算改为200万"

    # iteration_feedback → treat as revise_document action
    if iteration_feedback:
        user_message = f"ACTION:revise_document|feedback={iteration_feedback}"

    # Convert phase_action to feedback string
    if phase_action and isinstance(phase_action, dict):
        pa_type = phase_action.get("type", "")
        pa_feedback = phase_action.get("feedback", "")
        if pa_type == "confirm":
            user_message = user_message or "ACTION:confirm"
        elif pa_type == "keep_old":
            # keep_old is a frontend-only action — return minimal SSE acknowledgment
            async def _keep_old_gen2():
                yield context.utils.sse({"type": "done", "status": "completed"})
            return context.utils.stream_sse(_keep_old_gen2())
        elif pa_type in BRANCH_ACTIONS:
            user_message = f"ACTION:{pa_type}" + (f"|feedback={pa_feedback}" if pa_feedback else "")
        elif pa_type and not user_message:
            user_message = f"ACTION:{pa_type}"

    # Convert card_action to feedback string
    if card_action and isinstance(card_action, dict):
        ca_target = card_action.get("target", "")  # "brand" | "channel"
        ca_type = card_action.get("type", "")      # "confirm" | "redo" | "keep_old"
        ca_feedback = card_action.get("feedback", "")

        if ca_type == "redo" and ca_target:
            user_message = f"ACTION:redo_{ca_target}" + (f"|feedback={ca_feedback}" if ca_feedback else "")
        elif ca_type == "confirm":
            user_message = user_message or "ACTION:confirm"
        elif ca_type == "keep_old":
            # keep_old is a frontend-only action — return minimal SSE acknowledgment
            async def _keep_old_gen():
                yield context.utils.sse({"type": "done", "status": "completed"})
            return context.utils.stream_sse(_keep_old_gen())

    # Handle skip_discovery (frontend "信息够了，开始策划" button)
    if body.get("skip_discovery"):
        user_message = user_message or "ACTION:confirm"

    # History action
    if action == "history":
        return await _handle_history(context, body)

    # Init LLM
    try:
        init_llm(context.env)
        bind_collapse_llm()
    except Exception as e:
        log(f"LLM init error: {e}")
        return {"status_code": 500, "body": {"error": str(e)}}

    store = context.store
    cid = conversation_id
    persistence = get_persistence()

    # Check if this is a resume (pending feedback exists)
    is_resume = has_pending(cid)
    if not is_resume:
        is_resume = await load_pending_from_store(cid, store)
    log(f"turn={'resume' if is_resume else 'kickoff'} cid={cid}")

    # ── SSE generator ──
    async def gen():
        pending_writes: list[asyncio.Task] = []

        def fire_save(role: str, content: str, metadata: dict | None = None):
            async def _save():
                try:
                    await store.append_message(
                        conversation_id=cid, role=role,
                        content=content, metadata=metadata or {},
                    )
                except Exception as e:
                    log(f"store write failed: {e}")
            pending_writes.append(asyncio.create_task(_save()))

        try:
            yield context.utils.sse({"type": "flow_start"})

            # Save user message
            if user_message:
                fire_save("user", user_message)

            # ── Branch action: bypass Flow ──
            if is_resume and _is_branch_action(user_message):
                async for event in _handle_branch_action(
                    user_message, cid, persistence, locale, context
                ):
                    yield context.utils.sse(event)
                await sync_pending_to_store(cid, store)
                if pending_writes:
                    await asyncio.gather(*pending_writes, return_exceptions=True)
                yield context.utils.sse({"type": "done", "status": "completed"})
                return

            # ── Main Flow: kickoff or resume ──
            if is_resume:
                # Append user reply to qa_history for discovery context
                pending = persistence.load_pending_feedback(cid)
                flow = MarketingCampaignFlow.from_pending(cid, persistence=persistence)

                # Inject user answer into qa_history if still in discovery
                if flow.state.current_phase == "discovery" and user_message:
                    flow.state.qa_history = (
                        flow.state.qa_history + f"\nUser: {user_message}"
                    ).strip()

                streaming = await _stream_resume(flow, user_message)
            else:
                # First turn: kickoff
                if not user_message:
                    yield context.utils.sse({"type": "error", "message": "Missing message"})
                    yield context.utils.sse({"type": "done", "status": "error"})
                    return

                flow = MarketingCampaignFlow(persistence=persistence)
                # Set campaign_brief from first message
                streaming = await flow.kickoff_async(inputs={
                    "id": cid,
                    "campaign_name": campaign_name,
                    "campaign_brief": user_message,
                    "locale": locale,
                })

            # ── Streaming loop ──
            # Record phase BEFORE streaming to detect transitions
            phase_before = flow.state.current_phase
            prev_agent = ""
            current_content = ""
            agent_contents: list[tuple[str, str]] = []  # (agent_role, content)
            in_parallel = False  # Track if we're in parallel planning mode
            planning_emitted = False  # Track if we already sent phase_change for planning

            yield context.utils.sse({"type": "phase_change", "phase": phase_before, "progress": _phase_progress(phase_before)})

            # For first kickoff in discovery, emit initial agent_start
            if phase_before == "discovery":
                yield context.utils.sse({"type": "agent_start", "agent": "market_analyst"})

            async for chunk in streaming:
                raw_agent = (chunk.agent_role or "").strip()
                agent_role = _normalize_agent(raw_agent)  # Convert to frontend agent_id

                # Detect agent switch
                if agent_role and agent_role != prev_agent:
                    if prev_agent and current_content:
                        fire_save("assistant", current_content, {"agent": prev_agent})
                        agent_contents.append((prev_agent, current_content))
                        current_content = ""
                    if prev_agent:
                        lane = _agent_to_lane(prev_agent)
                        yield context.utils.sse({"type": "agent_end", "agent": prev_agent, **({"lane": lane} if lane else {})})

                    # Detect phase transitions based on agent role
                    lane = _agent_to_lane(agent_role)

                    if lane in ("brand", "channel") and not planning_emitted:
                        # Entering planning phase — emit phase_change + parallel_start
                        planning_emitted = True
                        yield context.utils.sse({"type": "phase_change", "phase": "planning", "progress": _phase_progress("planning")})
                        yield context.utils.sse({"type": "parallel_start", "lanes": ["brand", "channel"]})
                        in_parallel = True

                    if lane == "channel" and _agent_to_lane(prev_agent) == "brand":
                        # Switching from brand to channel within parallel
                        yield context.utils.sse({"type": "card_update", "card": "brand_creative", "data": {"raw": agent_contents[-1][1] if agent_contents else ""}})

                    if not lane and in_parallel:
                        # Exiting parallel mode
                        in_parallel = False
                        yield context.utils.sse({"type": "parallel_end"})

                    if agent_role == "chief_strategist" and phase_before not in ("discovery", "finalize"):
                        yield context.utils.sse({"type": "phase_change", "phase": "integration", "progress": _phase_progress("integration")})
                    elif agent_role == "copywriter":
                        yield context.utils.sse({"type": "phase_change", "phase": "content", "progress": _phase_progress("content")})

                    yield context.utils.sse({"type": "agent_start", "agent": agent_role, **({"lane": lane} if lane else {})})
                    prev_agent = agent_role

                if chunk.chunk_type == StreamChunkType.TEXT:
                    text = chunk.content or ""
                    current_content += text
                    yield context.utils.sse({
                        "type": "chunk",
                        "agent": agent_role or prev_agent,
                        "content": text,
                    })

            # Final agent content
            if prev_agent and current_content:
                fire_save("assistant", current_content, {"agent": prev_agent})
                agent_contents.append((prev_agent, current_content))
            if prev_agent:
                lane = _agent_to_lane(prev_agent)
                yield context.utils.sse({"type": "agent_end", "agent": prev_agent, **({"lane": lane} if lane else {})})

            if in_parallel:
                yield context.utils.sse({"type": "parallel_end"})

            # ── Post-streaming: emit structured events ──
            phase = flow.state.current_phase
            log(f"Post-streaming: phase_before={phase_before} phase_after={phase} "
                f"audience={bool(flow.state.audience_profile)} "
                f"brand={bool(flow.state.brand_creatives)} "
                f"channel={bool(flow.state.channel_plan)} "
                f"strategy={bool(flow.state.integrated_strategy)} "
                f"copy={bool(flow.state.copywriting)}")

            # Discovery phase: emit the question as a `message` event (frontend renders this as chat bubble)
            if phase_before == "discovery" and agent_contents:
                first_agent, first_content = agent_contents[0]
                # Strip [SUGGESTIONS] section for display
                display = first_content.split("[SUGGESTIONS]")[0].strip() if "[SUGGESTIONS]" in first_content else first_content
                # Also strip [READY] marker
                display = display.replace("[READY]", "").strip()
                if display:
                    yield context.utils.sse({
                        "type": "message",
                        "from": "market_analyst",
                        "content": display,
                        "phase": "discovery",
                    })

            # If phase changed during streaming (e.g., discovery → planning), emit final phase
            if phase != phase_before:
                yield context.utils.sse({"type": "phase_change", "phase": phase, "progress": _phase_progress(phase)})

            # Emit card updates based on what state has
            if flow.state.audience_profile:
                yield context.utils.sse({"type": "card_update", "card": "audience", "data": {"content": flow.state.audience_profile}})
            if flow.state.brand_creatives:
                yield context.utils.sse({"type": "card_update", "card": "brand_creative", "data": {"raw": flow.state.brand_creatives}})
            if flow.state.channel_plan:
                yield context.utils.sse({"type": "card_update", "card": "channel_plan", "data": {"raw": flow.state.channel_plan}})
            if flow.state.integrated_strategy:
                yield context.utils.sse({"type": "card_update", "card": "strategy", "data": {"raw": flow.state.integrated_strategy}})
            if flow.state.copywriting:
                yield context.utils.sse({"type": "card_update", "card": "copywriting", "data": {"raw": flow.state.copywriting}})

            # Emit suggestions (discovery phase only)
            if phase == "discovery" and agent_contents:
                _, last_content = agent_contents[-1]
                suggestions = _extract_suggestions(last_content)
                if suggestions:
                    yield context.utils.sse({"type": "suggestions", "suggestions": suggestions})

            # Emit actions
            yield context.utils.sse({"type": "actions", "actions": _get_actions(phase, flow.state, locale)})

            # Sync to store
            await sync_pending_to_store(cid, store)
            if pending_writes:
                await asyncio.gather(*pending_writes, return_exceptions=True)
            yield context.utils.sse({"type": "done", "status": "completed"})

        except Exception as e:
            log(f"stream error: {e}")
            yield context.utils.sse({"type": "error", "message": str(e)})
            await sync_pending_to_store(cid, store)
            if pending_writes:
                await asyncio.gather(*pending_writes, return_exceptions=True)
            yield context.utils.sse({"type": "done", "status": "error"})

    return context.utils.stream_sse(gen())


# ─── Branch action handler ───────────────────────────────────────────

async def _handle_branch_action(message, cid, persistence, locale, context):
    """Handle redo/rollback actions — direct crew calls, bypass Flow."""
    action, feedback = _parse_action(message)
    locale_instruction = "Chinese (中文)" if locale == "zh" else "English"

    # Load current state from persistence
    pending = persistence.load_pending_feedback(cid)
    if not pending:
        yield {"type": "error", "message": "No pending state found"}
        return
    state_data, _ = pending
    state = CampaignState(**state_data)

    inputs = {
        "campaign_name": state.campaign_name,
        "campaign_brief": state.campaign_brief + (f"\n\nFeedback: {feedback}" if feedback else ""),
        "audience_profile": state.audience_profile,
        "market_insights": state.market_insights,
        "locale_instruction": locale_instruction,
    }

    if action == "redo_brand":
        yield {"type": "phase_change", "phase": "planning"}
        yield {"type": "agent_start", "agent": "Brand & Creative Director"}
        result = BrandCreativeCrew().crew().kickoff(inputs=inputs)
        state.brand_creatives = _crew_text(result)
        yield {"type": "agent_end", "agent": "Brand & Creative Director"}
        yield {"type": "card_update", "card": "brand_creative", "data": {"raw": state.brand_creatives}}

    elif action == "redo_channel":
        yield {"type": "phase_change", "phase": "planning"}
        yield {"type": "agent_start", "agent": "Channel & Media Planner"}
        result = ChannelPlanningCrew().crew().kickoff(inputs=inputs)
        state.channel_plan = _crew_text(result)
        yield {"type": "agent_end", "agent": "Channel & Media Planner"}
        yield {"type": "card_update", "card": "channel_plan", "data": {"raw": state.channel_plan}}

    elif action == "rollback_to_planning":
        state.current_phase = "planning"
        yield {"type": "phase_change", "phase": "planning"}
        yield {"type": "card_update", "card": "brand_creative", "data": {"raw": state.brand_creatives}}
        yield {"type": "card_update", "card": "channel_plan", "data": {"raw": state.channel_plan}}

    elif action == "rollback_to_integration":
        state.current_phase = "integration"
        yield {"type": "phase_change", "phase": "integration"}
        yield {"type": "card_update", "card": "strategy", "data": {"raw": state.integrated_strategy}}

    elif action == "rollback_to_content":
        state.current_phase = "content"
        yield {"type": "phase_change", "phase": "content"}
        yield {"type": "card_update", "card": "copywriting", "data": {"raw": state.copywriting}}

    # Save updated state back to persistence (keeps Flow pending context intact)
    from crewai.flow.async_feedback.types import PendingFeedbackContext
    pending_ctx = pending[1] if pending else PendingFeedbackContext(
        method_name="planning_step", message="(user reviews)"
    )
    persistence.save_pending_feedback(cid, pending_ctx, state.model_dump())

    yield {"type": "actions", "actions": _get_actions(state.current_phase, state, locale)}


# ─── History handler ─────────────────────────────────────────────────

async def _handle_history(context, body):
    """Return conversation history from context.store."""
    conversation_id = getattr(context, "conversation_id", "") or body.get("conversation_id", "")
    if not conversation_id:
        return {"conversation_id": "", "chat_history": [], "current_phase": "start"}

    try:
        messages = await context.store.get_messages(
            conversation_id=conversation_id, limit=100, order="asc"
        )
        chat_history = []
        for m in messages:
            meta_data = m.metadata or {}
            agent = meta_data.get("agent", m.role)
            chat_history.append({"role": agent, "content": m.content})

        # Try to determine phase from persistence
        persistence = get_persistence()
        pending = persistence.load_pending_feedback(conversation_id)
        if pending:
            state_data = pending[0]
            current_phase = state_data.get("current_phase", "discovery")
        else:
            current_phase = "discovery" if chat_history else "start"

        return {
            "conversation_id": conversation_id,
            "chat_history": chat_history,
            "current_phase": current_phase,
        }
    except Exception:
        return {"conversation_id": conversation_id, "chat_history": [], "current_phase": "start"}


# ─── Utility functions ───────────────────────────────────────────────

def _phase_progress(phase: str) -> int:
    return {
        "discovery": 10,
        "planning": 30,
        "integration": 55,
        "content": 75,
        "finalize": 95,
    }.get(phase, 0)


def _extract_suggestions(text: str) -> list[str]:
    """Extract [SUGGESTIONS] section from discovery output."""
    if "[SUGGESTIONS]" not in text:
        return []
    parts = text.split("[SUGGESTIONS]", 1)
    if len(parts) < 2:
        return []
    suggestions = []
    for line in parts[1].strip().split("\n"):
        line = line.strip()
        if line.startswith("- "):
            suggestions.append(line[2:].strip())
        elif line:
            suggestions.append(line)
    return suggestions[:3]


def _get_actions(phase: str, state, locale: str) -> list[dict]:
    """Generate available actions for current phase."""
    zh = locale == "zh"
    actions = []

    if phase == "discovery":
        pass  # Just reply to continue

    elif phase == "planning":
        actions = [
            {"id": "ACTION:confirm", "label": "确认方案，继续" if zh else "Confirm & Continue"},
            {"id": "ACTION:redo_brand", "label": "重新生成品牌创意" if zh else "Redo Brand Creative"},
            {"id": "ACTION:redo_channel", "label": "重新生成渠道策略" if zh else "Redo Channel Strategy"},
        ]

    elif phase == "integration":
        actions = [
            {"id": "ACTION:confirm", "label": "确认，继续" if zh else "Confirm & Continue"},
            {"id": "ACTION:rollback_to_planning", "label": "返回方案策划" if zh else "Back to Planning"},
        ]

    elif phase == "content":
        actions = [
            {"id": "ACTION:confirm", "label": "确认，完成" if zh else "Confirm & Finish"},
            {"id": "ACTION:rollback_to_integration", "label": "返回策略整合" if zh else "Back to Integration"},
        ]

    elif phase == "finalize":
        actions = [
            {"id": "ACTION:generate_document", "label": "生成完整方案" if zh else "Generate Full Plan"},
        ]
        if state.integrated_strategy and len(state.integrated_strategy) > 500:
            actions.append(
                {"id": "ACTION:revise_document", "label": "修改方案" if zh else "Revise Plan"}
            )

    return actions


def _agent_to_lane(agent_role: str) -> str:
    """Map agent role to parallel lane name (for planning phase UI)."""
    agent_id = _normalize_agent(agent_role)
    if agent_id == "brand_creative_director":
        return "brand"
    if agent_id == "channel_planner":
        return "channel"
    return ""


def _normalize_agent(agent_role: str) -> str:
    """Map CrewAI agent role string to frontend agent_id.

    Frontend expects: market_analyst, brand_creative_director, channel_planner,
    chief_strategist, copywriter.
    CrewAI sends the 'role' field from agents.yaml which is a human-readable string.
    """
    if not agent_role:
        return ""
    lower = agent_role.lower().strip()
    if "market" in lower and ("analyst" in lower or "research" in lower):
        return "market_analyst"
    if "brand" in lower or "creative director" in lower:
        return "brand_creative_director"
    if "channel" in lower or "media" in lower:
        return "channel_planner"
    if "strategist" in lower or "chief" in lower:
        return "chief_strategist"
    if "copywriter" in lower or "copy" in lower:
        return "copywriter"
    return agent_role
