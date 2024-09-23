import socket
import struct
import threading

SERVER_IP = '127.0.0.1'
BUFFER_SIZE = 1024

def receive_messages(sock):
    while True:
        try:
            header = sock.recv(4)
            if not header:
                break

            msg_type, subtype, length = struct.unpack('>BBH', header)
            data = sock.recv(length-4).decode()
            print("\n")
            print(f"Received: {data}")
        except Exception as e:
            print(f"Error receiving message: {e}")
            break

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_port = int(input("Enter server port number: "))

    try:
        client.connect((SERVER_IP, server_port))
        print(f"Connected to server at {SERVER_IP}:{server_port}")

        threading.Thread(target=receive_messages, args=(client,)).start()

        while True:
            msg_type = int(input("Enter message type (2 or 3): "))
            subtype = int(input("Enter message subtype: "))
            if msg_type == 2:
                message = input("Enter your username: ")
            else:
                recipient = input("Enter recipient's username: ")
                message = input("Enter your message: ")
                message = f"{recipient} {message}"
                
                
            data = message.encode()
            length = 4 + len(data)
            header = struct.pack('>BBH', msg_type, subtype, length)
            client.send(header + data)
            print('\n')

    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
