import asyncio
import os
import re
import sys
import traceback

from botbuilder.core import MemoryStorage, TurnContext
from teams import Application, ApplicationOptions, TeamsAdapter
from teams.state import TurnState

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from browser.browser_agent import BrowserAgent
from config import Config

config = Config()

# Define storage and application
storage = MemoryStorage()
bot_app = Application[TurnState](
    ApplicationOptions(
        bot_app_id=config.APP_ID,
        storage=storage,
        adapter=TeamsAdapter(config),
    )
)


@bot_app.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, state: TurnState):
    await context.send_activity("How can I help you today?")


async def reset_session(context: TurnContext):
    session = context.has("session") and context.get("session")
    if session:
        session.session_state = []
    io = context.has("socket") and context.get("socket")
    if io:
        await io.emit("reset", {})


async def run_agent(context: TurnContext, query: str, activity_id: str):
    io = context.has("socket") and context.get("socket")
    if io:
        await io.emit("initializeGoal", query)

    browser_agent = BrowserAgent(context, activity_id)
    result = await browser_agent.run(query)
    return result


@bot_app.message(re.compile("operator: .*"))
async def on_operator(context: TurnContext, state: TurnState):
    query = context.activity.text.split("operator: ")[1]
    await reset_session(context)

    conversation_ref = TurnContext.get_conversation_reference(context.activity)

    # Send initial message and get activity ID
    initial_response = await context.send_activity(
        "Starting up the browser agent to do this work."
    )
    activity_id = initial_response.id

    async def background_task():
        result = await run_agent(context, query, activity_id)

        if isinstance(result, Exception):
            # If there was an error, send a new message instead of updating
            async def send_error(context: TurnContext):
                await context.send_activity(f"Error: {str(result)}")

            await context.adapter.continue_conversation(
                conversation_ref, send_error, config.APP_ID
            )

    asyncio.create_task(background_task())


@bot_app.error
async def on_error(context: TurnContext, error: Exception):
    # This check writes out errors to console log .vs. app insights.
    # NOTE: In production environment, you should consider logging this to Azure
    #       application insights.
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send a message to the user
    await context.send_activity("The bot encountered an error or bug.")
