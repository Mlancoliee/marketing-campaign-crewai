import yaml
from pathlib import Path
from crewai import Agent, Crew, Task, Process

from agents._lib.llm import get_streaming_llm


_AGENTS_YAML = Path(__file__).parent.parent / "agents.yaml"
_TASKS_YAML = Path(__file__).parent / "config" / "tasks.yaml"


class ChannelPlanningCrew:
    """渠道策划 Crew - 产出渠道组合+排期+预算"""

    def __init__(self):
        with open(_AGENTS_YAML, "r") as f:
            self.agents_config = yaml.safe_load(f)
        with open(_TASKS_YAML, "r") as f:
            self.tasks_config = yaml.safe_load(f)

    def crew(self, inputs: dict) -> Crew:
        llm = get_streaming_llm()

        channel_planner = Agent(
            role=self.agents_config["channel_planner"]["role"].strip(),
            goal=self.agents_config["channel_planner"]["goal"].strip(),
            backstory=self.agents_config["channel_planner"]["backstory"].strip(),
            llm=llm,
            verbose=False,
        )

        task_config = self.tasks_config["channel_strategy_task"]
        channel_task = Task(
            description=task_config["description"].format(**inputs),
            expected_output=task_config["expected_output"],
            agent=channel_planner,
        )

        return Crew(
            agents=[channel_planner],
            tasks=[channel_task],
            process=Process.sequential,
            verbose=False,
        )
