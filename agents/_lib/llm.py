import os
from crewai import LLM


def get_streaming_llm() -> LLM:
    """流式 LLM，给 Crew 使用"""
    return LLM(
        model="openai/@makers/deepseek-v4-flash",
        api_key=os.environ.get("AI_GATEWAY_API_KEY", ""),
        base_url=os.environ.get("AI_GATEWAY_BASE_URL", ""),
        stream=True,
        temperature=0.3,
        timeout=300,
    )


def get_router_llm() -> LLM:
    """非流式 LLM，给路由判断使用"""
    return LLM(
        model="openai/deepseek-v4-flash",
        api_key=os.environ.get("AI_GATEWAY_API_KEY", ""),
        base_url=os.environ.get("AI_GATEWAY_BASE_URL", ""),
        stream=False,
        temperature=0,
        timeout=60,
    )
