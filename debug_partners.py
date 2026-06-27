import sqlite3

DB_PATH = "instance/gmespay.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("📂 DB:", DB_PATH)

cursor.execute("SELECT id, name, code, contact_email, is_active FROM partners")
rows = cursor.fetchall()

print("\n🏢 PARTNERS:")
for r in rows:
    print(r)

conn.close()