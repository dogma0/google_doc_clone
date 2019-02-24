import asyncio
import json
import websockets
import os


class Doc:
    def __init__(self, docname, connected=set(), text='', revisions=[]):
        self.docname = docname
        self.connected = connected
        self.text = text
        self.revisions = revisions

    def add_connection(self, user_socket):
        self.connected.add(user_socket)

    def remove_connection(self, user_socket):
        self.connected.remove(user_socket)

    def add_revision(self, revision):
        if not os.path.exists(f'revisions/{self.docname}'):
            os.makedirs(f'revisions/{self.docname}')
        file = open(os.path.join(f'revisions/{self.docname}',
                                 str(self.get_hash(revision))), 'w')
        file.write(revision)
        file.close()

    def get_hash(self, revision):
        return abs(hash(self.docname+revision))

    def get_revisions(self):
        return self.revisions

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text

    def users_event(self):
        return json.dumps({'type': 'users', 'count': len(self.connected)})

    def state_event(self):
        return json.dumps({
            'type': 'state',
            'text': self.get_text(),
        })

    def get_revision_fnames(self):
        return [revision_fname for revision_fname in
                os.listdir(f'revisions/{self.docname}')]

    def revision_event(self):
        return json.dumps({
            'type': 'revision',
            'revision_links': self.get_revision_fnames()
        })

    async def notify_revisions(self):
        if os.listdir(f'revisions/{self.docname}'):
            message = self.revision_event()
            print(f'Message is {message}')
            await asyncio.wait([user.send(message) for user in self.connected])

    async def notify_state(self, text):
        if self.connected:       # asyncio.wait doesn't accept an empty list
            message = self.state_event()
            await asyncio.wait([user.send(message) for user in self.connected])

    async def notify_users(self):
        if self.connected:       # asyncio.wait doesn't accept an empty list
            message = self.users_event()
            await asyncio.wait([user.send(message) for user in self.connected])

    async def register(self, websocket):
        self.add_connection(websocket)
        await self.notify_users()
        await websocket.send(self.state_event())

    async def unregister(self, websocket):
        self.remove_connection(websocket)
        await self.notify_users()


DOCS = {'t1': Doc('t1')}


async def invite_subscription(ws):
    ''' Wait for websocket to state which document to join, 
    if the document doesn't exist, create
    a new one. Register websocket to the document after, and return the document.
    '''
    message = await ws.recv()
    doc_name = json.loads(message)['value']
    if doc_name not in DOCS:
        DOCS[doc_name] = Doc(doc_name)
    doc = DOCS[doc_name]
    await doc.register(ws)
    return doc


def get_doc(doc_name):
    return DOCS[doc_name]


async def ws_handler(websocket, path):
    print(f"===Handing a new connection: {websocket} ===")
    doc = await invite_subscription(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            if data['type'] == 'SET_REVISION':
                revision = data['value']
                doc.set_text(revision)
                doc.add_revision(revision)
                await doc.notify_state(revision)
                await doc.notify_revisions()
            elif data['type'] == 'SET_DOCNAME':
                doc_name = data['value']
                doc = DOCS[doc_name]
                await doc.notify_users()
            elif data['type'] == 'SET_DOCTEXT':
                text = data['value']
                doc.set_text(text)
                await doc.notify_state(text)
            elif data['type'] == 'GET_REVISION':
                await doc.notify_revisions()
    finally:
        await doc.unregister(websocket)


def start_server():
    print("===Starting WS server===")
    asyncio.get_event_loop().run_until_complete(
        websockets.serve(
            ws_handler,
            'localhost',
            7600
        )
    )
    asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    start_server()
