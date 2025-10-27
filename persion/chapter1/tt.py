from langchain_openai.chat_models import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
# key = os.getenv("OPENAI_API_KEY")
# base_url = os.getenv("OPENAI_BASE_URL")
# model = ChatOpenAI(api_key=key, base_url=base_url)
model = ChatOpenAI()
res=model.invoke("你好")
print(res.content)
