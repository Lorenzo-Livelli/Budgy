import bcrypt
from sqlalchemy import text

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

def create_user(conn, username, password):
    password_hash = hash_password(password)

    with conn.session as s:
        s.execute(
            text("""
                INSERT INTO users (username, password_hash)
                VALUES (:username, :password_hash)
            """),
            {
                "username": username.strip(),
                "password_hash": password_hash,
            },
        )
        s.commit()

def authenticate_user(conn, username, password):
    with conn.session as s:
        row = s.execute(
            text("""
                SELECT id, username, password_hash
                FROM users
                WHERE lower(username) = lower(:username)
            """),
            {"username": username.strip()},
        ).fetchone()

    if row is None:
        return None

    if not verify_password(password, row.password_hash):
        return None

    return {
        "id": row.id,
        "username": row.username,
    }

def generate_user_type_db(conn, user_id):

    default_colors = {
    "Salary": "#20FC8F",
    "Groceries": "#FF6B6C",
    "Rent": "#FFC145",
    "Entertainment": "#5B5F97",
    "Travel": "#FF6F91",
    "Mobility": "#6A0572"
    }

    default_characteristics = {
        "Salary": "Income",
        "Groceries": "Expense",
        "Rent": "Expense",
        "Entertainment": "Expense",
        "Travel": "Expense",
        "Mobility": "Expense"
    }

    with conn.session as s:

        s.execute(
            text(""" INSERT INTO type_characteristics (type, color, user_id, direction)
                    VALUES (:type, :color, :user_id, :direction)
                """),
            [
                {"type": type_, "color": color, "user_id": user_id, "direction": default_characteristics[type_]}
                for type_, color in zip(default_colors.keys(), default_colors.values())
            ]
        )
        s.commit()

def generate_user_budget_db(conn, user_id):
    with conn.session as s:
        s.execute(
            text(""" INSERT INTO budgets (type, amount, user_id)
                    VALUES (:type, :amount, :user_id)
                """),
            [
                {"type": type_, "amount": 0.00, "user_id": user_id}
                for type_ in ["Groceries", "Rent", "Entertainment", "Travel", "Mobility"]
            ]
        )
        s.commit()