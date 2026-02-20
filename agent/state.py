
from typing import Optional, TypedDict
from pydantic import BaseModel, Field


class TermOutput(BaseModel):
    term: str = Field(description="从问题中抽取的核心金融数值计算术语")

class AgentInput(BaseModel):
    pretty_context: str = Field(description="格式化后的金融数据上下文")
    question: str = Field(description="用户需要解决的具体问题")
    term: str = Field(description="解析出的术语")
    search_results: str = Field(description="检索到的术语相关信息")

class AgentOutput(BaseModel):
    """
    Agent 的最终输出结构。
    专注于数值结果的交付，同时处理无法回答的情况。
    """
    final_answer: Optional[float] = Field(
        default=None, 
        description="经过Python代码计算后的最终数值结果。如果计算失败、无法得出数值或决定拒绝回答，此项应为 None。"
    )
    
    is_solved: bool = Field(
        default=False, 
        description="标志位：如果成功计算出了有效的数值结果，置为 True。如果出错或因数据缺失无法回答，置为 False。"
    )

    is_refusal: bool = Field(
        default=False,
        description="标志位：如果因为上下文中缺少必要数据、问题超出范围等客观原因导致无法回答，请置为 True。"
    )

    refusal_reason: Optional[str] = Field(
        default=None,
        description="如果 is_refusal 为 True，请在此简要说明原因（例如：'Context missing 2019 revenue data'）。"
    )

    generated_code: Optional[str] = Field(
        default=None, 
        description="生成的可执行Python代码。"
    )

class SummaryOutput(BaseModel):
    summary: str = Field(description="标准化的搜索摘要")

class AnswerOutput(BaseModel):
    answer: str = Field(description="自然语言回答")

class State(TypedDict, total=False):
    pretty_context: str
    question: str
    term: str
    search_results: str
    search_summary: str
    needs_resummary: bool = False
    messages: list
    structured_response: Optional[AgentOutput]
    answer: str
    final_answer: Optional[float]
    is_solved: bool
    is_refusal: bool
    refusal_reason: Optional[str]
    generated_code: Optional[str]