import os
import re
import sys
import traceback

from botbuilder.core import MemoryStorage, TurnContext
from teams import Application, ApplicationOptions, TeamsAdapter
from teams.state import TurnState

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from browser.browser_agent import run_browser_agent
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

@bot_app.message(re.compile("search: .*"))
async def on_search(context: TurnContext, state: TurnState):
    await context.send_activity(f"You said: {context.activity.text}")
    query = context.activity.text.split("search: ")[1]
    result = await run_browser_agent(query, context)
    conversation_ref = TurnContext.get_conversation_reference(context.activity)
    async def send_result(context: TurnContext):
        action_results = result.action_results()
        last_result = action_results[-1] if action_results else None
        if last_result:
            await context.send_activity(last_result.extracted_content)
    await context.adapter.continue_conversation(conversation_ref, send_result, config.APP_ID)

@bot_app.error
async def on_error(context: TurnContext, error: Exception):
    # This check writes out errors to console log .vs. app insights.
    # NOTE: In production environment, you should consider logging this to Azure
    #       application insights.
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send a message to the user
    await context.send_activity("The bot encountered an error or bug.")