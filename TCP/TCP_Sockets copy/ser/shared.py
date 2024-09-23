import socket, struct

# ANSI escape codes
class ANSI:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'

# shared constants
_LOCALHOST = '127.0.0.1'
_PORTS = [30000, 30001, 30002, 30003, 30004]
_HEADER_FORMAT = '!BBHH'
_HEADER_SIZE = struct.calcsize(_HEADER_FORMAT)

# shared methods
def port_select(ports: list) -> int:
    def port_input() -> int:
        print('Select a port:')
        for p in range(len(ports)):
            print(f'{p}. {ports[p]}')
        try:
            x = int(input())
        except:
            return -1
        return x if 0 <= x < len(ports) else -1

    port_index = port_input()
    while port_index == -1:
        LOG_ERROR('Selected port is invalid or taken.\n')
        port_index = port_input()
    return port_index

def LOG_MESSAGE(message: str) -> None:
    print(f'{ANSI.YELLOW}LOG: {message}{ANSI.RESET}')

def LOG_ERROR(message: str) -> None:
    print(f'{ANSI.RED}ERROR: {message}{ANSI.RESET}')

def attempt_handshake(ip: str, port: int) -> socket.socket:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        sock.connect((ip, port))
        LOG_MESSAGE(f'connection with {(ip, port)} established.')
        return sock
    except OSError as err:
        LOG_ERROR(f'connection to {(ip, port)} failed.\n\t{err}')  # log failed connections
        return None

# protocol methods
def request_servers(server_sock: socket.socket) -> None:
    # prepare header values
    _type       = 0
    _sub_type   = 0
    _len        = 0
    _sub_len    = 0

    # construct header
    bytes_header = struct.pack(_HEADER_FORMAT, _type, _sub_type, _len, _sub_len)

    # send header
    send_via_socket(server_sock, bytes_header)
    return

def request_clients(server_sock: socket.socket) -> None:
    # prepare header values
    _type       = 0
    _sub_type   = 1
    _len        = 0
    _sub_len    = 0

    # construct header
    bytes_header = struct.pack(_HEADER_FORMAT, _type, _sub_type, _len, _sub_len)

    # send header
    send_via_socket(server_sock, bytes_header)
    return

def send_servers(server_sock: socket.socket, data: str) -> None:
    # prepare data segment
    bytes_data  = data.encode()

    # prepare header values
    _type       = 1
    _sub_type   = 0
    _len        = len(bytes_data)
    _sub_len    = 0

    # construct header
    bytes_header = struct.pack(_HEADER_FORMAT, _type, _sub_type, _len, _sub_len)

    # send header & data
    send_via_socket(server_sock, bytes_header, bytes_data)
    return

def send_clients(server_sock: socket.socket, data: str) -> None:
    # prepare data segment
    bytes_data  = data.encode()

    # prepare header values
    _type       = 1
    _sub_type   = 1
    _len        = len(bytes_data)
    _sub_len    = 0

    # construct header
    bytes_header = struct.pack(_HEADER_FORMAT, _type, _sub_type, _len, _sub_len)

    # send header & data
    send_via_socket(server_sock, bytes_header, bytes_data)
    return

def set_username(server_sock: socket.socket, data: str, client: bool) -> None:
    # prepare data segment
    bytes_username   = data.encode()

    # prepare header values
    _type       = 2
    _sub_type   = 1 if client else 0
    _len        = len(bytes_username)
    _sub_len    = 0

    # construct header
    bytes_header = struct.pack(_HEADER_FORMAT, _type, _sub_type, _len, _sub_len)

    # send header & data
    send_via_socket(server_sock, bytes_header, bytes_username)
    return

def send_message(server_sock: socket.socket, sender: str, recipient: str, data: str) -> None:
    # prepare data segment
    bytes_recipient = recipient.encode()
    message         = f'{sender}\0{recipient}\0{data}'
    bytes_message   = message.encode()

    # prepare header values
    _type       = 3
    _sub_type   = 0
    _len        = len(bytes_message)
    _sub_len    = len(bytes_recipient)

    # construct header
    bytes_header = struct.pack(_HEADER_FORMAT, _type, _sub_type, _len, _sub_len)

    # send header & data
    send_via_socket(server_sock, bytes_header, bytes_message)
    return

def send_via_socket(sock: socket.socket, header: bytes, data: bytes = None) -> None:
    try:
        sock.send(header)
    except Exception as err:
        LOG_ERROR(f'an error occurred while sending message header.\n\t{err}')
        return

    if data is None:
        return

    try:
        sock.send(data)
    except Exception as err:
        LOG_ERROR(f'an error occurred while sending message data.\n\t{err}')

def receive_via_socket(sock: socket.socket) -> dict:
    response = {
        'bytes_header': None,
        'type':         None,
        'sub_type':     None,
        'len':          None,
        'sub_len':      None,
        'bytes_data':   None,
        'data':         None,
        'error':        None
    }

    # receive header bytes
    try:
        bytes_header = sock.recv(_HEADER_SIZE)
        if len(bytes_header) == 0:
            raise ConnectionResetError
        response['bytes_header'] = bytes_header
        _type, _sub_type, _len, _sub_len = struct.unpack(_HEADER_FORMAT, bytes_header)
        response['type']     = _type
        response['sub_type'] = _sub_type
        response['len']      = _len
        response['sub_len']  = _sub_len
    except Exception as err:
        LOG_ERROR(f'an error occurred while retrieving message header.\n\t{err}')
        response['error']  = err
        return response
    
    if _len == 0:
        return response

    # receive data bytes
    try:
        bytes_data = sock.recv(_len)
        if len(bytes_data) == 0:
            raise ConnectionResetError
        response['bytes_data']  = bytes_data
        data       = bytes_data.decode()
        response['data']  = data
    except Exception as err:
        LOG_ERROR(f'an error occurred while retrieving message data.\n\t{err}')
        return response
    
    return response
