"""
MarketingCampaignFlow - 营销活动策划 Flow

阶段: Discovery → Parallel Planning → Integration → Content → Delivery → Open Iteration
"""
import asyncio
from crewai.flow.flow import Flow, start, listen, router, or_
from pydantic import BaseModel

from agents._lib.state import CampaignState
from agents._lib.feedback_provider import HumanFeedbackPending
from agents._lib.logger import make_logger
from agents._crews.discovery_crew import DiscoveryCrew
from agents._crews.brand_creative_crew import BrandCreativeCrew
from agents._crews.channel_planning_crew import ChannelPlanningCrew
from agents._crews.integration_crew import IntegrationCrew
from agents._crews.content_crew import ContentCrew

log = make_logger("Flow")

MAX_DISCOVERY_ROUNDS = 4


class MarketingCampaignFlow(Flow[CampaignState]):
    """营销活动策划多阶段 Flow"""

    # ─── Discovery ───────────────────────────────────────────────

    @start()
    async def discovery_step(self):
        log("Discovery phase started")
        self.state.current_phase = "discovery"
        self.state.discovery_rounds += 1

        locale_instruction = "Chinese (中文)" if self.state.locale == "zh" else "English"

        crew = DiscoveryCrew().crew(inputs={
            "campaign_brief": self.state.campaign_brief,
            "qa_history": self._format_qa_history(),
            "discovery_rounds": str(self.state.discovery_rounds),
            "locale_instruction": locale_instruction,
        })
        result = await crew.kickoff_async()
        output = str(result)

        # 存入 chat_history
        self.state.chat_history.append({
            "role": "market_analyst",
            "content": output,
            "phase": "discovery",
        })

        return output

    @router(discovery_step)
    def after_discovery(self, result: str):
        if "[READY]" in result:
            # 解析 audience_profile 和 market_insights
            content = result.split("[READY]", 1)[1].strip()
            self.state.audience_profile = content
            self.state.market_insights = content
            return "planning"
        elif self.state.discovery_rounds >= MAX_DISCOVERY_ROUNDS:
            # 强制进入下一阶段，用当前产出作为分析结果
            self.state.audience_profile = result
            self.state.market_insights = result
            return "planning"
        else:
            return "wait_answer"

    @listen("wait_answer")
    async def wait_for_answer(self):
        """暂停等待用户回答"""
        raise HumanFeedbackPending(context={
            "phase": "discovery",
            "round": self.state.discovery_rounds,
        })

    # ─── Parallel Planning ───────────────────────────────────────

    @listen("planning")
    async def parallel_planning_step(self):
        log("Parallel Planning phase started")
        self.state.current_phase = "planning"

        locale_instruction = "Chinese (中文)" if self.state.locale == "zh" else "English"
        inputs = {
            "campaign_name": self.state.campaign_name,
            "campaign_brief": self.state.campaign_brief,
            "audience_profile": self.state.audience_profile,
            "market_insights": self.state.market_insights,
            "locale_instruction": locale_instruction,
        }

        # 并行执行品牌创意和渠道策划
        brand_crew = BrandCreativeCrew().crew(inputs=inputs)
        channel_crew = ChannelPlanningCrew().crew(inputs=inputs)

        brand_result, channel_result = await asyncio.gather(
            brand_crew.kickoff_async(),
            channel_crew.kickoff_async(),
        )

        self.state.brand_creatives = [{"raw": str(brand_result)}]
        self.state.channel_plan = {"raw": str(channel_result)}

        # 存入 chat_history
        self.state.chat_history.append({
            "role": "brand_creative_director",
            "content": str(brand_result),
            "phase": "planning",
        })
        self.state.chat_history.append({
            "role": "channel_planner",
            "content": str(channel_result),
            "phase": "planning",
        })

        # 暂停等待用户操作（选创意/确认渠道）
        raise HumanFeedbackPending(context={
            "phase": "planning",
            "brand_creatives": self.state.brand_creatives,
            "channel_plan": self.state.channel_plan,
        })

    # ─── Redo 单条线 ─────────────────────────────────────────────

    @listen("redo_brand")
    async def redo_brand_step(self):
        log("Redo brand creative")
        locale_instruction = "Chinese (中文)" if self.state.locale == "zh" else "English"
        inputs = {
            "campaign_name": self.state.campaign_name,
            "campaign_brief": self.state.campaign_brief + "\n\nFeedback: " + self.state.latest_feedback,
            "audience_profile": self.state.audience_profile,
            "market_insights": self.state.market_insights,
            "locale_instruction": locale_instruction,
        }
        crew = BrandCreativeCrew().crew(inputs=inputs)
        result = await crew.kickoff_async()
        self.state.brand_creatives = [{"raw": str(result)}]
        self.state.brand_confirmed = False

        raise HumanFeedbackPending(context={
            "phase": "planning",
            "brand_creatives": self.state.brand_creatives,
            "channel_plan": self.state.channel_plan,
        })

    @listen("redo_channel")
    async def redo_channel_step(self):
        log("Redo channel planning")
        locale_instruction = "Chinese (中文)" if self.state.locale == "zh" else "English"
        inputs = {
            "campaign_name": self.state.campaign_name,
            "campaign_brief": self.state.campaign_brief + "\n\nFeedback: " + self.state.latest_feedback,
            "audience_profile": self.state.audience_profile,
            "market_insights": self.state.market_insights,
            "locale_instruction": locale_instruction,
        }
        crew = ChannelPlanningCrew().crew(inputs=inputs)
        result = await crew.kickoff_async()
        self.state.channel_plan = {"raw": str(result)}
        self.state.channel_confirmed = False

        raise HumanFeedbackPending(context={
            "phase": "planning",
            "brand_creatives": self.state.brand_creatives,
            "channel_plan": self.state.channel_plan,
        })

    # ─── Integration ─────────────────────────────────────────────

    @listen("integration")
    async def integration_step(self):
        log("Integration phase started")
        self.state.current_phase = "integration"

        locale_instruction = "Chinese (中文)" if self.state.locale == "zh" else "English"
        selected = self.state.brand_creatives[self.state.selected_creative_index] \
            if 0 <= self.state.selected_creative_index < len(self.state.brand_creatives) \
            else self.state.brand_creatives[0] if self.state.brand_creatives else {}

        crew = IntegrationCrew().crew(inputs={
            "campaign_name": self.state.campaign_name,
            "audience_profile": self.state.audience_profile,
            "selected_creative": str(selected),
            "channel_plan": str(self.state.channel_plan),
            "locale_instruction": locale_instruction,
        })
        result = await crew.kickoff_async()
        self.state.integrated_strategy = str(result)

        self.state.chat_history.append({
            "role": "chief_strategist",
            "content": self.state.integrated_strategy,
            "phase": "integration",
        })

        raise HumanFeedbackPending(context={
            "phase": "integration",
            "integrated_strategy": self.state.integrated_strategy,
        })

    # ─── Content ─────────────────────────────────────────────────

    @listen("content")
    async def content_step(self):
        log("Content phase started")
        self.state.current_phase = "content"

        locale_instruction = "Chinese (中文)" if self.state.locale == "zh" else "English"
        selected = self.state.brand_creatives[self.state.selected_creative_index] \
            if 0 <= self.state.selected_creative_index < len(self.state.brand_creatives) \
            else self.state.brand_creatives[0] if self.state.brand_creatives else {}

        crew = ContentCrew().crew(inputs={
            "campaign_name": self.state.campaign_name,
            "integrated_strategy": self.state.integrated_strategy,
            "selected_creative": str(selected),
            "locale_instruction": locale_instruction,
        })
        result = await crew.kickoff_async()
        self.state.copywriting = {"raw": str(result)}

        self.state.chat_history.append({
            "role": "copywriter",
            "content": str(result),
            "phase": "content",
        })

        raise HumanFeedbackPending(context={
            "phase": "content",
            "copywriting": self.state.copywriting,
        })

    # ─── Delivery ────────────────────────────────────────────────

    @listen("delivery")
    async def delivery_step(self):
        log("Delivery phase")
        self.state.current_phase = "delivery"
        raise HumanFeedbackPending(context={"phase": "delivery"})

    # ─── Open Iteration ──────────────────────────────────────────

    @listen("iteration")
    async def open_iteration_step(self):
        log(f"Open iteration #{self.state.iteration_count}")
        self.state.current_phase = "iteration"
        self.state.iteration_count += 1

        locale_instruction = "Chinese (中文)" if self.state.locale == "zh" else "English"
        target = self.state.iteration_target

        if target == "brand_creative":
            crew = BrandCreativeCrew().crew(inputs={
                "campaign_name": self.state.campaign_name,
                "campaign_brief": self.state.campaign_brief + "\n\nRevision feedback: " + self.state.latest_feedback,
                "audience_profile": self.state.audience_profile,
                "market_insights": self.state.market_insights,
                "locale_instruction": locale_instruction,
            })
            result = await crew.kickoff_async()
            self.state.brand_creatives = [{"raw": str(result)}]
        elif target == "channel_plan":
            crew = ChannelPlanningCrew().crew(inputs={
                "campaign_name": self.state.campaign_name,
                "campaign_brief": self.state.campaign_brief + "\n\nRevision feedback: " + self.state.latest_feedback,
                "audience_profile": self.state.audience_profile,
                "market_insights": self.state.market_insights,
                "locale_instruction": locale_instruction,
            })
            result = await crew.kickoff_async()
            self.state.channel_plan = {"raw": str(result)}
        elif target == "copywriting":
            selected = self.state.brand_creatives[self.state.selected_creative_index] \
                if 0 <= self.state.selected_creative_index < len(self.state.brand_creatives) \
                else self.state.brand_creatives[0] if self.state.brand_creatives else {}
            crew = ContentCrew().crew(inputs={
                "campaign_name": self.state.campaign_name,
                "integrated_strategy": self.state.integrated_strategy + "\n\nRevision feedback: " + self.state.latest_feedback,
                "selected_creative": str(selected),
                "locale_instruction": locale_instruction,
            })
            result = await crew.kickoff_async()
            self.state.copywriting = {"raw": str(result)}
        else:
            # 默认交给策略总监重新整合
            selected = self.state.brand_creatives[self.state.selected_creative_index] \
                if 0 <= self.state.selected_creative_index < len(self.state.brand_creatives) \
                else self.state.brand_creatives[0] if self.state.brand_creatives else {}
            crew = IntegrationCrew().crew(inputs={
                "campaign_name": self.state.campaign_name,
                "audience_profile": self.state.audience_profile,
                "selected_creative": str(selected),
                "channel_plan": str(self.state.channel_plan),
                "locale_instruction": locale_instruction + "\n\nRevision feedback: " + self.state.latest_feedback,
            })
            result = await crew.kickoff_async()
            self.state.integrated_strategy = str(result)

        raise HumanFeedbackPending(context={
            "phase": "iteration",
            "target": target,
        })

    # ─── Finalize ────────────────────────────────────────────────

    @listen("finalize")
    async def finalize_step(self):
        log("Flow finalized")
        self.state.finished = True
        self.state.current_phase = "done"
        return {
            "audience_profile": self.state.audience_profile,
            "brand_creatives": self.state.brand_creatives,
            "channel_plan": self.state.channel_plan,
            "integrated_strategy": self.state.integrated_strategy,
            "copywriting": self.state.copywriting,
        }

    # ─── Helpers ─────────────────────────────────────────────────

    def _format_qa_history(self) -> str:
        if not self.state.qa_history:
            return "(No previous Q&A)"
        lines = []
        for qa in self.state.qa_history:
            lines.append(f"Q: {qa.get('question', '')}")
            lines.append(f"A: {qa.get('answer', '')}")
        return "\n".join(lines)
