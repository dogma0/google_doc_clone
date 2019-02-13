import asyncio
import websockets
import json


class Document:
    def __init__(self, name, users=set(), state=''):
        self.name = name
        self.users = users
        self.state = state

    def add_user(self, user):
        self.users.add(user)

    def get_text(self):
        return self.state
    
    def set_text(self, text):
        self.state = text


documents = {
    't1':
    Document('t1', state='This is first line in t1.')
}


async def notify_collaborators(message):
    msg = message
    msg = json.loads(msg)
    doc_name, next_state = msg['doc_name'], msg['next_state']
    doc = documents[doc_name]
    print("Users are {0}".format(doc.users))
    await asyncio.wait([user.send(message) for user in doc.users])


async def register(websocket):
    doc_to_join = await websocket.recv()
    doc = documents[doc_to_join]
    doc.add_user(websocket)
    await websocket.send(doc.get_text())


async def consume_state_update(message):
    msg = message
    msg = json.loads(msg)
    doc_name, next_state = msg['doc_name'], msg['next_state']
    print(f"doc_name={doc_name}, next_state={next_state}")
    documents[doc_name].set_text(next_state)


async def process_next_state(websocket):
    print("Start processing the next state")
    async for message in websocket:
        await consume_state_update(message)
        await notify_collaborators(message)


async def connection_maker(websocket, path):
    print("New connection: {0}".format(websocket))
    await register(websocket)
    await process_next_state(websocket)

asyncio.get_event_loop().run_until_complete(
    websockets.serve(connection_maker, 'localhost', 9876, ping_interval=5)
)
asyncio.get_event_loop().run_forever()
