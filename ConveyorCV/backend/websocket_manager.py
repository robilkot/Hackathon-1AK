import json

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from model.model import StreamingMessage, DefaultJsonEncoder


class WebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.latest_message: StreamingMessage | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

        if self.latest_message is not None:
            await self.__send_message(websocket, self.latest_message)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def __send_message(self, ws: WebSocket, msg):
        try:
            msg_json = json.dumps(msg, cls=DefaultJsonEncoder)
            await ws.send_bytes(msg_json)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print('FUCK json, ', str(e))
            await ws.close()
            self.active_connections.remove(ws)

    async def broadcast_message(self, message: StreamingMessage):
        self.latest_message = message

        try:
            for ws in self.active_connections:
                await self.__send_message(ws, message)
        except RuntimeError as re:
            # todo shit
            if str(re) == 'Cannot call "send" once a close message has been sent.':
                raise InterruptedError
