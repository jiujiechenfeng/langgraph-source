# 参考: docs/docs/how-tos/graph-api.md
from typing_extensions import TypedDict
from typing import Annotated
from langchain_core.messages import AnyMessage, AIMessage
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages

# 1) 定义状态（字典/TypedDict），并为 messages 指定 add_messages 合并器


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    extra_field: int

# 2) 定义节点：读取 state，返回“部分状态更新”的字典


def node(state: State):
    messages = state["messages"]
    new_msg = AIMessage("Hello!")
    # 返回要更新的字段，不要原地修改
    return {"messages": messages + [new_msg], "extra_field": 10}


# 3) 搭图与编译
builder = StateGraph(State)
builder.add_node("node", node)
builder.set_entry_point("node")
graph = builder.compile()

# 4) 调用（invoke），严格遵循输入字典结构
out = graph.invoke({"messages": [], "extra_field": 0})
# out 是输出状态字典，如:
# {
#   "messages": [..., AIMessage("Hello!")],
#   "extra_field": 10
# }
