import utils
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
import random

# Extract selected time periods transactions from the database
def load_transactions(conn, user_id):
    with conn.session as s:
        transactions = s.execute(text('''SELECT id, amount, Type, date, ex_in, description FROM transactions WHERE user_id = :user_id'''), {"user_id": user_id}).fetchall()
        budget = s.execute(text('''SELECT type, amount FROM budgets WHERE user_id = :user_id'''), {"user_id": user_id}).fetchall()
        type_characteristics = s.execute(text('''SELECT type, color, direction FROM type_characteristics WHERE user_id = :user_id'''), {"user_id": user_id}).fetchall()

    user_transactions = pd.DataFrame(transactions, columns=["id", "amount", "type", "date", "ex_in", "description"])
    user_budget = pd.DataFrame(budget, columns=["type", "amount"])
    user_type_characteristics = pd.DataFrame(type_characteristics, columns=["type", "color", "direction"])

    user_transactions["date"] = pd.to_datetime(user_transactions["date"])

    return user_transactions, user_budget, user_type_characteristics

def insert_transaction(s, amount, category, date, description):
    s.execute(
        text('''INSERT INTO transactions (amount, type, date, ex_in, description, user_id) VALUES (:amount, :type, :date, :ex_in, :description, :user_id)'''),
        {
            "amount": amount,
            "type": category,
            "date": date,
            "ex_in": "Expense" if amount < 0 else "Income",
            "description": description,
            "user_id": st.session_state.user_id
        }
    )
    s.commit()

@st.dialog("Choose whether the type is an income or an expense")
def transaction_type_categorization(category):

    st.write(f"Is {category} an income or an expense?")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Income", key="income_button"):
            st.session_state.pending_type_direction = "Income"
            st.rerun()

    with col2:
        if st.button("Expense", key="expense_button"):
            st.session_state.pending_type_direction = "Expense"
            st.rerun()

