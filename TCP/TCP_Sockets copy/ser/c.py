import socket, sys, threading
import shared

def await_messages(server_sock: socket.socket):
    while True:
        response = shared.receive_via_socket(server_sock)

        # if caught any errors
        if response['error'] is not None:
            # check if it was caused due to the connection closing
            if isinstance(response['error'], ConnectionResetError):
                # close the socket, and end the thread
                server_sock.close()
                shared.LOG_MESSAGE('connection with server has been closed.')
                return
            # otherwise continue
            continue
        
        # ignore any protocol messages that aren't direct messages
        if response['type'] != 3:
            continue

        # unpack message
        sender, recipient, message = response['data'].split('\0', 2)
        print(f'{sender} -> {recipient}: {message}')

# port selection
port_index = shared.port_select(shared._PORTS)

# handshake attempt with selected server
server_sock = shared.attempt_handshake(shared._LOCALHOST, shared._PORTS[port_index])
if server_sock is None:
    shared.LOG_MESSAGE('Closing client...')
    input('press any key to exit.')
    exit()

# send username to the server
username = input('Enter your name: ')
shared.set_username(server_sock, username, True)

# create listener for the server
server_listener = threading.Thread(target=await_messages, args=(server_sock,))
server_listener.start()

# get user input and send via server
for line in sys.stdin:
    recipient, message = line.strip().split(' ', 1)
    shared.send_message(server_sock, username, recipient, message)

# close connection with server
server_sock.close()
server_listener.join()

shared.LOG_MESSAGE('done.')