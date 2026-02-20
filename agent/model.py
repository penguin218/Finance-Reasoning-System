import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model= os.getenv("MODEL_NAME"),
    base_url= os.getenv("MODEL_BASE_URL"),
    api_key= os.getenv("MODEL_API_KEY")
)
