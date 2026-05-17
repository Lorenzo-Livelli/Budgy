import sqlite3

# Initialize SQLite database
conn = sqlite3.connect("transactions.db")

c = conn.cursor()


# Create transactions table if it doesn't exist
c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        Type TEXT NOT NULL,
        date DATE NOT NULL,
        ex_in TEXT NOT NULL,
        description TEXT
    )
""")