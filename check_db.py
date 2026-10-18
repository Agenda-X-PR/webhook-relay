"""Quick script to verify the database schema."""

import sqlite3

conn = sqlite3.connect("webhooks.db")

tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()
print("Tables:", tables)

columns = conn.execute("PRAGMA table_info(events)").fetchall()
print("\nEvents table columns:")
for col in columns:
    # col = (cid, name, type, notnull, default, pk)
    print(f"  {col[1]:20s} {col[2]}")

conn.close()