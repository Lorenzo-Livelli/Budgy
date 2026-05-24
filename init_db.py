import sqlite3

# Initialize SQLite database
conn = sqlite3.connect("Budgy.db")

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

# Create type_colors table if it doesn't exist
c.execute("""
    CREATE TABLE IF NOT EXISTS type_colors (
        Type TEXT PRIMARY KEY,
        color TEXT NOT NULL
    )
""")

# add default colors for the types
default_colors = {
    "Salary": "#20FC8F",
    "Groceries": "#FF6B6C",
    "Rent": "#FFC145",
    "Entertainment": "#5B5F97",
    "Travel": "#FF6F91",
    "Mobility": "#6A0572"
    # ,"Other": "#B8B8D1"
}
for t, color in default_colors.items(): 
    c.execute("INSERT OR IGNORE INTO type_colors (Type, color) VALUES (:type, :color)", {"type": t, "color": color})
    conn.commit()

# create budgets table if it doesn't exist
c.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        Type TEXT PRIMARY KEY,
        amount REAL NOT NULL
    )
""")
    