import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from botbuilder.core import TurnContext
from browser_use import Agent, Browser
from browser_use.agent.views import AgentOutput
from browser_use.browser.context import BrowserContext
from browser_use.browser.views import BrowserState
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from browser.session import SessionStepState

llm = (
    AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_API_BASE"],
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        model_name=os.environ[
            "AZURE_OPENAI_DEPLOYMENT"
        ],  # BrowserUse has a bug where this model_name is required
    )
    if os.environ["AZURE_OPENAI_API_BASE"]
    else ChatOpenAI(model=os.environ["OPENAI_MODEL_NAME"])
)


async def run_browser_agent(query: str, context: TurnContext):
    browser = Browser()
    browser_context = BrowserContext(browser=browser)

    async def handle_screenshot_and_emit(step: SessionStepState, io):
        screenshot_new = await browser_context.take_screenshot()
        step.screenshot = screenshot_new

        session = context.has("session") and context.get("session")
        if session:
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
        else:
            print("No session")

    def step_callback(state: BrowserState, output: AgentOutput, step_number: int):
        session = context.has("session") and context.get("session")
        io = context.has("socket") and context.get("socket")
        if session:
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

            # Fire and forget the screenshot capture and session update
            asyncio.create_task(handle_screenshot_and_emit(step, io))
        else:
            print("No session")

    agent = Agent(
        task=query,
        llm=llm,
        register_new_step_callback=step_callback,
        browser_context=browser_context,
        generate_gif=False,
    )
    try:
        result = await agent.run()
        print(result)
        browser.close()
        return result
    except Exception as e:
        print(e)
        return "Ran into an error"
