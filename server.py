import asyncio
import json
import websockets


class Doc:
    def __init__(self, docname, connected=set(), text=''):
        self.docname = docname
        self.connected = connected
        self.text = text

    def add_connection(self, user_socket):
        self.connected.add(user_socket)

    def remove_connection(self, user_socket):
        self.connected.remove(user_socket)

    def get_text(self):
        return self.text
    
    def set_text(self, text):
        self.text = text

    def users_event(self):
        return json.dumps({'type': 'users', 'count': len(self.connected)})

    async def notify_state(self, text):
        if self.connected:       # asyncio.wait doesn't accept an empty list
            message = state_event(text)
            await asyncio.wait([user.send(message) for user in self.connected])

    async def notify_users(self):
        if self.connected:       # asyncio.wait doesn't accept an empty list
            message = self.users_event()
            await asyncio.wait([user.send(message) for user in self.connected])

    async def register(self, websocket):
        self.add_connection(websocket)
        await self.notify_users()

    async def unregister(self, websocket):
        self.remove_connection(websockets)
        await self.notify_users()

DOCS = {'t1': Doc('t1')}

def state_event(text):
    return json.dumps({'type': 'state', 'text': text})

async def get_collab_doc(ws):
    message = await ws.recv()
    doc_name = json.loads(message)['docname']
    doc = DOCS[doc_name]
    return doc

async def make_connection(websocket, path):
    doc = await get_collab_doc(websocket)
    await doc.register(websocket)
    try:
        await websocket.send(state_event(doc.get_text()))
        async for message in websocket:
            data = json.loads(message)
            doc.set_text(data['text'])
            await doc.notify_state(data['text'])
    finally:
        await doc.unregister(websocket)

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(
        websockets.serve(make_connection, 'localhost', 7600))
    asyncio.get_event_loop().run_forever()