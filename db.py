import sqlite3, random
from datetime import datetime, timedelta

DB = "platform.db"
SERVICES = ["Spark", "Flink", "Airflow", "Trino", "Druid", "Notebooks"]
TITLES = {
    "Spark": ["Executor OOM on shuffle stage", "Job stuck in pending queue", "Driver lost heartbeat"],
    "Flink": ["Checkpoint timeouts", "Backpressure on Kafka source", "TaskManager restarts"],
    "Airflow": ["Scheduler lag causing DAG delays", "Zombie tasks not cleaned up", "Metadata DB connection pool exhausted"],
    "Trino": ["Coordinator high memory", "Queries queued behind large scans", "Worker node unresponsive"],
    "Druid": ["Segment handoff delays", "Broker query timeouts", "Historical node disk full"],
    "Notebooks": ["Kernel fails to start", "Idle notebooks not culled", "Cluster attach timeout"],
}

def conn():
    return sqlite3.connect(DB, check_same_thread=False)

def seed():
    random.seed(7)
    c = conn()
    c.executescript("""
    DROP TABLE IF EXISTS incidents; DROP TABLE IF EXISTS metrics;
    CREATE TABLE incidents(id INTEGER PRIMARY KEY, service TEXT, severity TEXT, title TEXT,
                           status TEXT, created_at TEXT, resolved_at TEXT);
    CREATE TABLE metrics(ts TEXT, service TEXT, success_rate REAL, p95_latency_ms REAL, error_count INTEGER);
    """)
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    for s in SERVICES:
        base_lat = random.randint(200, 900)
        for h in range(14 * 24):
            ts = now - timedelta(hours=h)
            degraded = (s == "Airflow" and h < 6)   # Airflow is currently unhealthy (demo story)
            sr = random.uniform(0.80, 0.90) if degraded else random.uniform(0.975, 0.999)
            lat = base_lat * (random.uniform(2, 3) if degraded else random.uniform(0.8, 1.2))
            errs = random.randint(40, 120) if degraded else random.randint(0, 15)
            c.execute("INSERT INTO metrics VALUES (?,?,?,?,?)", (ts.isoformat(), s, round(sr, 4), round(lat), errs))
        for _ in range(random.randint(6, 12)):
            created = now - timedelta(hours=random.randint(8, 14 * 24))
            resolved = created + timedelta(minutes=random.randint(15, 360))
            c.execute("INSERT INTO incidents(service,severity,title,status,created_at,resolved_at) VALUES (?,?,?,?,?,?)",
                      (s, random.choice(["SEV1", "SEV2", "SEV2", "SEV3", "SEV3", "SEV3"]),
                       random.choice(TITLES[s]), "resolved", created.isoformat(), resolved.isoformat()))
    c.execute("INSERT INTO incidents(service,severity,title,status,created_at,resolved_at) VALUES (?,?,?,?,?,?)",
              ("Airflow", "SEV2", "Scheduler lag causing DAG delays", "open",
               (now - timedelta(hours=5)).isoformat(), None))
    c.commit()

if __name__ == "__main__":
    seed()
    print("seeded", DB)