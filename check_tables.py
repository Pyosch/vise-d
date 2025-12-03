import sqlite3
import os

db_path = r'C:\Users\mashu\.open-MaStR\data\sqlite\open-mastr.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")
    
conn.close()
