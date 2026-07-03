import asyncio
import websockets
import socket

# Setup UDP to listen to test.py
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)

connected_clients = set()

async def udp_to_ws():
    """Listens for UDP packets and forwards them to all connected web clients."""
    loop = asyncio.get_event_loop()
    while True:
        try:
            # Wait for data from test.py
            data, _ = await loop.sock_recvfrom(sock, 1024)
            if connected_clients:
                # Forward to Three.js
                message = data.decode('utf-8')
                tasks = [asyncio.create_task(client.send(message)) for client in connected_clients]
                await asyncio.gather(*tasks)
        except Exception as e:
            print(f"UDP forwarding error: {e}")

# CRITICAL FIX: Removed the 'path' argument to match modern websockets API
async def handler(websocket):
    """Manages web browser connections."""
    print("New Three.js client connected.")
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        print("Three.js client disconnected.")

async def main():
    print("Starting UDP-to-WebSocket Bridge on ws://127.0.0.1:8080...")
    server = await websockets.serve(handler, "127.0.0.1", 8080)
    await asyncio.gather(server.wait_closed(), udp_to_ws())

if __name__ == "__main__":
    asyncio.run(main())