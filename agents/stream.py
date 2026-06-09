"""
POST /stream - 营销活动策划 Agent 主入口

处理所有对话轮次：
- action: "history" → 返回存储的历史
- action: "send" → kickoff 或 resume
"""
import uuid
import asyncio
import traceback

from agents._lib.state import CampaignState
from agents._lib.persistence import save_state, load_state, delete_state
from agents._lib.logger import make_logger
from agents._lib.store_utils import persist_to_store, save_messages_to_store
from agents._lib.router import determine_next_route
from agents._lib.crew_runner import execute_crew_streaming, build_crew_for_route, update_state_after_crew
from agents._lib.sse_events import emit_card_update, generate_suggestions, get_actions_for_phase, format_qa_history
from agents._lib.helpers import route_to_phase, phase_to_progress, route_to_agent, route_to_lane, get_status_message

log = make_logger("Handler")




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
                save_state(conversation_id, state_dict, {"phase": current_phase})

                return {
                    "conversation_id": conversation_id,
                    "chat_history": chat_history,
                    "current_phase": current_phase,
                    "cards": cards,
                }
        except Exception:
            pass

    # 回退到内存 state
    stored = load_state(conversation_id)
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

    stored = load_state(conversation_id)

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
                save_state(conversation_id, state_dict, {"phase": current_phase})
                stored = load_state(conversation_id)
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
    """首次启动 — 直接调用 DiscoveryCrew（与 resume 路径一致）"""
    campaign_name = body.get("campaign_name", "")
    campaign_brief = body.get("message", body.get("campaign_brief", ""))

    yield {"type": "phase_change", "phase": "discovery", "progress": 10}
    yield {"type": "status", "message": "市场分析师正在准备提问..." if locale == "zh" else "Market analyst preparing questions...", "from": "chief_strategist"}
    yield {"type": "agent_start", "agent": "market_analyst"}

    # 构建初始状态
    state = CampaignState(
        campaign_name=campaign_name,
        campaign_brief=campaign_brief,
        locale=locale,
    )

    locale_instruction = "Chinese (中文)" if locale == "zh" else "English"

    try:
        # 复用 build_crew_for_route — 与 resume 路径完全一致
        crew, _ = build_crew_for_route(state, "discovery_resume", locale_instruction)
        if crew is None:
            yield {"type": "error", "message": "无法构建 Discovery Crew"}
            yield {"type": "agent_end", "agent": "market_analyst"}
            return

        result = await asyncio.wait_for(crew.kickoff_async(), timeout=300)
        result_text = str(result)

        # 更新 state（与 resume 路径一致）
        update_state_after_crew(state, "discovery_resume", result_text)

    except asyncio.TimeoutError:
        yield {"type": "error", "message": "LLM 响应超时，请重试"}
        yield {"type": "agent_end", "agent": "market_analyst"}
        return
    except Exception as e:
        yield {"type": "error", "message": str(e)}
        yield {"type": "agent_end", "agent": "market_analyst"}
        return

    # 输出 agent 产出
    if state.current_phase != "planning":
        # 还在 discovery 阶段 — 输出问题
        display = result_text
        if "[SUGGESTIONS]" in display:
            display = display.split("[SUGGESTIONS]")[0].strip()
        yield {"type": "message", "from": "market_analyst", "content": display, "phase": "discovery"}
    else:
        # [READY] 被检测到，已经进入 planning — 输出受众画像卡片
        yield {"type": "card_update", "card": "audience", "data": {"content": state.audience_profile}}

    yield {"type": "agent_end", "agent": "market_analyst"}

    # 输出卡片更新（如果有受众画像但还未通过上面输出）
    if state.audience_profile and state.current_phase != "planning":
        yield {"type": "card_update", "card": "audience", "data": {"content": state.audience_profile}}

    # 如果 discovery 判断 READY，自动继续执行 planning crew
    if state.current_phase == "planning":
        yield {"type": "phase_change", "phase": "planning", "progress": phase_to_progress("planning")}
        yield {"type": "status", "message": "信息收集完毕，开始策划..." if locale == "zh" else "Research complete, starting parallel planning...", "from": "chief_strategist"}
        yield {"type": "parallel_start", "lanes": ["brand", "channel"]}

        # 品牌创意流式
        yield {"type": "agent_start", "agent": "brand_creative_director", "lane": "brand"}
        try:
            async for event in execute_crew_streaming(state, "planning"):
                yield event
        except Exception as e:
            log(f"Planning brand error: {traceback.format_exc()}")
            yield {"type": "error", "message": str(e)}
            save_state(conversation_id, state.model_dump(), {"phase": "planning"})
            return
        yield {"type": "agent_end", "agent": "brand_creative_director", "lane": "brand"}
        yield {"type": "card_update", "card": "brand_creative", "data": {"creatives": state.brand_creatives}}

        # 渠道策略流式
        yield {"type": "agent_start", "agent": "channel_planner", "lane": "channel"}
        try:
            async for event in execute_crew_streaming(state, "planning_channel"):
                yield event
        except Exception as e:
            log(f"Planning channel error: {traceback.format_exc()}")
            yield {"type": "error", "message": str(e)}
            save_state(conversation_id, state.model_dump(), {"phase": "planning"})
            return
        yield {"type": "agent_end", "agent": "channel_planner", "lane": "channel"}
        yield {"type": "card_update", "card": "channel_plan", "data": {"plan": state.channel_plan}}

        yield {"type": "parallel_end"}

    # 输出推荐回答（仅 discovery 阶段）
    if state.current_phase != "planning":
        suggestions = generate_suggestions(state, locale)
        if suggestions:
            yield {"type": "suggestions", "suggestions": suggestions}

    # 输出可用操作
    phase = state.current_phase if state.current_phase == "planning" else "discovery"
    yield {"type": "actions", "actions": get_actions_for_phase(phase, state, locale)}

    # 保存状态
    save_state(conversation_id, state.model_dump(), {"phase": state.current_phase})
    await persist_to_store(context, conversation_id, state)
    await save_messages_to_store(context, conversation_id, state)


async def _stream_resume(body, stored, conversation_id, context):
    """恢复暂停的对话 - 根据路由直接调用对应 Crew"""
    state_dict = stored["state"]
    phase = state_dict.get("current_phase", "discovery")
    locale = state_dict.get("locale", "zh")

    # 恢复 state
    state = CampaignState(**state_dict)

    # 根据请求类型确定下一步
    next_route = determine_next_route(body, state, phase)

    if next_route == "done":
        delete_state(conversation_id)
        yield {"type": "phase_change", "phase": "done", "progress": 100}
        yield {"type": "status", "message": "营销方案已完成！" if locale == "zh" else "Campaign plan complete!", "from": "chief_strategist"}
        return

    if next_route == "wait":
        save_state(conversation_id, state.model_dump(), {"phase": phase})
        yield {"type": "status", "message": "已保存" if locale == "zh" else "Saved", "from": "chief_strategist"}
        return

    # Rollback：只切换阶段，恢复已有数据，不清除下游（redo 才清除）
    if next_route == "rollback_to_planning":
        state.current_phase = "planning"
        state.brand_confirmed = False
        state.channel_confirmed = False
        save_state(conversation_id, state.model_dump(), {"phase": "planning"})
        yield {"type": "phase_change", "phase": "planning", "progress": phase_to_progress("planning")}
        yield {"type": "status", "message": "已返回方案策划阶段" if locale == "zh" else "Back to planning", "from": "chief_strategist"}
        yield {"type": "card_update", "card": "brand_creative", "data": {"creatives": state.brand_creatives}}
        yield {"type": "card_update", "card": "channel_plan", "data": {"plan": state.channel_plan}}
        yield {"type": "actions", "actions": get_actions_for_phase("planning", state, locale)}
        return

    if next_route == "rollback_to_integration":
        state.current_phase = "integration"
        save_state(conversation_id, state.model_dump(), {"phase": "integration"})
        yield {"type": "phase_change", "phase": "integration", "progress": phase_to_progress("integration")}
        yield {"type": "status", "message": "已返回策略整合阶段" if locale == "zh" else "Back to integration", "from": "chief_strategist"}
        yield {"type": "card_update", "card": "strategy", "data": {"content": state.integrated_strategy}}
        yield {"type": "actions", "actions": get_actions_for_phase("integration", state, locale)}
        return

    # Restore：前进到已有数据的阶段（回退后再确认时不重新生成）
    if next_route == "restore_integration":
        state.current_phase = "integration"
        save_state(conversation_id, state.model_dump(), {"phase": "integration"})
        yield {"type": "phase_change", "phase": "integration", "progress": phase_to_progress("integration")}
        yield {"type": "status", "message": "策略整合方案已就绪" if locale == "zh" else "Strategy ready", "from": "chief_strategist"}
        yield {"type": "card_update", "card": "strategy", "data": {"content": state.integrated_strategy}}
        yield {"type": "actions", "actions": get_actions_for_phase("integration", state, locale)}
        return

    if next_route == "restore_content":
        state.current_phase = "content"
        save_state(conversation_id, state.model_dump(), {"phase": "content"})
        yield {"type": "phase_change", "phase": "content", "progress": phase_to_progress("content")}
        yield {"type": "status", "message": "营销文案已就绪" if locale == "zh" else "Copy ready", "from": "chief_strategist"}
        yield {"type": "card_update", "card": "copywriting", "data": {"content": state.copywriting}}
        yield {"type": "actions", "actions": get_actions_for_phase("content", state, locale)}
        return

    # Finalize：展示卡片总览（发送所有卡片数据确保前端状态完整）
    if next_route == "finalize":
        state.current_phase = "finalize"
        save_state(conversation_id, state.model_dump(), {"phase": "finalize"})
        yield {"type": "phase_change", "phase": "finalize", "progress": phase_to_progress("finalize")}
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
        yield {"type": "phase_change", "phase": "finalize", "progress": phase_to_progress("finalize")}
        msg = ("策略总监正在修订方案..." if next_route == "revise_document" else "策略总监正在整合生成完整方案...") if locale == "zh" else ("Revising plan..." if next_route == "revise_document" else "Generating full plan...")
        yield {"type": "status", "message": msg, "from": "chief_strategist"}
        yield {"type": "agent_start", "agent": "chief_strategist"}
        try:
            async for event in execute_crew_streaming(state, next_route):
                yield event
        except Exception as e:
            log(f"Document error: {traceback.format_exc()}")
            yield {"type": "error", "message": str(e)}
        yield {"type": "agent_end", "agent": "chief_strategist"}
        save_state(conversation_id, state.model_dump(), {"phase": "finalize"})
        return

    # Rollback to content
    if next_route == "rollback_to_content":
        state.current_phase = "content"
        save_state(conversation_id, state.model_dump(), {"phase": "content"})
        yield {"type": "phase_change", "phase": "content", "progress": phase_to_progress("content")}
        yield {"type": "status", "message": "已返回内容产出阶段" if locale == "zh" else "Back to content", "from": "chief_strategist"}
        yield {"type": "card_update", "card": "copywriting", "data": {"raw": state.copywriting.get("raw", "") if isinstance(state.copywriting, dict) else str(state.copywriting)}}
        yield {"type": "actions", "actions": get_actions_for_phase("content", state, locale)}
        return

    # 发送阶段变更
    new_phase = route_to_phase(next_route)
    progress = phase_to_progress(new_phase)
    yield {"type": "phase_change", "phase": new_phase, "progress": progress}

    # 发送状态提示
    status_msg = get_status_message(next_route, locale)
    if status_msg:
        yield {"type": "status", "message": status_msg, "from": "chief_strategist"}

    # 发送 agent_start
    agent = route_to_agent(next_route)
    if agent:
        yield {"type": "agent_start", "agent": agent, "lane": route_to_lane(next_route)}

    # 执行 Crew（流式）
    if next_route == "planning":
        # 并行：先品牌流式，再渠道流式
        yield {"type": "parallel_start", "lanes": ["brand", "channel"]}
        try:
            async for event in execute_crew_streaming(state, "planning"):
                yield event
            yield {"type": "agent_end", "agent": "brand_creative_director", "lane": "brand"}
            # 发送品牌卡片
            yield {"type": "card_update", "card": "brand_creative", "data": {"creatives": state.brand_creatives}}

            # 渠道
            yield {"type": "agent_start", "agent": "channel_planner", "lane": "channel"}
            async for event in execute_crew_streaming(state, "planning_channel"):
                yield event
            yield {"type": "agent_end", "agent": "channel_planner", "lane": "channel"}
            yield {"type": "card_update", "card": "channel_plan", "data": {"plan": state.channel_plan}}
        except Exception as e:
            log(f"Planning crew error: {traceback.format_exc()}")
            yield {"type": "error", "message": str(e)}
            save_state(conversation_id, state.model_dump(), {"phase": "planning"})
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
            crew, _ = build_crew_for_route(state, "discovery_resume", "Chinese (中文)" if locale == "zh" else "English")
            if crew:
                result = await asyncio.wait_for(crew.kickoff_async(), timeout=300)
                result_text = str(result)
                update_state_after_crew(state, "discovery_resume", result_text)
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
                yield {"type": "agent_end", "agent": agent, "lane": route_to_lane(next_route)}
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
            async for event in execute_crew_streaming(state, next_route):
                yield event
        except Exception as e:
            log(f"Crew execution error: {traceback.format_exc()}")
            yield {"type": "error", "message": str(e)}
            if agent:
                yield {"type": "agent_end", "agent": agent, "lane": route_to_lane(next_route)}
            return

        # 流式 chunk 已经将内容推送到前端 cards.raw，不需要再发 card_update

    # discovery_resume 且未进入 planning 时，附加推荐回答
    if next_route == "discovery_resume" and state.current_phase != "planning":
        suggestions = generate_suggestions(state, locale)
        if suggestions:
            yield {"type": "suggestions", "suggestions": suggestions}

    if agent and next_route != "planning":
        yield {"type": "agent_end", "agent": agent, "lane": route_to_lane(next_route)}

    # 如果 discovery_resume 中 Crew 判断 READY，state.current_phase 已被改为 planning
    # 需要自动继续执行 planning crew
    if state.current_phase == "planning" and next_route == "discovery_resume":
        yield {"type": "phase_change", "phase": "planning", "progress": phase_to_progress("planning")}
        yield {"type": "status", "message": "信息收集完毕，开始策划..." if locale == "zh" else "Research complete, starting parallel planning...", "from": "chief_strategist"}
        yield {"type": "parallel_start", "lanes": ["brand", "channel"]}

        # 品牌创意流式
        yield {"type": "agent_start", "agent": "brand_creative_director", "lane": "brand"}
        try:
            async for event in execute_crew_streaming(state, "planning"):
                yield event
        except Exception as e:
            log(f"Planning brand error: {traceback.format_exc()}")
            yield {"type": "error", "message": str(e)}
            save_state(conversation_id, state.model_dump(), {"phase": "planning"})
            return
        yield {"type": "agent_end", "agent": "brand_creative_director", "lane": "brand"}
        yield {"type": "card_update", "card": "brand_creative", "data": {"creatives": state.brand_creatives}}

        # 渠道策略流式
        yield {"type": "agent_start", "agent": "channel_planner", "lane": "channel"}
        try:
            async for event in execute_crew_streaming(state, "planning_channel"):
                yield event
        except Exception as e:
            log(f"Planning channel error: {traceback.format_exc()}")
            yield {"type": "error", "message": str(e)}
            save_state(conversation_id, state.model_dump(), {"phase": "planning"})
            return
        yield {"type": "agent_end", "agent": "channel_planner", "lane": "channel"}
        yield {"type": "card_update", "card": "channel_plan", "data": {"plan": state.channel_plan}}

        yield {"type": "parallel_end"}
        new_phase = "planning"
    else:
        state.current_phase = new_phase

    save_state(conversation_id, state.model_dump(), {"phase": state.current_phase})
    await persist_to_store(context, conversation_id, state)

    # 输出操作按钮
    yield {"type": "actions", "actions": get_actions_for_phase(new_phase, state, locale)}


