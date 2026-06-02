import yaml
from pathlib import Path
from crewai import Agent, Crew, Task, Process

from agents._lib.llm import get_streaming_llm


_AGENTS_YAML = Path(__file__).parent.parent / "agents.yaml"
_TASKS_YAML = Path(__file__).parent / "config" / "tasks.yaml"


class BrandCreativeCrew:
    """品牌创意 Crew - 产出 2-3 套创意方案"""

    def __init__(self):
        with open(_AGENTS_YAML, "r") as f:
            self.agents_config = yaml.safe_load(f)
        with open(_TASKS_YAML, "r") as f:
            self.tasks_config = yaml.safe_load(f)

    def crew(self, inputs: dict) -> Crew:
        llm = get_streaming_llm()

        brand_creative_director = Agent(
            role=self.agents_config["brand_creative_director"]["role"].strip(),
            goal=self.agents_config["brand_creative_director"]["goal"].strip(),
            backstory=self.agents_config["brand_creative_director"]["backstory"].strip(),
            llm=llm,
            verbose=False,
        )

        task_config = self.tasks_config["creative_concepts_task"]
        creative_task = Task(
            description=task_config["description"].format(**inputs),
            expected_output=task_config["expected_output"],
            agent=brand_creative_director,
        )

        return Crew(
            agents=[brand_creative_director],
            tasks=[creative_task],
            process=Process.sequential,
            verbose=False,
        )
