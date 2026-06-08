"""SSE 事件生成工具函数"""


def format_qa_history(state) -> str:
    if not state.qa_history:
        return "(No previous Q&A)"
    lines = []
    for qa in state.qa_history:
        lines.append(f"Q: {qa.get('question', '')}")
        lines.append(f"A: {qa.get('answer', '')}")
    return "\n".join(lines)


async def emit_card_update(state, route):
    """执行完成后发送对应的 card_update 事件"""
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


def generate_suggestions(state, locale):
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


def get_actions_for_phase(phase, state, locale):
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
        return []
    return []
