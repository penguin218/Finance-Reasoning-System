# 基于 LangGraph + MCP 的金融数值推理系统

一个面向金融数值推理的智能系统，融合 LangGraph 的流程编排能力与 LangChain 的工具与代理机制，围绕“可计算、可追溯、可复核”的目标工作。系统自动抽取核心术语、检索与摘要知识、生成并执行 Python 计算代码，最终输出结构化结果与自然语言解释，便于审计与复用。

## 系统结构

```
.
├─ agent/
│  ├─ graph.py            # LangGraph 图定义与编译入口
│  ├─ node.py             # 节点实现（抽取术语、搜索、摘要、求解、回答）
│  ├─ state.py            # 状态与结构化输出定义
│  └─ model.py            # LLM 实例配置
├─ mcp_config/
│  ├─ mcp_server.py       # MCP 工具服务（Tavily 搜索 + Python 执行器）
│  └─ client.py           # MCP 工具客户端
├─ langgraph.json         # LangGraph 运行配置
└─ README.md
```

## 系统特点

- MCP 工具接入：通过 `mcp_config/mcp_server.py` 暴露 Tavily 搜索与 Python 执行器，并由 `mcp_config/client.py` 统一接入工具
- LangGraph Studio 可视化：`langgraph dev` 启动后可在 Studio 中可视化查看与调试图流程
- create_agent 驱动：使用 LangChain 的 `create_agent` 统一装配模型、工具与上下文 Schema
- 中间件扩展：通过 middleware 注入 `ToolCallLimitMiddleware` 与 `SummarizationMiddleware`
- 对话摘要能力：`SummarizationMiddleware` 在对话过长时自动摘要，降低上下文负担
- 人工审批闭环：`interrupt` 机制支持摘要审批，拒绝后回到搜索环节

## Studio 操作截图

总体视图：左侧为 Workflow，右侧为节点调用情况

![LangGraph Studio 总览](<https://github.com/penguin218/Finance-Reasoning-System/blob/main/system_picture/workflow.png>)

人在回路：右下角INTERRUPT展示摘要审批与回流搜索的交互

![LangGraph Studio 人在回路](<https://github.com/penguin218/Finance-Reasoning-System/blob/main/system_picture/hitl.png>)

## 核心流程

1. 抽取术语：从问题中提取一个核心金融数值计算术语
2. 在线搜索：使用 Tavily 进行检索
3. 搜索摘要：生成标准化的三行摘要（术语 / 概念 / 公式）
4. 人工审批：通过 `interrupt` 决定继续或重新搜索
5. 构建消息：拼接上下文、问题、术语与搜索结果
6. 计算求解：调用 Agent 生成并执行 Python 代码
7. 自然语言答复：根据结构化结果输出回答

## 依赖与环境变量

推荐 Python 版本：3.11

安装依赖：

```bash
pip install -r requirements.txt
```

主要依赖包括（以实际环境为准）：

- langgraph
- langchain
- langchain_openai
- langchain_mcp_adapters
- fastmcp
- python-dotenv

环境变量：

- `MODEL_NAME`：模型名称
- `MODEL_BASE_URL`：模型 Base URL
- `MODEL_API_KEY`：模型 API Key
- `TAVILY_API_KEY`：Tavily 搜索 API Key
- `MCP_SERVER_URL`：MCP SSE 服务地址，默认 `http://localhost:8000/sse`

建议将变量写入 `.env`，并避免把密钥直接写进代码。

## 启动步骤

1. 创建 `.env` 并配置所需 Key

```env
MODEL_NAME=模型名称
MODEL_BASE_URL=模型服务地址
MODEL_API_KEY=你的模型KEY
TAVILY_API_KEY=你的Tavily KEY
MCP_SERVER_URL=http://localhost:8000/sse
```

2. 启动 MCP 工具服务

```bash
python mcp_config/mcp_server.py
```

3. 启动 LangGraph 开发服务

```bash
langgraph dev
```

LangGraph 会读取 `langgraph.json` 中的图配置并加载 `agent/graph.py:graph`。

## langgraph.json 的用途

`langgraph.json` 用于定义 LangGraph 的运行入口与依赖信息：包括图名称与对应的图对象路径，以及 `.env` 的加载位置。运行 `langgraph dev` 时会读取该文件完成图的加载与服务启动。

## 使用示例（Python）

```python
import asyncio
from agent.graph import graph

async def main():
    state = {
        "pretty_context": "本金: 100000, 年利率: 3.5%, 期限: 5年",
        "question": "计算复利本息和"
    }
    result = await graph.ainvoke(state)
    print(result)

asyncio.run(main())
```

## 输出结构

关键字段定义于 `agent/state.py`：

- `final_answer`: 数值计算结果
- `is_solved`: 是否成功得到数值结果
- `is_refusal`: 是否拒答
- `refusal_reason`: 拒答原因
- `generated_code`: 生成的 Python 代码
- `answer`: 自然语言回答

## 说明

- Tavily 搜索没有配置 `TAVILY_API_KEY` 时会返回提示文本
- 代码执行器基于 `exec`，仅用于开发与演示场景
