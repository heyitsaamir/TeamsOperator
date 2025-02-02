"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import os
from http import HTTPStatus
from typing import Awaitable, Callable

import socketio
from aiohttp import web
from botbuilder.core import TurnContext
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.core.middleware_set import Middleware

from bot import bot_app
from bot_web_sync import BotWebSync
from storage.in_memory_session_storage import InMemorySessionStorage

routes = web.RouteTableDef()
web_sync = BotWebSync()
session_storage = InMemorySessionStorage()

# Get the absolute path to the static directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
print(f"Static directory path: {STATIC_DIR}")
print(f"Directory exists: {os.path.exists(STATIC_DIR)}")
print(
    f"Directory contents: {os.listdir(STATIC_DIR) if os.path.exists(STATIC_DIR) else 'Directory not found'}"
)


@routes.post("/api/messages")
async def on_messages(req: web.Request) -> web.Response:
    res = await bot_app.process(req)

    if res is not None:
        return res

    return web.Response(status=HTTPStatus.OK)


# Add a route for the root path to serve index.html
@routes.get("/")
async def serve_index(request):
    index_path = os.path.join(STATIC_DIR, "index.html")
    print(f"Trying to serve index from: {index_path}")
    print(f"Index file exists: {os.path.exists(index_path)}")

    if not os.path.exists(index_path):
        return web.Response(text="Index file not found", status=404)

    try:
        with open(index_path, "r") as f:
            content = f.read()
        return web.Response(text=content, content_type="text/html")
    except Exception as e:
        print(f"Error reading file: {e}")
        return web.Response(text="Error reading index file", status=500)


@routes.get("/debug")
async def debug(request):
    return web.Response(text="Debug route working")


# Create the application with static file handling
app = web.Application(middlewares=[aiohttp_error_middleware])
app.router.add_static("/static/", path=STATIC_DIR, name="static", show_index=True)

# Add routes after app creation
app.add_routes(routes)


async def on_socket_connection(user_id: str, socket: socketio.AsyncServer):
    print("connection", user_id)
    session = session_storage.get_or_create_session(user_id)

    # Convert session state to message format expected by frontend
    messages = []
    if hasattr(session, "session_state"):
        messages = [
            {
                "screenshot": state.screenshot,
                "action": state.action,
                "memory": state.memory,
                "next_goal": state.next_goal,
                "actions": state.actions,
            }
            for state in session.session_state
        ]

    await socket.emit("initializeState", {"messages": messages})


async def on_socket_message(user_id: str, context: TurnContext, message: str):
    session = session_storage.get_session(user_id)
    if session:
        print(f"Message from {user_id}: {message}")
        print(f"Current session state: {session.session_state}")


class BuildStateMiddleware(Middleware):
    async def on_turn(self, context: TurnContext, logic: Callable[[], Awaitable]):
        conversation_ref = TurnContext.get_conversation_reference(context.activity)
        user_aad_id = conversation_ref.user.aad_object_id
        if user_aad_id:
            session = session_storage.get_or_create_session(user_aad_id)
            context.set("session", session)

        await logic()


bot_app._adapter.use(BuildStateMiddleware())

from config import Config


async def start_websocket(app: web.Application):
    await web_sync.listen(app, bot_app._adapter)
    web_sync.on("connection", on_socket_connection)
    web_sync.on("message", on_socket_message)


app.on_startup.append(start_websocket)

if __name__ == "__main__":
    web.run_app(app, host="localhost", port=Config.PORT)
