from http import HTTPStatus
import dashscope
import re
import json

dashscope.api_key = "sk-01e77b74da07453ca6f82a2891bc39bc"

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

def multimodal_conversation_call(img_path,text):
    messages = [
        {
            "role": "user",
            "content": [
                {"image": img_path},
                {"text": text}
            ]
        }
    ]
    response = dashscope.MultiModalConversation.call(model=dashscope.MultiModalConversation.Models.qwen_vl_chat_v1,
                                                     messages=messages)

    if response.status_code == HTTPStatus.OK:  #如果调用成功，则打印response
        print(response)
        result = response["output"]["choices"][0]["message"]["content"]
        return extract_info(result)

    else:  #如果调用失败
        print(response.code)  # 错误码
        print(response.message)  # 错误信息



if __name__ == '__main__':
    result = multimodal_conversation_call("https://bj.bcebos.com/v1/paddlenlp/models/community/GroundingDino/000000004505.jpg","框出图中的巴士")
    print(result)
