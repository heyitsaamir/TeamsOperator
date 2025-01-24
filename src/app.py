"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
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


@routes.post("/api/messages")
async def on_messages(req: web.Request) -> web.Response:
    res = await bot_app.process(req)

    if res is not None:
        return res

    return web.Response(status=HTTPStatus.OK)

app = web.Application(middlewares=[aiohttp_error_middleware])
app.add_routes(routes)

async def on_socket_connection(user_id: str, socket: socketio.AsyncServer):
    session = session_storage.get_or_create_session(user_id)
    await socket.emit("initializeState", {
        "browser_state": session.browser_state.title if session.browser_state else None,
        "session_state": session.session_state.is_complete
    })

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
