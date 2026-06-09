from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from agents._lib.llm import get_llm


@CrewBase
class ChannelPlanningCrew:
    """渠道策划 Crew — 设计渠道组合、时间线与预算分配。"""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "../agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def channel_planner(self) -> Agent:
        return Agent(
            config=self.agents_config["channel_planner"],
            llm=get_llm(),
            memory=False,
        )

    @task
    def channel_strategy_task(self) -> Task:
        return Task(
            config=self.tasks_config["channel_strategy_task"],
            agent=self.channel_planner(),
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
