import socket
import datetime
import time
import simpy
import random
import time # *221031 삭제해라

'''
Server : Python / Client : Unity (C#)

[221013] 단독 운용 모드는 비행갑판, 정비구역, 엘리베이터가 한번에 연동되어 흘러감
'''

class SocketProgramming():
    def __init__(self, HOST, PORT):
        self.TCP_IP = HOST
        self.TCP_PORT = PORT

#region << Unity C# -> SimPy : 운용자 입력 정보들 >>
    def MakeSocketforSimPy(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.TCP_IP, self.TCP_PORT))
        self.server_socket.listen()

        self.client_socket, self.addr = self.server_socket.accept()
        time.sleep(2) # 얘 없애면 아무것도 없는 정보 들어온다..! 유니티 쓰레깅
        self.ConnentSocketforSimPy()

    def ConnentSocketforSimPy(self):
        print('파이썬 실행 및 Unity Client 접속 완료!')
        self.CommunicationforSimPy()

    def CommunicationforSimPy(self):
        Receiveddata = self.client_socket.recv(1024).decode()

        #region << Unity C#으로부터 수신한 데이터 Processing >>
        Aircrafts_Less = Receiveddata.replace("\x07\x00\x00\x00", "") # F35B#i의 i < 10
        Aircrafts_More = Aircrafts_Less.replace("\x08\x00\x00\x00", "") # i >= 10

        Resources_Less = Aircrafts_More.replace("\x02\x00\x00\x00", "") # Resource 개수, i < 10
        Resources_More = Resources_Less.replace("\x03\x00\x00\x00", "") # i >= 10

        FinishProcessing = Resources_More.replace("\x04\x00\x00\x00", "")
        #endregion << 수신한 데이터 Processing >>
        
        global Infos
        Infos = FinishProcessing
        print("Infos from Unity C# :", Infos)

        ToClientFirst = "Success" # "Success" 값 바꾸지 말기
        Senddata = ToClientFirst.encode()
        SendLength = len(Senddata)

        self.client_socket.sendall(SendLength.to_bytes(4, byteorder='big'))
        self.client_socket.sendall(Senddata)

    def socketClose(self): # *221028
        self.server_socket.close()
#endregion << Unity C# -> SimPy : 운용자 입력 정보들 >>

    def MakeSocket(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.TCP_IP, self.TCP_PORT))
        self.server_socket.listen()

        self.client_socket, self.addr = self.server_socket.accept()
        time.sleep(3) # 얘 없애면 아무것도 없는 정보 들어온다..! 유니티 쓰레깅 / 5초에서 3초로, 220728 수정

    def ServerSend(self, AircraftNameandProcess): # (To. 유니티) 이동 시간 알려줘
        FuncCallToClient = AircraftNameandProcess
        Senddata = FuncCallToClient.encode()
        SendLength = len(Senddata)

        self.client_socket.sendall(SendLength.to_bytes(4, byteorder='big'))
        self.client_socket.sendall(Senddata)

    def ServerReceive(self): # (From. 유니티) 이동 시간 수신
        ReceiveCheck = len(self.client_socket.recv(1024).decode()) # 유니티로부터 수신한 데이터의 길이
        while True:
            if ReceiveCheck > 0:
                break

        TransferTimefromUnity = float(self.client_socket.recv(1024).decode())
        return TransferTimefromUnity

#region << Hangar의 Unity C# <-> SimPy >>
    def HangarMakeSocket(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.TCP_IP, self.TCP_PORT))
        self.server_socket.listen()

        self.client_socket, self.addr = self.server_socket.accept()
        #time.sleep(3)

    def HangarServerSend(self, HangarSignal): #Send
        FuncCallToClient = HangarSignal
        Senddata = FuncCallToClient.encode()
        SendLength = len(Senddata)

        self.client_socket.sendall(SendLength.to_bytes(4, byteorder='big'))
        self.client_socket.sendall(Senddata)

    def HangarServerReceive(self): #Receive
        HangarReceiveddata = self.client_socket.recv(2048).decode() # [221030] stream의 크기(버퍼사이즈라고 하나?)를 1024->2048로 바꾸니까 된다..아 근데 소켓 공부가 더 필요할거같은디
        return HangarReceiveddata     
#endregion << Hangar의 Unity C# <-> SimPy >>

class FilghtDeck(object):
    def __init__(self, env, STOVList):
        self.env = env
        self.STOVList = STOVList
        self.Start = self.env.process(self.AboutTakeOff())
        SocketCommunication.MakeSocket() # 유니티와의 내부 연동을 위한 "소켓 생성"

    def AboutTakeOff(self): # 함재기 이륙 관련 작업
        for i in self.STOVList:
            SName = i

            #print(SName, round(self.env.now, 2)) # *확인완료*

            with TakeOffSpot.request() as req:
                yield req

                # ★ (1) A구역의 함재기 -> 이륙 장소[Taxiing]
                SName_Process_Time = SName + ",ToTakeOff" + ",0.0" # (To. Unity) Taxiing 함수 Call
                SocketCommunication.ServerSend(SName_Process_Time)
                TransferTime = SocketCommunication.ServerReceive() # - (From. Unity) 함재기 이동 소요 시간 수신 -
                yield self.env.timeout(TransferTime)
                print(SName, "이륙 장소로 이동 완료", round(self.env.now, 2))

                # (2) 함재기 이륙
                TakeOffTime = random.uniform(2, 7) # - 이륙 소요 시간 -
                TakeOffTime_STR = str(TakeOffTime)
                SName_Process_Time = SName + ",TakeOff," + TakeOffTime_STR
                SocketCommunication.ServerSend(SName_Process_Time)
                ProcessFinishSignal = SocketCommunication.ServerReceive() # (From. Unity) "0.0"(초) 수신 -> 해당 작업이 끝났다는 신호로만 이해하면 됨
                yield self.env.timeout(TakeOffTime)
                print(SName, "이륙 완료", round(self.env.now, 2))

                self.env.process(self.Mission(SName))

    def Mission(self, SName): # 함재기 임무 수행 작업
        # (3) 함재기 임무 수행
        #print(SName, "임무 수행 시작", round(self.env.now, 2)) # *확인완료*
        MissionTime = random.uniform(60, 120) # - 임무 소요 시간 -
        MissionTime_STR = str(MissionTime)
        SName_Process_Time = SName + ",Mission," + MissionTime_STR
        SocketCommunication.ServerSend(SName_Process_Time)
        ProcessFinishSignal = SocketCommunication.ServerReceive()
        yield self.env.timeout(MissionTime)
        print(SName, "임무 수행 완료", round(self.env.now, 2))

        yield self.env.process(self.WaitTakeOffSpotforLand(SName))

    # 220913 추가 /  220907와 다른 점 X
    def WaitTakeOffSpotforLand(self, SName): # [이륙 장소(TakeOffSpot)가 비어있지 않다 = 어떠한 함재기가 이륙 준비 or 이륙 중 => 착륙하면 안돼!
        with TakeOffSpot.request() as req:
            yield req

            yield self.env.process(self.Land(SName))
    # 재성 레드자원 테스트
    def Land(self, SName):  # ★ 착륙 작업 및 착륙 장소의 함재기가 A구역으로 이동하는 작업[Towbar Tractor]
        with LandingSpot.request() as req:
            yield req

            # (4) 함재기 착륙
            LandingTime = random.uniform(2, 3) # - 착륙 소요 시간 -
            LandingTime_STR = str(LandingTime)
            SName_Process_Time = SName + ",Land," + LandingTime_STR
            SocketCommunication.ServerSend(SName_Process_Time)
            ProcessFinishSignal = SocketCommunication.ServerReceive()
            yield self.env.timeout(LandingTime) 
            print(SName, "착륙 완료", round(self.env.now, 2))

            # ShutDownTime, 함재기 엔진 정지도 추가 필
            # 항공요원 하차도 해야함

            # ★ (5) 착륙 장소의 함재기 -> A구역[Towbar Tractor]
            with Reds.request() as req:
                yield req

                # Towbar 트랙터 이동(자원 위치->착륙 지점) 시간 추가
                # Towbar 트랙터 체결 시간 추가
                SName_Process_Time = SName + ",ToAarea2" + ",0.0"
                SocketCommunication.ServerSend(SName_Process_Time)
                TransferTime = SocketCommunication.ServerReceive()
                yield self.env.timeout(TransferTime) # 함재기 이동 (착륙 장소->A 구역) 소요 시간
                # Towbar 트랙터 체결 해제 시간 추가
                print(SName, "A구역으로 이동 완료", round(self.env.now, 2))

        yield self.env.process(self.Inspection(SName))

    def Land(self, SName):  # ★ 착륙 작업 및 착륙 장소의 함재기가 A구역으로 이동하는 작업[Towbar Tractor]
        with LandingSpot.request() as req:
            yield req

            # (4) 함재기 착륙
            LandingTime = random.uniform(2, 3) # - 착륙 소요 시간 -
            LandingTime_STR = str(LandingTime)
            SName_Process_Time = SName + ",Land," + LandingTime_STR
            SocketCommunication.ServerSend(SName_Process_Time)
            ProcessFinishSignal = SocketCommunication.ServerReceive()
            yield self.env.timeout(LandingTime) 
            print(SName, "착륙 완료", round(self.env.now, 2))

            # ShutDownTime, 함재기 엔진 정지도 추가 필
            # 항공요원 하차도 해야함

            # ★ (5) 착륙 장소의 함재기 -> A구역[Towbar Tractor]
            with Tractors.request() as req:
                yield req

                # Towbar 트랙터 이동(자원 위치->착륙 지점) 시간 추가
                # Towbar 트랙터 체결 시간 추가
                SName_Process_Time = SName + ",ToAarea" + ",0.0"
                SocketCommunication.ServerSend(SName_Process_Time)
                TransferTime = SocketCommunication.ServerReceive()
                yield self.env.timeout(TransferTime) # 함재기 이동 (착륙 장소->A 구역) 소요 시간
                # Towbar 트랙터 체결 해제 시간 추가
                print(SName, "A구역으로 이동 완료", round(self.env.now, 2))

        yield self.env.process(self.Inspection(SName))

    def Inspection(self, SName): # 착륙 후 점검 -> 고장난 함재기 판단
        with Greens.request() as req:
            yield req

            # Green 자원 이동 시간 추가
            InspectionTime = random.uniform(10, 20)
            InspectionTime_STR = str(InspectionTime)
            SName_Process_Time = SName + ",Inspection," + InspectionTime_STR
            SocketCommunication.ServerSend(SName_Process_Time)
            ProcessFinishSignal = SocketCommunication.ServerReceive()
            yield self.env.timeout(InspectionTime)
            print(SName, "착륙 후 점검 완료", round(self.env.now, 2))

        yield self.env.process(self.Fueling(SName))

    global CheckAircraftList
    CheckAircraftList = [] # CheckAircraftList의 갯수가 4개가 되면 함재기 고장 판단하려고
    def Fueling(self, SName): # 급유
        with Purples.request() as req:
            yield req

            CheckAircraftList.append(SName)

            # Purple 자원 이동 시간 추가
            FuelingTime = random.triangular(20, 30, 40)
            FuelingTime_STR = str(FuelingTime)
            SName_Process_Time = SName + ",Fueling," + FuelingTime_STR
            SocketCommunication.ServerSend(SName_Process_Time)
            ProcessFinishSignal = SocketCommunication.ServerReceive()
            yield self.env.timeout(FuelingTime)
            print(SName, "급유 완료", round(self.env.now, 2))

        if (len(CheckAircraftList) == len(self.STOVList)):
            BrokenAircraft = random.choice(CheckAircraftList) # *221025 잠깐만 꺼둘게!!
            #BrokenAircraft = "F35B#3" # *221025 확인 후 삭제!
            print("고장난 함재기", BrokenAircraft)

            yield self.env.process(self.ToD2EV(BrokenAircraft))

    def ToD2EV(self, BrokenAircraft): # BrokenAircraft -> 고장난 함재기 이동
        with Tractors.request() as req:
            yield req

            # Towbar 트랙터 이동(자원 위치->착륙 지점) 시간 추가
            # Towbar 트랙터 체결 시간 추가
            BrokenName_Process_Time = BrokenAircraft + ",ToD2EV" + ",0.0"
            SocketCommunication.ServerSend(BrokenName_Process_Time)
            TransferTime = SocketCommunication.ServerReceive()
            yield self.env.timeout(TransferTime) # 함재기 이동 (착륙 장소->A 구역) 소요 시간
            # Towbar 트랙터 체결 해제 시간 추가
            print(BrokenAircraft, "D2 엘레베이터로 이동 완료", round(self.env.now, 2))

        yield self.env.process(self.ToHangar(BrokenAircraft))
            
    def ToHangar(self, BrokenAircraft): # 고장난 함재기 정비구역으로
        with D2Elevator.request() as req:
            yield req
            
            D2EV_Velocity = EV_Velocity[1] #엘리베이터 속도 받아와서 시간 계산하기
            D2EV_TransferTime = 10.3 / float(D2EV_Velocity) # 10.3:Unity 모델에서 계측한 엘베 높이
            
            D2EV_Time_STR = str(D2EV_TransferTime) 
            BrokenName_Process_Time = BrokenAircraft + ",ToHangar," + D2EV_Time_STR
            SocketCommunication.ServerSend(BrokenName_Process_Time)
            #ProcessFinishSignal = SocketCommunication.ServerReceive() # *221027-주석처리 유니티로부터 0.0의 값을 받을 것
            yield self.env.timeout(D2EV_TransferTime)
            
            print(BrokenAircraft, "Hangar로 이동 완료", round(self.env.now, 2))

            print("갑판 시뮬레이션 완성!")
            #SocketCommunication.socketClose() # *221028 추가, *221031 주석처리, *221102 주석처리해제, *221102 주석처리-> 이래도 비행갑판에서 씬 바꼈을 때 통신이 안되네..
            
        HangarSimulation = Hangar(env) # Hangar 클래스의 인스턴스 생성 *221028

class Hangar(object): # 220918 일단 정비구역 내 함재기 이동만 구현 / 221028 여기로 들어오는거 확인
    def __init__(self, env):
        self.env = env
        SocketCommunication.MakeSocket() # 안해주면 행거의 소켓 연결 불가
        self.Start = self.env.process(self.MoveinHangar())

    def MoveinHangar(self): # 정비구역 내, 함재기 이동 관련 작업
        while(True):
            HangarReceiveddata = SocketCommunication.HangarServerReceive()
            if(len(HangarReceiveddata)>0): # 유니티로부터 어떠한 정보를 받으면
                break;
  
        AircraftName_TransferTime = HangarReceiveddata.split(',')

        if(len(AircraftName_TransferTime)==2): # 장애물 함재기 이동 시
            Obs_AircraftName = AircraftName_TransferTime[0]
            Obs_TransferTime = float(AircraftName_TransferTime[1])
            print("장애물 함재기 이름:", Obs_AircraftName, Obs_TransferTime)
        
            yield self.env.timeout(Obs_TransferTime)

            self.env.process(self.MoveinHangar()) # 유니티가 보내는 정보 받아오려고 MoveinHangar() 다시 Call
            print(Obs_AircraftName, "[Hangar] 장애물 함재기 이동 완료", round(self.env.now, 2))

        else: # 목표 함재기 이동 시, len(~):3
            New_AircraftName = AircraftName_TransferTime[0]
            New_TransferTime = float(AircraftName_TransferTime[1])

            print("목표한 이동 함재기 이름:", New_AircraftName, "목표 함재기 이동 시간:", New_TransferTime)
        
            yield self.env.timeout(New_TransferTime)
            print(New_AircraftName, "[Hangar] 목표 함재기 이동 완료", round(self.env.now, 2))

            # sendserver D1 엘리베이터 이용해서 올리자!
            SocketCommunication.HangarServerSend("GotoDeck")

            SocketCommunication.HangarMakeSocket() # ★★★★ 여기서 유니티가 정비구역->갑판으로 씬이 바뀌니까 소켓을 다시 켜줘야 함! ★★★★
            yield self.env.process(self.ToDeck(New_AircraftName))

            #Simulation.ToDeck(New_AircraftName) # *221031 안들어가지네.. 왜지     

    def ToDeck(self, NewAircraft): # 대체할 새로운 함재기 비행갑판으로
        with D1Elevator.request() as req:
            yield req
            
            D1EV_Velocity = EV_Velocity[0] #엘리베이터 속도 받아와서 시간 계산하기
            D1EV_TransferTime = 10.3 / float(D1EV_Velocity) # 10.3:Unity 모델에서 계측한 엘베 높이
            print("D1EV_TransferTime :", D1EV_TransferTime)

            D1EV_Time_STR = str(D1EV_TransferTime)
            NewName_Process_Time = NewAircraft + ",ToDeck," + D1EV_Time_STR
           
            #SocketCommunication.HangarServerSend(NewName_Process_Time)
            SocketCommunication.ServerSend(NewName_Process_Time) # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

            ProcessFinishSignal = SocketCommunication.ServerReceive() # 221102 여기서 에러 발생
            yield self.env.timeout(D1EV_TransferTime)
            
            print(NewAircraft, "Deck로 이동 완료", round(self.env.now, 2))

            print("정비구역 시뮬레이션 완성!")

SocketCommunication = SocketProgramming("127.0.0.1", 6500)
SocketCommunication.MakeSocketforSimPy()

# 아래는 SimPy 관련 정보 및 SimPy 실행
SimPyData = Infos
print("Data using SimPy :", SimPyData)
# [221013] 단독 운용 모드에서, 사용자가 입력한 정보를 비행갑판, 정비구역, 엘리베이터 구역 별로 나눠서 데이터를 정리해야 함

Deck_AircraftList = SimPyData.split('@') # 결과값의 형태는 List
forDeckResource = Deck_AircraftList[-1]
Deck_AircraftList.pop(-1)
print("Deck_AircraftList", Deck_AircraftList)

Deck_ResourceList = forDeckResource.split('$')
forHangarAircraft = Deck_ResourceList[-1]
Deck_ResourceList.pop(-1) 
print("Deck_ResourceList :", Deck_ResourceList)

Hangar_AircraftList = forHangarAircraft.split('%')
forHangarResource = Hangar_AircraftList[-1]
Hangar_AircraftList.pop(-1)
print("Hangar_AircraftList :", Hangar_AircraftList)

Hangar_ResourceList = forHangarResource.split('&')
forElVelos = Hangar_ResourceList[-1]
Hangar_ResourceList.pop(-1)
print("Hangar_ResourceList :", Hangar_ResourceList)

EV_Velocity = forElVelos.split('^')
EV_Velocity.pop(-1) # 마지막으로 남은 빈칸('') 빼는거
print("EV_Velocity :", EV_Velocity)

# SimPy 구현을 위한 관련 정보들
env = simpy.Environment()

TakeOffSpot = simpy.Resource(env, capacity=1)
LandingSpot = simpy.Resource(env, capacity=1)

D1Elevator = simpy.Resource(env, capacity=1) # D1Elevator : 정비구역 -> 갑판
D2Elevator = simpy.Resource(env, capacity=1) # D2Elevator : 갑판 -> 정비구역

# FlightDeck의 장비,인적 자원
Tractors = simpy.Resource(env, capacity= int(Deck_ResourceList[0])) # Tractors : Towbar Tractor
Reds = simpy.Resource(env, capacity= int(Deck_ResourceList[1])) 
Browns = simpy.Resource(env, capacity= len(Deck_AircraftList)) # or int(Deck_ResourceList[2])
Purples = simpy.Resource(env, capacity= int(Deck_ResourceList[3]))
Greens = simpy.Resource(env, capacity= int(Deck_ResourceList[4]))
# Players = simpy.Resource(env, capacity= int(Deck_ResourceList[5])) #//재성 이거 수정함

# Hangar의 장비,인적 자원
#Hangar_Tractors = simpy.Resource(env, capacity= int(ResourceList[0])) # Hangar_Tractors : Towbarless Tractor
#Hangar_Greens = simpy.Resource(env, capacity= int(ResourceList[1]))

SocketCommunication.socketClose() # *221028 추가, 필요한가....?

Simulation = FilghtDeck(env, Deck_AircraftList) # FilghtDeck 클래스의 인스턴스 생성
#HangarSimulation = Hangar(env) # Hangar 클래스의 인스턴스 생성 -> 여기서 부르면 비행갑판에서 비행기가 안움직임(221028)
env.run()


#client_socket.close()
#server_socket.close()