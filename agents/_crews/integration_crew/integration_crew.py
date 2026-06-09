from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from agents._lib.llm import get_llm


@CrewBase
class IntegrationCrew:
    """策略整合 Crew — 策略总监将品牌+渠道整合为统一方案。"""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "../agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def chief_strategist(self) -> Agent:
        return Agent(
            config=self.agents_config["chief_strategist"],
            llm=get_llm(),
            memory=False,
        )

    @task
    def integrate_task(self) -> Task:
        return Task(
            config=self.tasks_config["integrate_task"],
            agent=self.chief_strategist(),
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
