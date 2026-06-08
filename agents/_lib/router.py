"""路由判断逻辑"""


def determine_next_route(body, state, current_phase):
    """根据请求体确定下一步路由（直接操作 state）"""
    if body.get("finish"):
        return "done"

    # Discovery 阶段
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
            state.integrated_strategy = ""
            state.copywriting = {}
            return f"redo_{target}"
        elif action_type == "keep_old":
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
                if state.integrated_strategy:
                    return "restore_integration"
                return "integration"
            else:
                return "wait"

    # Phase action
    phase_action = body.get("phase_action")
    if phase_action:
        action_type = phase_action.get("type", "")
        feedback = phase_action.get("feedback", "")

        if action_type == "confirm":
            if current_phase == "planning":
                state.brand_confirmed = True
                state.channel_confirmed = True
                state.selected_creative_index = 0
                if state.integrated_strategy:
                    return "restore_integration"
                return "integration"
            elif current_phase == "integration":
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
                state.copywriting = {}
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
            return "revise_document"
        else:
            state.iteration_target = classify_target(iteration_feedback)
            return "iteration"

    return "wait"


def classify_target(feedback: str) -> str:
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
