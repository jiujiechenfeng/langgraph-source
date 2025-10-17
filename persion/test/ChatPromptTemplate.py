from langchain.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import SystemMessage, AIMessageChunk
from dotenv import load_dotenv
#读取.env中配置的环境变量
load_dotenv()

chat_model = ChatTongyi(model="qwen-max")

# 定义提示词模版字符串
template_string = """将以下用三重反引号括起来的文本翻译成风格为 {style} 的文本。\\n文本: ```{text}```"""

# 创建 ChatPromptTemplate 实例
prompt_template=ChatPromptTemplate.from_template(template_string)
# 查看模版中的输入变量
print(prompt_template.messages[0].prompt.input_variables)

# 定义客户的投诉风格和文本
customer_style = """刻薄"""
customer_email = """
你好，我遇见了一个问题，我解决不掉，需要你的帮助，你能帮我吗？
"""

# 使用模版格式化消息
customer_messages = prompt_template.format_messages(
    style=customer_style,
    text=customer_email
)

# 打印生成的消息类型和内容
# print(type(customer_messages))         # 输出: <class 'list'>
# print(type(customer_messages[0])) # 输出: <class 'langchain.schema.HumanMessage'>
user_message = [
    SystemMessage(content='你是一个助手'),
    customer_messages[0]
]
# 获取模型回复
# response = chat_model.invoke(user_message)  # 直接传递消息列表
# 输出回复内容
# print(response.content)

for chunk in chat_model.stream(user_message):
    if isinstance(chunk, AIMessageChunk):
        print(chunk.content, end="", flush=True)