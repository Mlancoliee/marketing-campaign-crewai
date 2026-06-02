"""
POST /stream - 营销活动策划 Agent 主入口

处理所有对话轮次：
- action: "history" → 返回存储的历史
- action: "send" → kickoff 或 resume Flow
"""
import uuid
import asyncio
import traceback

from agents._lib.state import CampaignState
from agents._lib.flow import MarketingCampaignFlow
from agents._lib.feedback_provider import HumanFeedbackPending
from agents._lib.persistence import save_flow_state, load_flow_state, delete_flow_state
from agents._lib.logger import make_logger

log = make_logger("Handler")


async def _persist_to_store(context, conversation_id: str, state):
    """将当前状态持久化到 context.store（Blob 存储，跨重启可恢复）"""
    if not hasattr(context, "store"):
        return
    try:
        # 构建 cards 快照
        cards = {
            "audience": {"content": state.audience_profile} if state.audience_profile else None,
            "brand_creative": {"creatives": state.brand_creatives} if state.brand_creatives else None,
            "channel_plan": {"plan": state.channel_plan} if state.channel_plan else None,
            "strategy": {"content": state.integrated_strategy} if state.integrated_strategy else None,
            "copywriting": state.copywriting if state.copywriting else None,
        }
        # 先确保对话存在（append 一条 system 消息会自动创建对话）
        try:
            await context.store.get_conversation(conversation_id=conversation_id)
        except Exception:
            # 对话不存在，创建它
            await context.store.append_message(
                conversation_id=conversation_id,
                role="system",
                content=f"Campaign: {state.campaign_name}",
                metadata={"type": "init"},
            )
        # 更新对话元信息（存储 phase + cards）
        await context.store.update_conversation(
            conversation_id=conversation_id,
            metadata={
                "current_phase": state.current_phase,
                "cards": cards,
                "campaign_name": state.campaign_name,
            },
        )
    except Exception as e:
        log(f"Persist to store failed: {e}")


def _normalize_role(role: str) -> str:
    """将自定义 agent role 映射为 context.store 接受的标准 role"""
    if role == "user":
        return "user"
    return "assistant"  # 所有 agent 角色统一为 assistant


async def _save_messages_to_store(context, conversation_id: str, state):
    """将 chat_history 中的新消息保存到 context.store"""
    if not hasattr(context, "store"):
        return
    try:
        for msg in state.chat_history:
            await context.store.append_message(
                conversation_id=conversation_id,
                role=_normalize_role(msg.get("role", "assistant")),
                content=msg.get("content", ""),
                metadata={"phase": msg.get("phase", ""), "agent": msg.get("role", "")},
            )
        # 保存后清空 chat_history 避免重复写入
        state.chat_history = []
    except Exception as e:
        log(f"Save messages failed: {e}")


async def handler(context):
    """Pages Agent handler 入口"""
    body = context.request.body
    action = body.get("action", "send")

    if action == "history":
        return await _handle_history(context, body)
    else:
        return await _handle_send(context, body)


def _sse(context, data):
    """使用 context.utils.sse 构造一帧 SSE"""
    return context.utils.sse(data)


async def _handle_history(context, body):
    """返回对话历史 - 从 context.store 读取"""
    conversation_id = body.get("conversation_id", "")

    # 从平台 store 读取
    if hasattr(context, "store") and conversation_id:
        try:
            # 读取对话元信息（存储了 phase 和 cards）
            meta = await context.store.get_conversation(conversation_id=conversation_id)
            if meta and meta.metadata:
                # 读取消息历史
                messages = await context.store.get_messages(conversation_id=conversation_id, limit=100, order="asc")
                chat_history = []
                for m in messages:
                    meta_data = m.metadata or {}
                    if meta_data.get("type") == "init":
                        continue
                    role = meta_data.get("agent", m.role)
                    chat_history.append({"role": role, "content": m.content, "phase": meta_data.get("phase", "")})

                cards = meta.metadata.get("cards", {})
                current_phase = meta.metadata.get("current_phase", "start")

                # 重建 state 写回内存，确保后续操作能 resume
                state_dict = {
                    "campaign_name": meta.metadata.get("campaign_name", ""),
                    "campaign_brief": "",
                    "locale": "zh",
                    "current_phase": current_phase,
                    "chat_history": chat_history,
                    "qa_history": [],
                    "discovery_rounds": 0,
                    "audience_profile": (cards.get("audience") or {}).get("content", ""),
                    "market_insights": (cards.get("audience") or {}).get("content", ""),
                    "brand_creatives": (cards.get("brand_creative") or {}).get("creatives", []),
                    "channel_plan": (cards.get("channel_plan") or {}).get("plan", {}),
                    "selected_creative_index": 0,
                    "brand_confirmed": current_phase not in ("discovery", "planning"),
                    "channel_confirmed": current_phase not in ("discovery", "planning"),
                    "integrated_strategy": (cards.get("strategy") or {}).get("content", ""),
                    "copywriting": cards.get("copywriting") or {},
                    "latest_feedback": "",
                    "iteration_target": "",
                    "iteration_count": 0,
                    "finished": False,
                }
                save_flow_state(conversation_id, state_dict, {"phase": current_phase})

                return {
                    "conversation_id": conversation_id,
                    "chat_history": chat_history,
                    "current_phase": current_phase,
                    "cards": cards,
                }
        except Exception:
            pass

    # 回退到内存 state
    stored = load_flow_state(conversation_id)
    if stored and stored.get("state"):
        state = stored["state"]
        return {
            "conversation_id": conversation_id,
            "chat_history": state.get("chat_history", []),
            "current_phase": state.get("current_phase", "discovery"),
            "cards": {
                "audience": {"content": state.get("audience_profile", "")} if state.get("audience_profile") else None,
                "brand_creative": {"creatives": state.get("brand_creatives", [])} if state.get("brand_creatives") else None,
                "channel_plan": {"plan": state.get("channel_plan", {})} if state.get("channel_plan") else None,
                "strategy": {"content": state.get("integrated_strategy", "")} if state.get("integrated_strategy") else None,
                "copywriting": {"content": state.get("copywriting", {})} if state.get("copywriting") else None,
            },
        }
    return {"conversation_id": conversation_id, "chat_history": [], "current_phase": "start"}


async def _handle_send(context, body):
    """处理用户发送：kickoff 或 resume"""
    conversation_id = body.get("conversation_id", str(uuid.uuid4()))
    locale = body.get("locale", "zh")

    stored = load_flow_state(conversation_id)

    # 如果内存没有但 context.store 有，自动恢复（处理多实例/重启场景）
    if stored is None and hasattr(context, "store") and body.get("conversation_id"):
        try:
            meta = await context.store.get_conversation(conversation_id=conversation_id)
            if meta and meta.metadata and meta.metadata.get("current_phase", "start") != "start":
                cards = meta.metadata.get("cards", {})
                current_phase = meta.metadata.get("current_phase", "start")
                state_dict = {
                    "campaign_name": meta.metadata.get("campaign_name", ""),
                    "campaign_brief": "",
                    "locale": locale,
                    "current_phase": current_phase,
                    "chat_history": [],
                    "qa_history": [],
                    "discovery_rounds": 0,
                    "audience_profile": (cards.get("audience") or {}).get("content", ""),
                    "market_insights": (cards.get("audience") or {}).get("content", ""),
                    "brand_creatives": (cards.get("brand_creative") or {}).get("creatives", []),
                    "channel_plan": (cards.get("channel_plan") or {}).get("plan", {}),
                    "selected_creative_index": 0,
                    "brand_confirmed": current_phase not in ("discovery", "planning"),
                    "channel_confirmed": current_phase not in ("discovery", "planning"),
                    "integrated_strategy": (cards.get("strategy") or {}).get("content", ""),
                    "copywriting": cards.get("copywriting") or {},
                    "latest_feedback": "",
                    "iteration_target": "",
                    "iteration_count": 0,
                    "finished": False,
                }
                save_flow_state(conversation_id, state_dict, {"phase": current_phase})
                stored = load_flow_state(conversation_id)
        except Exception:
            pass

    # ── SSE 流式响应 ──
    async def generate_sse():
        try:
            # 首先发送 conversation_id
            yield _sse(context, {"type": "conversation_id", "data": {"id": conversation_id}})

            if stored is None:
                # 只有首次请求（带 campaign_name/campaign_brief）才 kickoff
                # 如果前端传了 conversation_id 但后端找不到 state，说明会话过期
                if body.get("conversation_id") and not body.get("campaign_name") and not body.get("campaign_brief"):
                    yield _sse(context, {"type": "error", "message": "会话已过期，请新建" if locale == "zh" else "Session expired, please start new"})
                else:
                    async for event in _stream_kickoff(body, conversation_id, locale, context):
                        yield _sse(context, event)
            else:
                # 后续请求 - resume
                async for event in _stream_resume(body, stored, conversation_id, context):
                    yield _sse(context, event)
        except Exception as e:
            log(f"Error: {traceback.format_exc()}")
            yield _sse(context, {"type": "error", "message": str(e)})

        yield _sse(context, {"type": "done"})
        yield _sse(context, "[DONE]")

    return context.utils.stream_sse(generate_sse())


async def _stream_kickoff(body, conversation_id, locale, context):
    """首次启动 Flow"""
    campaign_name = body.get("campaign_name", "")
    campaign_brief = body.get("message", body.get("campaign_brief", ""))

    yield {"type": "phase_change", "phase": "discovery", "progress": 10}
    yield {"type": "status", "message": "市场分析师正在准备提问..." if locale == "zh" else "Market analyst preparing questions...", "from": "chief_strategist"}
    yield {"type": "agent_start", "agent": "market_analyst"}

    flow = MarketingCampaignFlow()
    flow.state.campaign_name = campaign_name
    flow.state.campaign_brief = campaign_brief
    flow.state.locale = locale

    try:
        await asyncio.wait_for(flow.kickoff_async(), timeout=300)
    except asyncio.TimeoutError:
        yield {"type": "error", "message": "LLM 响应超时，请重试"}
        yield {"type": "agent_end", "agent": "market_analyst"}
        return
    except HumanFeedbackPending as e:
        # Flow 暂停 - 保存状态（内存）
        save_flow_state(conversation_id, flow.state.model_dump(), e.context)

        # 输出最新的 agent 产出
        if flow.state.chat_history:
            last_msg = flow.state.chat_history[-1]
            content = last_msg.get("content", "")
            if "[SUGGESTIONS]" in content:
                content = content.split("[SUGGESTIONS]")[0].strip()
            yield {"type": "message", "from": last_msg.get("role", "market_analyst"), "content": content, "phase": "discovery"}

        yield {"type": "agent_end", "agent": "market_analyst"}

        # 输出卡片更新
        if flow.state.audience_profile:
            yield {"type": "card_update", "card": "audience", "data": {"content": flow.state.audience_profile}}

        # 输出推荐回答
        suggestions = _generate_suggestions(flow.state, locale)
        if suggestions:
            yield {"type": "suggestions", "suggestions": suggestions}

        # 输出可用操作
        phase = e.context.get("phase", "discovery") if e.context else "discovery"
        yield {"type": "actions", "actions": _get_actions_for_phase(phase, flow.state, locale)}

        # 持久化到 context.store（所有输出完成后）
        await _persist_to_store(context, conversation_id, flow.state)
        await _save_messages_to_store(context, conversation_id, flow.state)

    except Exception as e:
        yield {"type": "error", "message": str(e)}


async def _stream_resume(body, stored, conversation_id, context):
    """恢复暂停的 Flow - 直接调用 Crew 而非 Flow methods"""
    state_dict = stored["state"]
    phase = state_dict.get("current_phase", "discovery")
    locale = state_dict.get("locale", "zh")

    # 恢复 state
    state = CampaignState(**state_dict)

    # 根据请求类型确定下一步
    next_route = _determine_next_route_from_state(body, state, phase)

    if next_route == "done":
        delete_flow_state(conversation_id)
        yield {"type": "phase_change", "phase": "done", "progress": 100}
        yield {"type": "status", "message": "营销方案已完成！" if locale == "zh" else "Campaign plan complete!", "from": "chief_strategist"}
        return

    if next_route == "wait":
        save_flow_state(conversation_id, state.model_dump(), {"phase": phase})
        yield {"type": "status", "message": "等待确认另一个方案..." if locale == "zh" else "Waiting for other confirmation...", "from": "chief_strategist"}
        yield {"type": "actions", "actions": _get_actions_for_phase(phase, state, locale)}
        return

    # Rollback：只切换阶段，恢复已有数据，不清除下游（redo 才清除）
    if next_route == "rollback_to_planning":
        state.current_phase = "planning"
        state.brand_confirmed = False
        state.channel_confirmed = False
        save_flow_state(conversation_id, state.model_dump(), {"phase": "planning"})
        yield {"type": "phase_change", "phase": "planning", "progress": _phase_to_progress("planning")}
        yield {"type": "status", "message": "已返回方案策划阶段" if locale == "zh" else "Back to planning", "from": "chief_strategist"}
        yield {"type": "card_update", "card": "brand_creative", "data": {"creatives": state.brand_creatives}}
        yield {"type": "card_update", "card": "channel_plan", "data": {"plan": state.channel_plan}}
        yield {"type": "actions", "actions": _get_actions_for_phase("planning", state, locale)}
        return

    if next_route == "rollback_to_integration":
        state.current_phase = "integration"
        save_flow_state(conversation_id, state.model_dump(), {"phase": "integration"})
        yield {"type": "phase_change", "phase": "integration", "progress": _phase_to_progress("integration")}
        yield {"type": "status", "message": "已返回策略整合阶段" if locale == "zh" else "Back to integration", "from": "chief_strategist"}
        yield {"type": "card_update", "card": "strategy", "data": {"content": state.integrated_strategy}}
        yield {"type": "actions", "actions": _get_actions_for_phase("integration", state, locale)}
        return

    # Restore：前进到已有数据的阶段（回退后再确认时不重新生成）
    if next_route == "restore_integration":
        state.current_phase = "integration"
        save_flow_state(conversation_id, state.model_dump(), {"phase": "integration"})
        yield {"type": "phase_change", "phase": "integration", "progress": _phase_to_progress("integration")}
        yield {"type": "status", "message": "策略整合方案已就绪" if locale == "zh" else "Strategy ready", "from": "chief_strategist"}
        yield {"type": "card_update", "card": "strategy", "data": {"content": state.integrated_strategy}}
        yield {"type": "actions", "actions": _get_actions_for_phase("integration", state, locale)}
        return

    if next_route == "restore_content":
        state.current_phase = "content"
        save_flow_state(conversation_id, state.model_dump(), {"phase": "content"})
        yield {"type": "phase_change", "phase": "content", "progress": _phase_to_progress("content")}
        yield {"type": "status", "message": "营销文案已就绪" if locale == "zh" else "Copy ready", "from": "chief_strategist"}
        yield {"type": "card_update", "card": "copywriting", "data": {"content": state.copywriting}}
        yield {"type": "actions", "actions": _get_actions_for_phase("content", state, locale)}
        return

    # Finalize：展示卡片总览（发送所有卡片数据确保前端状态完整）
    if next_route == "finalize":
        state.current_phase = "finalize"
        save_flow_state(conversation_id, state.model_dump(), {"phase": "finalize"})
        yield {"type": "phase_change", "phase": "finalize", "progress": _phase_to_progress("finalize")}
        yield {"type": "status", "message": "所有模块已完成，可以生成完整方案" if locale == "zh" else "All modules ready, generate full plan", "from": "chief_strategist"}
        # 发送所有卡片数据
        yield {"type": "card_update", "card": "audience", "data": {"content": state.audience_profile}}
        yield {"type": "card_update", "card": "brand_creative", "data": {"creatives": state.brand_creatives}}
        yield {"type": "card_update", "card": "channel_plan", "data": {"plan": state.channel_plan}}
        yield {"type": "card_update", "card": "strategy", "data": {"raw": state.integrated_strategy}}
        yield {"type": "card_update", "card": "copywriting", "data": state.copywriting if isinstance(state.copywriting, dict) else {"raw": str(state.copywriting)}}
        return

    # 生成完整方案文档（流式）
    if next_route == "generate_document" or next_route == "revise_document":
        state.current_phase = "finalize"
        yield {"type": "phase_change", "phase": "finalize", "progress": _phase_to_progress("finalize")}
        msg = ("策略总监正在修订方案..." if next_route == "revise_document" else "策略总监正在整合生成完整方案...") if locale == "zh" else ("Revising plan..." if next_route == "revise_document" else "Generating full plan...")
        yield {"type": "status", "message": msg, "from": "chief_strategist"}
        yield {"type": "agent_start", "agent": "chief_strategist"}
        try:
            async for event in _execute_crew_streaming(state, next_route):
                yield event
        except Exception as e:
            log(f"Document error: {traceback.format_exc()}")
            yield {"type": "error", "message": str(e)}
        yield {"type": "agent_end", "agent": "chief_strategist"}
        save_flow_state(conversation_id, state.model_dump(), {"phase": "finalize"})
        return

    # Rollback to content
    if next_route == "rollback_to_content":
        state.current_phase = "content"
        save_flow_state(conversation_id, state.model_dump(), {"phase": "content"})
        yield {"type": "phase_change", "phase": "content", "progress": _phase_to_progress("content")}
        yield {"type": "status", "message": "已返回内容产出阶段" if locale == "zh" else "Back to content", "from": "chief_strategist"}
        yield {"type": "card_update", "card": "copywriting", "data": {"raw": state.copywriting.get("raw", "") if isinstance(state.copywriting, dict) else str(state.copywriting)}}
        yield {"type": "actions", "actions": _get_actions_for_phase("content", state, locale)}
        return

    # 发送阶段变更
    new_phase = _route_to_phase(next_route)
    progress = _phase_to_progress(new_phase)
    yield {"type": "phase_change", "phase": new_phase, "progress": progress}

    # 发送状态提示
    status_msg = _get_status_message(next_route, locale)
    if status_msg:
        yield {"type": "status", "message": status_msg, "from": "chief_strategist"}

    # 发送 agent_start
    agent = _route_to_agent(next_route)
    if agent:
        yield {"type": "agent_start", "agent": agent, "lane": _route_to_lane(next_route)}

    # 执行 Crew（流式）
    if next_route == "planning":
        # 并行：先品牌流式，再渠道流式
        yield {"type": "parallel_start", "lanes": ["brand", "channel"]}
        try:
            async for event in _execute_crew_streaming(state, "planning"):
                yield event
            yield {"type": "agent_end", "agent": "brand_creative_director", "lane": "brand"}
            # 发送品牌卡片
            yield {"type": "card_update", "card": "brand_creative", "data": {"creatives": state.brand_creatives}}

            # 渠道
            yield {"type": "agent_start", "agent": "channel_planner", "lane": "channel"}
            async for event in _execute_crew_streaming(state, "planning_channel"):
                yield event
            yield {"type": "agent_end", "agent": "channel_planner", "lane": "channel"}
            yield {"type": "card_update", "card": "channel_plan", "data": {"plan": state.channel_plan}}
        except Exception as e:
            log(f"Planning crew error: {traceback.format_exc()}")
            yield {"type": "error", "message": str(e)}
            save_flow_state(conversation_id, state.model_dump(), {"phase": "planning"})
            return
        yield {"type": "parallel_end"}
    elif next_route == "delivery":
        # delivery 不执行 crew，直接输出所有卡片
        yield {"type": "card_update", "card": "audience", "data": {"content": state.audience_profile}}
        yield {"type": "card_update", "card": "brand_creative", "data": {"creatives": state.brand_creatives}}
        yield {"type": "card_update", "card": "channel_plan", "data": {"plan": state.channel_plan}}
        yield {"type": "card_update", "card": "strategy", "data": {"content": state.integrated_strategy}}
        yield {"type": "card_update", "card": "copywriting", "data": {"content": state.copywriting}}
    elif next_route == "discovery_resume":
        # discovery 不流式：执行 crew 后一次性发送结果
        try:
            crew, _ = _build_crew_for_route(state, "discovery_resume", "Chinese (中文)" if locale == "zh" else "English")
            if crew:
                result = await asyncio.wait_for(crew.kickoff_async(), timeout=300)
                result_text = str(result)
                _update_state_after_crew(state, "discovery_resume", result_text)
                # 输出问题（去掉 SUGGESTIONS）
                if state.current_phase != "planning":
                    display = result_text
                    if "[SUGGESTIONS]" in display:
                        display = display.split("[SUGGESTIONS]")[0].strip()
                    yield {"type": "message", "from": "market_analyst", "content": display, "phase": "discovery"}
                else:
                    # READY 了，输出受众画像卡片
                    yield {"type": "card_update", "card": "audience", "data": {"content": state.audience_profile}}
        except Exception as e:
            log(f"Discovery crew error: {traceback.format_exc()}")
            yield {"type": "error", "message": str(e)}
            if agent:
                yield {"type": "agent_end", "agent": agent, "lane": _route_to_lane(next_route)}
            return
    else:
        # 其他路由：流式执行
        # 先清空前端对应卡片（避免新 chunk 追加在旧内容后面）
        clear_card_map = {
            "integration": "strategy",
            "content": "copywriting",
            "redo_brand": "brand_creative",
            "redo_channel": "channel_plan",
        }
        clear_card = clear_card_map.get(next_route)
        if clear_card:
            yield {"type": "card_update", "card": clear_card, "data": {"raw": ""}}

        try:
            async for event in _execute_crew_streaming(state, next_route):
                yield event
        except Exception as e:
            log(f"Crew execution error: {traceback.format_exc()}")
            yield {"type": "error", "message": str(e)}
            if agent:
                yield {"type": "agent_end", "agent": agent, "lane": _route_to_lane(next_route)}
            return

        # 流式 chunk 已经将内容推送到前端 cards.raw，不需要再发 card_update

    # discovery_resume 且未进入 planning 时，附加推荐回答
    if next_route == "discovery_resume" and state.current_phase != "planning":
        suggestions = _generate_suggestions(state, locale)
        if suggestions:
            yield {"type": "suggestions", "suggestions": suggestions}

    if agent and next_route != "planning":
        yield {"type": "agent_end", "agent": agent, "lane": _route_to_lane(next_route)}

    # 如果 discovery_resume 中 Crew 判断 READY，state.current_phase 已被改为 planning
    # 需要自动继续执行 planning crew
    if state.current_phase == "planning" and next_route == "discovery_resume":
        yield {"type": "phase_change", "phase": "planning", "progress": _phase_to_progress("planning")}
        yield {"type": "status", "message": "信息收集完毕，开始策划..." if locale == "zh" else "Research complete, starting parallel planning...", "from": "chief_strategist"}
        yield {"type": "parallel_start", "lanes": ["brand", "channel"]}

        # 品牌创意流式
        yield {"type": "agent_start", "agent": "brand_creative_director", "lane": "brand"}
        try:
            async for event in _execute_crew_streaming(state, "planning"):
                yield event
        except Exception as e:
            log(f"Planning brand error: {traceback.format_exc()}")
            yield {"type": "error", "message": str(e)}
            save_flow_state(conversation_id, state.model_dump(), {"phase": "planning"})
            return
        yield {"type": "agent_end", "agent": "brand_creative_director", "lane": "brand"}
        yield {"type": "card_update", "card": "brand_creative", "data": {"creatives": state.brand_creatives}}

        # 渠道策略流式
        yield {"type": "agent_start", "agent": "channel_planner", "lane": "channel"}
        try:
            async for event in _execute_crew_streaming(state, "planning_channel"):
                yield event
        except Exception as e:
            log(f"Planning channel error: {traceback.format_exc()}")
            yield {"type": "error", "message": str(e)}
            save_flow_state(conversation_id, state.model_dump(), {"phase": "planning"})
            return
        yield {"type": "agent_end", "agent": "channel_planner", "lane": "channel"}
        yield {"type": "card_update", "card": "channel_plan", "data": {"plan": state.channel_plan}}

        yield {"type": "parallel_end"}
        new_phase = "planning"
    else:
        state.current_phase = new_phase

    save_flow_state(conversation_id, state.model_dump(), {"phase": state.current_phase})
    await _persist_to_store(context, conversation_id, state)

    # 输出操作按钮
    yield {"type": "actions", "actions": _get_actions_for_phase(new_phase, state, locale)}


def _determine_next_route_from_state(body, state, current_phase):
    """根据请求体确定下一步路由（直接操作 state）"""
    # 用户完成
    if body.get("finish"):
        return "done"

    # Discovery 阶段 - 用户回答或跳过
    if current_phase == "discovery":
        if body.get("skip_discovery"):
            state.audience_profile = "Based on brief: " + state.campaign_brief
            state.market_insights = state.audience_profile
            return "planning"
        message = body.get("message", "")
        if message:
            state.qa_history.append({"question": "", "answer": message})
            state.chat_history.append({"role": "user", "content": message, "phase": "discovery"})
        return "discovery_resume"

    # Planning 阶段 - 卡片操作
    card_action = body.get("card_action")
    if card_action:
        target = card_action.get("target", "")
        action_type = card_action.get("type", "")
        feedback = card_action.get("feedback", "")

        if action_type == "redo":
            state.latest_feedback = feedback
            # redo 时清除下游数据
            state.integrated_strategy = ""
            state.copywriting = {}
            return f"redo_{target}"
        elif action_type == "keep_old":
            # 恢复旧数据（前端传来 previous_data）
            previous_data = card_action.get("previous_data")
            if previous_data:
                if target == "brand":
                    state.brand_creatives = previous_data.get("creatives", state.brand_creatives)
                elif target == "channel":
                    state.channel_plan = previous_data.get("plan", state.channel_plan)
            return "wait"
        elif action_type == "confirm":
            if target == "brand":
                state.brand_confirmed = True
                state.selected_creative_index = card_action.get("selected_index", 0)
            elif target == "channel":
                state.channel_confirmed = True

            if state.brand_confirmed and state.channel_confirmed:
                # 如果策略已存在（回退后再确认），不重新生成
                if state.integrated_strategy:
                    return "restore_integration"
                return "integration"
            else:
                return "wait"

    # Phase action (Integration / Content)
    phase_action = body.get("phase_action")
    if phase_action:
        action_type = phase_action.get("type", "")
        feedback = phase_action.get("feedback", "")

        if action_type == "confirm":
            if current_phase == "integration":
                if state.copywriting:
                    return "restore_content"
                return "content"
            elif current_phase == "content":
                return "finalize"
            elif current_phase == "finalize":
                return "generate_document"
        elif action_type == "redo":
            state.latest_feedback = feedback
            if current_phase == "integration":
                state.copywriting = {}  # 清除下游
                return "integration"
            elif current_phase == "content":
                return "content"
        elif action_type == "rollback":
            if current_phase == "integration":
                state.brand_confirmed = False
                state.channel_confirmed = False
                return "rollback_to_planning"
            elif current_phase == "content":
                return "rollback_to_integration"
            elif current_phase == "finalize":
                return "rollback_to_content"
        elif action_type == "keep_old":
            # 恢复旧数据（feedback 中包含旧内容）
            if current_phase == "integration" and feedback:
                state.integrated_strategy = feedback
            elif current_phase == "content" and feedback:
                state.copywriting = {"raw": feedback}
            return "wait"

    # 方案修改
    iteration_feedback = body.get("iteration_feedback", "")
    if iteration_feedback:
        state.latest_feedback = iteration_feedback
        if current_phase == "finalize":
            # 方案调整阶段：直接修改完整文档
            return "revise_document"
        else:
            # 旧逻辑（卡片级迭代，目前不再使用）
            state.iteration_target = _classify_target(iteration_feedback)
            return "iteration"

    return "wait"


async def _execute_crew_streaming(state, route):
    """执行 Crew 并流式输出 token（通过 event bus 或回退到分块）"""
    from crewai.utilities.streaming import create_streaming_state, signal_end, _unregister_handler, _current_stream_ids
    from crewai.types.streaming import StreamChunkType

    locale_instruction = "Chinese (中文)" if state.locale == "zh" else "English"

    # 构建 crew
    crew, agent_role = _build_crew_for_route(state, route, locale_instruction)
    if crew is None:
        return

    # 设置流式状态
    task_info = {"index": 0, "name": route, "id": "", "agent_role": agent_role, "agent_id": ""}
    result_holder = []
    streaming_state = create_streaming_state(task_info, result_holder, use_async=True)
    stream_id = streaming_state.stream_id

    # 后台执行 crew（设置 stream_id context 让 task 继承，5 分钟超时）
    async def run_crew():
        try:
            result = await asyncio.wait_for(crew.kickoff_async(), timeout=300)
            result_holder.append(str(result))
        except asyncio.TimeoutError:
            result_holder.append(Exception("LLM 响应超时，请重试"))
        except Exception as e:
            result_holder.append(e)
        finally:
            signal_end(streaming_state, is_async=True)

    # 在创建 task 前设置 context（task 会继承当前 context）
    token = _current_stream_ids.set((*_current_stream_ids.get(), stream_id))
    task = asyncio.create_task(run_crew())
    _current_stream_ids.reset(token)

    # 流式消费 chunks（带超时检测）
    full_content = ""
    got_chunks = False
    try:
        while True:
            try:
                item = await asyncio.wait_for(streaming_state.async_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                # 检查 task 是否已完成但没有 chunks
                if task.done():
                    break
                continue
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            if item.chunk_type == StreamChunkType.TEXT:
                text = item.content or ""
                full_content += text
                got_chunks = True
                yield {"type": "chunk", "agent": agent_role, "content": text}
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        _unregister_handler(streaming_state.handler)

    # 获取最终结果
    final_result = result_holder[0] if result_holder else full_content
    if isinstance(final_result, Exception):
        raise final_result
    final_text = str(final_result) if final_result else full_content

    # 如果 event bus 没有产出任何 chunk，回退到整段输出
    if not got_chunks and final_text:
        yield {"type": "chunk", "agent": agent_role, "content": final_text}

    # 更新 state
    _update_state_after_crew(state, route, final_text)


def _build_crew_for_route(state, route, locale_instruction):
    """根据路由构建对应的 Crew，返回 (crew, agent_role)"""
    from agents._crews.discovery_crew import DiscoveryCrew
    from agents._crews.brand_creative_crew import BrandCreativeCrew
    from agents._crews.channel_planning_crew import ChannelPlanningCrew
    from agents._crews.integration_crew import IntegrationCrew
    from agents._crews.content_crew import ContentCrew

    if route == "discovery_resume":
        state.discovery_rounds += 1
        crew = DiscoveryCrew().crew(inputs={
            "campaign_brief": state.campaign_brief,
            "qa_history": _format_qa_history(state),
            "discovery_rounds": str(state.discovery_rounds),
            "locale_instruction": locale_instruction,
        })
        return crew, "market_analyst"

    elif route == "planning":
        # 并行执行 — 这里只返回 brand crew，channel 单独处理
        crew = BrandCreativeCrew().crew(inputs={
            "campaign_name": state.campaign_name,
            "campaign_brief": state.campaign_brief,
            "audience_profile": state.audience_profile,
            "market_insights": state.market_insights,
            "locale_instruction": locale_instruction,
        })
        return crew, "brand_creative_director"

    elif route == "planning_channel":
        crew = ChannelPlanningCrew().crew(inputs={
            "campaign_name": state.campaign_name,
            "campaign_brief": state.campaign_brief,
            "audience_profile": state.audience_profile,
            "market_insights": state.market_insights,
            "locale_instruction": locale_instruction,
        })
        return crew, "channel_planner"

    elif route in ("redo_brand",):
        crew = BrandCreativeCrew().crew(inputs={
            "campaign_name": state.campaign_name,
            "campaign_brief": state.campaign_brief + "\n\nFeedback: " + state.latest_feedback,
            "audience_profile": state.audience_profile,
            "market_insights": state.market_insights,
            "locale_instruction": locale_instruction,
        })
        return crew, "brand_creative_director"

    elif route in ("redo_channel",):
        crew = ChannelPlanningCrew().crew(inputs={
            "campaign_name": state.campaign_name,
            "campaign_brief": state.campaign_brief + "\n\nFeedback: " + state.latest_feedback,
            "audience_profile": state.audience_profile,
            "market_insights": state.market_insights,
            "locale_instruction": locale_instruction,
        })
        return crew, "channel_planner"

    elif route == "integration":
        selected = state.brand_creatives[state.selected_creative_index] \
            if state.selected_creative_index >= 0 and state.brand_creatives else (state.brand_creatives[0] if state.brand_creatives else {})
        crew = IntegrationCrew().crew(inputs={
            "campaign_name": state.campaign_name,
            "audience_profile": state.audience_profile,
            "selected_creative": str(selected),
            "channel_plan": str(state.channel_plan),
            "locale_instruction": locale_instruction,
        })
        return crew, "chief_strategist"

    elif route == "content":
        selected = state.brand_creatives[state.selected_creative_index] \
            if state.selected_creative_index >= 0 and state.brand_creatives else (state.brand_creatives[0] if state.brand_creatives else {})
        crew = ContentCrew().crew(inputs={
            "campaign_name": state.campaign_name,
            "integrated_strategy": state.integrated_strategy + ("\n\nFeedback: " + state.latest_feedback if state.latest_feedback else ""),
            "selected_creative": str(selected),
            "locale_instruction": locale_instruction,
        })
        return crew, "copywriter"

    elif route == "iteration":
        target = state.iteration_target
        state.iteration_count += 1
        if target == "copywriting":
            selected = state.brand_creatives[state.selected_creative_index] \
                if state.selected_creative_index >= 0 and state.brand_creatives else (state.brand_creatives[0] if state.brand_creatives else {})
            crew = ContentCrew().crew(inputs={
                "campaign_name": state.campaign_name,
                "integrated_strategy": state.integrated_strategy + "\n\nFeedback: " + state.latest_feedback,
                "selected_creative": str(selected),
                "locale_instruction": locale_instruction,
            })
            return crew, "copywriter"
        elif target == "brand_creative":
            crew = BrandCreativeCrew().crew(inputs={
                "campaign_name": state.campaign_name,
                "campaign_brief": state.campaign_brief + "\n\nFeedback: " + state.latest_feedback,
                "audience_profile": state.audience_profile,
                "market_insights": state.market_insights,
                "locale_instruction": locale_instruction,
            })
            return crew, "brand_creative_director"
        elif target == "channel_plan":
            crew = ChannelPlanningCrew().crew(inputs={
                "campaign_name": state.campaign_name,
                "campaign_brief": state.campaign_brief + "\n\nFeedback: " + state.latest_feedback,
                "audience_profile": state.audience_profile,
                "market_insights": state.market_insights,
                "locale_instruction": locale_instruction,
            })
            return crew, "channel_planner"
        else:
            selected = state.brand_creatives[state.selected_creative_index] \
                if state.selected_creative_index >= 0 and state.brand_creatives else (state.brand_creatives[0] if state.brand_creatives else {})
            crew = IntegrationCrew().crew(inputs={
                "campaign_name": state.campaign_name,
                "audience_profile": state.audience_profile,
                "selected_creative": str(selected),
                "channel_plan": str(state.channel_plan),
                "locale_instruction": locale_instruction + "\n\nFeedback: " + state.latest_feedback,
            })
            return crew, "chief_strategist"

    elif route == "generate_document":
        # 生成完整结构化营销方案文档
        brand_raw = state.brand_creatives[0].get("raw", "") if state.brand_creatives else ""
        channel_raw = state.channel_plan.get("raw", "") if isinstance(state.channel_plan, dict) else str(state.channel_plan)
        copy_raw = state.copywriting.get("raw", "") if isinstance(state.copywriting, dict) else str(state.copywriting)

        all_content = f"""
Campaign: {state.campaign_name}

=== AUDIENCE PROFILE ===
{state.audience_profile}

=== BRAND CREATIVE ===
{brand_raw}

=== CHANNEL STRATEGY ===
{channel_raw}

=== INTEGRATED STRATEGY ===
{state.integrated_strategy}

=== MARKETING COPY ===
{copy_raw}
"""
        from agents._crews.integration_crew import IntegrationCrew
        crew = IntegrationCrew().crew(inputs={
            "campaign_name": state.campaign_name,
            "audience_profile": all_content,
            "selected_creative": "",
            "channel_plan": "",
            "locale_instruction": locale_instruction + """

YOUR TASK: Generate a COMPLETE, STRUCTURED marketing campaign plan document.
This is the FINAL deliverable document. It must include ALL of the following chapters:

1. 项目概述 (Project Overview) — campaign name, objectives, timeline
2. 目标受众 (Target Audience) — demographics, insights, personas
3. 品牌策略与创意 (Brand Strategy & Creative) — positioning, slogan, visual direction
4. 渠道策略 (Channel Strategy) — channel mix, roles, budget allocation
5. 内容与文案 (Content & Copy) — headlines, body, CTAs, social variants
6. 执行排期 (Timeline & Execution) — phases, milestones, key dates
7. 预算分配 (Budget Breakdown) — detailed allocation with rationale
8. KPI与评估 (KPIs & Measurement) — success metrics, tracking methods

If you find any inconsistencies between the modules, RESOLVE them in this document and note what you changed.
Output the document in Markdown format with clear heading hierarchy.
""",
        })
        return crew, "chief_strategist"

    elif route == "revise_document":
        # 基于现有完整文档 + 用户反馈，重新生成修订版
        from agents._crews.integration_crew import IntegrationCrew
        crew = IntegrationCrew().crew(inputs={
            "campaign_name": state.campaign_name,
            "audience_profile": state.integrated_strategy,  # 当前完整文档作为输入
            "selected_creative": "",
            "channel_plan": "",
            "locale_instruction": locale_instruction + f"""

The above is the CURRENT marketing plan document.
The user has requested the following change:
"{state.latest_feedback}"

Please revise the document to incorporate this feedback.
Keep the same structure and format.
Only change the parts that are affected by the feedback.
Output the COMPLETE revised document in Markdown.
""",
        })
        return crew, "chief_strategist"

    return None, ""


def _update_state_after_crew(state, route, result_text):
    """Crew 执行完后更新 state"""
    if route == "discovery_resume":
        if "[READY]" in result_text:
            content = result_text.split("[READY]", 1)[1].strip()
            state.audience_profile = content
            state.market_insights = content
            state.current_phase = "planning"
        else:
            state.chat_history.append({"role": "market_analyst", "content": result_text, "phase": "discovery"})
    elif route == "planning":
        state.brand_creatives = [{"raw": result_text}]
    elif route == "planning_channel":
        state.channel_plan = {"raw": result_text}
    elif route == "redo_brand":
        state.brand_creatives = [{"raw": result_text}]
    elif route == "redo_channel":
        state.channel_plan = {"raw": result_text}
    elif route == "integration":
        state.integrated_strategy = result_text
    elif route == "content":
        state.copywriting = {"raw": result_text}
    elif route == "iteration":
        target = state.iteration_target
        if target == "copywriting":
            state.copywriting = {"raw": result_text}
        elif target == "brand_creative":
            state.brand_creatives = [{"raw": result_text}]
        elif target == "channel_plan":
            state.channel_plan = {"raw": result_text}
        else:
            state.integrated_strategy = result_text
    elif route == "generate_document":
        # 完整方案文档存入 state
        state.integrated_strategy = result_text
    elif route == "revise_document":
        # 修订版文档替换
        state.integrated_strategy = result_text


def _format_qa_history(state) -> str:
    if not state.qa_history:
        return "(No previous Q&A)"
    lines = []
    for qa in state.qa_history:
        lines.append(f"Q: {qa.get('question', '')}")
        lines.append(f"A: {qa.get('answer', '')}")
    return "\n".join(lines)


async def _emit_card_update(state, route):
    """执行完成后发送对应的 card_update 事件（使用 raw 字段保持一致）"""
    if route == "discovery_resume":
        if state.audience_profile and state.current_phase == "planning":
            yield {"type": "card_update", "card": "audience", "data": {"content": state.audience_profile}}
    elif route == "redo_brand":
        yield {"type": "card_update", "card": "brand_creative", "data": {"creatives": state.brand_creatives}}
    elif route == "redo_channel":
        yield {"type": "card_update", "card": "channel_plan", "data": {"plan": state.channel_plan}}
    elif route == "integration":
        yield {"type": "card_update", "card": "strategy", "data": {"raw": state.integrated_strategy}}
    elif route == "content":
        yield {"type": "card_update", "card": "copywriting", "data": {"raw": state.copywriting.get("raw", "") if isinstance(state.copywriting, dict) else str(state.copywriting)}}
    elif route == "iteration":
        target = state.iteration_target
        if target == "brand_creative":
            yield {"type": "card_update", "card": "brand_creative", "data": {"creatives": state.brand_creatives}}
        elif target == "channel_plan":
            yield {"type": "card_update", "card": "channel_plan", "data": {"plan": state.channel_plan}}
        elif target == "copywriting":
            yield {"type": "card_update", "card": "copywriting", "data": {"content": state.copywriting}}
        else:
            yield {"type": "card_update", "card": "strategy", "data": {"content": state.integrated_strategy}}


def _classify_target(feedback: str) -> str:
    """简单关键词分类，判断迭代目标"""
    feedback_lower = feedback.lower()
    if any(w in feedback_lower for w in ["文案", "标题", "copy", "headline", "cta", "slogan"]):
        return "copywriting"
    elif any(w in feedback_lower for w in ["创意", "品牌", "creative", "brand", "视觉", "visual"]):
        return "brand_creative"
    elif any(w in feedback_lower for w in ["渠道", "预算", "排期", "channel", "budget", "timeline"]):
        return "channel_plan"
    else:
        return "strategy"


def _generate_suggestions(state, locale):
    """从 state.chat_history 最后一条消息中提取 [SUGGESTIONS]"""
    if not hasattr(state, "chat_history") or not state.chat_history:
        return []
    last = state.chat_history[-1] if state.chat_history else {}
    content = last.get("content", "")
    if "[SUGGESTIONS]" not in content:
        return []
    parts = content.split("[SUGGESTIONS]", 1)
    suggestions_text = parts[1].strip() if len(parts) > 1 else ""
    suggestions = []
    for line in suggestions_text.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            suggestions.append(line[2:].strip())
        elif line and not line.startswith("["):
            suggestions.append(line)
    return suggestions[:3]


def _get_actions_for_phase(phase, state, locale):
    """根据阶段返回操作按钮"""
    zh = locale == "zh"

    if phase == "discovery":
        return [
            {"id": "skip", "label": "信息够了，开始策划" if zh else "Start Planning", "type": "confirm"},
        ]
    elif phase == "planning":
        actions = []
        if not state.brand_confirmed:
            actions.append({"id": "confirm_brand", "label": "确认创意" if zh else "Confirm Creative", "type": "confirm", "target": "brand"})
            actions.append({"id": "redo_brand", "label": "重做创意" if zh else "Redo Creative", "type": "redo", "target": "brand"})
        if not state.channel_confirmed:
            actions.append({"id": "confirm_channel", "label": "确认渠道" if zh else "Confirm Channel", "type": "confirm", "target": "channel"})
            actions.append({"id": "redo_channel", "label": "重做渠道" if zh else "Redo Channel", "type": "redo", "target": "channel"})
        return actions
    elif phase == "integration":
        return [
            {"id": "confirm", "label": "确认策略" if zh else "Confirm Strategy", "type": "confirm"},
            {"id": "redo", "label": "修改策略" if zh else "Revise", "type": "redo"},
            {"id": "rollback", "label": "返回策划阶段" if zh else "Back to Planning", "type": "rollback"},
        ]
    elif phase == "content":
        return [
            {"id": "confirm", "label": "确认文案" if zh else "Confirm Copy", "type": "confirm"},
            {"id": "redo", "label": "修改文案" if zh else "Revise", "type": "redo"},
            {"id": "rollback", "label": "调整策略" if zh else "Back to Strategy", "type": "rollback"},
        ]
    elif phase == "finalize":
        return []  # finalize 阶段由前端 FinalizeView 自己管理按钮
    return []


def _route_to_phase(route):
    phase_map = {
        "discovery_resume": "discovery",
        "planning": "planning",
        "redo_brand": "planning",
        "redo_channel": "planning",
        "integration": "integration",
        "content": "content",
        "finalize": "finalize",
        "generate_document": "finalize",
        "revise_document": "finalize",
        "iteration": "finalize",
    }
    return phase_map.get(route, "discovery")


def _phase_to_progress(phase):
    progress_map = {
        "discovery": 15,
        "planning": 35,
        "integration": 55,
        "content": 75,
        "finalize": 90,
    }
    return progress_map.get(phase, 0)


def _route_to_agent(route):
    agent_map = {
        "discovery_resume": "market_analyst",
        "planning": "brand_creative_director",
        "redo_brand": "brand_creative_director",
        "redo_channel": "channel_planner",
        "integration": "chief_strategist",
        "content": "copywriter",
        "iteration": "chief_strategist",
    }
    return agent_map.get(route)


def _route_to_lane(route):
    if route in ("redo_brand", "planning"):
        return "brand"
    if route == "redo_channel":
        return "channel"
    return None


def _get_status_message(route, locale):
    zh = locale == "zh"
    msg_map = {
        "discovery_resume": "市场分析师正在分析你的回答..." if zh else "Analyst processing your answer...",
        "planning": "品牌创意和渠道策划同时启动..." if zh else "Brand creative and channel planning started...",
        "redo_brand": "品牌创意总监正在重新设计..." if zh else "Creative director redesigning...",
        "redo_channel": "渠道策划师正在重新规划..." if zh else "Channel planner redesigning...",
        "integration": "策略总监正在整合方案..." if zh else "Strategist integrating plan...",
        "content": "文案专家正在撰写..." if zh else "Copywriter writing...",
        "delivery": "方案已就绪" if zh else "Plan ready",
        "iteration": "正在修改对应模块..." if zh else "Revising module...",
    }
    return msg_map.get(route, "")



