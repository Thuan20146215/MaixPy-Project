import socket
import time
import threading #parallel execution
import datetime
import pygame
from pygame.locals import QUIT, KEYDOWN, K_f, K_F11, FULLSCREEN
import sys
local_ip = ""
local_port = 80
width = 320
height = 240

# jpeg 20 fps
# esp32 spi dma temp buffer MAX Len: 4k

def server_receive(conn): #Receive image only
    conn.settimeout(10)
    conn_end = False
    pack_size = 1024*5
    while True:
        if conn_end:
            break
        #char_data = b"" 
        img = b"" #the complete img data received from the cilent
        tmp = b'' #stores the last byte received to assist detecing the start marker of the img. it helps identify the start of the new img segment
        while True: #It ensures that the image data is correctly captured even if it is received in multiple segments.
            try:
                client_data = conn.recv(1)
            except socket.timeout:
                conn_end = True
                break
            
            if tmp == b'\xFF' and client_data == b'\xD8':
                img = b'\xFF\xD8' #check start marker JPEG
                
                break #it checks if the combination of the last received byte (tmp) and the current byte (client_data) forms the start marker of a JPEG image (\xFF\xD8). If so, it initializes the img variable with this start marker (b'\xFF\xD8') and breaks out of the loop.
            tmp = client_data
        while True:
            try:
                client_data = conn.recv(4096) #client 2048 bytes but server can receive more 
            except socket.timeout:#break the while loop (line 21,36)
                client_data = None
                conn_end = True 
            if not client_data:
                break
            # print("received data,len:",len(client_data) )
            img += client_data
            if img[-2:] == b'\xFF\xD9':#check end marker JPEG
                break
            if len(client_data) > pack_size: #breaks out of the loop to prevent receiving too much data.
                break

        print("recive end, pic len:", len(img))
        print(img[:2])
        print(img[-2:])
        # if not img.startswith(b'\xFF\xD8') or not img.endswith(b'\xFF\xD9'):
        #     print("image error") #If the received data does not start or end with these markers, it implies that the received data is not a complete JPEG image
        #     continue
        if img.startswith(b'\xFF\xD8'):
            pass
        f = open("tmp.jpg", "wb")
        f.write(img)
        f.close()
        try:
            surface = pygame.image.load("tmp.jpg").convert()
            # Loads the image from the file "tmp.jpg" into a Pygame surface and converts it to a format suitable for display.
            screen.blit(surface, (0, 0))
            pygame.display.update()
            #Updates the display to show the newly blitted image.
            print("recieve ok")
        except Exception as e:
            print(e)
        ###############
        conn.settimeout(5)
        try:
            message = input("Enter your message: ")
            #message = "thuan"
            if message=='exit':
                message = 'exit'
                conn.send(message.encode())
                break
            conn.send(message.encode())
        except socket.timeout:
            print('No connection received within the timeout period. Exiting')
            sys.exit(1)
        ##################
    conn.close()
    print("receive thread end")


def receiveThread2(conn): #Receive image and send string
    conn.settimeout(5)
    conn_end = False
    pack_size = 1024*5
    cl_send = b""
    print("start")
    while True:
        if conn_end:
            break
        
        # Receive data
        while True:#not cl_send[-5:-3] == b'\xFF\xD9':
            try:
                data = conn.recv(4096)
            except socket.timeout:
                data = None
                conn_end = True
            if not data:
                break
            cl_send += data
            if cl_send[-5:-3] == b'\xFF\xD9':#check end marker JPEG
                break
            #if img[-2:] == b'\xFF\xD9':#check end marker JPEG
            #    break
      
        print(len(cl_send))
        print(cl_send[:2])
        print(cl_send[-5:-3])
        print(cl_send[-3:])
        
        if cl_send.startswith(b'\xFF\xD8'):# and data.endswith(b'\xFF\xD9'):  # Check if data starts with JPEG header
            # It's an image
            # Process image data as needed
            # Example: Write image data to a file
            
            f = open("received_image.jpg", "wb")
            f.write(cl_send[:-3])
            print("Received image, length:", len(cl_send[:-3]))
            f.close()
            # Display the received image using Pygame
            string_data = cl_send[-3:].decode('utf-8')
            try:
                surface = pygame.image.load("received_image.jpg").convert()
                screen.blit(surface, (0, 0))
                pygame.display.update()
                print("Received image successfully")
            except Exception as e:
                print(e)
            if string_data == "non":
                conn.settimeout(5)
                try:
                    message = input("Enter your message: ")
                    #message = "thuan"
                    conn.send(message.encode())
                    if not (message==''):
                        break
                except socket.timeout:
                    print('No connection received within the timeout period. Exiting')
                    sys.exit(1)
            else: 
                print('Have subcribed')
                
                time.sleep(1)#
    conn.close()
    print("Receive thread ended")

def receiveThread1(conn): #Receive image and string both
    conn.settimeout(10)
    conn_end = False
    pack_size = 1024*5
    cl_send = b""
    while True:
        if conn_end:
            break
        
        # Receive data
        while not cl_send[-6:-4] == b'\xFF\xD9':
            try:
                data = conn.recv(4096)
            except socket.timeout:
                conn_end = True
                break
            cl_send += data
            #if img[-2:] == b'\xFF\xD9':#check end marker JPEG
            #    break
      
        print(len(cl_send))
        print(cl_send[:2])
        print(cl_send[-6:-4])
        print(cl_send[-4:])
        
        if cl_send.startswith(b'\xFF\xD8'):# and data.endswith(b'\xFF\xD9'):  # Check if data starts with JPEG header
            # It's an image
            # Process image data as needed
            # Example: Write image data to a file
            #with open("received_image.jpg", "wb") as f:
            f = open("received_image.jpg", "wb")
            f.write(cl_send[:-4])
            print("Received image, length:", len(cl_send[:-4]))
            f.close()
            # Display the received image using Pygame
            string_data = cl_send[-4:].decode('utf-8')
            print("Name: ", string_data)
            cl_send = b"" #evade message keep prints in terminal althoungh client doesn't send anything
            string_data = b""
            try:
                surface = pygame.image.load("received_image.jpg").convert()
                screen.blit(surface, (0, 0))
                pygame.display.update()
                print("Received image successfully")
            except Exception as e:
                print(e)
                #break
            except UnicodeDecodeError: #evade message keep prints in terminal althoungh client doesn't send anything
                break
        # else:
        #     # It's a string
        #     try:
        #         string_data = data.decode('utf-8')
        #         print("Received string:", string_data)
        #     # Process string data as needed
        #     except UnicodeDecodeError:
        #         break

    conn.close()
    print("Receive thread ended")

def receiveThread(conn): #Receive image only
    conn.settimeout(10)
    conn_end = False
    pack_size = 1024*5
    while True:
        if conn_end:
            break
        #char_data = b"" 
        img = b"" #the complete img data received from the cilent
        tmp = b'' #stores the last byte received to assist detecing the start marker of the img. it helps identify the start of the new img segment
        while True: #It ensures that the image data is correctly captured even if it is received in multiple segments.
            try:
                client_data = conn.recv(1)
            except socket.timeout:
                conn_end = True
                break
            
            if tmp == b'\xFF' and client_data == b'\xD8':
                img = b'\xFF\xD8' #check start marker JPEG
                
                break #it checks if the combination of the last received byte (tmp) and the current byte (client_data) forms the start marker of a JPEG image (\xFF\xD8). If so, it initializes the img variable with this start marker (b'\xFF\xD8') and breaks out of the loop.
            tmp = client_data
        while True:
            try:
                client_data = conn.recv(4096) #client 2048 bytes but server can receive more 
            except socket.timeout:#break the while loop (line 21,36)
                client_data = None
                conn_end = True 
            if not client_data:
                break
            # print("received data,len:",len(client_data) )
            img += client_data
            if img[-2:] == b'\xFF\xD9':#check end marker JPEG
                break
            if len(client_data) > pack_size: #breaks out of the loop to prevent receiving too much data.
                break

        print("recive end, pic len:", len(img))
        print(img[:2])
        print(img[-2:])
        if not img.startswith(b'\xFF\xD8') or not img.endswith(b'\xFF\xD9'):
            print("image error") #If the received data does not start or end with these markers, it implies that the received data is not a complete JPEG image
            continue
        f = open("tmp.jpg", "wb")
        f.write(img)
        f.close()
        try:
            surface = pygame.image.load("tmp.jpg").convert()
            # Loads the image from the file "tmp.jpg" into a Pygame surface and converts it to a format suitable for display.
            screen.blit(surface, (0, 0))
            pygame.display.update()
            #Updates the display to show the newly blitted image.
            print("recieve ok")
        except Exception as e:
            print(e)
        ###############
        conn.settimeout(5)
        try:
            message = input("Enter your message: ")
            #message = "thuan"
            conn.send(message.encode())
            print("ssS")
            if not (message==''):
                break
        except socket.timeout:
            print('No connection received within the timeout period. Exiting')
            sys.exit(1)
        ##################
    conn.close()
    print("receive thread end")

def server(): # This allows the server to handle multiple clients concurrently.
    while True:
        conn, addr = sk.accept()
        print("hello client,ip:")
        print(addr)
        t = threading.Thread(target=receiveThread, args=(conn,))
        t.setDaemon(True)
        t.start()

def start_tcp_server( ip, port): #Send string
    #create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #sock.settimeout(10)
    server_address = (ip, port)
    #bind port
    print('starting listen on ip %s, port %s' % server_address)
    sock.bind(server_address)
    #starting listening, allow only one connection
    try:
        sock.listen(1)
    except socket.error as e:
        print("fail to listen on port %s" % e)
        sys.exit(1)
    while True:
        sock.settimeout(20) 
        try: 
            print("waiting for connection")
            client, addr = sock.accept()
            print('having a connection')
            # message = "thuan"
            # client.send(message.encode())
            while True:
                #client.send(b'I am server')
                print((client.recv(20)).decode())
                message = input("Enter your message: ")
                #message = "thuan"
                client.send(message.encode())
                if not (message==''):
                    break
            #print('send OSError: [Errno 128(32)] EIO')
            client.close()
        except socket.timeout:
            print('No connection received within the timeout period. Exiting')
            sys.exit(1)

def start_tcp_serverre(ip, port): #Receive string
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (ip, port)
        sock.bind(server_address)
        sock.listen(1)
        print(f"Listening on {ip}:{port}")

        while True:
            print("Waiting for connection...")
            client, addr = sock.accept()
            print(f"Connected to {addr}")

            try:
                while True:
                    data = client.recv(1024).decode()  # Receive data from client
                    if not data:
                        break  # Connection closed by client
                    print(f"Received data: {data}")
                    # Process the received data (e.g., handle commands)
                    if data == "exit":
                        break

                    # Send a response back to the client (optional)
                    response = input("Enter your response: ")
                    client.send(response.encode())

            except Exception as e:
                print(f"Error handling client: {e}")
            finally:
                client.close()

    except Exception as e:
        print(f"Error setting up server: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    pygame.init() #Initializes Pygame modules
    screen = pygame.display.set_mode((width, height), 0, 32)
    #Creates a Pygame window with the specified width and height, using a 32-bit color depth
    pygame.display.set_caption("pic from client")

    ip_port = (local_ip, local_port)
    sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM) ##TCP
    sk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #Sets a socket option to allow the reuse of the socket address.
    #This is useful when the server needs to restart quickly after being stopped.
    sk.bind(ip_port)
    sk.listen(50)
    print("accept now, wait for client")
    tmp = threading.Thread(target=server, args=())
    tmp.setDaemon(True)
    tmp.start() # allowing the server to accept and handle client connections while the main program continues to execute.

    while True:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit()
    #start_tcp_serverre(local_ip,local_port)
    #start_tcp_server(local_ip,local_port,socket.socket(socket.AF_INET, socket.SOCK_STREAM))
