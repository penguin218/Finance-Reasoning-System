import json
import os
import re
import textwrap
import urllib.request
from fastmcp import FastMCP

mcp = FastMCP("MCP_SERVER")

@mcp.tool()
def tavily_search(query: str) -> str:
    if not query:
        return ""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return "TAVILY_API_KEY is not set"
    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": 5
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.tavily.com/search",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8", errors="ignore")
        parsed = json.loads(raw)
        results = parsed.get("results", [])
        if not results:
            return parsed.get("answer", "") or ""
        lines = []
        for item in results:
            title = item.get("title") or ""
            url = item.get("url") or ""
            content = item.get("content") or ""
            line = " - ".join([part for part in [title, url, content] if part])
            if line:
                lines.append(line)
        return "\n".join(lines)
    except Exception as exc:
        return f"Tavily search error: {exc}"

def extract_code_block(text: str) -> str:
    pattern = r"```python\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)
    if "def solution" in text or "import" in text:
        return text
    return ""

def _execute_code(program: str, function_name: str = "solution") -> str:
    cleaned_code = extract_code_block(program)
    if not cleaned_code:
        return "Error: No valid Python code block found. Please wrap code in ```python ... ```."
    if f"def {function_name}" not in cleaned_code:
        indented_code = textwrap.indent(cleaned_code, "    ")
        program_str = f"def {function_name}():\n{indented_code}"
    else:
        program_str = cleaned_code
    full_program = (
        "import pandas as pd\n"
        "import numpy as np\n"
        "import math\n"
        "from decimal import Decimal\n"
        f"{program_str}"
    )
    global_namespace = {}
    try:
        exec(full_program, global_namespace)
        if function_name not in global_namespace:
            return f"Error: Function '{function_name}' was not defined in the code."
        func_to_run = global_namespace[function_name]
        try:
            execution_result = func_to_run()
            return f"Execution Success. Result: {execution_result}"
        except TypeError:
            return "Error: TypeError during execution. Ensure 'solution()' takes no arguments."
        except Exception as e:
            return f"Runtime Error inside function: {str(e)}"
    except Exception as e:
        return f"Syntax/Compile Error: {str(e)}"

@mcp.tool()
def financial_python_executor(code: str) -> str:
    return _execute_code(code)

if __name__ == "__main__":
    mcp.run(transport="sse")
