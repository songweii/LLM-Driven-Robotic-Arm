from core.realsense2 import *
from core.wrap_xarm import xarm6_grasp
# from picodet.predict import PicoDet
from calibrate import Calibration
import cv2

def hsv2bgr(h, s, v):
    h_i = int(h * 6)
    f = h * 6 - h_i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)

    r, g, b = 0, 0, 0

    if h_i == 0:
        r, g, b = v, t, p
    elif h_i == 1:
        r, g, b = q, v, p
    elif h_i == 2:
        r, g, b = p, v, t
    elif h_i == 3:
        r, g, b = p, q, v
    elif h_i == 4:
        r, g, b = t, p, v
    elif h_i == 5:
        r, g, b = v, p, q

    return int(b * 255), int(g * 255), int(r * 255)

def random_color(id):
    h_plane = (((id << 2) ^ 0x937151) % 100) / 100.0
    s_plane = (((id << 3) ^ 0x315793) % 100) / 100.0
    return hsv2bgr(h_plane, s_plane, 1)

def get_color(label):
    """
    Generate a color based on the label name.
    """
    np.random.seed(hash(label) % 2 ** 32)
    return tuple(int(x) for x in np.random.randint(0, 255, 3))

def display(img, results):
    """
    显示图像及其检测结果。

    参数:
    img: 输入的图像数组。
    results: 检测结果的列表，每个元素包含一个检测框的信息，如左上角坐标、宽度、高度和类型。

    返回:
    center_points: 检测框中心点的列表。
    cls: 检测框类型的列表。
    """
    center_points = []
    cls = []
    # Add the detection boxes and labels
    for result in results:
        x, y, width, height = int(result['x']), int(result['y']), int(result['width']), int(result['height'])
        color = get_color(result['type'])
        cv2.rectangle(img, (x, y), (x + width, y + height), color, 2)
        cv2.putText(img, result['type'], (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        cls.append(result['type'])
        # Calculate the center point
        x_center = x + width // 2
        y_center = y + height // 2
        center_points.append([x_center, y_center])
        #抓取最后一个
        #center_point = [x_center, y_center]
    # Display the image
    cv2.imshow('Detection Results', img)
    cv2.waitKey(1)

    return center_points,cls



if __name__ == "__main__":

    # model = PicoDet("picodet/model/")         # model
    robot = xarm6_grasp()                             # robot
    realcam = Realsense2()                      # camera

    # #获取标定数据
    # cal_data = np.load(f'C:\\Users\\24432\\Desktop\\demo1\\demo\\output\\imgSave\\Folder_2024_07_06_09_31_51\\data.npy', allow_pickle=True).item()
    cal_data = np.load(f'data.npy', allow_pickle=True).item()
    RT_cam2gri = cal_data['RT_cam2gripper']
    RT_cam2gri[:3, 3] *= 1000
    RT_obj2cam = np.identity(4)
    RT_gri2base = np.identity(4)

    # LOOP
    for img in realcam:
        #robot.move_init_pose()                   # 初始位姿
        rgb_img, _, _ = img                       # rgb图，深度图，深度信息
        if len(np.array(rgb_img).shape) == 3:
            # 使用模型对图像进行预测
            # results = model.detect(rgb_img)
            # img_xy, cls = display(rgb_img, results)
            # img_xy = []
            # img_xy.append([5, 5])
            # if img_xy:
            #     real_xyz = realcam.pixel2point(img_xy[0]) #只抓取第一个
            #     RT_obj2cam[:3, 3] = np.array(real_xyz) * 1000
            #     RT_gri2base = Calibration.Cartesian2Homogeneous(robot.get_current_pose())
            #     RT_gri2base[:3, 3] *= 1000
            #     RT_obj2base = RT_gri2base.dot(RT_cam2gri.dot(RT_obj2cam))

                # action
                # robot.move_xyz(RT_obj2base[:3, 3])
                # robot.move_xyz([-80, 40, 350])
                # robot.move([-104, -163, 344, -139, -29, 170])   #工具坐标系安全点
                # robot.move_xyz([-106, 0, 277])  #安全（位置低）
                # robot.move_xyz([120,0,0])  # error
                # print(RT_obj2base[:3, 3])
                # robot.arm.ToolDOInstant(1,1)

                #垂直抓放demo
                # robot.move_xyz([-50, -200, 200])  # 安全（位置很低）
                # robot.arm.DO(1, 1)  # jia
                # time.sleep(3)
                # robot.move_xyz([50, -300, 100]) #安全（位置很低）
                # time.sleep(2)
                # robot.arm.DO(1, 0)  # fang
                # if robot.arm.GetToolDO(1) == 1:
                #     print("成功抓取")
                # break

                # 插花demo
                robot.move_xyz([50, -300, 116.7])
                robot.arm.DO(1, 1)  # jia
                time.sleep(3)
                robot.move_xyz([0, -200, 250])
                time.sleep(3)
                robot.arm.DO(1, 0)  # fang
                if robot.arm.GetToolDO(1) == 1:
                    print("成功抓取")
                break
                robot.move


                # 连续指令测试
                # robot.move_xyz([-50, -200, 200])
                # time.sleep(0.2)
                # robot.move_xyz([-40, -180, 210])
                # time.sleep(0.2)
                # robot.move_xyz([-30, -160, 220])
                # time.sleep(0.2)
                # robot.move_xyz([-20, -140, 230])
                # time.sleep(0.2)
                # robot.move_xyz([-10, -120, 240])
                # time.sleep(0.2)
                # robot.move_xyz([0, -100, 250])
                # time.sleep(0.2)

    print("End.")






