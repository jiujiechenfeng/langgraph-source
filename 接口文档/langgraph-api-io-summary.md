# LangGraph 主要方法与类型（输入/输出）总结

> 基于仓库 `langgraph` 源码与文档梳理，重点覆盖 StateGraph 构建方法、编译后运行方法（Pregel/CompiledStateGraph），以及 LangGraph/“langchain_core”自定义类型与返回载荷的字段说明。便于快速查阅方法的参数、返回值与事件/流数据形态。

## StateGraph 构建 API

- `StateGraph(state_schema, context_schema=None, input_schema=None, output_schema=None)`

  - 输入：
    - `state_schema`: 图状态类型（`TypedDict`/`pydantic`/`dataclass`/`TypedDictLike`）。
    - `context_schema`: 可选，运行时静态上下文类型。
    - `input_schema`: 可选，输入类型，默认与 `state_schema` 相同。
    - `output_schema`: 可选，输出类型，默认与 `state_schema` 相同。
  - 输出：`StateGraph` 构建器实例。
- `add_node(node | name, action=None, *, defer=False, metadata=None, input_schema=None, retry_policy=None, cache_policy=None, destinations=None, **deprecated)`

  - 输入：
    - `node`: 可为 `StateNode`（函数/`Runnable`，签名接收 state 与可选 config/runtime），或字符串（节点名）。
    - `action`: 当 `node` 为字符串时，配套的函数/`Runnable`。
    - `defer`: 推迟执行至运行结束前（收尾阶段）。
    - `metadata`: 节点元数据字典。
    - `input_schema`: 指定该节点的输入模式（不指定时默认用图的 `state_schema`）。
    - `retry_policy`: 节点重试策略（可单个或序列，匹配第一个生效）。
    - `cache_policy`: 节点缓存策略。
    - `destinations`: 用于“无边”或返回 `Command` 的图渲染提示（仅用于可视化，不影响执行）。可为 `{目标节点名: 边标签}` 或 `(目标节点名, ...)`。
  - 输出：`Self`（便于链式调用）。
- `add_edge(start_key: str | list[str], end_key: str)`

  - 输入：
    - `start_key`: 起始节点名或节点名列表；若为列表，表示等待“全部”完成后再执行 `end_key`。
    - `end_key`: 目标节点名。
  - 约束/异常：
    - 禁止 `END` 作为起点、`START` 作为终点；所有节点需已 `add_node`。
  - 输出：`Self`。
- `add_conditional_edges(source, path, path_map=None)`

  - 输入：
    - `source`: 条件边的发出节点名。
    - `path`: 可返回单个或多个目的（节点名或 `END`），可为 `Callable`/`Awaitable`/`Runnable`。
    - `path_map`: 可选，将 `path` 返回的枚举值映射到节点名（无则需 `path` 返回节点名）。
  - 说明：无类型提示或 `path_map` 时，渲染会假设可转到图中任意节点。
  - 输出：`Self`。
- `add_sequence(nodes: Sequence[StateNode | (name, StateNode)])`

  - 输入：按顺序执行的一组节点，名称缺省时按对象名推断；名称需唯一。
  - 异常：空序列或重复名称将抛错。
  - 输出：`Self`。
- `set_entry_point(key: str)` / `set_conditional_entry_point(path, path_map=None)`

  - 输入：设置图的入口节点；条件入口同 `add_conditional_edges(START, ...)`。
  - 输出：`Self`。
- `set_finish_point(key: str)`

  - 输入：设置图的结束节点；到达该节点即停止执行。
  - 输出：`Self`。
- `validate(interrupt: Sequence[str] | None = None)`

  - 输入：可选中断节点名列表，用于校验图结构与中断配置。
  - 输出：`Self`。
- `compile(checkpointer=None, *, cache=None, store=None, interrupt_before=None, interrupt_after=None, debug=False, name=None)`

  - 输入：
    - `checkpointer`: `None | bool | BaseCheckpointSaver`（详见类型）。
    - `cache`: `BaseCache | None`。
    - `store`: `BaseStore | None`。
    - `interrupt_before`/`interrupt_after`: 要在节点前/后中断的节点名序列或 `"*"`。
    - `debug`: 是否开启调试模式。
    - `name`: 编译后图名，默认 `"LangGraph"`。
  - 输出：`CompiledStateGraph`（实现 `Runnable` 接口，可 `invoke/stream/batch/async`）。

## 编译后运行（Pregel / CompiledStateGraph）

- `get_input_jsonschema(config: RunnableConfig | None) -> dict[str, Any]`

  - 输出：输入 JSONSchema（由构建器的 `input_schema` 与图 `channels` 生成）。
- `get_output_jsonschema(config: RunnableConfig | None) -> dict[str, Any]`

  - 输出：输出 JSONSchema（由构建器的 `output_schema` 与图 `channels` 生成）。
- `stream(input: InputT | Command | None, config: RunnableConfig | None = None, *, context=None, stream_mode=None, print_mode=(), output_keys=None, interrupt_before=None, interrupt_after=None, durability=None, subgraphs=False, debug=None) -> Iterator[dict[str, Any] | Any]`

  - 输入：
    - `input`: 图输入或 `Command`。
    - `config`: 运行配置（见“配置字段”）。
    - `context`: 静态上下文（与 `context_schema` 对应）。
    - `stream_mode`: 单个或列表，详见类型 `StreamMode`。
    - `print_mode`: 同 `stream_mode`，仅打印不影响输出。
    - `output_keys`: 要流出的通道键，默认所有非上下文通道。
    - `interrupt_before`/`interrupt_after`: 在指定节点前/后中断（默认取自编译时设置）。
    - `durability`: 持久化模式（`sync|async|exit`）。
    - `subgraphs`: 是否包含子图事件；为真时输出形如 `(namespace, data)` 或 `(namespace, mode, data)`。
    - `debug`: 覆盖运行时调试开关。
  - 输出（按 `stream_mode` 形态）：
    - `"values"`: 每步状态值（含中断）。
    - `"updates"`: 每步节点/任务更新，若多节点同一步执行会分别发出多个更新。
    - `"messages"`: LLM 消息的流式 token 与元数据，二元组 `(token, metadata)`。
    - `"checkpoints"`: 创建检查点事件（同 `get_state()` 返回格式）。
    - `"tasks"`: 任务开始/结束事件（含结果/错误）。
    - `"custom"`: 由节点内部通过 `StreamWriter` 写入的自定义数据。
    - 列表模式时输出为 `(mode, data)` 或 `(namespace, mode, data)`。
- `invoke(input, config=None, *, context=None, stream_mode="values", print_mode=(), output_keys=None, interrupt_before=None, interrupt_after=None, durability=None, **kwargs) -> dict[str, Any] | Any`

  - 行为：内部使用 `stream`；当 `stream_mode == "values"` 时返回“最新值”（若包含中断则合并 `{"__interrupt__": [...]}`），否则返回输出块列表。
- `ainvoke(...) -> dict[str, Any] | Any`

  - 同步版 `invoke` 的异步变体。
- `get_state(config: RunnableConfig, *, subgraphs: bool = False) -> StateSnapshot`

  - 要求：必须设置检查点器（否则抛错）。支持通过 `checkpoint_ns` 路由到子图。
  - 输出：`StateSnapshot`（见“类型与字段”）。
- `aget_state(...) -> StateSnapshot`

  - 异步变体。
- `update_state(config: RunnableConfig, values: dict[str, Any] | Any | None, as_node: str | None = None, task_id: str | None = None) -> RunnableConfig`

  - 行为：将 `values` 作为指定节点/任务的写入更新应用到图状态（未指定 `as_node` 时，尝试选择最近更新的节点）。
  - 输出：更新后的 `RunnableConfig`（新的检查点配置）。
- `aupdate_state(...) -> RunnableConfig`

  - 异步变体。

## 类型与字段（langgraph.types）

- `Durability`: `"sync" | "async" | "exit"`

  - 执行持久化模式（同步/异步/退出时持久化）。
- `All`: `"*"`

  - 表示对“所有节点”应用（如中断）。
- `Checkpointer`: `None | bool | BaseCheckpointSaver`

  - `True`: 启用持久化检查点；`False`: 禁用（不继承父图）；`None`: 继承父图。
- `StreamMode`: `"values" | "updates" | "checkpoints" | "tasks" | "debug" | "messages" | "custom"`

  - 控制 `stream` 输出模式（见上文各模式含义）。
- `StreamWriter`: `Callable[[Any], None]`

  - 在 `"custom"` 模式下注入到节点内部的写出函数。
- `RetryPolicy`（`NamedTuple`）

  - 字段：
    - `initial_interval: float`（首个重试前的等待秒数，默认0.5）
    - `backoff_factor: float`（指数退避因子，默认2.0）
    - `max_interval: float`（两次重试的最大间隔秒数，默认128.0）
    - `max_attempts: int`（最大尝试次数（含首次），默认3）
    - `jitter: bool`（是否加入随机抖动，默认True）
    - `retry_on: Exception | Sequence[Exception] | Callable[[Exception], bool]`（触发重试的异常或判定逻辑，默认 `default_retry_on`）
- `CachePolicy`（`dataclass`）

  - 字段：
    - `key_func: Callable[..., str|bytes]`（默认 `default_cache_key`，按输入生成缓存键）
    - `ttl: int | None`（缓存生存时间秒；`None` 为不过期）
- `Interrupt`（`dataclass`）

  - 字段：
    - `value: Any`（中断关联值）
    - `id: str`（中断ID，用于直接恢复）
  - 兼容/变更：`interrupt_id` 属性已弃用（请使用 `id`）。
- `StateUpdate`（`NamedTuple`）

  - 字段：`values: dict[str, Any] | None`, `as_node: str | None`, `task_id: str | None`
  - 用途：批量/单次 `update_state` 时的更新载体。
- `PregelTask`（`NamedTuple`）

  - 字段：`id`, `name`, `path`, `error`, `interrupts: tuple[Interrupt, ...]`, `state: None | RunnableConfig | StateSnapshot`, `result: Any | None`
- `PregelExecutableTask`（`dataclass`）

  - 字段：`name`, `input`, `proc: Runnable`, `writes: deque[(str, Any)]`, `config: RunnableConfig`, `triggers: Sequence[str]`, `retry_policy: Sequence[RetryPolicy]`, `cache_key: CacheKey | None`, `id`, `path`, `writers`, `subgraphs`
- `StateSnapshot`（`NamedTuple`）

  - 字段与含义：
    - `values: dict[str, Any] | Any`（当前通道值）
    - `next: tuple[str, ...]`（本步每个任务将执行的节点名）
    - `config: RunnableConfig`（用于获取快照的配置）
    - `metadata: CheckpointMetadata | None`（检查点元数据）
    - `created_at: str | None`（快照创建时间戳）
    - `parent_config: RunnableConfig | None`（父快照的配置）
    - `tasks: tuple[PregelTask, ...]`（本步待执行任务，若已尝试可含错误）
    - `interrupts: tuple[Interrupt, ...]`（本步发生且待处理的中断）
- `Send`

  - 用途：在条件边中向特定节点发送“下一步输入”（可与图核心 state 不同），支持并行/Map-Reduce 场景。
  - 字段：`node: str`, `arg: Any`。
- `Command[N]`（`dataclass`, 泛型）

  - 作用：在节点返回值中发出“更新图状态/跳转节点/恢复中断”等命令。
  - 字段：
    - `graph: str | None`（`None` 当前图；`Command.PARENT` 最近的父图）
    - `update: Any | None`（状态更新，可为映射/二元组列表/具注解对象/单值）
    - `resume: dict[str, Any] | Any | None`（恢复值；与 `interrupt()` 搭配）
    - `goto: Send | Sequence[Send | N] | N`（跳转节点，或以 `Send` 指定输入）
  - 常量：`Command.PARENT = "__parent__"`（指向父图）。
- `interrupt(value: Any) -> Any`

  - 作用：在节点内部触发“可恢复的中断”，将 `value` 暴露给客户端；首次调用抛出 `GraphInterrupt`，随后调用在同一任务内将返回恢复值。
  - 要求：必须启用 `checkpointer`（依赖持久化状态）。
  - 搭配：由客户端通过 `Command(resume=...)` 恢复继续执行；多次中断按出现顺序匹配恢复列表。

## 配置字段（RunnableConfig / configurable）

- `config["configurable"]` 典型键：
  - `thread_id: str`（使用检查点器时必须；用于标识会话/线程）
  - `checkpoint_ns: str`（检查点命名空间；可用于子图路由、`get_state` 子图查询）
  - `checkpoint_id: str`（具体检查点ID）
  - `durability: Durability`（持久化模式，默认 `"async"`）
  - `runtime: Runtime`（运行时对象，含 `store` 等）
  - `cache: BaseCache`（运行时缓存实现）
  - 其他运行键（内部使用）：`send`, `stream`, `task_id`, `node_finished`, `read` 等。

## 输出/流数据形态要点

- `invoke` 默认 `stream_mode="values"`：返回“最终状态值”，如有中断则合并 `{"__interrupt__": Interrupt(...)}`。
- `stream` 用列表模式可同时订阅多个 `StreamMode`，输出统一为 `(mode, data)`；在子图开启时为 `(namespace, mode, data)`。
- `get_state`/`stream` 的检查点事件载荷与 `StateSnapshot` 字段一致（可据此解析任务、中断、父配置等信息）。

---

以上覆盖了官方主要方法与自定义类型的关键输入/输出与字段。更多使用示例与边界行为可结合仓库的 How-to 与 Reference 文档继续深入。
