import os, json
from groq import Groq
from dotenv import load_dotenv
import tools

load_dotenv()
client = Groq()  # reads GROQ_API_KEY
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

SYSTEM = (
    "You are PlatformPulse, a support assistant for internal engineers using a data platform "
    "(Spark, Flink, Airflow, Trino, Druid, Notebooks).\n"
    "Rules:\n"
    "- Use the tools for every fact about health, metrics, incidents. Never guess.\n"
    "- Only give troubleshooting steps that come from search_runbooks results. If it returns no match, "
    "say 'No runbook found for this' and stop. Do not invent steps, config names, or procedures.\n"
    "- You can only look things up. Do not offer to create tickets, runbooks, or take any action.\n"
    "- Timestamps in the data are local time (IST). Never label them UTC.\n"
    "- Output for Slack: short, bullet lists with '-', *bold* with single asterisks. "
    "No tables, no headings, no code blocks unless showing a command."
)
def _tool(name, desc, props, required=()):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": list(required)}}}

TOOLS = [
    _tool("get_service_health", "Current health of one service: success rate, p95 latency, errors, open incidents over the last 6 hours.",
          {"service": {"type": "string"}}, ["service"]),
    _tool("list_recent_incidents", "List incidents, newest first. Optionally filter by service, days back, and status ('open' or 'resolved').",
          {"service": {"type": "string"}, "days": {"type": "integer"}, "status": {"type": "string"}}),
    _tool("search_runbooks", "Search troubleshooting runbooks by keywords describing the problem.",
          {"query": {"type": "string"}}, ["query"]),
]
FUNCS = {f.__name__: f for f in (tools.get_service_health, tools.list_recent_incidents, tools.search_runbooks)}

def ask(question: str, max_steps: int = 6) -> str:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    for _ in range(max_steps):
        resp = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS,
                                              tool_choice="auto", temperature=0, max_tokens=1024)
        msg = resp.choices[0].message
        if not msg.tool_calls:                                    # model is done
            return msg.content or ""
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [{"id": tc.id, "type": "function",
                                         "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                                        for tc in msg.tool_calls]})
        for tc in msg.tool_calls:                                 # model asked for tools
            try:
                args = json.loads(tc.function.arguments or "{}")
                out = FUNCS[tc.function.name](**args)
            except Exception as e:
                out = {"error": str(e)}
            print(f"[tool] {tc.function.name}({tc.function.arguments})")
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(out)})
    return "Sorry, I couldn't finish that. Try a more specific question."

if __name__ == "__main__":
    while True:
        print(ask(input("you> ")), "\n")