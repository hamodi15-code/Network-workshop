import socket
UDP_IP = '0.0.0.0'
UDP_PORT = 9999
client_dict={}
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
sock.bind((UDP_IP, UDP_PORT))

while True:
    data, addr = sock.recvfrom(1024)
    data = data.decode()
    if data.find(' ')==-1:
        # If the name does not exist we will add it to the dict
        if data not in client_dict:
            client_dict[data]=addr
            print(data,"-->Connected to the server!!!")
    else:
        #If we entered the else
        # then the message type is of a target customer and a message to him
        target_customer,message=data.split(" ",1)
        if target_customer not in client_dict:
            error_message="sorry you can't sent message to this client "
            sock.sendto(error_message.encode(), addr)
        else:
            sock.sendto(message.encode(),client_dict[target_customer])