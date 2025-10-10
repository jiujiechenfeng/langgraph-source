# filename: single_agent_chat.py
from langchain_community.chat_models import ChatTongyi
from typing import List
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
load_dotenv()
# 选择你要用的模型（任选一种，按需安装依赖）
# 1) OpenAI: pip install langchain-openai
#    环境变量：OPENAI_API_KEY
# from langchain_openai import ChatOpenAI
# model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 2) 通义千问（可选）：pip install dashscope langchain-community
#    环境变量：DASHSCOPE_API_KEY
model = ChatTongyi(model="qwen-max")

# 提示词模版（包含系统提示、历史消息占位符和用户输入）
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个友好的中文助手，回答要简洁、准确、可执行。"),
    MessagesPlaceholder("history"),
    ("human", "{input}")
])


def agent(state: MessagesState):
    messages = state.get("messages", [])
    user_text = messages[-1].content if messages else ""
    history: List = messages[:-1]

    prompt_value = prompt.invoke({"history": history, "input": user_text})
    ai_msg = model.invoke(prompt_value.to_messages())
    return {"messages": [ai_msg]}


# 构建图：单节点，START -> agent -> END
graph = StateGraph(MessagesState)
graph.add_node("agent", agent)
graph.add_edge(START, "agent")
graph.add_edge("agent", END)

# 使用内存检查点保存会话状态，实现多轮对话
app = graph.compile(checkpointer=MemorySaver())

if __name__ == "__main__":
    print("输入内容并按回车发送，输入 exit 退出。")
    thread = {"configurable": {"thread_id": "demo"}}
    while True:
        text = input("你: ").strip()
        if text.lower() in {"exit", "quit"}:
            break
        # 流式打印助手回复（逐字/逐段输出）
        print("助手:", end=" ")
        for msg, meta in app.stream(
            {"messages": [HumanMessage(content=text)]},
            config=thread,
            stream_mode="messages",
        ):
            # 仅打印来自 agent 节点的 AI 消息片段
            if meta.get("langgraph_node") == "agent" and getattr(msg, "content", None):
                if isinstance(msg.content, str):
                    print(msg.content, end="", flush=True)
        print()
