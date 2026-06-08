"""持久化到 context.store 的工具函数"""
from agents._lib.logger import make_logger

log = make_logger("Store")


async def persist_to_store(context, conversation_id: str, state):
    """将当前状态持久化到 context.store（Blob 存储，跨重启可恢复）"""
    if not hasattr(context, "store"):
        return
    try:
        cards = {
            "audience": {"content": state.audience_profile} if state.audience_profile else None,
            "brand_creative": {"creatives": state.brand_creatives} if state.brand_creatives else None,
            "channel_plan": {"plan": state.channel_plan} if state.channel_plan else None,
            "strategy": {"content": state.integrated_strategy} if state.integrated_strategy else None,
            "copywriting": state.copywriting if state.copywriting else None,
        }
        try:
            await context.store.get_conversation(conversation_id=conversation_id)
        except Exception:
            await context.store.append_message(
                conversation_id=conversation_id,
                role="system",
                content=f"Campaign: {state.campaign_name}",
                metadata={"type": "init"},
            )
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
    return "assistant"


async def save_messages_to_store(context, conversation_id: str, state):
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
        state.chat_history = []
    except Exception as e:
        log(f"Save messages failed: {e}")
