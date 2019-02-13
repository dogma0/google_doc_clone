import asyncio
import websockets
import json

async def hello():
    async with websockets.connect(
            'ws://localhost:9876', ping_interval=5) as websocket:
        doc_name = input("GDoc to join?")
        await websocket.send(doc_name)
        async for message in websocket:
            doc = message
            print(f"< {doc}")
            nextdoc = input("What is the next state?") 
            await websocket.send(json.dumps({
                'doc_name': doc_name,
                'next_state': nextdoc}))

asyncio.get_event_loop().run_until_complete(hello())
asyncio.get_event_loop().run_forever()