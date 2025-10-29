"""
合并示例 A/B/C/D 到一个可运行的 Python 文件，展示 LangGraph 的核心能力：
- A：顺序编排（纯函数节点，不调用大模型）
- B：条件分支（关键词路由，不调用大模型）
- C：循环（环路 + 条件退出，不调用大模型）
- D：持久化与恢复（MemorySaver，thread_id 累积状态）

运行：
python persion/chapter1/langgraph_examples_combined.py

示例严格遵循官方约定：
- 状态用 TypedDict 定义
- 节点返回“部分状态更新”的字典
- 消息字段使用 add_messages 作为 reducer 来合并
"""

from typing import Annotated

from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages


# =========================
# 示例 A：顺序编排（不调用大模型）
# =========================
class StateA(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def clean_text_A(state: StateA) -> StateA:
    input_msg = state["messages"][-1]
    text = input_msg.content.strip().lower()
    print(f"[A-clean_text] 原始输入: {input_msg.content} -> 清洗后: {text}")
    return {"messages": [AIMessage(content=f"(清洗结果)：{text}")]}  # 追加一条 AIMessage 表示处理结果


def summarize_A(state: StateA) -> StateA:
    last_ai = state["messages"][-1]
    print(f"[A-summarize] 接收到: {last_ai.content}")
    return {"messages": [AIMessage(content=f"总结：你输入的是“{last_ai.content}”")]}


def run_example_A():
    print("\n=========================")
    print("示例A：顺序编排（不调用大模型）")
    print("=========================")
    builder = StateGraph(StateA)
    builder.add_node("clean", clean_text_A)
    builder.add_node("summarize", summarize_A)
    builder.set_entry_point("clean")
    builder.add_edge("clean", "summarize")
    builder.add_edge("summarize", END)
    graph = builder.compile()

    inputs = {"messages": [HumanMessage(content="   Hello LangGraph!   ")]}  # 标准输入结构
    print("=== 流式事件（A） ===")
    for event in graph.stream(inputs):
        print(event)
    print("=== 最终输出（A） ===")
    print(graph.invoke(inputs))


# =========================
# 示例 B：条件分支（不调用大模型）
# =========================
class StateB(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def classifier_B(state: StateB) -> StateB:
    last = state["messages"][-1]
    print(f"[B-classifier] 收到: {last.content}")
    return {"messages": [AIMessage(content="已分类（关键词检查）")]}


def run_tool_path_B(state: StateB) -> StateB:
    print("[B-tools] 进入工具路径（这里不调用模型，只演示业务逻辑）")
    return {"messages": [AIMessage(content="工具路径执行完成")]}


def should_route_B(state: StateB) -> str:
    # 如果用户消息包含“工具”，路由到 tools，否则结束
    human = state["messages"][0]
    return "tools" if "工具" in human.content else "end"


def run_example_B():
    print("\n=========================")
    print("示例B：条件分支（关键词路由，不调用大模型）")
    print("=========================")
    builder = StateGraph(StateB)
    builder.add_node("classify", classifier_B)
    builder.add_node("tools", run_tool_path_B)
    builder.set_entry_point("classify")
    builder.add_conditional_edges("classify", should_route_B, {"tools": "tools", "end": END})
    graph = builder.compile()

    inputs1 = {"messages": [HumanMessage(content="请执行工具相关的操作")]}  # 会走 tools
    inputs2 = {"messages": [HumanMessage(content="不需要工具，直接结束")]}  # 会走 end

    print("=== 流式事件（B-走 tools） ===")
    for e in graph.stream(inputs1):
        print(e)
    print("=== 最终输出（B-走 tools） ===")
    print(graph.invoke(inputs1))

    print("\n=== 流式事件（B-走 end） ===")
    for e in graph.stream(inputs2):
        print(e)
    print("=== 最终输出（B-走 end） ===")
    print(graph.invoke(inputs2))


# =========================
# 示例 C：循环（环路 + 条件退出，不调用大模型）
# =========================
class LoopStateC(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    count: int


def step_C(state: LoopStateC) -> LoopStateC:
    c = state["count"]
    print(f"[C-step] 当前计数: {c} -> 将执行一次步骤")
    return {
        "messages": [AIMessage(content=f"已执行一步，剩余计数={c-1}")],
        "count": c - 1,  # 整数字段默认“最后写入覆盖”
    }


def should_continue_C(state: LoopStateC) -> str:
    return "loop" if state["count"] > 0 else "end"


def run_example_C():
    print("\n=========================")
    print("示例C：循环（计数器递减直到结束）")
    print("=========================")
    builder = StateGraph(LoopStateC)
    builder.add_node("step", step_C)
    builder.set_entry_point("step")
    builder.add_conditional_edges("step", should_continue_C, {"loop": "step", "end": END})
    graph = builder.compile()

    inputs = {"messages": [HumanMessage(content="开始循环")], "count": 3}
    print("=== 流式事件（C-循环3次） ===")
    for e in graph.stream(inputs):
        print(e)
    print("=== 最终输出（C） ===")
    print(graph.invoke(inputs))


# =========================
# 示例 D：持久化与恢复（MemorySaver）
# =========================
class StateD(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def node_D(state: StateD) -> StateD:
    last = state["messages"][-1]
    print(f"[D-node] 处理: {last.content}")
    return {"messages": [AIMessage(content=f"处理完成：{last.content}")]}


def run_example_D():
    print("\n=========================")
    print("示例D：持久化与恢复（同线程累积状态）")
    print("=========================")
    builder = StateGraph(StateD)
    builder.add_node("n", node_D)
    builder.set_entry_point("n")
    builder.add_edge("n", END)
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "demo-thread"}}

    print("=== 第一次调用（D） ===")
    out1 = graph.invoke({"messages": [HumanMessage(content="第一次消息")]}, config=config)
    print(out1)

    print("\n=== 第二次调用（D，同线程，状态会追加） ===")
    out2 = graph.invoke({"messages": [HumanMessage(content="第二次消息")]}, config=config)
    print(out2)


def main():
    run_example_A()
    run_example_B()
    run_example_C()
    run_example_D()


if __name__ == "__main__":
    main()