# Slack bot - support Assistant for a Data Platform

A Slack chatbot and dashboard that help engineers check the health of a data platform (Spark, Flink, Airflow, Trino, Druid, Notebooks) without digging through multiple tools. It runs on **sample data** that I generated to mimic real platform telemetry.


## The problem

Support engineers on a data platform answer the same questions again and again: *"Is Airflow healthy?"*, *"What broke this week?"*, *"How do I fix a scheduler lag?"* The answers sit in dashboards, incident logs and runbooks. PlatformPulse answers them in one message, inside the Slack channel where people already ask.

I built this as a small version of that workflow to learn the tools involved: tool-calling LLM agents, Slack integrations and dashboards.

## What it does

- **Slack bot:** ask in a channel or DM, e.g. `@Slack bot is Airflow healthy?` or `what broke this week across all services?`
- **Slash commands:**
  - `/platform-health` shows every service's status instantly, with no AI involved
  - `/incident-summary [service]` summarizes recent incidents and suggests fix guides
- **Dashboard (Streamlit + Plotly):** incidents over time, mean time to resolve, response speed (p95 latency) and success rate per service, with an "Ask PlatformPulse" box

## How it works

```
Slack  →  Slack Bolt (Socket Mode)  →  agent loop (LLM)  →  tools  →  SQLite
                                                                        ↑
                                              Streamlit dashboard ──────┘
```

1. A question arrives from Slack (or the dashboard).
2. The LLM is given three tools and decides which to call:
   - `get_service_health(service)` – success rate, latency, errors and open incidents over the last 6 hours
   - `list_recent_incidents(service, days, status)` – incident history
   - `search_runbooks(query)` – fix guides
3. My code runs the chosen tool and sends the result back to the LLM.
4. This repeats (up to 6 steps) until the LLM writes the final answer.

The model never touches the database directly. It can only ask for the three tools above.

## Design decisions

- **Answers come from tool results only.** If no runbook matches, the bot says so and doesn't invent steps.
- **`/platform-health` skips the LLM.** For a fixed question, plain code is faster, free and always consistent.
- **Step limit.** The agent loop stops after 6 steps to avoid runaway loops and cost.
- **Errors are returned to the model as data** (e.g. unknown service), so it can explain them instead of crashing.

## Issues I found and fixed

- **Made-up runbook steps.** For incident types with no runbook, the first version wrote its own troubleshooting steps and offered to "open a request with the documentation team", which it can't do. I fixed this with stricter rules in the system prompt (only use runbook results, say "No runbook found", don't offer actions).
- **Wrong time label.** The bot called local-time data "UTC". Fixed in the prompt.
- **Slack formatting.** Slack doesn't render markdown tables or `**bold**`. The prompt now asks for bullets, and a small helper converts bold syntax.

## Evaluation

`eval.py` runs N questions through the agent (healthy and degraded services, a question with no runbook, an unknown service, a request for an action it can't perform) and checks the answers.

Result: **X / N passing** *(fill in after running `python eval.py`)*

The checks are simple text matches, so a failure can mean a wrong answer or just different wording.

## Run it

Requirements: Python 3.10+, a free [Groq](https://console.groq.com) API key, and a Slack workspace you control.

```bash
git clone https://github.com/Mahima-R-S/platformpulse
cd platformpulse
pip install -r requirements.txt
python db.py                 # create the sample database
```

Create a `.env` file (never commit it):

```
GROQ_API_KEY=...
GROQ_MODEL=openai/gpt-oss-120b
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

```bash
python agent.py              # try the agent in the terminal
streamlit run dashboard.py   # dashboard at http://localhost:8501
python slack_bot.py          # start the Slack bot
```

### Slack app setup (short version)

1. Create an app at api.slack.com/apps and turn on **Socket Mode**. Create an app-level token with the `connections:write` scope.
2. Bot scopes: `app_mentions:read`, `chat:write`, `commands`, `im:history`, `im:read`.
3. Event subscriptions (bot events): `app_mention`, `message.im`.
4. Create the slash commands `/platform-health` and `/incident-summary`.
5. Install the app to your workspace and run `/invite @YourApp` in a channel.

## Project files

| File | Purpose |
|---|---|
| `db.py` | Creates and fills the sample SQLite database |
| `tools.py` | The three tools and the runbook text |
| `agent.py` | The LLM agent loop |
| `dashboard.py` | Streamlit dashboard |
| `slack_bot.py` | Slack bot and slash commands |
| `eval.py` | Test questions for the agent |

## Limitations

- The data is generated, not from a real platform.
- Runbook search is simple keyword matching.
- No user authentication or access control.
- Free-tier model limits can slow responses.

## What I'd do next

- Read real metrics from a monitoring system such as Prometheus instead of sample data
- Replace keyword runbook search with embedding-based retrieval
- Expose the tools through an MCP server
- Log every tool call for debugging and auditing
- Add more evaluation questions

## Notes

Built over a weekend with AI-assisted coding (Claude), and I reviewed and tested each part myself.
