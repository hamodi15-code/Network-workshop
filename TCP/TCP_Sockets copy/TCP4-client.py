import socket
import struct
import threading
import time

SERVER_IP = '127.0.0.1'
BUFFER_SIZE = 1024
start_times = {}  # Dictionary to track start times

def receive_messages(sock):
    while True:
        try:
            header = sock.recv(4)
            if not header:
                break

            msg_type, subtype, length = struct.unpack('>BBH', header)
            data = sock.recv(length-4).decode()
            if msg_type == 4 and subtype == 1:  # Echo response
                handle_echo_response(sock, data)
            else:
                print(f"\nReceived: {data}")
        except ConnectionResetError as e:
            print(f"Connection was reset: {e}")
            break
        except Exception as e:
            print(f"Error receiving message: {e}")
            break

def handle_echo_response(sock, data):
    rtt = time.time() - start_times[sock]  # Access start time from dictionary
    print(f"RTT: {rtt}")
    del start_times[sock]  # Clean up the entry after use

def send_echo_request(sock):
    msg_type = 4
    subtype = 0  # Echo request
    data = b'ECHO'
    length = 4 + len(data)
    header = struct.pack('>BBH', msg_type, subtype, length)
    
    start_times[sock] = time.time()  # Store start time in the dictionary
    
    sock.send(header + data)

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_port = int(input("Enter server port number: "))

    try:
        client.connect((SERVER_IP, server_port))
        print(f"Connected to server on port {server_port}")
    except ConnectionRefusedError:
        print(f"Could not connect to server on port {server_port}")
        return

    recv_thread = threading.Thread(target=receive_messages, args=(client,))
    recv_thread.start()

    while True:
        msg = input("Enter message to send or 'exit' to quit: ")
        if msg.lower() == 'exit':
            client.close()
            break
        elif msg.lower() == 'echo':
            send_echo_request(client)
        else:
            client.send(msg.encode())

if __name__ == "__main__":
    main()
