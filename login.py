import streamlit as st
import login_utils
from sqlalchemy import text

conn = st.connection("supabase", type="sql")

if "user_id" in st.session_state:
    st.switch_page("pages/new_main.py")

st.title("Budgy Login")

tab_login, tab_register = st.tabs(["Login", "Register"])

with tab_login:
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login"):
        user = login_utils.authenticate_user(conn, username, password)

        if user is None:
            st.error("Invalid username or password.")
        else:
            st.session_state.user_id = user["id"]
            st.session_state.username = user["username"]
            st.switch_page("pages/new_main.py")

with tab_register:
    new_username = st.text_input("Username", key="register_username")
    new_password = st.text_input("Password", type="password", key="register_password")


    if st.button("Create account"):
        login_utils.create_user(conn, new_username, new_password)
        # Extract the user_id from the database
        user_id = conn.session.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {"username": new_username.strip()},
        ).fetchone()[0]

        login_utils.generate_user_type_db(conn, user_id)
        login_utils.generate_user_budget_db(conn, user_id)
        st.success("Account created. You can log in now.")
        

