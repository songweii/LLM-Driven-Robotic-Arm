import erniebot
import re
import sys
import ast
from meta_actions import *

# from utils import LLM, VLM
from global_vars import robot, realcam


class Planner:

    def __init__(self, api_type="aistudio", access_token="2f486dfb4e1511984e187e18de9d84dc641a2132",
                 llm_model='ernie-4.0'):
        # 可直接改为用政淋封装的
        erniebot.api_type = api_type
        erniebot.access_token = access_token
        self.llm = llm_model
        # self.dialog_mem_between_LLM_and_VLM = [{'role': 'user',  # user 即 VLM
        #                                         'content': 'To better assist you in making decisions, '
        #                                                    'what detailed scenario information I need to provide?'}]
        self.dialog_mem_between_LLM_and_human = []
        self.step_by_step_plan = None

    def respond_human_request(self, goal):
        # 接收人类目标指令，并得到相应输出
        prompt = goal

        self.dialog_mem_between_LLM_and_human = prompt

        response = erniebot.ChatCompletion.create(
            model=self.llm,
            messages=self.dialog_mem_between_LLM_and_human,
            temperature=0.1
        )

        step_by_step_plan = response.get_result()

        return step_by_step_plan

    # def VLM_ask_LLM(self):
    #     # 向 VLM 获取信息，可能多轮对话，目前只有这单轮
    #     response = erniebot.ChatCompletion.create(
    #         model=self.llm,
    #         messages=self.dialog_mem_between_LLM_and_VLM,
    #     )  # response: you need to tell me the color of the bottle
    #
    #     print(response.get_result())  # 打印机器人的回复
    #     self.dialog_mem_between_LLM_and_VLM.append(response.to_message())
    #
    #     return response.get_result()

    def meta_action_to_func_call(self, message):
        execution_message = None

        # 转 func call 代码
        lines = [' '.join(message.split("\n"))]
        find_action = False
        for line in lines:
            execution_message = "Function is not executed!"
            find_action = True
            function_names = re.findall(r'(\w+)\(', line)

            function_executed = False
            for function_name in function_names:
                print(function_name)
                try:
                    func = getattr(sys.modules[__name__], function_name)

                    matches = re.findall(r'{}\((.+?)\)'.format(function_name), line)
                    arguments = re.split(r'\s*,\s*', matches[0])

                    arguments.append(robot)
                    arguments.append(realcam)

                    # arguments = self.extract_params(line, function_name)
                    ori_arguments = [str(argument) for argument in arguments]
                    execution_message = "Execute successfully!"
                    # execution_message = "Execute successfully! Now you have picked up the toothbrush, please place it on my palm."
                    func(*arguments)  # execution_message = "Function is executed successfully!"
                    function_executed = True
                    break  # at most one function is executed in one turn
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    try:
                        execution_message = f"{function_name}({', '.join(ori_arguments)}) cannot be executed: {e}"
                    except UnboundLocalError:
                        execution_message = f"I may make a syntax error when calling {function_name} (e.g., unmatched parenthesis). I need to fix it and reuse the tool"
                    continue
            break  # should at most be one line starts with Action

        if not find_action:
            execution_message = "No executable function found! Need to recheck the action."

        return execution_message

    def extract_params(self, data, function_name):
        pattern = re.compile(r'\b' + re.escape(function_name) + r'\((.*?)\)', re.DOTALL)
        match = pattern.search(data)
        if not match:
            return "Function call not found."

        params_str = match.group(1)
        params = []
        depth = 0
        start = 0
        # print(params_str)
        for i, char in enumerate(params_str):
            if char == '(':
                if depth == 0:
                    start = i + 1
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    params.append(params_str[start:i])
                    start = i + 1
            elif char == ',' and depth == 0:
                if start != i:
                    params.append(params_str[start:i])
                start = i + 1

        try:
            params = ast.literal_eval(params_str)
            if isinstance(params, list):
                params = [params]
            return list(params)
        except Exception as e:
            try:
                params = ast.literal_eval(f"[{params_str}]")
                if isinstance(params, list):
                    params = [params]
                return list(params)
            except Exception as e:
                return f"Error parsing parameters: {e}"


# 决策
# models = erniebot.Model.list()
# ('ernie-3.5', '文心大模型（ernie-3.5）')
# ('ernie-turbo', '文心大模型（ernie-turbo）')
# ('ernie-4.0', '文心大模型（ernie-4.0）'),
# ('ernie-longtext', '文心大模型（ernie-longtext）')
# ('ernie-text-embedding', '文心百中语义模型')
# ('ernie-vilg-v2', '文心一格模型')


if __name__ == '__main__':
    planner = Planner()
    # step_by_step_plan = planner.respond_human_request([{'role': 'user',
    #                                                     'content': "You are a helpful assistant that pays attention to the user's instructions and excels at fulfilling the user's request by operating a robot arm in a tabletop environment.\n        Pay attention to the relationships between objects, including: On, Under, Right, Front, Left, Behind, Next-to, In.\n        To achieve this, you can use the following tools:\n        1. Pick(object): Pick out the object. For example, executing Pick(apple), the robot arm will go to where the apple is and pick it up. \n        2. Move(relation, reference_object): move to the specified position. For example, executing Move(left, banana), the robot arm will move to the left of the banana. \n        3. Place(relation, reference_object): move to the specified position to place the picked object. For example, executing Place(left, banana), the robot arm will move to the left of the banana and place the picked object there. \n        Here are some examples of decomposing a user's request:\n        1. objects = [blue block, yellow block, mug]\n        # User: place the blue block on the yellow block.\n        # Agent should decompose it into these several steps: Pick(blue block), Place(On, yellow block).\n        2. objects = [hand, mouse, bottle]\n        # User: shake hand with me.\n        # Agent should move to where the hand is: Move(Next-to, hand).\n        Notice:\n        1. Single Action Rule: Execute only ONE action at a time. After receiving the observation from its execution, you may proceed with another action. \n        2. DO NOT GENERATE ANYTHING THAT IS NOT SEEN IN THE TABLE.\n        WHEN TO STOP:\n        When the current scene matches the user's request, you must finally answer with DONE.\n        "},
    #                                                    {'role': 'assistant',
    #                                                     'content': "I've understood your instruction, start please."},
    #                                                    {'role': 'user',
    #                                                     'content': "Current scene on the table: There are an apple, a banana and a mug on the table. Objects: [apple, banana, mug]. The user's request: Pick up the apple and place it to the left of the banana."},
    #                                                    {'role': 'assistant',
    #                                                     'content': 'Thought: I need to firstly pick up the apple. \n            Action: Pick(apple)'},
    #                                                    {'role': 'user',
    #                                                     'content': 'Observation: Execute successfully! Current scene on the table: There are a banana and a mug.'},
    #                                                    {'role': 'assistant',
    #                                                     'content': 'Thought: I have grasped the apple, so now I just need to place it to the left of the banana.\n            Action: Place(Left, banana)'},
    #                                                    {'role': 'user',
    #                                                     'content': 'Observation: Execute successfully! Current scene on the table: There is an apple to its right a banana, and also a mug.'},
    #                                                    {'role': 'assistant',
    #                                                     'content': "Thought: I have fulfilled the user's request. DONE."},
    #                                                    {'role': 'user',
    #                                                     'content': 'Current scene on the table: {"ref": "white car", "box": {"top_left": [0, 623], "bottom_right": [145, 789]}}. Objects: [\'egg\', \'bottle\', \'pen\']. The user\'s request: Please tell me how to reach the white car..'}])
    # print(step_by_step_plan)
    planner.extract_params("Action: Move(Next-to, table)")


