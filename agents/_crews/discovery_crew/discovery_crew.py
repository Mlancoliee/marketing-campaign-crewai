from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from agents._lib.llm import get_llm


@CrewBase
class DiscoveryCrew:
    """市场调研 Crew — 市场分析师向用户提问收集信息。

    单 Agent Crew：PM 每轮决定继续提问还是输出 [READY] 进入下一阶段。
    """

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "../agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def market_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["market_analyst"],
            llm=get_llm(),
            memory=False,
        )

    @task
    def interview_task(self) -> Task:
        return Task(
            config=self.tasks_config["interview_task"],
            agent=self.market_analyst(),
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
