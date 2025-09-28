import os, json, sqlite3, asyncio
from datetime import datetime

DB_PATH = os.environ.get("FLOW_STATUS_DB","infra/db/flow_status.db")
os.makedirs(os.path.dirname(DB_PATH),exist_ok=True)


def _connect():
    conn = sqlite3.connect(DB_PATH,timeout=30)
    conn.execute(
        """     
        CREATE TABLE IF NOT EXISTS flow_status(
            check_in_id TEXT PRIMARY KEY,
            status TEXT,
            data_json TEXT,
            updated_at TEXT
        )
        """)
    return conn

async def _run(fn,*args,**kwargs):
    return await asyncio.to_thread(fn,*args, **kwargs)
