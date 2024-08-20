import KPU as kpu
import micropython, random
import time, network, gc, sys
import socket, sensor, image, lcd, utime

from Maix import GPIO
from fpioa_manager import fm
from board import board_info
fm.register(board_info.BOOT_KEY, fm.fpioa.GPIOHS0)

start_processing = False  # Global variable to check button press state
BOUNCE_PROTECTION = 50


def set_key_state(*_):
    global start_processing
    start_processing = True
    utime.sleep_ms(BOUNCE_PROTECTION)



key_gpio = GPIO(GPIO.GPIOHS0, GPIO.IN)
key_gpio.irq(set_key_state, GPIO.IRQ_RISING, GPIO.WAKEUP_NOT_SUPPORT)


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

SSID = "ECLO"
PASW = "www.eclo.vn"

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

def face_rec():#should be 85
    global start_processing
    anchor = (1.889, 2.5245, 2.9465, 3.94056, 3.99987, 5.3658, 5.155437,
              6.92275, 6.718375, 9.01025)  # anchor for face detect
    try:
        task_fd = None
        task_fd = kpu.load(0x300000)
        a = kpu.init_yolo2(task_fd, 0.5, 0.3, 5, anchor)
        start_time = time.ticks_ms()
        while True:
            img = sensor.snapshot()
            clock.tick()
            code = kpu.run_yolo2(task_fd, img)
            if code:
                for i in code:
                    a = img.draw_rectangle(i.rect())

                if start_processing:
                    img.save('face.jpg',quality=70,overwrite=True) #former 40

                    micropython.schedule(send_file_to_server,'face.jpg')
                    start_processing = False
                    #break #just take 1 pic
            a = lcd.display(img)
            elapsed_time = time.ticks_diff(time.ticks_ms(), start_time)
            if elapsed_time > 40000:  # 20 seconds
                print("20 seconds elapsed. Turning off camera.")
                break
    except Exception as e:
        raise e
    finally:
        gc.collect()
        if not task_fd is None:
            kpu.deinit(task_fd) # reInitializes KPU


try:
    import usocket as socket
except:
    import socket

def send_file_to_server(file_path):
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    url = '/users/check-in'
    host = '192.168.1.200'
    port = 8081

    # Read the file content
    with open(file_path, 'rb') as f:
        file_content = f.read()

    # Create the multipart form-data content
    data = (
        "--" + boundary + "\r\n"
        "Content-Disposition: form-data; name=\"image\"; filename=\"" + file_path + "\"\r\n"
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode('utf-8') + file_content + ("\r\n--" + boundary + "--\r\n").encode('utf-8')
    content_length = len(data)

    # Construct the HTTP request
    request = (
        "POST " + url + " HTTP/1.1\r\n"
        "Host: " + host + ":" + str(port) + "\r\n"
        "Content-Type: multipart/form-data; boundary=" + boundary + "\r\n"
        "Content-Length: " + str(content_length) + "\r\n"
        "Connection: close\r\n\r\n"
    ).encode('utf-8') + data

    # Create a socket and connect to the server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))

    s.settimeout(10)  # Timeout set to 10 seconds

    try:
        # Send the request in chunks
        total_sent = 0
        while total_sent < len(request):
            sent = s.send(request[total_sent:total_sent + 2048])
            if sent == 0:
                raise RuntimeError("Socket connection broken")
            total_sent += sent

        # Receive the server's response (handle as needed)
        try:
            response = s.recv(1024)
            print('Server response:', response.decode('utf-8'))
        except socket.timeout:
            print("Receiving data from the server timed out")

    except Exception as e:
        print("Socket error: ",e)
    finally:
        # Close the socket
        s.close()


if __name__ == "__main__":
    # It is recommended to callas a class library (upload network_espat.py)

    # from network_esp32 import wifi
    if wifi.isconnected() == False:
        check_wifi_net()
    print('network state:', wifi.isconnected(), wifi.ifconfig())
    clock = time.clock()
    init_lcd()

    try:
        face_rec()
    except OSError as e:
        print('stop camera')
    finally:
        gc.collect()

