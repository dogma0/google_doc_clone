import asyncio
import json
import os

import websockets


storage_dirname = 'commits'


class Document:
    def __init__(self, name, connections=set(), text='', commits=[]):
        self.name = name
        self.connections = connections
        self.text = text
        self.commits = commits
        self.storage_path = f'{storage_dirname}/{self.name}'

    def add_connection(self, connection):
        self.connections.add(connection)

    def remove_connection(self, connection):
        self.connections.remove(connection)

    def add_commit(self, commit):
        def get_hash(revision):
            return abs(hash(self.name+revision))
        commit_fname = os.path.join(self.storage_path,
                                    str(get_hash(commit)))
        with open(commit_fname, 'w') as f:
            f.write(commit)

    def get_commits(self):
        return self.commits

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text

    def connections_event(self):
        return json.dumps({
            'type': 'connections',
            'value': len(self.connections)})

    def text_event(self):
        return json.dumps({
            'type': 'text',
            'value': self.get_text(),
        })

    def commits_event(self):
        return json.dumps({
            'type': 'commits',
            'value': [fname for fname in
                      os.listdir(self.storage_path)]
        })

    async def notify_commits(self):
        if os.listdir(self.storage_path):
            message = self.commits_event()
            await asyncio.wait(
                [connection.send(message)
                 for connection in self.connections]
            )

    async def notify_text(self, text):
        if self.connections:       # asyncio.wait doesn't accept an empty list
            message = self.text_event()
            await asyncio.wait(
                [connection.send(message)
                 for connection in self.connections]
            )

    async def notify_connections(self):
        if self.connections:       # asyncio.wait doesn't accept an empty list
            message = self.connections_event()
            await asyncio.wait(
                [connection.send(message)
                 for connection in self.connections]
            )

    async def register(self, websocket):
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)
        self.add_connection(websocket)
        await self.notify_connections()
        await websocket.send(self.text_event())
        await websocket.send(self.commits_event())

    async def unregister(self, websocket):
        self.remove_connection(websocket)
        await self.notify_connections()
        if not self.connections:
            del DOCUMENTS[self.name]


DOCUMENTS = {}


async def invite(websocket):
    ''' Block till connection says which document it likes to edit and view,
    return the object representing the document.
    '''
    def getfiles_modtime_sorted(dirpath):
        a = [s for s in os.listdir(dirpath)
             if os.path.isfile(os.path.join(dirpath, s))]
        a.sort(key=lambda s: os.path.getmtime(os.path.join(dirpath, s)))
        return a
    message = await websocket.recv()
    req = json.loads(message)
    print(f"--> req: {req}")
    if req['type'] == "START_CONN":
        doc_name = json.loads(message)['value']
        if doc_name not in DOCUMENTS:
            doc_dir = f'commits/{doc_name}'
            if os.listdir(doc_dir):
                latest_ver = getfiles_modtime_sorted(doc_dir)[-1]
                with open(f'{doc_dir}/{latest_ver}') as f:
                    DOCUMENTS[doc_name] = Document(
                        doc_name,
                        text=f.read())
            else:
                DOCUMENTS[doc_name] = Document(doc_name)
        doc = DOCUMENTS[doc_name]
        await doc.register(websocket)
        return doc
    raise ValueError("Connection is not established!")


async def ws_handler(websocket, path):
    print(f"--> Handing a new connection: {websocket}")
    doc = await invite(websocket)
    try:
        # Wait for messages to come in from websocket
        print(f"--> Start processing messages for {websocket}")
        async for message in websocket:
            req = json.loads(message)
            # APIs for websocket clients
            if req['type'] == 'ADD_COMMIT':
                commit = req['value']
                doc.set_text(commit)
                doc.add_commit(commit)
                await doc.notify_text(commit)
                await doc.notify_commits()
            elif req['type'] == 'SET_TEXT':
                text = req['value']
                doc.set_text(text)
                await doc.notify_text(text)
            elif req['type'] == 'GET_COMMITS':
                await doc.notify_commits()
            else:
                print(f'''--> ERROR: Connection {websocket} is trying to using an 
                undefined API. request => {req}''')
    finally:
        await doc.unregister(websocket)


def start_server():
    print("--> Starting WS server")
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
