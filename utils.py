from http import HTTPStatus
import dashscope
from dashscope import MultiModalConversation
import re
import json
import erniebot


class LLM:
    # 封装 LLM API call
    def __init__(self, api_type="aistudio", api_key="2f486dfb4e1511984e187e18de9d84dc641a2132", model="ernie-4.0"):
        erniebot.api_type = api_type
        erniebot.access_token = api_key
        self.model = model

    def conv_call(self, prompt):

        messages = [{
            'role': 'user',
            'content': prompt
        }]
        response = erniebot.ChatCompletion.create(
            model=self.model,
            messages=messages,
        )

        return response.get_result()


# llm = LLM(model="ernie-4.0")
# llm_response = llm.conv_call('你好，机器人，我口渴了')
# print(llm_response)


class VLM:
    # 封装 VLM API call
    def __init__(self, api_key="sk-01e77b74da07453ca6f82a2891bc39bc"):
        dashscope.api_key = api_key

    @staticmethod
    def extract_info(content):
        # 提取<ref>标签内的内容
        ref_pattern = re.compile(r'<ref>(.*?)</ref>')
        ref_match = ref_pattern.search(content)
        ref_content = ref_match.group(1) if ref_match else None

        # 提取<box>标签内的坐标
        box_pattern = re.compile(r'<box>\((\d+),(\d+)\),\((\d+),(\d+)\)</box>')
        box_match = box_pattern.search(content)
        box_coords = ((int(box_match.group(1)), int(box_match.group(2))),
                      (int(box_match.group(3)), int(box_match.group(4)))) if box_match else None

        # 返回结果
        if ref_content and box_coords:
            result = {
                "ref": ref_content,
                "box": {
                    "top_left": box_coords[0],
                    "bottom_right": box_coords[1]
                }
            }
            return json.dumps(result, ensure_ascii=False)
        else:
            return content

    @staticmethod
    def mm_conv_call(img_path, text):

        local_file = f'file://{img_path}'
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": local_file},
                    {"text": text}
                ]
            }
        ]

        # response = dashscope.MultiModalConversation.call(
        # model=dashscope.MultiModalConversation.Models.qwen_vl_chat_v1, messages=messages)
        # if response.status_code == HTTPStatus.OK:  # 如果调用成功，则打印response
        #     result = response["output"]["choices"][0]["message"]["content"]
        #     return VLM.extract_info(result)
        # else:  # 如果调用失败
        #     print(response.code)  # 错误码
        #     print(response.message)  # 错误信息
        #     return ""

        response = MultiModalConversation.call(model='qwen-vl-plus', messages=messages)
        boxes_details = []
        if "choices" in response["output"]:
            result = response["output"]["choices"][0]["message"]["content"][0]

            if 'box' in result:
                return VLM.extract_info(result['box'])
            elif 'text' in result:
                return result['text']
        else:
            print(response.code)  # 错误码
            print(response.message)  # 错误信息
            return ""


# vlm = VLM()
# vlm_response = vlm.mm_conv_call("./demo.jpg",
#                                 "这幅图中有什么东西？")
# print(vlm_response)  # 这幅图显示了一条城市街道，有一辆红色的公共汽车在路上行驶......
# vlm_response2 = vlm.mm_conv_call("./demo.jpg",
#                                  "框出图中的巴士")
# print(vlm_response2)  # {"ref": "巴士", "box": {"top_left": [178, 276], "bottom_right": [805, 894]}}
