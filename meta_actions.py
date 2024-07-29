# 这里定义 meta action
import time

from perceptor import Perceptor
from utils import VLM
from core.wrap_xarm import xarm6
from core.realsense2 import *
from core.calibrate import Calibration
import math

img_path = "camera_output/output.jpg"  # from 政淋


def Pick(object, robot, realcam):
    """Pick out the object. For example, executing Pick(apple), the robot arm will go to where the apple is and pick it up.

    Args:
        object (str): the target object to pick up
    """
    Move("To", object, robot=robot, realcam=realcam)
    robot.arm.DO(1, 1)
    robot.move_init_pose()
    # robot.arm.ToolDOInstant(1, 1)
    # if robot.arm.GetToolDO(1) == 1:
    #     print("成功抓取")


def Move(relation, reference_object, robot, realcam):
    """Move to the specified position. For example, executing Move(left, banana), the robot arm will move to the left of the banana.

    Args:
        relation (str): the position relationship between target object and reference object
        reference_object (str): a reference object
    """
    # 1. 根据参数得到目标位置坐标
    # 1.1. 检测参照物体坐标
    perceptor = Perceptor(VLM())
    obj_lst = perceptor.detect_obj_list(img_path)
    x_center, y_center = None, None
    for obj in obj_lst:
        reference_object = reference_object.replace("\'", '')
        reference_object = reference_object.replace("\"", '')

        print("reference object:")
        print(reference_object)

        if obj['ref'] == reference_object:
            top_left = obj['box']['top_left']
            bottom_right = obj['box']['bottom_right']
            x_center = int((top_left[0] + bottom_right[0]) / 2)
            y_center = int((top_left[1] + bottom_right[1]) / 2)

    # 视觉-运动
    cal_data = np.load(f'core/data.npy', allow_pickle=True).item()
    RT_cam2gri = cal_data['RT_cam2gripper']
    RT_cam2gri[:3, 3] *= 1000
    RT_obj2cam = np.identity(4)
    RT_gri2base = np.identity(4)

    if x_center and y_center:
        real_xyz = realcam.pixel2point((x_center, y_center))  # 只抓取第一个
        RT_obj2cam[:3, 3] = np.array(real_xyz) * 1000

        print("pose:")
        robot.get_current_pose()

        RT_gri2base = Calibration.Cartesian2Homogeneous(robot.get_current_pose())
        RT_gri2base[:3, 3] *= 1000
        RT_obj2base = RT_gri2base.dot(RT_cam2gri.dot(RT_obj2cam))

        # 1.2. 根据参数确定目标位置坐标, On, Under, Right, Front, Left, Behind, Next-to, In
        RT_obj2base[2, 3] += 20  # 偏差矫正
        if relation == 'On':
            RT_obj2base[2, 3] += 50
        elif relation == 'Under':
            RT_obj2base[2, 3] -= 40
        elif relation == 'Right':
            RT_obj2base[1, 3] += 40
        elif relation == 'Left':
            RT_obj2base[1, 3] -= 40
        elif relation == 'Front':
            RT_obj2base[0, 3] += 40
        elif relation == 'Behind':
            RT_obj2base[0, 3] -= 40

        robot.move_xyz(RT_obj2base[:3, 3])
        print("base:")
        print(RT_obj2base[:3, 3])
        print("Move Done!")
    else:
        print("Fail to locate reference object!")

    # # FOR SHAKE
    # robot.arm.DO(1, 1)
    # time.sleep(1)
    # robot.arm.DO(1, 0)
    # time.sleep(2)
    # robot.move_init_pose()

    ## 1.2. 人工确定目标位置


# def Place(relation, reference_object, robot, realcam):
#     """Move to the specified position and place the picked object there.
#
#     Args:
#         relation (str): the position relationship between target object and reference object
#         reference_object (str): a reference object
#     """
#     Move("To", reference_object, robot=robot, realcam=realcam)
#     robot.arm.DO(1, 0)
#     robot.move_init_pose()


def Place(relation, reference_object, robot, realcam):
    """Move to the specified position and place the picked object there.

    Args:
        relation (str): the position relationship between target object and reference object
        reference_object (str): a reference object
    """
    # Move("To", reference_object, robot=robot, realcam=realcam)

    # a1, a2, a3, a4, a5, a6 = robot.GetAngle()
    # print(a1, a2, a3, a4, a5, a6)

    Move("To", reference_object, robot=robot, realcam=realcam)

    a1, a2, a3, rx, ry, rz = robot.get_current_pose()
    print(rx, ry, rz)
    robot.arm.MovJ(a1, a2 + 40, a3 + 100, -90, 0, -180, coordinateMode=0, user=-1, tool=1, a=-1, v=-1, cp=-1)

    robot.arm.DO(1, 0)
    # robot.move_init_pose()


if __name__ == '__main__':
    # "camerapose": "-59.9, -131.3, 321, -180, 0, -180",
    from global_vars import robot, realcam

    Place("on", "hand", robot, realcam)
