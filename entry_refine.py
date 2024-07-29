from planner import Planner
from perceptor import Perceptor
from executor import Executor
from prompts import Prompt
import erniebot
import cv2
import os
import time
import threading
import planner
from utils import VLM
from speech2text import speech2text
import numpy as np

from global_vars import robot, realcam

camera_event = threading.Event()
get_pic_event = threading.Event()


def capture_and_save():
    # 获取当前时间
    start_time = time.time()

    # 设置图像保存间隔（秒）
    save_interval = 0.5

    for img in realcam:
        # 逐帧捕获图像
        camera_event.wait()
        rgb_img, _, _ = img  # rgb图，深度图，深度信息

        # 显示当前帧
        cv2.imshow('camera', rgb_img)

        # 获取当前时间
        current_time = time.time()

        # 检查是否到达保存时间间隔
        # if current_time - start_time >= save_interval:
        cv2.imwrite(f"camera_output/output.jpg", rgb_img)
        # 更新开始时间
        start_time = current_time
        get_pic_event.set()

    # cv2.destroyAllWindows()


if __name__ == '__main__':

    planner = Planner()
    perceptor = Perceptor(VLM())
    executor = Executor()
    prompts = Prompt()

    # 获取标定数据
    cal_data = np.load(f'core/data.npy', allow_pickle=True).item()
    RT_cam2gri = cal_data['RT_cam2gripper']
    RT_cam2gri[:3, 3] *= 1000
    RT_obj2cam = np.identity(4)
    RT_gri2base = np.identity(4)
    robot.move_init_pose()  # 目前太靠左
    robot.arm.DO(1, 0)

    time.sleep(5)

    camera_event.set()
    # 创建并启动捕获和保存图像的线程
    capture_thread = threading.Thread(target=capture_and_save)
    capture_thread.start()

    task_instruction = "Please pick up the toothbrush and place it on my hand."
    # task_instruction = speech2text()
    # task_instruction = "Please pick up the flower in the center of the scene"
    VLM_scene_description = None
    execution_message = None
    flag = 1

    while True:
        # 保存到特定路径下
        scene_path = f'camera_output/output.jpg'

        # 轮询等待图片保存好
        print('camera wait')
        get_pic_event.wait()
        print('camera ready')

        camera_event.clear()
        get_pic_event.clear()

        VLM_scene_description = perceptor.generate_scene_description(
            img_path=scene_path,
            task_instruction=task_instruction)

        print("\nScene Description: ")
        print(VLM_scene_description)

        obj_info = perceptor.detect_obj_list(scene_path)
        objects = perceptor.obj_list
        print(f"\nObjects: {objects}")

        if flag == 1:
            flag = 0
            goal = prompts.generate_llm_prompt_refined(query=task_instruction,
                                                       objects=objects,
                                                       desc=VLM_scene_description)
        else:
            # if execution_message == "Execute successfully! Now you have picked up the toothbrush, please place it on my palm.":
            if execution_message == "Execute successfully!":
                goal_prompt = f"Observation: {execution_message} Current scene: " + VLM_scene_description
                planner.dialog_mem_between_LLM_and_human.append(
                    {'role': 'user',  # 成功执行后，如果尚未完整最终目标，告诉LLM当前的场景描述进入下一轮决策
                     'content': goal_prompt})
            else:
                goal_prompt = f"Observation: {execution_message}"
                planner.dialog_mem_between_LLM_and_human.append(
                    {'role': 'user', 'content': goal_prompt}
                )
            goal = goal_prompt
        print("\nPlaner's input prompt: ")
        print(goal)

        meta_actions = planner.respond_human_request(goal)
        print("\nMeta actions: ")
        print(meta_actions)

        if "DONE" in meta_actions:
            print("Goal Done!!")
            exit(0)
        else:
            execution_message = planner.meta_action_to_func_call(meta_actions)
            time.sleep(8)
            camera_event.set()
