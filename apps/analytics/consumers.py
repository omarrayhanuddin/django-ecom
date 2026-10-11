"""WebSocket consumer broadcasting the live visitor count."""
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .live import add_visitor, live_count, remove_visitor

GROUP = "visitors"


class LiveVisitorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        session = self.scope.get("session")
        self.session_key = getattr(session, "session_key", None)
        if self.session_key is None and session is not None:
            await sync_to_async(session.create)()
            self.session_key = session.session_key

        await self.channel_layer.group_add(GROUP, self.channel_name)
        await self.accept()
        count = await sync_to_async(add_visitor)(self.session_key)
        await self.channel_layer.group_send(
            GROUP, {"type": "visitor_update", "count": count}
        )

    async def disconnect(self, code):
        await self.channel_layer.group_discard(GROUP, self.channel_name)
        count = await sync_to_async(remove_visitor)(self.session_key)
        await self.channel_layer.group_send(
            GROUP, {"type": "visitor_update", "count": count}
        )

    async def visitor_update(self, event):
        await self.send(text_data=str(event["count"]))
