# init_db.py
import sqlite3

# Read the SQL schema
with open('schema.sql', 'r', encoding='utf-8') as f:
    schema = f.read()

# Connect (or create) chat.db
conn = sqlite3.connect('chat.db')
# Execute all schema statements at once
conn.executescript(schema)
conn.close()

print("✅ chat.db initialized with your schema.")
