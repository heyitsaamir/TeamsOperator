import asyncio
import logging
import os
from typing import Optional

from botbuilder.core import TurnContext
from browser_use import Agent, Browser, BrowserConfig
from browser_use.agent.views import AgentOutput
from browser_use.browser.context import BrowserContext
from browser_use.browser.views import BrowserState
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from browser.session import SessionStepState


class BrowserAgent:
    def __init__(self, context: TurnContext):
        self.context = context
        self.browser = Browser(
            config=BrowserConfig(
                chrome_instance_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            )
        )
        self.browser_context = BrowserContext(browser=self.browser)
        self.llm = self._setup_llm()

    @staticmethod
    def _setup_llm():
        if azure_endpoint := os.environ.get("AZURE_OPENAI_API_BASE", None):
            return AzureChatOpenAI(
                azure_endpoint=azure_endpoint,
                azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
                openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
                model_name=os.environ[
                    "AZURE_OPENAI_DEPLOYMENT"
                ],  # BrowserUse has a bug where this model_name is required
            )
        return ChatOpenAI(model=os.environ["OPENAI_MODEL_NAME"])

    async def _handle_screenshot_and_emit(
        self, step: SessionStepState, io: Optional[object]
    ) -> None:
        screenshot_new = await self.browser_context.take_screenshot()
        step.screenshot = screenshot_new

        if session := self.context.get("session"):
            session.session_state.append(step)

            if io:
                await io.emit(
                    "message",
                    {
                        "screenshot": step.screenshot,
                        "action": step.action,
                        "memory": step.memory,
                        "next_goal": step.next_goal,
                        "actions": step.actions,
                    },
                )

    def step_callback(
        self, state: BrowserState, output: AgentOutput, step_number: int
    ) -> None:
        io = self.context.get("socket")
        if not io:
            logging.warning("Socket not available for real-time updates")

        if session := self.context.get("session"):
            actions = (
                [action.model_dump_json(exclude_unset=True) for action in output.action]
                if output.action
                else []
            )

            step = SessionStepState(
                screenshot=None,
                action=output.current_state.evaluation_previous_goal,
                memory=output.current_state.memory,
                next_goal=output.current_state.next_goal,
                actions=actions,
            )

            asyncio.create_task(self._handle_screenshot_and_emit(step, io))
        else:
            logging.warning("Session not available to store step state")

    async def run(self, query: str) -> str:
        agent = Agent(
            task=query,
            llm=self.llm,
            register_new_step_callback=self.step_callback,
            browser_context=self.browser_context,
            generate_gif=False,
            message_context="For Trello, navigate to 'https://trello.com/b/4YEoaDa4/mvp'",
        )

        try:
            result = await agent.run()
            asyncio.create_task(self.browser_context.close())

            action_results = result.action_results()
            if action_results and (last_result := action_results[-1]):
                return last_result.extracted_content
            return "No results found"

        except Exception as e:
            return f"Error during browser agent execution: {str(e)}"
