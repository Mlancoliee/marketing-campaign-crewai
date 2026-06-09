"""Crew 执行引擎 — 构建、流式执行、状态更新"""
import re
import asyncio

from agents._lib.sse_events import format_qa_history


async def execute_crew_streaming(state, route):
    """执行 Crew 并流式输出 token（通过 event bus 或回退到分块）"""
    from crewai.utilities.streaming import create_streaming_state, signal_end, _unregister_handler, _current_stream_ids
    from crewai.types.streaming import StreamChunkType

    locale_instruction = "Chinese (中文)" if state.locale == "zh" else "English"

    crew, agent_role = build_crew_for_route(state, route, locale_instruction)
    if crew is None:
        return

    task_info = {"index": 0, "name": route, "id": "", "agent_role": agent_role, "agent_id": ""}
    result_holder = []
    streaming_state = create_streaming_state(task_info, result_holder, use_async=True)
    stream_id = streaming_state.stream_id

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

    token = _current_stream_ids.set((*_current_stream_ids.get(), stream_id))
    task = asyncio.create_task(run_crew())
    _current_stream_ids.reset(token)

    full_content = ""
    got_chunks = False
    try:
        while True:
            try:
                item = await asyncio.wait_for(streaming_state.async_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
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

    final_result = result_holder[0] if result_holder else full_content
    if isinstance(final_result, Exception):
        raise final_result
    final_text = str(final_result) if final_result else full_content

    if not got_chunks and final_text:
        yield {"type": "chunk", "agent": agent_role, "content": final_text}

    update_state_after_crew(state, route, final_text)


def build_crew_for_route(state, route, locale_instruction):
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
            "qa_history": format_qa_history(state),
            "discovery_rounds": str(state.discovery_rounds),
            "locale_instruction": locale_instruction,
        })
        return crew, "market_analyst"

    elif route == "planning":
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
            "locale_instruction": locale_instruction + "\n\nYOUR TASK: Generate a COMPLETE, STRUCTURED marketing campaign plan document.\nThis is the FINAL deliverable document. It must include ALL of the following chapters:\n\n1. 项目概述 (Project Overview)\n2. 目标受众 (Target Audience)\n3. 品牌策略与创意 (Brand Strategy & Creative)\n4. 渠道策略 (Channel Strategy)\n5. 内容与文案 (Content & Copy)\n6. 执行排期 (Timeline & Execution)\n7. 预算分配 (Budget Breakdown)\n8. KPI与评估 (KPIs & Measurement)\n\nIf you find any inconsistencies between the modules, RESOLVE them and note what you changed.\nOutput in Markdown format with clear heading hierarchy.",
        })
        return crew, "chief_strategist"

    elif route == "revise_document":
        from agents._crews.integration_crew import IntegrationCrew
        crew = IntegrationCrew().crew(inputs={
            "campaign_name": state.campaign_name,
            "audience_profile": state.integrated_strategy,
            "selected_creative": "",
            "channel_plan": "",
            "locale_instruction": locale_instruction + f'\n\nThe above is the CURRENT marketing plan document.\nThe user has requested the following change:\n"{state.latest_feedback}"\n\nPlease revise the document to incorporate this feedback.\nKeep the same structure and format. Only change the parts that are affected.\nOutput the COMPLETE revised document in Markdown.',
        })
        return crew, "chief_strategist"

    return None, ""


def _clean_html(text: str) -> str:
    """清理 LLM 输出中的 HTML 标签"""
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text


def update_state_after_crew(state, route, result_text):
    """Crew 执行完后更新 state"""
    result_text = _clean_html(result_text)
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
    elif route in ("generate_document", "revise_document"):
        state.integrated_strategy = result_text
