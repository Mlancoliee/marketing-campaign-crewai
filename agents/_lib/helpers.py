"""路由到阶段/Agent/进度的映射工具"""


def route_to_phase(route):
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


def phase_to_progress(phase):
    progress_map = {
        "discovery": 15,
        "planning": 35,
        "integration": 55,
        "content": 75,
        "finalize": 90,
    }
    return progress_map.get(phase, 0)


def route_to_agent(route):
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


def route_to_lane(route):
    if route in ("redo_brand", "planning"):
        return "brand"
    if route == "redo_channel":
        return "channel"
    return None


def get_status_message(route, locale):
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
