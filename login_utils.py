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