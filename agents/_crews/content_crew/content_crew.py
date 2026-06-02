import yaml
from pathlib import Path
from crewai import Agent, Crew, Task, Process

from agents._lib.llm import get_streaming_llm


_AGENTS_YAML = Path(__file__).parent.parent / "agents.yaml"
_TASKS_YAML = Path(__file__).parent / "config" / "tasks.yaml"


class ContentCrew:
    """内容产出 Crew - 文案专家生成营销文案"""

    def __init__(self):
        with open(_AGENTS_YAML, "r") as f:
            self.agents_config = yaml.safe_load(f)
        with open(_TASKS_YAML, "r") as f:
            self.tasks_config = yaml.safe_load(f)

    def crew(self, inputs: dict) -> Crew:
        llm = get_streaming_llm()

        copywriter = Agent(
            role=self.agents_config["copywriter"]["role"].strip(),
            goal=self.agents_config["copywriter"]["goal"].strip(),
            backstory=self.agents_config["copywriter"]["backstory"].strip(),
            llm=llm,
            verbose=False,
        )

        task_config = self.tasks_config["copywriting_task"]
        copy_task = Task(
            description=task_config["description"].format(**inputs),
            expected_output=task_config["expected_output"],
            agent=copywriter,
        )

        return Crew(
            agents=[copywriter],
            tasks=[copy_task],
            process=Process.sequential,
            verbose=False,
        )
