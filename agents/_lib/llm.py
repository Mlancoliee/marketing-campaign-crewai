"""LLM singletons — streaming (for Crews) + non-streaming (for @human_feedback collapse)."""

from crewai import LLM
from .logger import make_logger

log = make_logger("llm")

_llm = None
_collapse_llm = None

DEFAULT_MODEL = "openai/@makers/deepseek-v4-flash"


def init_llm(context_env):
    """Initialize LLM singletons from context.env. Must be called once at handler start."""
    global _llm, _collapse_llm
    if _llm is not None:
        return _llm

    env = context_env or {}
    api_key = env.get("AI_GATEWAY_API_KEY", "")
    base_url = env.get("AI_GATEWAY_BASE_URL", "")
    if not api_key or not base_url:
        raise RuntimeError("Missing AI_GATEWAY_API_KEY or AI_GATEWAY_BASE_URL")

    model = env.get("AI_GATEWAY_MODEL", "").strip() or DEFAULT_MODEL
    # Ensure model has openai/ prefix for LiteLLM routing
    if not model.startswith("openai/"):
        model = f"openai/{model}"

    log(f"Initializing LLM with model={model}")
    _llm = LLM(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0.3,
        timeout=300,
        stream=True,
    )
    _collapse_llm = LLM(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0,
        timeout=60,
        stream=False,
    )
    return _llm


def get_llm() -> LLM:
    """Get the streaming LLM singleton. Raises if init_llm() not called."""
    if _llm is None:
        raise RuntimeError("Call init_llm(context.env) first.")
    return _llm


def get_collapse_llm() -> LLM:
    """Get the non-streaming LLM for @human_feedback collapse routing."""
    if _collapse_llm is None:
        raise RuntimeError("Call init_llm(context.env) first.")
    return _collapse_llm
