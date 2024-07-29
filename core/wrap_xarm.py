from core.dobot_api import DobotApiDashboard, DobotApiFeedBack,  alarmAlarmJsonFile
from core.utils import *
import sys
import random
import csv
import keyboard
import json
import threading
import time
import re

class item:
    def __init__(self):
        self.robotErrorState = ''
        self.robotEnableStatus = 0
        self.robotMode = 0
        self.robotCurrentCommandID = 0

class xarm6(object):
    def __init__(self):
        self.armPort = 29999
        self.feedPortFour = 30004
        self.arm = None
        self.feedFour = None
        self.__globalLockValue = threading.Lock()
        self.__robotSyncBreak = threading.Event()
        self.limit_xyz = [(50, 450), (-200, 200), (0, 700),(90,180),(-60,60),(-60,60)]
        try:
            # with open(r"config.json", 'r') as file:
            with open(r"./core/config.json", 'r') as file:
                config = json.load(file)
                camerapose_string = config['camerapose']
                self.camerapose = [float(x) for x in camerapose_string.split(',')]
                self.ip = config["ip"]
        except FileNotFoundError:
            print("config.json not found.")
            raise
        except json.JSONDecodeError:
            print("Invalid JSON in config file config.json.")
            raise

        self.feedData = item()  # 定义结构对象
        self.init_robot()
    
    def __call__(self, action):
        """Calls the move(action) method with given arguments to perform grasp."""
        return self.MovJ(action,0)

    def init_robot(self):
        self.arm = DobotApiDashboard(self.ip, self.armPort)
        self.feedFour = DobotApiFeedBack(self.ip, self.feedPortFour)
        enableState = self.parseResultId(self.arm.EnableRobot())

        if enableState[0] != 0:
            print("使能失败: 检查29999端口是否被占用")
            return
        print("使能成功")

        feed_thread = threading.Thread(
            target=self.GetFeed)  # 机器状态反馈线程
        feed_thread.daemon = True
        feed_thread.start()

        feed_thread1 = threading.Thread(
            target=self.ClearRobotError)  # 机器错误状态清错线程
        feed_thread1.daemon = True
        feed_thread1.start()

        # move to init pose
        #self.move_init_pose()
        
        self.arm.User(0) #设置全局的用户坐标系
        self.arm.Tool(1) #设置全局的工具坐标系，指软件中坐标系id
        self.arm.SpeedFactor(50)
        self.arm.AccJ(50)
        self.arm.AccL(50)
        self.arm.VelJ(50)
        self.arm.VelL(50)
        self.arm.CP(1)

    def move_init_pose(self):
        self.arm.MovJ(*self.camerapose,0)

    def _move_boundary(self, action):
        new_action = []
        action = action if isinstance(action, list) else action.tolist()
        for l, a in zip(self.limit_xyz, action):
            new_action.append(max(l[0], min(l[1], a)))
        return new_action

    def move(self, action):
        #self.arm.MovJ(*self._move_boundary(action), 0)
        print(action)
        self.arm.MovJ(*action, 0)
        time.sleep(0.5)  # wait 1 s

    def move_xyz(self, xyz):
        #固定抓取位姿
        pose = [180, 0, -170]
        self.arm.MovJ(*xyz,*pose, 0)
        time.sleep(0.5)  # wait 1 s

    def get_current_pose(self):
        data = self.arm.GetPose()
        match = re.search(r'{([^}]*)}', data)
        if match:
            data = match.group(1).split(',')
            data = [float(x) for x in data]
            return data
        else:
            self.move_init_pose()
            print_and_write(None, f"Robot pose acquisition failed.", 31)
            sys.exit()

    def collect_and_save_data(self,file_name, interval):
        """
        收集并保存数据函数。

        通过键盘输入's'开始和结束数据收集，收集到的数据以csv格式保存到指定文件中。
        数据收集间隔由interval参数指定。

        :param file_name: 保存数据的文件名
        :param interval: 数据收集的间隔时间（秒）
        """
        print("请按下 's' 键开始采集数据，再次按下 's' 键结束采集数据...")
        keyboard.wait('s')
        print(f"开始采集数据，每隔{interval}秒记录一次数据...")
        self.arm.StartDrag()
        collecting = True
        def stop_collecting():
            nonlocal collecting
            collecting = False

        keyboard.add_hotkey('s', stop_collecting)

        with open(file_name, 'w', newline='') as file:
            writer = csv.writer(file)
            while collecting:
                data = self.arm.GetPose()
                match = re.search(r'{([^}]*)}', data)
                print(data)
                if match:
                    data = match.group(1).split(',')
                    data =[float(x) for x in data]
                print(data)
                writer.writerow(data)
                time.sleep(interval)

        self.arm.StopDrag()
        print(f"数据已保存到 {file_name}")

    def read_csv_and_action(self,file_name):
        """
        用于快速复现data.txt中的位姿
        读取CSV文件中的数据，并根据数据执行相应动作。
        本函数打开指定的CSV文件，逐行读取其中的数据，将每行数据转换为浮点数列表，
        然后调用self.move方法，将这个列表作为参数，执行相应的动作。

        参数:
        file_name (str): CSV文件的名称，本函数将打开这个文件进行读取。
        """
        with open(file_name, 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                action = [float(x) for x in row]
                self.move(action)

    def read_csv_and_calibrate(self,line_number,file_name = "data.csv"):
        """
        用于对数据中的特定某一行进行读取，标定的时候执行
        从CSV文件中读取指定行的数据，并根据这些数据执行校准操作。
        参数:
        line_number -- 读取的行号
        file_name -- CSV文件的名称，默认为"data.csv"

        返回:
        无
        """
        try:
            with open(file_name, 'r') as file:
                reader = csv.reader(file)
                for i, row in enumerate(reader):
                    if i == line_number:
                        action = [float(x) for x in row]
                        self.move(action)
                        return  # 读取到特定行后退出函数
                print(f"行号 {line_number} 超出范围")
        except Exception as e:
            print(f"读取文件时出错: {e}")

    def ClearRobotError(self):
        """
        清除机器人的错误状态。

        该方法通过查询机器人当前的错误状态，如果存在错误，则尝试清除错误并恢复机器人正常运行。
        """
        dataController, dataServo = alarmAlarmJsonFile()
        while True:
            self.__globalLockValue.acquire()  # robotErrorState加锁
            if self.feedData.robotErrorState:
                geterrorID = self.parseResultId(self.arm.GetErrorID())
                if geterrorID[0] == 0:
                    for i in range(1, len(geterrorID)):
                        alarmState = False
                        for item in dataController:
                            if geterrorID[i] == item["id"]:
                                print("机器告警 Controller GetErrorID",
                                      i, item["zh_CN"]["description"])
                                alarmState = True
                                break
                        if alarmState:
                            continue

                        for item in dataServo:
                            if geterrorID[i] == item["id"]:
                                print("机器告警 Servo GetErrorID", i,
                                      item["zh_CN"]["description"])
                                break

                    choose = input("输入1, 将清除错误, 机器继续运行: ")
                    if int(choose) == 1:
                        clearError = self.parseResultId(
                            self.arm.ClearError())
                        if clearError[0] == 0:
                            self.__globalLockValue.release()
                            print("--机器清错成功--")
                            break
            else:
                robotMode = self.parseResultId(self.arm.RobotMode())
                if robotMode[0] == 0 and robotMode[1] == 11:
                    print("机器发生碰撞")
                    choose = input("输入1, 将清除碰撞, 机器继续运行: ")
                    self.arm.ClearError()
            self.__globalLockValue.release()
            time.sleep(5)

    def GetFeed(self):
        """
        不断循环获取机械臂的反馈数据，并更新机器臂状态。
        """
        while True:
            feedInfo = self.feedFour.feedBackData()
            if hex((feedInfo['test_value'][0])) == '0x123456789abcdef':
                # Refresh Properties
                self.__globalLockValue.acquire()  # 互斥量    robotErrorState robotEnableStatus加锁
                self.feedData.robotErrorState = feedInfo['error_status'][0]
                self.feedData.robotEnableStatus = feedInfo['enable_status'][0]
                self.feedData.robotMode = feedInfo['robot_mode'][0]
                self.feedData.robotCurrentCommandID = feedInfo['currentcommandid'][0]
                self.__globalLockValue.release()
            time.sleep(0.01)

    def parseResultId(self, valueRecv):
        """
        解析返回值中结果ID的信息。
        """
        if valueRecv.find("Not Tcp") != -1:  # 通过返回值判断机器是否处于tcp模式
            print("Control Mode Is Not Tcp")
            return [1]
        recvData = re.findall(r'-?\d+', valueRecv)
        recvData = [int(num) for num in recvData]
        #  返回tcp指令返回值的所有数字数组
        if len(recvData) == 0:
            return [2]
        return recvData


class xarm6_grasp(object):
    def __init__(self):
        self.armPort = 29999
        self.feedPortFour = 30004
        self.arm = None
        self.feedFour = None
        self.__globalLockValue = threading.Lock()
        self.__robotSyncBreak = threading.Event()
        self.limit_xyz = [(50, 450), (-200, 200), (0, 700), (90, 180), (-60, 60), (-60, 60)]
        try:
            with open(r"config.json", 'r') as file:
            # with open(r"./core/config.json", 'r') as file:
                config = json.load(file)
                camerapose_string = config['camerapose']
                self.camerapose = [float(x) for x in camerapose_string.split(',')]
                self.ip = config["ip"]
        except FileNotFoundError:
            print("config.json not found.")
            raise
        except json.JSONDecodeError:
            print("Invalid JSON in config file config.json.")
            raise

        self.feedData = item()  # 定义结构对象
        self.init_robot()

    def __call__(self, action):
        """Calls the move(action) method with given arguments to perform grasp."""
        return self.MovJ(action, 0)

    def init_robot(self):
        self.arm = DobotApiDashboard(self.ip, self.armPort)
        self.feedFour = DobotApiFeedBack(self.ip, self.feedPortFour)
        enableState = self.parseResultId(self.arm.EnableRobot())

        if enableState[0] != 0:
            print("使能失败: 检查29999端口是否被占用")
            return
        print("使能成功")

        feed_thread = threading.Thread(
            target=self.GetFeed)  # 机器状态反馈线程
        feed_thread.daemon = True
        feed_thread.start()

        feed_thread1 = threading.Thread(
            target=self.ClearRobotError)  # 机器错误状态清错线程
        feed_thread1.daemon = True
        feed_thread1.start()

        # move to init pose
        # self.move_init_pose()

        self.arm.User(0)  # 设置全局的用户坐标系
        self.arm.Tool(1)  # 设置全局的工具坐标系，指软件中坐标系id
        self.arm.SpeedFactor(50)
        self.arm.AccJ(50)
        self.arm.AccL(50)
        self.arm.VelJ(50)
        self.arm.VelL(50)
        self.arm.CP(1)

    def move_init_pose(self):
        self.arm.MovJ(*self.camerapose, 0)

    def _move_boundary(self, action):
        new_action = []
        action = action if isinstance(action, list) else action.tolist()
        for l, a in zip(self.limit_xyz, action):
            new_action.append(max(l[0], min(l[1], a)))
        return new_action

    def move(self, action):
        # self.arm.MovJ(*self._move_boundary(action), 0)
        print(action)
        self.arm.MovJ(*action, 0)
        time.sleep(0.5)  # wait 1 s

    def move_xyz(self, xyz):
        # 固定抓取位姿
        pose = [180, 0, -170]
        self.arm.MovJ(*xyz, *pose, 0)
        time.sleep(0.5)  # wait 1 s

    def get_current_pose(self):
        data = self.arm.GetPose()
        match = re.search(r'{([^}]*)}', data)
        if match:
            data = match.group(1).split(',')
            data = [float(x) for x in data]
            return data
        else:
            self.move_init_pose()
            print_and_write(None, f"Robot pose acquisition failed.", 31)
            sys.exit()

    def collect_and_save_data(self, file_name, interval):
        """
        收集并保存数据函数。

        通过键盘输入's'开始和结束数据收集，收集到的数据以csv格式保存到指定文件中。
        数据收集间隔由interval参数指定。

        :param file_name: 保存数据的文件名
        :param interval: 数据收集的间隔时间（秒）
        """
        print("请按下 's' 键开始采集数据，再次按下 's' 键结束采集数据...")
        keyboard.wait('s')
        print(f"开始采集数据，每隔{interval}秒记录一次数据...")
        self.arm.StartDrag()
        collecting = True

        def stop_collecting():
            nonlocal collecting
            collecting = False

        keyboard.add_hotkey('s', stop_collecting)

        with open(file_name, 'w', newline='') as file:
            writer = csv.writer(file)
            while collecting:
                data = self.arm.GetPose()
                match = re.search(r'{([^}]*)}', data)
                print(data)
                if match:
                    data = match.group(1).split(',')
                    data = [float(x) for x in data]
                print(data)
                writer.writerow(data)
                time.sleep(interval)

        self.arm.StopDrag()
        print(f"数据已保存到 {file_name}")

    def read_csv_and_action(self, file_name):
        """
        用于快速复现data.txt中的位姿
        读取CSV文件中的数据，并根据数据执行相应动作。
        本函数打开指定的CSV文件，逐行读取其中的数据，将每行数据转换为浮点数列表，
        然后调用self.move方法，将这个列表作为参数，执行相应的动作。

        参数:
        file_name (str): CSV文件的名称，本函数将打开这个文件进行读取。
        """
        with open(file_name, 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                action = [float(x) for x in row]
                self.move(action)

    def read_csv_and_calibrate(self, line_number, file_name="data.csv"):
        """
        用于对数据中的特定某一行进行读取，标定的时候执行
        从CSV文件中读取指定行的数据，并根据这些数据执行校准操作。
        参数:
        line_number -- 读取的行号
        file_name -- CSV文件的名称，默认为"data.csv"

        返回:
        无
        """
        try:
            with open(file_name, 'r') as file:
                reader = csv.reader(file)
                for i, row in enumerate(reader):
                    if i == line_number:
                        action = [float(x) for x in row]
                        self.move(action)
                        return  # 读取到特定行后退出函数
                print(f"行号 {line_number} 超出范围")
        except Exception as e:
            print(f"读取文件时出错: {e}")

    def ClearRobotError(self):
        """
        清除机器人的错误状态。

        该方法通过查询机器人当前的错误状态，如果存在错误，则尝试清除错误并恢复机器人正常运行。
        """
        dataController, dataServo = alarmAlarmJsonFile()
        while True:
            self.__globalLockValue.acquire()  # robotErrorState加锁
            if self.feedData.robotErrorState:
                geterrorID = self.parseResultId(self.arm.GetErrorID())
                if geterrorID[0] == 0:
                    for i in range(1, len(geterrorID)):
                        alarmState = False
                        for item in dataController:
                            if geterrorID[i] == item["id"]:
                                print("机器告警 Controller GetErrorID",
                                      i, item["zh_CN"]["description"])
                                alarmState = True
                                break
                        if alarmState:
                            continue

                        for item in dataServo:
                            if geterrorID[i] == item["id"]:
                                print("机器告警 Servo GetErrorID", i,
                                      item["zh_CN"]["description"])
                                break

                    choose = input("输入1, 将清除错误, 机器继续运行: ")
                    if int(choose) == 1:
                        clearError = self.parseResultId(
                            self.arm.ClearError())
                        if clearError[0] == 0:
                            self.__globalLockValue.release()
                            print("--机器清错成功--")
                            break
            else:
                robotMode = self.parseResultId(self.arm.RobotMode())
                if robotMode[0] == 0 and robotMode[1] == 11:
                    print("机器发生碰撞")
                    choose = input("输入1, 将清除碰撞, 机器继续运行: ")
                    self.arm.ClearError()
            self.__globalLockValue.release()
            time.sleep(5)

    def GetFeed(self):
        """
        不断循环获取机械臂的反馈数据，并更新机器臂状态。
        """
        while True:
            feedInfo = self.feedFour.feedBackData()
            if hex((feedInfo['test_value'][0])) == '0x123456789abcdef':
                # Refresh Properties
                self.__globalLockValue.acquire()  # 互斥量    robotErrorState robotEnableStatus加锁
                self.feedData.robotErrorState = feedInfo['error_status'][0]
                self.feedData.robotEnableStatus = feedInfo['enable_status'][0]
                self.feedData.robotMode = feedInfo['robot_mode'][0]
                self.feedData.robotCurrentCommandID = feedInfo['currentcommandid'][0]
                self.__globalLockValue.release()
            time.sleep(0.01)

    def parseResultId(self, valueRecv):
        """
        解析返回值中结果ID的信息。
        """
        if valueRecv.find("Not Tcp") != -1:  # 通过返回值判断机器是否处于tcp模式
            print("Control Mode Is Not Tcp")
            return [1]
        recvData = re.findall(r'-?\d+', valueRecv)
        recvData = [int(num) for num in recvData]
        #  返回tcp指令返回值的所有数字数组
        if len(recvData) == 0:
            return [2]
        return recvData

if __name__ == '__main__':
    robot = xarm6()
    # robot.move_init_pose()

    # action = [300, 50, 200, 15, 2, 32]
    # robot.move(action)

    text = robot.arm.GetPose(0, 1)
    print(text)

    robot.collect_and_save_data('data.csv',5)

    robot.read_csv_and_action('data.csv')


