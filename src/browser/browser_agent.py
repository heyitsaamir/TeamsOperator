import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from botbuilder.core import TurnContext
from browser_use import Agent
from browser_use.agent.views import AgentOutput
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
    def step_callback(state: BrowserState, output: AgentOutput, step_number: int):
        session = context.has("session") and context.get("session")
        io = context.has("socket") and context.get("socket")
        if session:
            # Extract planned actions
            actions = (
                [action.model_dump_json(exclude_unset=True) for action in output.action]
                if output.action
                else []
            )

            step = SessionStepState(
                screenshot=state.screenshot,
                action=output.current_state.evaluation_previous_goal,
                memory=output.current_state.memory,
                next_goal=output.current_state.next_goal,
                actions=actions,
            )

            session.session_state.append(step)
        else:
            print("No session")

        if io and step:
            asyncio.create_task(
                io.emit(
                    "message",
                    {
                        "screenshot": step.screenshot,
                        "action": step.action,
                        "memory": step.memory,
                        "next_goal": step.next_goal,
                        "actions": step.actions,
                    },
                )
            )
        else:
            print("No socket")

    agent = Agent(
        task=query,
        llm=llm,
        register_new_step_callback=step_callback,
    )
    try:
        result = await agent.run()
        print(result)
        return result
    except Exception as e:
        print(e)
        return "Ran into an error"
