from pydantic import BaseModel, ConfigDict


class CampaignState(BaseModel):
    """营销活动策划 Flow 的全局状态"""

    model_config = ConfigDict(extra="allow")

    # 基础信息
    campaign_name: str = ""
    campaign_brief: str = ""
    locale: str = "zh"  # "zh" | "en"

    # Discovery 阶段
    qa_history: list[dict] = []
    discovery_rounds: int = 0
    audience_profile: str = ""
    market_insights: str = ""

    # Parallel Planning 阶段
    brand_creatives: list[dict] = []
    channel_plan: dict = {}
    selected_creative_index: int = -1
    brand_confirmed: bool = False
    channel_confirmed: bool = False

    # Integration 阶段
    integrated_strategy: str = ""

    # Content 阶段
    copywriting: dict = {}

    # 开放迭代
    latest_feedback: str = ""
    iteration_target: str = ""
    iteration_count: int = 0

    # 全局控制
    current_phase: str = "discovery"
    chat_history: list[dict] = []
    finished: bool = False
