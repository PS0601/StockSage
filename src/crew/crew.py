# SPDX-License-Identifier: MIT
"""CrewAI crew for stock analysis using YAML-based agent and task definitions."""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from src.core.config.config import CREW_VERBOSE
from src.core.config.llm import get_llm
from src.crew.schemas import (
    FinalReportOutput,
    FinancialHealthOutput,
    PerformanceOutput,
    ReviewOutput,
    SentimentOutput,
    ValuationOutput,
)
from src.crew.tools.calculator import FinancialCalculatorTool
from src.crew.tools.csv_reader import CSVReaderTool
from src.crew.tools.search import create_search_tool


@CrewBase
class StockAnalysisCrew:
    """Stock analysis crew — 6 agents, 6 tasks, sequential execution. Data sanity is computed in sanity.py."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self):
        self.csv_reader = CSVReaderTool()
        self.calculator = FinancialCalculatorTool()
        self.search_tool = create_search_tool()
        self.llm = get_llm()

    # ── Agents ──────────────────────────────────────────────

    @agent
    def ratio_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["ratio_analyst"],
            tools=[self.csv_reader, self.calculator],
            llm=self.llm,
            verbose=CREW_VERBOSE,
        )

    @agent
    def performance_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["performance_analyst"],
            tools=[self.csv_reader, self.calculator],
            llm=self.llm,
            verbose=CREW_VERBOSE,
        )

    @agent
    def fundamental_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["fundamental_analyst"],
            tools=[self.csv_reader, self.calculator],
            llm=self.llm,
            verbose=CREW_VERBOSE,
        )

    @agent
    def sentiment_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["sentiment_analyst"],
            tools=[self.csv_reader, self.search_tool],
            llm=self.llm,
            verbose=CREW_VERBOSE,
        )

    @agent
    def market_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["market_reviewer"],
            tools=[self.csv_reader],
            llm=self.llm,
            verbose=CREW_VERBOSE,
        )

    @agent
    def investment_advisor(self) -> Agent:
        return Agent(
            config=self.agents_config["investment_advisor"],
            tools=[],
            llm=self.llm,
            verbose=CREW_VERBOSE,
        )

    # ── Tasks ───────────────────────────────────────────────

    @task
    def analyze_valuation_ratios(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_valuation_ratios"],
            output_pydantic=ValuationOutput,
        )

    @task
    def analyze_price_performance(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_price_performance"],
            output_pydantic=PerformanceOutput,
        )

    @task
    def analyze_financial_health(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_financial_health"],
            output_pydantic=FinancialHealthOutput,
        )

    @task
    def analyze_market_sentiment(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_market_sentiment"],
            output_pydantic=SentimentOutput,
        )

    @task
    def review_analysis(self) -> Task:
        return Task(
            config=self.tasks_config["review_analysis"],
            output_pydantic=ReviewOutput,
        )

    @task
    def generate_investment_report(self) -> Task:
        return Task(
            config=self.tasks_config["generate_investment_report"],
            output_pydantic=FinalReportOutput,
        )

    # ── Crew ────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=CREW_VERBOSE,
        )
