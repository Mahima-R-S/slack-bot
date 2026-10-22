import os, re
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import agent, tools

load_dotenv()
app = App(token=os.environ["SLACK_BOT_TOKEN"])
def fmt(text: str) -> str:
    return text.replace("**", "*")
@app.event("app_mention")
def on_mention(event, say):
    text = re.sub(r"<@[^>]+>", "", event["text"]).strip()
    say(text=fmt(agent.ask(text)), thread_ts=event.get("thread_ts") or event["ts"])

@app.event("message")
def on_dm(event, say):
    if event.get("channel_type") == "im" and not event.get("bot_id"):
        say(fmt(agent.ask(event["text"])))

@app.command("/platform-health")
def health(ack, respond):
    ack()
    lines = []
    for s in tools.SERVICES:
        h = tools.get_service_health(s)
        icon = ":large_green_circle:" if h["status"] == "healthy" else ":red_circle:"
        lines.append(f"{icon} *{s}*: success {h['success_rate_pct']}%, p95 {h['p95_latency_ms']}ms, open incidents {h['open_incidents']}")
    respond("\n".join(lines))

@app.command("/incident-summary")
def summary(ack, respond, command):
    ack()
    svc = command["text"].strip() or "all services"
    respond(fmt(agent.ask(f"Summarize incidents from the last 7 days for {svc}. Group by theme, call out anything still open, and suggest a runbook if relevant.")))

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()