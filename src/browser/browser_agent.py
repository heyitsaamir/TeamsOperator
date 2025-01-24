import asyncio
import os

from botbuilder.core import TurnContext
from browser_use import Agent
from browser_use.agent.views import AgentOutput
from browser_use.browser.views import BrowserState
from langchain_openai import AzureChatOpenAI

llm = AzureChatOpenAI(azure_endpoint=os.environ["AZURE_OPENAI_API_BASE"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],)


async def run_browser_agent(query: str, context: TurnContext):           
    def step_callback(state: BrowserState, output: AgentOutput, step_number: int):
        session = context.has("session") and context.get("session")
        io = context.has("socket") and context.get("socket")
        if session:
            session.browser_state = state
        else:
            print("No session")
        if io:
            asyncio.create_task(io.emit("message", {
                "screenshot": state.screenshot,
                "action": output.current_state.evaluation_previous_goal
            }))
        else:
            print("No socket")
        print("Step callback", output)
        
    agent = Agent(
        task=query,
        llm=llm,
        register_new_step_callback=step_callback
    )
    try:
        result = await agent.run()
        print(result)
        return result
    except Exception as e:
        print(e)
        