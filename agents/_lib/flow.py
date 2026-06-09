"""MarketingCampaignFlow — 主流程 Flow (5 步)

生命周期:
  kickoff → discovery_step (循环提问) → pause
  resume  → after_discovery → continue_discovery / "planning"
  ...     → discovery_step → pause → ...
  resume  → after_discovery → "planning"
          → planning_step (品牌+渠道) → pause
  resume  → after_planning → "integration"
          → integration_step → pause
  resume  → after_integration → "content"
          → content_step → pause
  resume  → after_content → "finalize"
          → finalize_step (Flow 结束)

分支操作（redo_brand / rollback 等）不在 Flow 内处理，
由 stream.py handler 层拦截后直接调用 Crew。
"""

from pydantic import BaseModel, ConfigDict

from crewai.flow import Flow, listen, or_, router, start
from crewai.flow.human_feedback import human_feedback

from .feedback_provider import PROVIDER
from .llm import get_collapse_llm
from .logger import make_logger
from .._crews.discovery_crew.discovery_crew import DiscoveryCrew
from .._crews.brand_creative_crew.brand_creative_crew import BrandCreativeCrew
from .._crews.channel_planning_crew.channel_planning_crew import ChannelPlanningCrew
from .._crews.integration_crew.integration_crew import IntegrationCrew
from .._crews.content_crew.content_crew import ContentCrew

log = make_logger("Flow")

MAX_DISCOVERY_ROUNDS = 4


class CampaignState(BaseModel):
    """营销活动策划 Flow 的全局状态"""

    model_config = ConfigDict(extra="allow")

    # 基础信息
    id: str = ""  # conversation_id, set via kickoff(inputs={"id": cid})
    campaign_name: str = ""
    campaign_brief: str = ""
    locale: str = "zh"

    # Discovery 阶段
    qa_history: str = ""
    discovery_rounds: int = 0
    audience_profile: str = ""
    market_insights: str = ""

    # Planning 阶段
    brand_creatives: str = ""
    channel_plan: str = ""
    brand_confirmed: bool = False
    channel_confirmed: bool = False

    # Integration 阶段
    integrated_strategy: str = ""

    # Content 阶段
    copywriting: str = ""

    # 控制
    current_phase: str = "discovery"
    finished: bool = False

    # 内部标志
    _ready: bool = False


class MarketingCampaignFlow(Flow[CampaignState]):
    """营销活动策划主流程 — 5 步 + human_feedback 暂停/恢复"""

    stream = True

    # ─── Discovery: 市场分析师循环提问 ───────────────────────────

    @start()
    def begin(self):
        """Flow 入口 — 初始化阶段"""
        self.state.current_phase = "discovery"

    @listen(or_(begin, "continue_discovery"))
    @human_feedback(message="(user replies)", provider=PROVIDER)
    def discovery_step(self):
        """市场分析师提一个问题或输出 [READY]"""
        s = self.state
        s.discovery_rounds += 1
        locale_instruction = "Chinese (中文)" if s.locale == "zh" else "English"

        output = DiscoveryCrew().crew().kickoff(inputs={
            "campaign_brief": s.campaign_brief,
            "qa_history": s.qa_history or "(No previous Q&A)",
            "discovery_rounds": str(s.discovery_rounds),
            "locale_instruction": locale_instruction,
        })
        text = _crew_text(output)

        # 检测是否信息充足
        if "[READY]" in text:
            s._ready = True
            content = text.split("[READY]", 1)[1].strip()
            s.audience_profile = content
            s.market_insights = content
        else:
            # 追加到 qa_history
            clean = text.split("[SUGGESTIONS]")[0].strip() if "[SUGGESTIONS]" in text else text
            s.qa_history = (s.qa_history + f"\nAnalyst: {clean}").strip()

        return text

    @router(discovery_step)
    def after_discovery(self):
        # Check if user explicitly wants to skip discovery (e.g., "信息够了，开始策划")
        feedback = ""
        if self.last_human_feedback:
            feedback = (self.last_human_feedback.feedback or "").lower()
        if self.state._ready or self.state.discovery_rounds >= MAX_DISCOVERY_ROUNDS:
            return "planning"
        if any(k in feedback for k in ("skip", "confirm", "action:confirm", "够了", "开始策划", "next")):
            # User wants to skip — use whatever info we have
            if not self.state.audience_profile:
                self.state.audience_profile = self.state.qa_history
                self.state.market_insights = self.state.qa_history
            return "planning"
        return "continue_discovery"

    # ─── Planning: 品牌创意 + 渠道策划（顺序执行，流式输出）─────

    @listen("planning")
    @human_feedback(message="(user reviews)", provider=PROVIDER)
    def planning_step(self):
        """品牌创意 → 渠道策划（顺序执行，streaming 自动分段）"""
        s = self.state
        s.current_phase = "planning"
        locale_instruction = "Chinese (中文)" if s.locale == "zh" else "English"

        inputs = {
            "campaign_name": s.campaign_name,
            "campaign_brief": s.campaign_brief,
            "audience_profile": s.audience_profile,
            "market_insights": s.market_insights,
            "locale_instruction": locale_instruction,
        }

        brand_result = BrandCreativeCrew().crew().kickoff(inputs=inputs)
        s.brand_creatives = _crew_text(brand_result)

        channel_result = ChannelPlanningCrew().crew().kickoff(inputs=inputs)
        s.channel_plan = _crew_text(channel_result)

        return f"{s.brand_creatives}\n\n---\n\n{s.channel_plan}"

    @router(planning_step)
    def after_planning(self):
        feedback = (self.last_human_feedback.feedback or "") if self.last_human_feedback else ""
        if _is_confirm(feedback):
            return "integration"
        if "redo_brand" in feedback:
            return "redo_brand"
        if "redo_channel" in feedback:
            return "redo_channel"
        return "planning"

    # ─── Redo Brand / Channel (流式，保持在 planning 阶段) ────────

    @listen("redo_brand")
    @human_feedback(message="(user reviews)", provider=PROVIDER)
    def redo_brand_step(self):
        """重做品牌创意"""
        s = self.state
        locale_instruction = "Chinese (中文)" if s.locale == "zh" else "English"
        feedback_text = ""
        if self.last_human_feedback:
            raw = self.last_human_feedback.feedback or ""
            if "|feedback=" in raw:
                feedback_text = raw.split("|feedback=", 1)[1]

        result = BrandCreativeCrew().crew().kickoff(inputs={
            "campaign_name": s.campaign_name,
            "campaign_brief": s.campaign_brief + (f"\n\nFeedback: {feedback_text}" if feedback_text else ""),
            "audience_profile": s.audience_profile,
            "market_insights": s.market_insights,
            "locale_instruction": locale_instruction,
        })
        s.brand_creatives = _crew_text(result)
        s.current_phase = "planning"
        return s.brand_creatives

    @router(redo_brand_step)
    def after_redo_brand(self):
        feedback = (self.last_human_feedback.feedback or "") if self.last_human_feedback else ""
        if _is_confirm(feedback):
            return "integration"
        if "redo_brand" in feedback:
            return "redo_brand"
        if "redo_channel" in feedback:
            return "redo_channel"
        return "planning"

    @listen("redo_channel")
    @human_feedback(message="(user reviews)", provider=PROVIDER)
    def redo_channel_step(self):
        """重做渠道策略"""
        s = self.state
        locale_instruction = "Chinese (中文)" if s.locale == "zh" else "English"
        feedback_text = ""
        if self.last_human_feedback:
            raw = self.last_human_feedback.feedback or ""
            if "|feedback=" in raw:
                feedback_text = raw.split("|feedback=", 1)[1]

        result = ChannelPlanningCrew().crew().kickoff(inputs={
            "campaign_name": s.campaign_name,
            "campaign_brief": s.campaign_brief + (f"\n\nFeedback: {feedback_text}" if feedback_text else ""),
            "audience_profile": s.audience_profile,
            "market_insights": s.market_insights,
            "locale_instruction": locale_instruction,
        })
        s.channel_plan = _crew_text(result)
        s.current_phase = "planning"
        return s.channel_plan

    @router(redo_channel_step)
    def after_redo_channel(self):
        feedback = (self.last_human_feedback.feedback or "") if self.last_human_feedback else ""
        if _is_confirm(feedback):
            return "integration"
        if "redo_brand" in feedback:
            return "redo_brand"
        if "redo_channel" in feedback:
            return "redo_channel"
        return "planning"

    # ─── Integration: 策略整合 ───────────────────────────────────

    @listen("integration")
    @human_feedback(message="(user reviews)", provider=PROVIDER)
    def integration_step(self):
        """策略总监整合品牌+渠道为统一方案"""
        s = self.state
        s.current_phase = "integration"
        locale_instruction = "Chinese (中文)" if s.locale == "zh" else "English"

        result = IntegrationCrew().crew().kickoff(inputs={
            "campaign_name": s.campaign_name,
            "audience_profile": s.audience_profile,
            "selected_creative": s.brand_creatives,
            "channel_plan": s.channel_plan,
            "locale_instruction": locale_instruction,
        })
        s.integrated_strategy = _crew_text(result)
        return s.integrated_strategy

    @router(integration_step)
    def after_integration(self):
        feedback = (self.last_human_feedback.feedback or "") if self.last_human_feedback else ""
        if _is_confirm(feedback):
            return "content"
        return "integration"

    # ─── Content: 文案产出 ───────────────────────────────────────

    @listen("content")
    @human_feedback(message="(user reviews)", provider=PROVIDER)
    def content_step(self):
        """文案专家产出营销文案"""
        s = self.state
        s.current_phase = "content"
        locale_instruction = "Chinese (中文)" if s.locale == "zh" else "English"

        result = ContentCrew().crew().kickoff(inputs={
            "campaign_name": s.campaign_name,
            "integrated_strategy": s.integrated_strategy,
            "selected_creative": s.brand_creatives,
            "locale_instruction": locale_instruction,
        })
        s.copywriting = _crew_text(result)
        return s.copywriting

    @router(content_step)
    def after_content(self):
        feedback = (self.last_human_feedback.feedback or "") if self.last_human_feedback else ""
        if _is_confirm(feedback):
            return "finalize"
        return "content"

    # ─── Finalize ────────────────────────────────────────────────

    @listen("finalize")
    @human_feedback(message="(user reviews final plan)", provider=PROVIDER)
    def finalize_step(self):
        """方案定稿阶段 — Flow 暂停，等待用户生成完整方案或结束"""
        self.state.current_phase = "finalize"
        return "All modules complete. Ready to generate full plan."

    @router(finalize_step)
    def after_finalize(self):
        feedback = (self.last_human_feedback.feedback or "") if self.last_human_feedback else ""
        if _is_confirm(feedback) or "generate" in feedback.lower():
            return "generate_document"
        if "revise" in feedback.lower() or "iteration_feedback" in feedback:
            return "revise_document"
        return "finalize"

    @listen("generate_document")
    @human_feedback(message="(user reviews document)", provider=PROVIDER)
    def generate_document_step(self):
        """生成完整方案文档"""
        s = self.state
        locale_instruction = "Chinese (中文)" if s.locale == "zh" else "English"

        all_content = f"""Campaign: {s.campaign_name}
=== AUDIENCE ===
{s.audience_profile}
=== BRAND CREATIVE ===
{s.brand_creatives}
=== CHANNEL STRATEGY ===
{s.channel_plan}
=== INTEGRATED STRATEGY ===
{s.integrated_strategy}
=== MARKETING COPY ===
{s.copywriting}"""

        result = IntegrationCrew().crew().kickoff(inputs={
            "campaign_name": s.campaign_name,
            "audience_profile": all_content,
            "selected_creative": "",
            "channel_plan": "",
            "locale_instruction": locale_instruction + "\n\nYOUR TASK: Generate a COMPLETE marketing campaign plan document with all chapters.",
        })
        s.integrated_strategy = _crew_text(result)
        return s.integrated_strategy

    @router(generate_document_step)
    def after_generate_document(self):
        feedback = (self.last_human_feedback.feedback or "") if self.last_human_feedback else ""
        if "revise" in feedback.lower() or "|feedback=" in feedback:
            return "revise_document"
        if _is_confirm(feedback):
            return "done"
        return "generate_document"

    @listen("revise_document")
    @human_feedback(message="(user reviews revised document)", provider=PROVIDER)
    def revise_document_step(self):
        """修改方案文档"""
        s = self.state
        locale_instruction = "Chinese (中文)" if s.locale == "zh" else "English"

        # Extract feedback from the human feedback
        revision_feedback = ""
        if self.last_human_feedback:
            raw = self.last_human_feedback.feedback or ""
            if "|feedback=" in raw:
                revision_feedback = raw.split("|feedback=", 1)[1]
            else:
                revision_feedback = raw

        result = IntegrationCrew().crew().kickoff(inputs={
            "campaign_name": s.campaign_name,
            "audience_profile": s.integrated_strategy,
            "selected_creative": "",
            "channel_plan": "",
            "locale_instruction": locale_instruction + f'\n\nRevise the document based on this feedback: "{revision_feedback}"',
        })
        s.integrated_strategy = _crew_text(result)
        return s.integrated_strategy

    @router(revise_document_step)
    def after_revise_document(self):
        feedback = (self.last_human_feedback.feedback or "") if self.last_human_feedback else ""
        if "revise" in feedback.lower() or "|feedback=" in feedback:
            return "revise_document"
        if _is_confirm(feedback):
            return "done"
        return "generate_document"

    @listen("done")
    def done_step(self):
        """Flow 结束"""
        self.state.finished = True
        return "Done."


# ─── Helpers ─────────────────────────────────────────────────────

def bind_collapse_llm():
    """Patch the real LLM into @human_feedback methods after init_llm()."""
    llm = get_collapse_llm()
    for name in ("discovery_step", "planning_step", "redo_brand_step", "redo_channel_step",
                 "integration_step", "content_step", "finalize_step",
                 "generate_document_step", "revise_document_step"):
        method = getattr(MarketingCampaignFlow, name, None)
        if method:
            setattr(method, "_hf_llm", llm)


def _crew_text(output) -> str:
    """Extract text from CrewOutput."""
    raw = getattr(output, "raw", None)
    return str(raw).strip() if raw else str(output).strip()


def _is_confirm(feedback: str) -> bool:
    """Check if feedback indicates confirmation."""
    lower = feedback.lower().strip()
    return any(k in lower for k in (
        "confirm", "确认", "action:confirm",
        "approve", "通过", "下一步", "next",
    ))
