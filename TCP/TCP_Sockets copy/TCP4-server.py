import socket
import struct
import threading
import time

SERVER_IP = '127.0.0.1'
PORTS = [3000, 3001, 3002, 3003, 3004]
port_index = 0
servers = {}
users = {}
sockets = {}
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def handle_client(client_socket, client_address):
    while True:
        try:
            header = client_socket.recv(4)
            if not header:
                break

            msg_type, subtype, length = struct.unpack('>BBH', header)
            data = client_socket.recv(length - 4)

            if msg_type == 0:  # Request information about connections
                if subtype == 0:  # of servers
                    response = construct_response(0, 0, servers)
                elif subtype == 1:  # of clients
                    response = construct_response(0, 1, users)
                client_socket.send(response)

            elif msg_type == 1:  # Answer to a request for information
                process_info_response(subtype, data)

            elif msg_type == 2:  # Setting a username for the connection
                username = data.decode()
                if subtype == 1:  # client
                    users[client_address] = username
                    sockets[username] = client_socket
                    print(f"User {username} connected from {client_address}")
                else:  # server
                    servers[client_address] = username

            elif msg_type == 3:  # Send message
                dest, message = data.decode().split(' ', 1)
                if dest in sockets:
                    send_message(sockets[dest], users[client_address], dest, message)
                else:
                    query_servers_for_recipient(client_socket, users[client_address], dest, message)

            elif msg_type == 4:  # Echo message for RTT calculation
                if subtype == 0:  # Echo request
                    send_echo_response(client_socket)

        except ConnectionResetError as e:
            print(f"Client {client_address} disconnected unexpectedly: {e}")
            break
        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
            break

    client_socket.close()
    if client_address in users:
        del sockets[users[client_address]]
        del users[client_address]
    elif client_address in servers:
        del servers[client_address]

def send_via_socket(sock, header, data=None):
    if data is None:
        return

    try:
        sock.send(header + data)
    except Exception as err:
        print(f"Error sending message data: {err}")

def send_message(server_sock, sender, recipient, data):
    recipient_socket = sockets.get(recipient)
    if recipient_socket:
        bytes_recipient = recipient.encode()
        message = f'{sender}\0{"->"}\0{recipient}\0{":"}\0{data}'
        bytes_message = message.encode()
        _type = 3
        _sub_type = 0
        _len = len(bytes_message)
        _sub_len = len(bytes_recipient)
        bytes_header = struct.pack('>BBH', _type, _sub_type, _len)
        send_via_socket(recipient_socket, bytes_header, bytes_message)
    else:
        print(f"Recipient {recipient} not found")

def send_echo_response(client_socket):
    _type = 4
    _sub_type = 1  # Echo response
    data = b'ECHO'
    length = 4 + len(data)
    header = struct.pack('>BBH', _type, _sub_type, length)
    send_via_socket(client_socket, header, data)

def construct_response(msg_type, subtype, data_dict):
    data = '\0'.join(f"{addr}:{name}" for addr, name in data_dict.items()).encode()
    header = struct.pack('>BBH', msg_type, subtype, len(data))
    return header + data

def process_info_response(subtype, data):
    info = data.decode().split('\0')
    if subtype == 0:
        servers.update(dict(item.split(':') for item in info))
    else:
        users.update(dict(item.split(':') for item in info))

def query_servers_for_recipient(sender_socket, sender, recipient, message):
    for conn_server in servers.items():
        try:
            print(f"Querying server at {conn_server} for recipient {recipient}...")
            data = message.encode()
            length = 4 + len(data)
            header = struct.pack('>BBH', 0, 1, length)
            send_via_socket(conn_server, header, data)
            server.connect(conn_server)
            response_header = server.recv(4)
            if response_header:
                msg_type, subtype, length = struct.unpack('>BBH', response_header)
                response_data = server.recv(length - 4)
                process_info_response(subtype, response_data)
                    
                if recipient in users.values():
                    print(f"Recipient {recipient} found on server {conn_server}. Forwarding message...")
                    send_message(conn_server, sender, recipient, message)
                    break
        except Exception as e:
            print(f"Error querying server {conn_server}: {e}")

def request_servers(server_sock: socket.socket) -> None:
    _type = 0
    _sub_type = 0
    _len = 0
    bytes_header = struct.pack('>BBH', _type, _sub_type, _len)
    send_via_socket(server_sock, bytes_header)

def request_clients(server_sock: socket.socket) -> None:
    _type = 0
    _sub_type = 1
    _len = 0
    bytes_header = struct.pack('>BBH', _type, _sub_type, _len)
    send_via_socket(server_sock, bytes_header)

def connect_to_servers(addresses: list[tuple[str, int]]) -> None:
    global servers

    for ip, port in addresses:
        if ip == SERVER_IP and port in PORTS[port_index]:
            continue
        if (ip, port) in servers.keys():
            continue

        try:
            server.connect((ip, port))
            print(f'Connection with {(ip, port)} established.')
        except OSError as err:
            print(f'Connection to {(ip, port)} failed.\n\t{err}')

        if server is None:
            continue
        servers[(ip, port)] = server

def connect_all():
    for port in PORTS:
        if port == PORTS[port_index]:
            continue
        addr = SERVER_IP
        try:
            server.connect((addr, PORTS[port_index]))
            print(f'Connection with {(addr, PORTS[port_index])} established.')
        except OSError as err:
            print(f'Connection to {(addr, PORTS[port_index])} failed.\n\t{err}')

        if server is not None:
            servers[addr] = server
            print(f'Requesting server list from {addr}.')
            addresses = request_servers(server)
            if addresses is None:
                print(f'Failed to retrieve server list from {addr}.')
                continue
            print(f'Received server list from {addr}.')
            connect_to_servers(addresses)
            break

def main():
    print('Select a port:')
    for p in range(len(PORTS)):
        print(f'{p}. {PORTS[p]}')

    port_index = int(input())
    server.bind(('0.0.0.0', PORTS[port_index]))
    server.listen(5)
    print(f"Server listening on port {PORTS[port_index]}")
    connect_all()

    while True:
        client_socket, client_address = server.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()

if __name__ == "__main__":
    main()
