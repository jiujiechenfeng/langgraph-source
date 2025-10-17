import os
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import HumanMessage, SystemMessage, AIMessageChunk
from dotenv import load_dotenv

# 读取.env中配置的环境变量
load_dotenv()

# 初始化 ChatTongyi 模型
chat_model = ChatTongyi(model="qwen-max")
# 创建用户消息
message = [
    SystemMessage(content='你是一个友好的助手'),
    HumanMessage(content="给我介绍一下深度学习")
]
# 获取模型回复
# response = chat_model.invoke(message)  # 直接传递消息列表
# 输出回复内容
# print(response.content)
for chunk in chat_model.stream(message):
    if isinstance(chunk, AIMessageChunk):
        print(chunk.content, end="", flush=True)
print()
