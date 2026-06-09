from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from agents._lib.llm import get_llm


@CrewBase
class BrandCreativeCrew:
    """品牌创意 Crew — 产出 2-3 套创意方案。"""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "../agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def brand_creative_director(self) -> Agent:
        return Agent(
            config=self.agents_config["brand_creative_director"],
            llm=get_llm(),
            memory=False,
        )

    @task
    def creative_concepts_task(self) -> Task:
        return Task(
            config=self.tasks_config["creative_concepts_task"],
            agent=self.brand_creative_director(),
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
