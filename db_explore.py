import pandas as pd
import sqlite3
import atexit

# Connect to the SQL database
# conn = sqlite3.connect('data/240603_database sample.db', check_same_thread=False)
# database_table = 'merge'

conn = sqlite3.connect('data/240912_inputs_online_tool.db', check_same_thread=False)
database_table = 'inputs_online_tool'

# Register a function to close the connection when the app shuts down
def close_db():
    conn.close()

atexit.register(close_db)

# Fetch data from the database
L_LIMIT = 0
U_LIMIT = 1_000
query = f"SELECT * FROM {database_table} LIMIT {L_LIMIT}, {U_LIMIT}"
# query = f"SELECT * FROM inputs_online_tool LIMIT {L_LIMIT}, {U_LIMIT}"
df = pd.read_sql_query(query, conn)