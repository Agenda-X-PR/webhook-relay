"""Quick script to view stored webhook events."""

import sqlite3

conn = sqlite3.connect("webhooks.db")
rows = conn.execute(
    "SELECT id, provider, event_id, event_type, status, attempts FROM events ORDER BY id"
).fetchall()

if not rows:
    print("No events stored yet.")
else:
    print(f"{len(rows)} event(s):")
    for r in rows:
        print(
            f"  id={r[0]} provider={r[1]} event_id={r[2]} "
            f"type={r[3]} status={r[4]} attempts={r[5]}"
        )

conn.close()