import logging
from inspect import isawaitable
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union
from urllib.parse import parse_qs

import socketio
from aiohttp import web
from botbuilder.core import TurnContext
from botbuilder.core.middleware_set import Middleware
from botbuilder.schema import ConversationReference
from teams import TeamsAdapter

logger = logging.getLogger(__name__)

ConnectionCallback = Callable[[str, socketio.AsyncServer], Union[None, Awaitable[None]]]
WebSyncCallback = Callable[[str, Optional[TurnContext], Any], None]


class ScopedSocket:
    def __init__(self, io: socketio.AsyncServer, sid: str):
        self.io = io
        self.sid = sid

    async def emit(self, event: str, data: Any):
        await self.io.emit(event, data, to=self.sid)


class SocketMiddleware(Middleware):
    def __init__(
        self,
        io: socketio.AsyncServer,
        user_conversation_ref: Dict[str, ConversationReference],
        user_sid: Dict[str, str],
    ):
        self.io = io
        self.user_conversation_ref = user_conversation_ref
        self.user_sid = user_sid

    async def on_turn(self, context: TurnContext, logic: Callable[[], Awaitable]):
        conversation_ref = TurnContext.get_conversation_reference(context.activity)
        user_aad_id = conversation_ref.user.aad_object_id

        if user_aad_id:
            self.user_conversation_ref[user_aad_id] = conversation_ref
            sid = self.user_sid.get(user_aad_id)
            if sid:
                session = await self.io.get_session(sid)
                if session:
                    context.set("socket", ScopedSocket(self.io, sid))
                else:
                    logger.debug("No active session!!!!! %s", self.io.get_session(sid))
            else:
                logger.debug("No sid")

        await logic()


class BotWebSync:
    def __init__(self):
        self.callbacks: Dict[str, List[WebSyncCallback]] = {}
        self.connection_callbacks: List[ConnectionCallback] = []
        self.io: Optional[socketio.AsyncServer] = None
        self.user_conversation_ref: Dict[str, ConversationReference] = {}
        self.user_sid: Dict[str, str] = {}

    async def listen(
        self, app: web.Application, adapter: TeamsAdapter, opts: Dict[str, Any] = None
    ) -> socketio.AsyncServer:
        self.io = socketio.AsyncServer(
            async_mode="aiohttp",
            cors_allowed_origins="*",  # For development. In production, specify exact origins
            **opts or {},
        )
        self.io.attach(app)

        adapter.use(
            SocketMiddleware(self.io, self.user_conversation_ref, self.user_sid)
        )

        @self.io.event
        async def connect(sid, environ, auth):
            # Parse query string to get userAadId
            query = environ.get("QUERY_STRING", "")
            params = parse_qs(query)
            user_aad_id = params.get("userAadId", [None])[0]

            if user_aad_id:
                await self.io.enter_room(sid, user_aad_id)
                self.user_sid[user_aad_id] = sid
                await self.io.save_session(sid, {"user_aad_id": user_aad_id})
                logger.info("User connected: %s", user_aad_id)

                for callback in self.connection_callbacks:
                    result = callback(user_aad_id, self.io)
                    if isawaitable(result):
                        await result
            else:
                return False  # Reject connection if no userAadId

        @self.io.event
        async def disconnect(sid):
            user_aad_id = self.user_sid.get(sid)
            if user_aad_id:
                await self.io.leave_room(sid, user_aad_id)
                del self.user_sid[user_aad_id]
                logger.info("User disconnected: %s", user_aad_id)

        # Register all event handlers
        for event, callbacks in self.callbacks.items():

            @self.io.event(event)
            async def event_handler(sid, data, event=event):
                try:
                    session = await self.io.get_session(sid)
                    user_aad_id = session.get("user_aad_id") if session else None

                    if user_aad_id:
                        conversation_ref = self.user_conversation_ref.get(user_aad_id)

                        if conversation_ref:

                            async def process_callbacks(context: TurnContext):
                                for callback in self.callbacks[event]:
                                    await callback(user_aad_id, context, data)

                            await adapter.continue_conversation(
                                conversation_ref, process_callbacks
                            )
                        else:
                            for callback in self.callbacks[event]:
                                await callback(user_aad_id, None, data)
                except KeyError:
                    logger.debug("Session not found for sid: %s", sid)
                    return

        return self.io

    def on(self, event: str, callback: Union[ConnectionCallback, WebSyncCallback]):
        if event == "connection":
            self.connection_callbacks.append(callback)
        else:
            if event not in self.callbacks:
                self.callbacks[event] = []
            self.callbacks[event].append(callback)
