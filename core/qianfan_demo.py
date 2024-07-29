import requests
import json
from wrap_xarm import xarm6
import numpy as np
from grasp import display
import threading
from picodet.predict import PicoDet
from core.realsense2 import *
import sys

API_KEY = "bCT0Qp7nYn7CH3EiRXcAZ3Ml"
SECRET_KEY = "H9I6G2gz0DvGSuzPDEF3DnTWDM4XVCqF"

class colors:  # You may need to change color settings
    RED = "\033[31m"
    ENDC = "\033[m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"

# 初始化一个全局变量用于存储最新的检测结果
latest_detection = None

def infer_thread(realcam, model):
    """独立线程进行推理的函数"""
    global latest_detection
    while True:
        for img in realcam:
            rgb_img, _, _ = img                      # rgb图，深度图，深度信息
            if len(np.array(rgb_img).shape) == 3:
                # 使用模型对图像进行预测
                results = model.detect(rgb_img)
                _, cls = display(rgb_img, results)
                # 直接更新全局变量
                if cls is not None:
                    latest_detection = cls

def action(script):
    try:
        # if script == "nods":
        #     action_pose1 = [-12.8502, 82.0165, 535.3324, -12.8210, -53.9930, -176.1641]
        #     action_pose2 = [98.8198, 71.5135, 464.8654, -162.9306, -58.1757, -24.1207]
        # if script == "shake":
        #     action_pose1 = [59.6426, 28.3089, 495.5015, 169.7462, -77.7247, -38.8517]
        #     action_pose2 = [83.4040, 104.2719, 487.8577, -134.4399, -65.6396, -25.6943]
        # for i in range(3):
        #     robot.move(action_pose1)
        #     robot.move(action_pose2)
        robot.move_init_pose()
    except Exception as e:
        return {"status": False, "error_message": "action_error"}
    else:
        return {"status": True}

action_desc = {
            "name": "action",
            "description": "控制机械臂执行动作,需要根据回答来执行命令",
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "机械臂执行的动作，包括点头，摇头，抓取等",
                        "enum":["nods","shake"]
                    }
                },
                "required": [
                    "script"
                ]
            },
            "responses": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "boolean",
                        "description": "执行动作是否成功，true表示成功，false表示失败"
                    },
                    "error_message": {
                        "type": "string",
                        "description": "执行动作失败原因"
                    }
                },
                "required": [
                    "status"
                ]
            }
        }

name2function = {
    "action": action
}

functions = [action_desc]

def get_access_token():
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": SECRET_KEY}
    return str(requests.post(url, params=params).json().get("access_token"))

def to_pretty_json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)

def ask(prompt,use_functions = True,auto_func_call = True,_max_recur_depth = 5):
    if isinstance(prompt, str):
        prompt = {"role": "user", "content": prompt}
    chat_history.append(prompt)

    if use_functions:
        payload = json.dumps({
            "messages": chat_history,
            "functions": functions,
            "temperature": 0.3
        })
    else:
        payload = json.dumps({
            "messages": chat_history,
            "temperature": 0.3
        })
    response = requests.request("POST", url, headers=headers, data=payload).json()
    print(response)
    if 'function_call' in response:
        function_call = response['function_call']
        chat_history.append(
            {
                "role": "assistant",
                "content": None,
                "function_call": function_call,
            }
        )
        if auto_func_call:
            func_name = function_call['name']
            try:
                func = name2function[func_name]
            except KeyError as e:
                raise KeyError("函数{}不存在".format(func_name)) from e
            func_args = function_call['arguments']
            try:
                func_args = json.loads(func_args)
            except json.JSONDecodeError as e:
                raise ValueError("无法从{}解析参数".format(repr(func_args))) from e
            if not isinstance(func_args, dict):
                raise TypeError("{}不是字典".format(repr(func_args)))
            print("【函数调用】函数名称：{}，请求参数：{}".format(func_name, to_pretty_json(func_args)))
            func_res = func(**func_args)
            print("【函数调用】响应参数：{}".format(to_pretty_json(func_res)))
            message = {
                "role": "function",
                "name": func_name,
                "content": json.dumps(func_res, ensure_ascii=False),
            }
            # 根据允许的最大递归层级判断是否应该设置`use_functions`和`auto_func_call`为`False`
            # 这样做主要是为了限制调用函数的次数，防止无限递归
            return ask(
                message,
                auto_func_call=(auto_func_call and _max_recur_depth > 1),
                _max_recur_depth=_max_recur_depth - 1,
            )
        else:
            return function_call
    else:
        chat_history.append(
            {
                "role": "assistant",
                "content": response["result"]
            }
        )
        return response["result"]

url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token=" + get_access_token()
chat_history= [
  {
    "role": "user",
    "content": "你作为一个实体的机械臂，我会告诉你周围的环境，你需要根据我的描述的事实性，点头代表事实为真，摇头代表事实为假，比如说我询问你天是蓝色的吗，你需要执行点头的动作，天是粉色的吗？，执行摇头的动作，请你以function call的方式输出执行的动作"
  },
  {
    "role": "assistant",
    "content": "明白了，我会回答你的问题的同时执行一些动作。请问你有什么具体的问题呢？"
  }
]
headers = {
    "Content-Type": "application/json"
}
model = PicoDet("picodet/model/")  #model
robot = xarm6()  # robot
realcam = Realsense2()  # camera

infer_thread = threading.Thread(target=infer_thread, args=(realcam, model))
infer_thread.daemon = True  # 设置为守护线程，主线程结束时自动关闭
infer_thread.start()

def main():
    print("start!")
    global latest_detection
    while True:
        question = input(colors.RED + "question> " + colors.ENDC) + "你的面前的环境中有{}".format(latest_detection)
        latest_detection = None
        if question == "!quit" or question == "!exit":
            break

        response = ask(question)
        print("\n{}\n".format(response))


if __name__ == "__main__":
    main()

