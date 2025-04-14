from database.db import engine
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text("DELETE FROM patients"))
    conn.execute(text("DELETE FROM csv_uploads"))
    conn.execute(text("DELETE FROM models"))
    conn.execute(text("DELETE FROM diseases"))

print("✅ All data truncated.")
