from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

# 设置 API 密钥
# 初始化 ChatTongyi 模型
chat_model = ChatTongyi(model="qwen-max")

review_template = """
请从以下文本中提取以下信息：

1. 是否作为礼物购买（gift）：如果是礼物，请回答True；如果不是或未知，请回答False。
2. 到货天数（delivery_days）：提取产品到货所需的天数，如果信息不存在，请输出-1。
3. 价格或价值的评价（price_value）：提取任何与价格或价值相关的句子，并以逗号分隔的Python列表形式输出。

请以JSON格式输出，键包括：
- gift
- delivery_days
- price_value

文本：{text}
"""

# 创建 ChatPromptTemplate 实例
prompt_template = ChatPromptTemplate.from_template(review_template)

# 示例用户评论
customer_review = """
这款叶吹机非常棒！它有四个设置：蜡烛吹风、微风、风城和龙卷风模式。
它在两天内送达，正好赶上我妻子的周年纪念礼物。
我觉得它稍微比其他叶吹机贵一些，但多出来的功能让我觉得物有所值。
"""

# 格式化提示
messages = prompt_template.format_messages(text=customer_review)

# 调用语言模型
response = chat_model.invoke(messages)
print(response.content)  # 字符串而非字典

from langchain.output_parsers import ResponseSchema, StructuredOutputParser

# 定义每个字段的输出模式
gift_schema = ResponseSchema(name="gift", description="是否作为礼物购买")
delivery_days_schema = ResponseSchema(name="delivery_days", description="产品到货天数")
price_value_schema = ResponseSchema(name="price_value", description="价格或价值的评价")

# 将所有模式组合成一个列表
response_schemas = [gift_schema, delivery_days_schema, price_value_schema]

# 使用模式列表初始化输出解析器
output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

format_instructions = output_parser.get_format_instructions()

# 将解析指令嵌入提示模版
review_template_with_format = """
请从以下文本中提取以下信息：

1. 是否作为礼物购买（gift）：如果是礼物，请回答True；如果不是或未知，请回答False。
2. 到货天数（delivery_days）：提取产品到货所需的天数，如果信息不存在，请输出-1。
3. 价格或价值的评价（price_value）：提取任何与价格或价值相关的句子，并以逗号分隔的Python列表形式输出。

{format_instructions}

文本：{text}
"""

# 格式化消息
messages = prompt_template.format_messages(text=customer_review, format_instructions=format_instructions)
response = chat_model.invoke(messages)

# 解析模型输出
output_dict = output_parser.parse(response.content)
print(output_dict)

print(output_dict.get('delivery_days'))  # 输出 2
