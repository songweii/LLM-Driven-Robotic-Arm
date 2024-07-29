import json

from utils import VLM
from prompts import Prompt
import cv2


# VLM 做感知

class Perceptor:
    def __init__(self, vlm):
        self.vlm = vlm
        self.detected_objects = []
        self.obj_list = []
        self.scene_info = ""
        self.dialog_mem_between_VLM_and_LLM = []

    def answer(self, img_path, question):
        # 回答 Planner 的问题
        self.dialog_mem_between_VLM_and_LLM.append(
            {
                'role': 'user',
                'content': question
            }
        )
        response = self.vlm.mm_conv_call(img_path, self.dialog_mem_between_VLM_and_LLM)
        self.dialog_mem_between_VLM_and_LLM.append(
            {
                'role': 'bot',
                'content': response
            }
        )
        return response

    def generate_scene_description(self, img_path, task_instruction=''):

        general_prompt = Prompt().vlm_desc_prompt(task_instruction)

        response = self.vlm.mm_conv_call(img_path, general_prompt)
        self.scene_info = response
        return self.scene_info

    def detect_obj_list(self, img_path):
        # 按需得到目标检测框
        general_prompt = ('What are the major objects in this picture? Output format (JSON Format, Do not generate other content): '
                          '{"objects": ["xxx", "xxx", ...]}')

        response = self.vlm.mm_conv_call(img_path, general_prompt)
        obj_list = json.loads(response)['objects']

        self.detected_objects = []
        self.obj_list = []

        # 读取图片信息
        image = cv2.imread(img_path)
        height, width, _ = image.shape

        for obj in obj_list:
            find_one_prompt = f'Extract reference box of {obj}.'
            result = self.vlm.mm_conv_call(img_path, find_one_prompt)

            result = json.loads(result)

            x1, y1 = result['box']['top_left']
            x2, y2 = result['box']['bottom_right']
            label = result['ref']

            x1_new = int(x1 * width / 1000)
            y1_new = int(y1 * height / 1000)
            x2_new = int(x2 * width / 1000)
            y2_new = int(y2 * height / 1000)

            # x1_new = x1
            # y1_new = y1
            # x2_new = x2
            # y2_new = y2

            self.obj_list.append(label)
            self.detected_objects.append(
                {
                    'ref': label,
                    'box': {
                        'top_left': [x1_new, y1_new],
                        'bottom_right': [x2_new, y2_new]
                    }
                }
            )

        return self.detected_objects
