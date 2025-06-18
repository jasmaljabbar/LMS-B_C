import http.server
import ssl
import socketserver
import os

# --- Configuration ---
PORT = 9000
CERT_FILE = 'cert.pem'
KEY_FILE = 'key.pem'
# --- End Configuration ---

# Ensure certificate and key files exist
if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
    print(f"Error: Certificate file '{CERT_FILE}' or key file '{KEY_FILE}' not found.")
    print("Please generate them using OpenSSL:")
    print("openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes")
    exit(1)

# Handler for serving files (same as SimpleHTTPServer)
Handler = http.server.SimpleHTTPRequestHandler

# Create a standard TCP server
# Use 0.0.0.0 to listen on all available interfaces
# Use 127.0.0.1 or localhost to listen only on the loopback interface
httpd = socketserver.TCPServer(("0.0.0.0", PORT), Handler)

# Wrap the server socket with SSL/TLS
# Uses recommended security settings from Python 3.6+
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

print(f"Serving HTTPS on port {PORT}...")
print(f"Access it at: https://localhost:{PORT}")
print(f"(Or replace localhost with your machine's actual IP address if accessing from another device)")
print("\nWarning: You will likely see a browser security warning because the certificate is self-signed.")
print("You'll need to manually accept the risk to proceed.")

try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("\nServer stopped.")
    httpd.server_close()

