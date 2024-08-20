# Untitled - By: DELL - Wed Apr 17 2024

import time, network, gc, sys
import socket, sensor, image, lcd, utime
import KPU as kpu
import micropython
import utime
from Maix import GPIO
from fpioa_manager import fm
from board import board_info
fm.register(board_info.BOOT_KEY, fm.fpioa.GPIOHS0)
face_saved=False
sendrec = False
send_suc = False
start_processing = False
tmp = ""
fin = False
class wifi():

    nic = None

    def reset(force=False, reply=5, is_hard=True):
        if force == False and __class__.isconnected():
            return True
        try:
            # IO map for ESP32 on Maixduino
            fm.register(25,fm.fpioa.GPIOHS10)#cs
            fm.register(8,fm.fpioa.GPIOHS11)#rst
            fm.register(9,fm.fpioa.GPIOHS12)#rdy

            if is_hard:
                print("Use Hareware SPI for other maixduino")
                fm.register(28,fm.fpioa.SPI1_D0, force=True)#mosi
                fm.register(26,fm.fpioa.SPI1_D1, force=True)#miso
                fm.register(27,fm.fpioa.SPI1_SCLK, force=True)#sclk
                __class__.nic = network.ESP32_SPI(cs=fm.fpioa.GPIOHS10, rst=fm.fpioa.GPIOHS11, rdy=fm.fpioa.GPIOHS12, spi=1)
                print("ESP32_SPI firmware version:", __class__.nic.version())
            else:
                # Running within 3 seconds of power-up can cause an SD load error
                print("Use Software SPI for other hardware")
                fm.register(28,fm.fpioa.GPIOHS13, force=True)#mosi
                fm.register(26,fm.fpioa.GPIOHS14, force=True)#miso
                fm.register(27,fm.fpioa.GPIOHS15, force=True)#sclk
                __class__.nic = network.ESP32_SPI(cs=fm.fpioa.GPIOHS10,rst=fm.fpioa.GPIOHS11,rdy=fm.fpioa.GPIOHS12, mosi=fm.fpioa.GPIOHS13,miso=fm.fpioa.GPIOHS14,sclk= fm.fpioa.GPIOHS15)
                print("ESP32_SPI firmware version:", __class__.nic.version())

            # time.sleep_ms(500) # wait at ready to connect
        except Exception as e:
            print(e)
            return False
        return True

    def connect(ssid="wifi_name", pasw="pass_word"):
        if __class__.nic != None:
            return __class__.nic.connect(ssid, pasw)

    def ifconfig(): # should check ip != 0.0.0.0
        if __class__.nic != None:
            return __class__.nic.ifconfig()

    def isconnected():
        if __class__.nic != None:
            return __class__.nic.isconnected()
        return False

SSID = "Hm"
PASW = "thuan123"

def check_wifi_net(reply=5):
    if wifi.isconnected() != True:
        for i in range(reply):
            try:
                wifi.reset(is_hard=True)
                print('try AT connect wifi...')
                wifi.connect(SSID, PASW)
                if wifi.isconnected():
                    break
            except Exception as e:
                print(e)
    return wifi.isconnected()

def init_lcd():
    lcd.init(type=1)
    lcd.rotation(0)
    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.QVGA)
    #sensor.set_hmirror(True)
    sensor.set_vflip(True)
    sensor.skip_frames(time = 2000)
    sensor.run(1)

def face_recognize(task_fe,img_face,record_ftrs):
    global max_score, feature, index
    fmap = kpu.forward(task_fe, img_face)
    feature = kpu.face_encode(fmap[:])
    reg_flag = False
    scores = []

    for j in range(len(record_ftrs)):
        score = kpu.face_compare(record_ftrs[j], feature)
        scores.append(score)
    max_score = 0
    index = 0
    for k in range(len(scores)):
        if max_score < scores[k]:
            max_score = scores[k]
            index = k
    return max_score,feature, index

def lm_detect(task_ld,img,ai,i, dst_point,img_face):

    face_cut = img.cut(i.x(), i.y(), i.w(), i.h())
    face_cut = face_cut.resize(128, 128)
    a = face_cut.pix_to_ai()
    fmap = kpu.forward(task_ld, face_cut)
    plist = fmap[:]

    le = (i.x() + int(plist[0] * i.w() - 10), i.y() + int(plist[1] * i.h()))
    re = (i.x() + int(plist[2] * i.w()), i.y() + int(plist[3] * i.h()))
    nose = (i.x() + int(plist[4] * i.w()), i.y() + int(plist[5] * i.h()))
    lm = (i.x() + int(plist[6] * i.w()), i.y() + int(plist[7] * i.h()))
    rm = (i.x() + int(plist[8] * i.w()), i.y() + int(plist[9] * i.h()))
    a = img.draw_circle(le[0], le[1], 4)
    a = img.draw_circle(re[0], re[1], 4)
    a = img.draw_circle(nose[0], nose[1], 4)
    a = img.draw_circle(lm[0], lm[1], 4)
    a = img.draw_circle(rm[0], rm[1], 4)

    src_point = [le, re, nose, lm, rm]
    T = image.get_affine_transform(src_point, dst_point)
    a = image.warp_affine_ai(img, img_face, T)
    a = img_face.ai_to_pix()
    del(face_cut)
    del(T)
    del(le,re,nose,lm,rm)
    return a, img_face

def save_names(result):
    global data_received
    data_received = result

def face_detect(ACCURACY=70):#should be 85
    global start_processing,face_saved, sendrec, tmp
    anchor = (1.889, 2.5245, 2.9465, 3.94056, 3.99987, 5.3658, 5.155437,
              6.92275, 6.718375, 9.01025)  # anchor for face detect
    dst_point = [(44, 59), (84, 59), (64, 82), (47, 105),
                 (81, 105)]  # standard face key point position

    img_lcd = image.Image()#
    img_face = image.Image(size=(128, 128))
    a = img_face.pix_to_ai()
    record_ftr = []
    record_ftrs = []

    name = []
    names = []
    try:
        task_fd = None
        task_fd = kpu.load(0x300000)
        task_ld = kpu.load(0x400000)
        task_fe = kpu.load(0x500000)

        a = kpu.init_yolo2(task_fd, 0.5, 0.3, 5, anchor)

        while True:
            img = sensor.snapshot()
            clock.tick()
            code = kpu.run_yolo2(task_fd, img)
            #img_bytes = img.to_bytes() #Convert compressd img to bytes
            #print("I: ",len(img_bytes))
            if code:
                for i in code:
                    a = img.draw_rectangle(i.rect())
                    lm_detect(task_ld,img,a,i, dst_point,img_face)
                    face_recognize(task_fe,img_face,record_ftrs)
                    if max_score > ACCURACY:
                        a = img.draw_string(i.x(), i.y(), ("%s :%2.1f" % (
                            names[index], max_score)), color=(0, 255, 0), scale=2)
                        sendrec = False
                        char_data = names[index]
                    else:
                        a = img.draw_string(i.x(), i.y(), ("X :%2.1f" % (
                            max_score)), color=(255, 0, 0), scale=2)
                        sendrec = True

                    break
                #print("1",send_suc)
                #print("3",sendrec)

                if not sendrec:
                    img_bytes = img.to_bytes() #Convert compressd img to bytes
                    #print("X: ",len(img_bytes))
                    img.save("face.jpg",quality=70,overwrite=True) #former 40
                    sendrec = False
                    print("Hello, meet you again",char_data)
                    print("#############")
                    micropython.schedule(send_client,addr)
                    utime.sleep(0.5)
                else:

                    img.save("face.jpg",quality=70,overwrite=True) #former 40
                    sendrec = False
                    #micropython.schedule(send_client, addr) #it's workkkkkkkkkkkk
                    print("ready receive")
                    micropython.schedule(receive_data,addr)
                    utime.sleep(0.5)
                    while send_suc:
                        pass
                    if tmp[:3] == 'acc':
                        print("hello",tmp[3:])
                        record_ftr = feature
                        record_ftrs.append(record_ftr)
                        name = tmp[3:]
                        names.append(name)
                        print(names)
                        print("#############")

                    tmp = ""

            fps = clock.fps()
            a = lcd.display(img)
    except Exception as e:
        raise e
    finally:
        gc.collect()
        if not task_fd is None:
            kpu.deinit(task_fd) # reInitializes KPU
            kpu.deinit(task_ld)
            kpu.deinit(task_fe)

def send_client(char_data):
    #Data send include img.encode(b\xff\d8\...\xff\xd9) + str.encode(b'Mr.1')
    global fin
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    addr = ('192.168.33.218', 80)
    while True: #connect websocket
        try:
            sock = socket.socket()
            print(sock)
            sock.connect(addr)
            break
        except Exception as e:
            print("connect error:", e)
            sock.close()
            return

    try:
        with open("face.jpg", "rb") as f:
            img = f.read()
        block = int(len(img)/2048) #splits the img bytes into blocks(2048) and send them over the socket connect using sock.send()
        for i in range(block):
            send_len = sock.send(img[i*2048:(i+1)*2048]) #send the current block over the socketyo
        send_len2 = sock.send(img[block*2048:]) #after sending all block, send remaining bytes
    except Exception as e:
        print("Error sending image data:", e)
    char_data = "rec"
    try:
        char_data_bytes = char_data.encode("utf-8")
        sock.send(char_data_bytes)
    except Exception as e:
        print("Error sending char data:", e)

    sock.close()##
    #print("fps:", clock.fps())
    print("send img successfully")

def receive_data(addr):
    global send_suc
    global tmp

    send_suc = False
    print("start recognize")
    addr = ('192.168.33.218', 80)
    while True: #connect websocket
        try:
            sock = socket.socket()
            print(sock)
            sock.connect(addr)
            break
        except Exception as e:
            print("connect error:", e)
            sock.close()
            continue

     #receive data every 5s
    try:
        with open("face.jpg", "rb") as f:
            img = f.read()
        block = int(len(img)/2048) #splits the img bytes into blocks(2048) and send them over the socket connect using sock.send()
        for i in range(block):
            send_len = sock.send(img[i*2048:(i+1)*2048]) #send the current block over the socketyo
        send_len2 = sock.send(img[block*2048:]) #after sending all block, send remaining bytes
    except Exception as e:
        print("Error sending image data:", e)
    char_data = "non"
    try:
        char_data_bytes = char_data.encode("utf-8")
        sock.send(char_data_bytes)
    except Exception as e:
        print("Error sending char data:", e)


    print("subscribing.....")

    while True:
        sock.settimeout(4)
        try:
            tmp = sock.recv(16).decode('utf-8')
            #print("recv:", tmp)
            #if not tmp:  # If tmp is an empty string, indicating no more data received
                #break
            if tmp[:3] == 'acc':
                print("recv:", tmp[3:])
                break
        except socket.timeout:  # Handle timeout exception
            print("Socket timed out while receiving data")
            break
        except Exception as e:  # Handle other exceptions
            print("Error receiving data:", e)
            break
    sock.close()
    print("recv end")
    sen_suc = True
    print("2",send_suc)
    return sen_suc
    #return tmp

if __name__ == "__main__":
    # It is recommended to callas a class library (upload network_espat.py)

    # from network_esp32 import wifi
    if wifi.isconnected() == False:
        check_wifi_net()
    print('network state:', wifi.isconnected(), wifi.ifconfig())
    clock = time.clock()
    init_lcd()
    addr = ('192.168.153.218', 80)

    try:
        face_detect()   #save face img and store face img after detected in MCU


        #receive_data(addr) #send face img after detected and store input data which receive from server
    except OSError as e:
        print('stop camera')
    finally:
        gc.collect()

