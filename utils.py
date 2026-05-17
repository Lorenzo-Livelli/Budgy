import utils
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

def type_colors(type):
    if type == "Salary":
        return 'color: #20FC8F;'  
    if type == "Groceries":
        return 'color: #FF6B6C;'  
    if type == "Rent":
        return 'color: #FFC145;'  
    if type == "Entertainment":
        return 'color: #5B5F97;'  
    if type == "Other":
        return 'color: #B8B8D1;'
    if type == "Travel":
        return 'color: #FF6F91;'
    if type == "Mobility":
        return 'color: #6A0572;'
    return 'color: #000000;'  # Default color

def format_database(df):

    # Drop the id column as it's not needed for display
    df = df.drop(columns=["id"])

    # Convert numbers to fixed strings with commas for decimals and dots for thousands
    df["Amount"] = df["Amount"].apply(
        lambda x: f"{float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d/%m/%Y')

    # extract the amount column and apply the color formatting
    styled_df = (
    df.style
    .map(
        lambda x: 'color: #bf2817;'
        if isinstance(x, str) and x.startswith('-')
        else 'color: #54b86d;',
        subset=['Amount']
    )
    .map(
        lambda x: 'color: #bf2817;'
        if x == 'Expense'
        else 'color: #54b86d;',
        subset=['Income/Expense']
    )
    .map(
        utils.type_colors,
        subset=['Type']
    )
    )

    return styled_df
    

# Extract selected time periods transactions from the database
def load_transactions(conn, time_period):
    if st.session_state.time_period == "Last 30 days":
        with conn.session as s:
            rows = s.execute("SELECT id, amount, Type, date, ex_in, description FROM transactions WHERE date >= date('now', '-30 days')").fetchall()
            st.session_state.transactions = pd.DataFrame(
                rows, columns=["id", "Amount", "Type", "Date", "Income/Expense", "Description"]
            )
    elif st.session_state.time_period == "Last 7 days":
        with conn.session as s:
            rows = s.execute("SELECT id, amount, Type, date, ex_in, description FROM transactions WHERE date >= date('now', '-7 days')").fetchall()
            st.session_state.transactions = pd.DataFrame(
                rows, columns=["id", "Amount", "Type", "Date", "Income/Expense", "Description"]
            )
    else:
        with conn.session as s:
            rows = s.execute("SELECT id, amount, Type, date, ex_in, description FROM transactions").fetchall()
            st.session_state.transactions = pd.DataFrame(
                rows, columns=["id", "Amount", "Type", "Date", "Income/Expense", "Description"]
            )
    
    return st.session_state.transactions.copy()