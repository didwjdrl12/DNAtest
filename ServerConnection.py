import socket, time, threading, ipaddress, traceback
from pymavlink import mavutil

from pymavlink.dialects.v20 import cms as mavlink2   ## cms.xml Include 하여 Mavlink Generate 후 선언

# 210426 Jeonggi Yang
import os


################################################# 테스트 환경에 맞게 설정 필요 ###############################################
# TC Receive IP/Port(GCS로 부터 TC 수신 할 드론의 IP/Port 정보)
RECEIVE_IP = "192.168.1.53"
RECEIVE_PORT = 10001

# 연결관리서버로 부터 응답메시지 받을 포트 정보
CMS_RECEIVE_PORT = 14550

# CMS(연결관리서버) 연결 정보
#CMS_IP = "112.216.221.96" # Soletop CMS
CMS_IP = "129.254.221.96" # ETRI
# CMS_IP = "192.168.0.17" 
CMS_PORT = 25000
CMS_addr = (CMS_IP, CMS_PORT)

# mav 인스턴스 설정
mav = mavlink2.MAVLink("")
# Drone SysID 설정
mav.srcSystem = 13 # It should be the same with the drone's MAVLINK SYS ID


################################################# 설정 불필요 #############################################
# RelayServer 연결 정보(연결관리서버로 부터 수신 받음)
RELAYSERVER_IP = ""
RELAYSERVER_PORT = 0
RELAYSERVER_addr = (RELAYSERVER_IP, RELAYSERVER_PORT)

# MediaServer 연결 정보(연결관리서버로 부터 수신 받음)
MEDIASERVER_IP = ""
MEDIASERVER_PORT = 0
MEDIASERVER_addr = (MEDIASERVER_IP, MEDIASERVER_PORT)

# 시뮬레이터 이름 및 타입 설정
simulatorName = "Drone {0}".format(mav.srcSystem)
deviceType = 0



## 연결관리서버로 정보 요청(50000)/응답(50001) 받는 함수
def Create_50000_Message():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
    sock.bind(('', CMS_RECEIVE_PORT))

    try:
        # 50000 생성 후 전송
        if deviceType == 0: # 드론
            # 요청 메시지(50000) 생성
            msg = mavlink2.MAVLink_connection_info_request_message(mav.srcSystem, deviceType).pack(mav, force_mavlink1=False)

        sock.sendto(msg, CMS_addr) # 요청 메시지(50000) 전송

        print("Connection Info Request Message(50000) Send Complete!!")

        # Data Receive Blocking
        data, addr = sock.recvfrom(1024)

        # decode an incoming message
        m2 = mav.decode(bytearray(data))
        print("%s Decoding message... %d" % (simulatorName, m2.get_msgId()))

        # 연결정보 응답(50001) 수신 후 Parsing
        if m2.get_msgId() == 50001:
            drone_id = m2.drone_id
            validate_result = m2.validate_result

            relayserver_ip = m2.relayserver_ip
            relayserver_port = m2.relayserver_port
            mediaserver_ip = m2.mediaserver_ip
            mediaserver_port = m2.mediaserver_port

            rs_conn_IP = ipaddress.ip_address(relayserver_ip).compressed # RelayServer IP주소 String 형태로 변환
            ms_conn_IP = ipaddress.ip_address(mediaserver_ip).compressed # MediaServer IP주소 String 형태로 변환

            # RelayServer IP/Port 정보 설정
            global RELAYSERVER_IP
            global RELAYSERVER_PORT
            RELAYSERVER_IP = rs_conn_IP
            RELAYSERVER_PORT = relayserver_port

            # MediaServer IP/Port 정보 설정
            global MEDIASERVER_IP
            global MEDIASERVER_PORT
            MEDIASERVER_IP = ms_conn_IP
            MEDIASERVER_PORT =  mediaserver_port

            print("연결정보 수신 = \n SysID : %d \n RelayServerIP : %s \n RelayServerPort : %d \n MediaServerIP : %s \n MediaServerPort : %d" % (drone_id, rs_conn_IP, relayserver_port, ms_conn_IP, mediaserver_port))

            return True

        else:
            return False


    except Exception as e:
        print("연결정보 획득 실패 EX=", e)
        return False


# 릴레이서버로 TM 전송하는 클래스
class SenderSimulator(threading.Thread):
    def __init__(self, sendIP, sendPORT):
        threading.Thread.__init__(self)
        self.daemon = True  # 데몬 쓰레드 여부 설정(True = 메인 쓰레드 종료시 같이 종료됨)

        self.sendIP = sendIP
        self.sendPORT = sendPORT

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP

        while True:
            try:
                # Relay 서버로 Heartbeat 전송(1초 주기)
                sock.sendto(
                    mavlink2.MAVLink_heartbeat_message(mavutil.mavlink.MAV_TYPE_GCS,mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0, 1
                    ).pack(mav, force_mavlink1=False), (self.sendIP, self.sendPORT))

                time.sleep(1.0)

            except Exception as e:
                print("SenderSimulator 예외가 발생하였습니다. EX=", e)


# TC 수신 클래스
class ReceiverSimulator(threading.Thread):
    def __init__(self, receiveIP, receivePORT):
        threading.Thread.__init__(self)
        self.daemon = True  # 데몬 쓰레드 여부 설정(True = 메인 쓰레드 종료시 같이 종료됨)

        self.receiveIP = receiveIP
        self.receivePORT = receivePORT

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        sock.bind((self.receiveIP, self.receivePORT))
        
        while True:
            try:
                data, addr = sock.recvfrom(1024)

                # decode an incoming message
                m2 = mav.decode(bytearray(data))
                print(">>>>>>>>>> Receive message : msgId = #%d" % (m2.get_msgId()))

            except Exception as e:
                print("%s 에서 예외가 발생하였습니다. %s" % (simulatorName, e))



if __name__ == '__main__':

    if not RECEIVE_IP :  # IP 가 null or empty 일 경우
        RECEIVE_IP = socket.gethostbyname(socket.getfqdn()) # LocalHost 주소 받아오기
    PIXHAWK_PORT = "/dev/ttyTHS0:115200"
    while True:
        try:
            # 연결정보(50000) 요청 하기
            if Create_50000_Message() == True:
                #os.environ["RELAYSERVER_IP"] = RELAYSERVER_IP
                RELAYSERVER_IP_PORT = RELAYSERVER_IP + ':' + str(RELAYSERVER_PORT)
                command = "mavlink-routerd -e "+ RELAYSERVER_IP_PORT +" -e 127.0.0.1 " + PIXHAWK_PORT
                print(command)
                os.system(command) # connect mavlink router")
                while(1):
                    pass
                break
            else:
                print("%s 연결정보 획득 실패!!" % simulatorName)

        except Exception as e:
            print("Exception EX=", e)
