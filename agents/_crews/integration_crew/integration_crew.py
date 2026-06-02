import yaml
from pathlib import Path
from crewai import Agent, Crew, Task, Process

from agents._lib.llm import get_streaming_llm


_AGENTS_YAML = Path(__file__).parent.parent / "agents.yaml"
_TASKS_YAML = Path(__file__).parent / "config" / "tasks.yaml"


class IntegrationCrew:
    """策略整合 Crew - 策略总监整合品牌+渠道为统一方案"""

    def __init__(self):
        with open(_AGENTS_YAML, "r") as f:
            self.agents_config = yaml.safe_load(f)
        with open(_TASKS_YAML, "r") as f:
            self.tasks_config = yaml.safe_load(f)

    def crew(self, inputs: dict) -> Crew:
        llm = get_streaming_llm()

        chief_strategist = Agent(
            role=self.agents_config["chief_strategist"]["role"].strip(),
            goal=self.agents_config["chief_strategist"]["goal"].strip(),
            backstory=self.agents_config["chief_strategist"]["backstory"].strip(),
            llm=llm,
            verbose=False,
        )

        task_config = self.tasks_config["integrate_task"]
        integrate_task = Task(
            description=task_config["description"].format(**inputs),
            expected_output=task_config["expected_output"],
            agent=chief_strategist,
        )

        return Crew(
            agents=[chief_strategist],
            tasks=[integrate_task],
            process=Process.sequential,
            verbose=False,
        )
