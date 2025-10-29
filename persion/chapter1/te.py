# 安装 LangGraph
# pip install -U langgraph

from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

# 定义状态
class State(TypedDict):
    messages: Annotated[list, operator.add]

# 创建图
graph = StateGraph(State)

# 定义节点函数
def call_model(state):
    # 这里可以调用 LLM 模型
    # 为简化示例，我们只返回一个固定消息
    return {"messages": [{"role": "assistant", "content": "Hello! How can I help you today?"}]}

# 添加节点
graph.add_node("model", call_model)

# 设置入口点
graph.set_entry_point("model")

# 添加条件边（这里简单地结束）
graph.add_edge("model", END)

# 编译图
app = graph.compile()

# 使用应用
result = app.invoke({"messages": [{"role": "user", "content": "Hi there!"}]})
print(result)
