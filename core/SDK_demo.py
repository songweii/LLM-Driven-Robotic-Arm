import erniebot
import json
import re
from VLM import multimodal_conversation_call

erniebot.api_type = "aistudio"
erniebot.access_token = "your_token"


def llm_model(PROMPT='你好，你是谁？'):

    response = erniebot.ChatCompletion.create(
        model="ernie-3.5",
        messages=[{"role": "user", "content": PROMPT}],
        top_p=0.8,
        temperature=0.3,
        penalty_score=1.0
    )

    response = response["result"]
    return response

response = llm_model()
print(response)

