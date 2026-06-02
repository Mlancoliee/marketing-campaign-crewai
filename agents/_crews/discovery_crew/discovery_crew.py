import yaml
from pathlib import Path
from crewai import Agent, Crew, Task, Process

from agents._lib.llm import get_streaming_llm


_AGENTS_YAML = Path(__file__).parent.parent / "agents.yaml"
_TASKS_YAML = Path(__file__).parent / "config" / "tasks.yaml"


class DiscoveryCrew:
    """市场调研 Crew - 市场分析师向用户提问收集信息"""

    def __init__(self):
        with open(_AGENTS_YAML, "r") as f:
            self.agents_config = yaml.safe_load(f)
        with open(_TASKS_YAML, "r") as f:
            self.tasks_config = yaml.safe_load(f)

    def crew(self, inputs: dict) -> Crew:
        llm = get_streaming_llm()

        market_analyst = Agent(
            role=self.agents_config["market_analyst"]["role"].strip(),
            goal=self.agents_config["market_analyst"]["goal"].strip(),
            backstory=self.agents_config["market_analyst"]["backstory"].strip(),
            llm=llm,
            verbose=False,
        )

        task_config = self.tasks_config["interview_task"]
        interview_task = Task(
            description=task_config["description"].format(**inputs),
            expected_output=task_config["expected_output"],
            agent=market_analyst,
        )

        return Crew(
            agents=[market_analyst],
            tasks=[interview_task],
            process=Process.sequential,
            verbose=False,
        )
