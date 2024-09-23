import socket
import threading
import time
# Function to handle client connections
def handle_client(client_socket):
    with client_socket:
        message = client_socket.recv(1024).decode('utf-8')
        if message == "Hello":
            client_socket.sendall(b"World")
        else:
            client_socket.sendall(b"Invalid message")


# Main server function
def server(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(('127.0.0.1', port))
        server_socket.listen(1)
        #print(f"Server listening on port {port}")

        while True:
            client_socket, addr = server_socket.accept()
            print(f"Accepted connection from {addr},port:{port}")
            client_handler = threading.Thread(target=handle_client, args=(client_socket,))
            client_handler.start()


# Function to test server connections
def test_server(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_socket:
            test_socket.connect(('127.0.0.1', port))
            test_socket.sendall(b"Hello")
            response = test_socket.recv(1024).decode('utf-8')
            print(f"Received: {response}")
    except ConnectionRefusedError:
        print(f"Connection to port {port} refused")


if __name__ == "__main__":
    ports = [5001, 5002, 5003,5004,5005]  # Example port numbers for testing
    select = int(input("select client port 1-5\n"))
    select-=1
    threading.Thread(target=server, args=(ports[select],)).start()
    time.sleep(1)  # Wait for servers to start
    for port in ports:
        if port != ports[select]:
            test_server(port)
