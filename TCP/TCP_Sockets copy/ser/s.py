import socket, threading
import shared

def setup_listener(port: int) -> socket.socket:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(('0.0.0.0', port))
    listener.listen(1)
    return listener

def await_connections(listener: socket.socket) -> None:
    global temp
    shared.LOG_MESSAGE('awaiting for connections...')
    while True:
        conn_socket, conn_address = listener.accept()
        temp.append(conn_socket)
        shared.LOG_MESSAGE(f'connection with {conn_address} established.')
        threading.Thread(target=respond_to_connection, args=(conn_socket, conn_address)).start()

def respond_to_connection(conn_socket: socket.socket, conn_address: tuple[str, int]) -> None:
    global clients, servers, temp

    if conn_socket is None:
        shared.LOG_ERROR(f'cant respond to connection {conn_address=}  {conn_socket=}')
        return

    while True:
        response = shared.receive_via_socket(conn_socket)

        # if caught any errors
        if response['error'] is not None:
            # check if it was caused due to the connection closing
            if isinstance(response['error'], ConnectionResetError):
                # close the socket, and end the thread
                conn_socket.close()
                shared.LOG_MESSAGE(f'connection with {conn_address} has been closed.')
                return
            # otherwise continue
            continue
        
        # check if the connection is held with a server
        conn_is_server = conn_socket in servers.values()

        # received a request for a server list
        if   response['type'] == 0 and response['sub_type'] == 0:
            shared.LOG_MESSAGE(f'received a server list request, replying.')
            share_servers(conn_socket)
        # received a request for a client list
        elif response['type'] == 0 and response['sub_type'] == 1:
            shared.LOG_MESSAGE(f'received a client list request, replying.')
            share_clients(conn_socket)
        # received an answer for a server list request
        elif response['type'] == 1 and response['sub_type'] == 0:
            shared.LOG_MESSAGE(f'received an answer for a server list request,'
                               + '\n\tbut it was not requested.'
                               + f'\n\tsender {conn_address}.')
            continue  # unused functionality
        # received an answer for a client list request
        elif response['type'] == 1 and response['sub_type'] == 1:
            shared.LOG_MESSAGE(f'received an answer for a client list request,'
                               + '\n\tbut it was not requested.'
                               + f'\n\tsender {conn_address}.')
            continue  # unused functionality
        # received a request for setting a server username
        elif response['type'] == 2 and response['sub_type'] == 0:
            shared.LOG_MESSAGE(f'received a request for registering a server.'
                               + f'\n\tsender {conn_address}.')
            # remove server from temp list
            try:
                temp.remove(conn_address)
            except:
                pass
            
            servers[(conn_address[0], int(response['data']))] = conn_socket
            shared.LOG_MESSAGE(f'registered {conn_address} as server at port {response['data']}.')
        # received a request for setting a client username
        elif response['type'] == 2 and response['sub_type'] == 1:
            # remove client from temp list
            try:
                temp.remove(conn_address)
            except:
                pass

            # if selected username is already taken, close connection and show an error
            if response['data'] in clients:
                shared.LOG_ERROR(f'requested username "{response['data']}" by {conn_address} is already taken!'
                                 + '\n\tclosing connection...')
                conn_socket.close()
                return
            
            # otherwise register the connection under the requested username
            clients[response['data']] = conn_socket
            shared.LOG_MESSAGE(f'registered {conn_address} as "{response['data']}".')
        # received a request for direct message forwarding
        elif response['type'] == 3:
            # unpack message
            sender, recipient, message = response['data'].split('\0', 2)

            # if a direct connection with recipient is established, forward the message directly
            if recipient in clients:
                shared.LOG_MESSAGE(f'forwarding message...\n\t{sender} -> {recipient}: {message}')
                shared.send_message(clients[recipient], sender, recipient, message)
            # if the sender is a server, drop the broadcasted message to avoid flooding
            elif conn_is_server:
                shared.LOG_MESSAGE(f'received a message forwarding broadcast, dropping package.')
                continue
            # otherwise broadcast the message to other servers
            else:
                shared.LOG_MESSAGE(f'broadcasting message...\n\t{sender} -> {recipient}: {message}')
                broadcast_to_servers(response['bytes_header'], response['bytes_data'])

def share_servers(requester: socket.socket) -> None:
    # prepare a list of available servers, skip requester
    server_list = [f'{addr}:{port}' for (addr, port), sock in servers.items() if sock != requester]
    server_list.append(f'{shared._LOCALHOST}:{shared._PORTS[port_index]}')

    # prepare the message data
    data = '\0'.join(server_list)
    shared.send_servers(requester, data)

def share_clients(requester: socket.socket) -> None:
    # prepare a list of available clients
    client_list = [username for username in clients.keys()]

    # prepare the message data
    data = '\0'.join(client_list)
    shared.send_clients(requester, data)

def request_servers(server: socket.socket) -> list[tuple[str, int]]:
    # perform the request
    shared.request_servers(server)

    response = shared.receive_via_socket(server)

    # if caught any errors
    if response['error'] is not None:
        # close the socket, and end the thread
        server.close()
        return None
    
    # break up addresses and return as a list
    return [(address.split(':')[0], int(address.split(':')[1])) for address in response['data'].split('\0')]

def connect_to_servers(addresses: list[tuple[str, int]]) -> None:
    global servers

    for ip, port in addresses:
        # skip ourselves
        if ip == shared._LOCALHOST and port == shared._PORTS[port_index]:
            continue

        # skip connected
        if (ip, port) in servers.keys():
            continue

        # connect to server, and register connection socket
        conn = shared.attempt_handshake(ip, port)
        if conn is None:
            continue
        servers[(ip, port)] = conn

        # register as server
        shared.set_username(conn, str(shared._PORTS[port_index]), False)

def broadcast_to_servers(bytes_header: bytes, bytes_data: bytes) -> None:
    for server in servers.values():
        shared.send_via_socket(server, bytes_header, bytes_data)


# port selection
port_index = shared.port_select(shared._PORTS)
servers = {}
clients = {}
temp    = []

# attempt handshakes with everyone (servers), except ourselves
for p in shared._PORTS:
    if p == shared._PORTS[port_index]:
        continue
    addr = (shared._LOCALHOST, p)
    conn = shared.attempt_handshake(*addr)
    # if establised a connection with another server
    if conn is not None:
        # register the server
        servers[addr] = conn
        shared.set_username(conn, str(shared._PORTS[port_index]), False)

        # request the active servers list
        shared.LOG_MESSAGE(f'requesting server list from {addr}.')
        addresses = request_servers(conn)

        # if failed retrieving connections, resort to iterational connections
        if addresses is None:
            shared.LOG_ERROR(f'failed to retrieve server list from {addr}.')
            continue

        # and connect to those
        shared.LOG_MESSAGE(f'received server list from {addr}.')
        connect_to_servers(addresses)
        break

# discard any failed connections
servers = {addr:sock for addr, sock in servers.items() if sock is not None}

# open threads for active connections
for addr, sock in servers.items():
    threading.Thread(target=respond_to_connection, args=(sock, addr)).start()

# listener setup
listener = setup_listener(shared._PORTS[port_index])
await_connections(listener)

# disconnect from clients
for client in clients.values():
    client.close()

# disconnect from servers
for server in servers.values():
    server.close()

shared.LOG_MESSAGE('done.')
