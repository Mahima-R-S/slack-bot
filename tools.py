from datetime import datetime, timedelta
from db import conn, SERVICES

_LOOKUP = {s.lower(): s for s in SERVICES}

def _norm(service):
    return _LOOKUP.get((service or "").strip().lower())

def get_service_health(service: str) -> dict:
    s = _norm(service)
    if not s:
        return {"error": f"Unknown service '{service}'. Known: {SERVICES}"}
    c = conn()
    rows = c.execute("SELECT success_rate, p95_latency_ms, error_count FROM metrics "
                     "WHERE service=? ORDER BY ts DESC LIMIT 6", (s,)).fetchall()
    sr = sum(r[0] for r in rows) / len(rows)
    lat = sum(r[1] for r in rows) / len(rows)
    errs = sum(r[2] for r in rows)
    open_inc = c.execute("SELECT COUNT(*) FROM incidents WHERE service=? AND status='open'", (s,)).fetchone()[0]
    return {"service": s, "window": "last 6 hours",
            "success_rate_pct": round(sr * 100, 2), "p95_latency_ms": round(lat),
            "error_count": errs, "open_incidents": open_inc,
            "status": "healthy" if sr >= 0.95 and open_inc == 0 else "degraded"}

def list_recent_incidents(service: str = "", days: int = 7, status: str = "") -> list:
    c = conn()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    q = "SELECT id, service, severity, title, status, created_at, resolved_at FROM incidents WHERE created_at >= ?"
    args = [cutoff]
    if service:
        s = _norm(service)
        if not s:
            return [{"error": f"Unknown service '{service}'"}]
        q += " AND service=?"; args.append(s)
    if status:
        q += " AND status=?"; args.append(status)
    q += " ORDER BY created_at DESC LIMIT 25"
    cols = ["id", "service", "severity", "title", "status", "created_at", "resolved_at"]
    return [dict(zip(cols, r)) for r in c.execute(q, args).fetchall()]

RUNBOOKS = {
    "Airflow scheduler lag": "1) Check scheduler heartbeat in UI. 2) Check metadata DB connections and slow queries. 3) Restart scheduler pod if heartbeat stale >5 min. 4) Clear zombie tasks. Escalate to SEV1 if >30 min of delay.",
    "Spark executor OOM": "1) Check which stage failed in Spark UI. 2) Increase spark.executor.memory or reduce partition size. 3) Look for data skew on the shuffle key. 4) Re-run with spark.sql.shuffle.partitions tuned.",
    "Flink checkpoint timeout": "1) Check for backpressure in the Flink UI. 2) Increase checkpoint timeout. 3) Check state backend size and disk IO. 4) Enable unaligned checkpoints if backpressure persists.",
    "Trino coordinator memory": "1) Identify top memory queries from the Trino UI. 2) Kill runaway queries. 3) Lower query.max-memory-per-node for the offending group. 4) Notify the owning team.",
    "Notebook kernel fails to start": "1) Check cluster attach status. 2) Verify the user's image and quota. 3) Cull idle kernels. 4) Recreate the pod.",
    "Druid segment handoff delay": "1) Check coordinator logs. 2) Verify deep storage reachability. 3) Check historical node disk usage. 4) Restart the stuck ingestion task.",
}

def search_runbooks(query: str) -> list:
    words = set(query.lower().split())
    scored = []
    for title, body in RUNBOOKS.items():
        text = (title + " " + body).lower()
        score = sum(1 for w in words if w in text)
        if score:
            scored.append((score, title, body))
    scored.sort(reverse=True)
    return [{"title": t, "steps": b} for _, t, b in scored[:2]] or [{"message": "No matching runbook"}]