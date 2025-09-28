# apps/stream/read_models/flow_status_repo.py
import os, json, sqlite3, asyncio
from datetime import datetime
from typing import Optional, Dict, Any

DB_PATH = os.environ.get("FLOW_STATUS_DB", "infra/db/flow_status.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flow_status (
            check_in_id TEXT PRIMARY KEY,
            status TEXT,
            data_json TEXT,
            updated_at TEXT
        )
    """)
    return conn

async def _run(fn, *args, **kwargs):
    return await asyncio.to_thread(fn, *args, **kwargs)

def _upsert_row(check_in_id: str, status: str, data: Dict[str, Any]):
    conn = _connect()
    try:
        payload = json.dumps(data, ensure_ascii=False)
        now = datetime.utcnow().isoformat() + "Z"
        conn.execute("""
            INSERT INTO flow_status (check_in_id, status, data_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(check_in_id) DO UPDATE SET
                status=excluded.status,
                data_json=excluded.data_json,
                updated_at=excluded.updated_at
        """, (check_in_id, status, payload, now))
        conn.commit()
    finally:
        conn.close()

def _get_row(check_in_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.execute("SELECT status, data_json, updated_at FROM flow_status WHERE check_in_id = ?", (check_in_id,))
        row = cur.fetchone()
        if not row:
            return None
        status, data_json, updated_at = row
        data = json.loads(data_json) if data_json else {}
        data.update({"status": status, "updatedAt": updated_at})
        return data
    finally:
        conn.close()

# ---------- API pública assíncrona ----------

async def set_status(check_in_id: str, status: str, extra: Optional[Dict[str, Any]] = None):
    data = await _run(_get_row, check_in_id) or {}
    data.update(extra or {})
    await _run(_upsert_row, check_in_id, status, data)

async def save_spot_list(check_in_id: str, spots: list):
    current = await _run(_get_row, check_in_id) or {}
    current["spots"] = spots
    await _run(_upsert_row, check_in_id, "spots_consulted", current)

async def set_reserved_spot(check_in_id: str, spot: Dict[str, Any]):
    current = await _run(_get_row, check_in_id) or {}
    current["spot"] = spot
    await _run(_upsert_row, check_in_id, "spot_reserved", current)

async def get_status(check_in_id: str) -> Optional[Dict[str, Any]]:
    return await _run(_get_row, check_in_id)
