"""
基于你仓库内的 LangGraph 官方用法，提供一个“完整示例：图 + 边 + 工具调用”。

特点
- 使用 StateGraph 和 add_messages（官方推荐的消息合并器）
- 条件边：根据是否存在 tool_calls 决定是否调用工具或结束
- 工具调用：定义两个工具（get_weather、multiply），由模型触发调用，工具结果通过 ToolMessage 写回状态
- 读取 .env：从 /Users/gaoxinyue/Desktop/AI/langgraph-source/persion/chapter1/.env 加载 OPENAI_* 配置

运行
python persion/chapter1/langgraph_tool_example.py
"""

import os
from typing import Annotated

from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict

from dotenv import load_dotenv

from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages


# 1) 定义图的状态：只包含 messages，并使用 add_messages 作为 reducer
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


# 2) 定义工具（参考官方 @tool 方式）
@tool
def get_weather(city: str) -> str:
    """返回指定城市的当前温度(整数，示例固定返回 26)。"""
    # 在真实场景中，这里可以接第三方天气 API；为演示简化为固定值。
    return "26"


@tool
def multiply(a: int, b: int) -> int:
    """计算乘法 a*b。"""
    return a * b


TOOLS = [get_weather, multiply]
TOOL_MAP = {t.name: t for t in TOOLS}


# 3) 节点：LLM Agent（绑定工具），根据当前 messages 产生 AIMessage（可能包含 tool_calls）
def agent_node(state: State) -> State:
    messages = state["messages"]

    # ChatOpenAI 会从环境变量读取 OPENAI_API_KEY / OPENAI_BASE_URL
    # 也可传入 model，它将影响工具调用能力（请确保所选模型支持 tool calls）。
    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model_name, temperature=0)

    # 绑定工具，使模型能输出 tool_calls
    llm_with_tools = llm.bind_tools(TOOLS)

    # 返回部分状态更新：仅追加 AI 的响应消息
    ai_msg = llm_with_tools.invoke(messages)
    return {"messages": [ai_msg]}


# 4) 节点：执行工具调用（把 AIMessage 的 tool_calls 逐个执行，并以 ToolMessage 写回）
def call_tools_node(state: State) -> State:
    messages = state["messages"]
    # 找到最新的 AIMessage（包含 tool_calls）
    last_ai = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            last_ai = msg
            break

    if last_ai is None:
        return {}

    tool_calls = getattr(last_ai, "tool_calls", None) or last_ai.additional_kwargs.get("tool_calls")
    if not tool_calls:
        return {}

    results: list[ToolMessage] = []
    for tc in tool_calls:
        name = tc.get("name")
        args = tc.get("args", {})
        tc_id = tc.get("id")

        tool_ = TOOL_MAP.get(name)
        if tool_ is None:
            # 未知工具，直接返回一个错误的 ToolMessage（也可选择忽略）
            results.append(ToolMessage(content=f"Unknown tool: {name}", tool_call_id=tc_id, name=name))
            continue

        try:
            # @tool 装饰器生成的对象支持 .invoke(args)
            observation = tool_.invoke(args)
            # 把工具结果写回：ToolMessage，带上 tool_call_id 以便模型继续关联
            results.append(ToolMessage(content=str(observation), tool_call_id=tc_id, name=name))
        except Exception as e:
            results.append(ToolMessage(content=f"Tool error: {e}", tool_call_id=tc_id, name=name))

    # 返回部分状态更新：追加所有 ToolMessage
    return {"messages": results}


# 5) 条件路由：判断是否需要继续调用工具
def should_continue(state: State) -> str:
    messages = state["messages"]
    if not messages:
        return "end"
    last = messages[-1]
    if isinstance(last, AIMessage):
        tool_calls = getattr(last, "tool_calls", None) or last.additional_kwargs.get("tool_calls")
        if tool_calls:
            return "tools"
    return "end"


def build_graph():
    builder = StateGraph(State)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", call_tools_node)

    # 入口
    builder.set_entry_point("agent")

    # 条件边：agent -> (tools 或 END)
    builder.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END},
    )

    # 工具执行完返回 agent（循环），直到模型不再请求工具
    builder.add_edge("tools", "agent")

    # 可选：持久化，便于回放与恢复
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    return graph


def main():
    # 加载 .env（使用你提供的绝对路径）
    load_dotenv(dotenv_path="/Users/gaoxinyue/Desktop/AI/langgraph-source/persion/chapter1/.env")

    graph = build_graph()

    # 示例输入：请模型先调用 get_weather(city=北京)，再把结果乘以 3
    # 使用标准字典输入结构，messages 列表中放入 HumanMessage
    inputs: State = {
        "messages": [
            HumanMessage(
                content=(
                    "请先用 get_weather(city=北京) 获取温度(返回整数)，再用 multiply(a=温度, b=3) 计算结果，最后给出答案。"
                )
            )
        ]
    }

    # 配置 thread_id 便于持久化区分会话
    config = {"configurable": {"thread_id": "tool-demo"}}

    print("=== 流式事件(节选) ===")
    for step in graph.stream(inputs, config=config):
        # 每个 step 是一次状态增量或事件字典
        print(step)

    print("\n=== 最终输出 ===")
    output = graph.invoke(inputs, config=config)
    # 输出是状态字典，包含 messages（包含 AI 的最终回复）
    print(output)


if __name__ == "__main__":
    main()