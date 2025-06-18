import asyncio
import json
import ssl  # Import the ssl module
import websockets
from websockets.legacy.protocol import WebSocketCommonProtocol
from websockets.legacy.server import WebSocketServerProtocol

HOST = "us-central1-aiplatform.googleapis.com"
SERVICE_URL = f"wss://{HOST}/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent"

DEBUG = False


async def proxy_task(
    client_websocket: WebSocketCommonProtocol, server_websocket: WebSocketCommonProtocol
) -> None:
    """
    Forwards messages from one WebSocket connection to another.

    Args:
        client_websocket: The WebSocket connection from which to receive messages.
        server_websocket: The WebSocket connection to which to send messages.
    """
    async for message in client_websocket:
        try:
            data = json.loads(message)
            if DEBUG:
                print("proxying: ", data)
            await server_websocket.send(json.dumps(data))
        except Exception as e:
            print(f"Error processing message: {e}")

    await server_websocket.close()


async def create_proxy(
    client_websocket: WebSocketCommonProtocol, bearer_token: str
) -> None:
    """
    Establishes a WebSocket connection to the server and creates two tasks for
    bidirectional message forwarding between the client and the server.

    Args:
        client_websocket: The WebSocket connection of the client.
        bearer_token: The bearer token for authentication with the server.
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}",
    }

    # Note: The connection *to* the Google service is already WSS (defined in SERVICE_URL)
    # No changes needed here for that part.
    async with websockets.connect(
        SERVICE_URL, additional_headers=headers
    ) as server_websocket:
        client_to_server_task = asyncio.create_task(
            proxy_task(client_websocket, server_websocket)
        )
        server_to_client_task = asyncio.create_task(
            proxy_task(server_websocket, client_websocket)
        )
        await asyncio.gather(client_to_server_task, server_to_client_task)


async def handle_client(client_websocket: WebSocketServerProtocol) -> None:
    """
    Handles a new client connection, expecting the first message to contain a bearer token.
    Establishes a proxy connection to the server upon successful authentication.

    Args:
        client_websocket: The WebSocket connection of the client.
    """
    print("New connection...")
    # Wait for the first message from the client
    try:
        auth_message = await asyncio.wait_for(client_websocket.recv(), timeout=5.0)
        auth_data = json.loads(auth_message)

        if "bearer_token" in auth_data:
            bearer_token = auth_data["bearer_token"]
        else:
            print("Error: Bearer token not found in the first message.")
            await client_websocket.close(code=1008, reason="Bearer token missing")
            return

        await create_proxy(client_websocket, bearer_token)
    except asyncio.TimeoutError:
        print("Timeout waiting for authentication message.")
        await client_websocket.close(code=1008, reason="Authentication timeout")
    except Exception as e:
        print(f"Error during initial connection handling: {e}")
        await client_websocket.close(code=1011, reason="Server error during handshake")


async def main() -> None:
    """
    Starts the WebSocket server (now using WSS) and listens for incoming client connections.
    """
    # --- SSL Configuration for WSS ---
    # Create an SSL context for the server
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # Load your certificate and private key.
    # For development/testing, you can generate self-signed certificates using openssl:
    # openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 365 -nodes -subj "/CN=localhost"
    # IMPORTANT: Replace 'cert.pem' and 'key.pem' with the actual paths to your certificate files.
    # In production, use certificates from a trusted Certificate Authority (CA).
    certfile = "cert.pem"  # Replace with your certificate file path
    keyfile = "key.pem"    # Replace with your private key file path

    try:
        ssl_context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        print(f"SSL context loaded using cert: '{certfile}', key: '{keyfile}'")
    except FileNotFoundError:
        print(f"\n*** Error: Certificate ('{certfile}') or key ('{keyfile}') file not found. ***")
        print("    WSS requires SSL certificates. Please generate self-signed certificates for testing")
        print("    (e.g., using openssl req ...) or provide paths to valid certificate files.")
        print("    Server cannot start in WSS mode without certificates.\n")
        return # Exit if certs are missing
    except Exception as e:
        print(f"\n*** Error loading certificate/key: {e} ***")
        print("    Please ensure the certificate and key files are valid and permissions are correct.")
        print("    Server cannot start in WSS mode.\n")
        return # Exit on other SSL errors

    # Start the secure WebSocket server (WSS) by passing the ssl_context
    async with websockets.serve(
        handle_client,
        "0.0.0.0",
        8080,
        ssl=ssl_context  # Pass the SSL context here to enable WSS
    ):
        print("Running secure websocket server (wss://) on 0.0.0.0:8080...")
        # Run forever
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
