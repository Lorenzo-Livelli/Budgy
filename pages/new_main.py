import streamlit as st
import pandas as pd
import new_utils
import plotly.graph_objects as go
from sqlalchemy import text
from datetime import datetime
import elements as el

conn = st.connection("supabase", type="sql")

if "user_id" not in st.session_state:
    st.switch_page("login.py")

user_transactions, user_budget, user_type_characteristics = new_utils.load_transactions(conn, st.session_state.user_id)

st.title("Budgy", text_alignment="center")

####################################################################################################################################################################################
# Sidebar

st.sidebar.markdown("<p style='font-size:38px;'><strong>Menu:</strong></p>", unsafe_allow_html=True)

ordered_user_transactions = el.time_period_and_order(user_transactions)

st.sidebar.markdown('<hr>', unsafe_allow_html=True)

el.add_transaction(conn, user_type_characteristics)

st.sidebar.markdown('<hr>', unsafe_allow_html=True)
st.sidebar.markdown('<p style="font-size:18px;"><strong>Remove a transaction:</strong></p>', unsafe_allow_html=True)

el.remove_transaction(conn, user_transactions)

st.sidebar.markdown('<hr>', unsafe_allow_html=True)

st.sidebar.markdown('<p style="font-size:18px;"><strong>Set monthly budget:</strong></p>', unsafe_allow_html=True)

el.set_monthly_budget(conn, user_budget)

#####################################################################################################################################################################################

el.summary_table(ordered_user_transactions, user_type_characteristics)

period_balance = ordered_user_transactions["amount"].sum()
if st.session_state.time_period != "All time":
    st.markdown(f"<p style='text-align: right;  color: {'#54b86d' if period_balance >= 0 else '#bf2817'}; font-size: 18px;'>Period: {period_balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " </p>", unsafe_allow_html=True)

# Display the total balance
total_balance = conn.session.execute("SELECT SUM(amount) FROM transactions").fetchone()[0] or 0
st.markdown(f"<p style='text-align: right; color: {'#54b86d' if total_balance >= 0 else '#bf2817'}; font-size: 24px;'>All time: {total_balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " </p>", unsafe_allow_html=True)

el.chart(ordered_user_transactions)

el.pie_chart(ordered_user_transactions, user_type_characteristics)

# st.markdown('<br>', unsafe_allow_html=True)
# st.markdown("<h3 style='text-align: Left;'>Budget </h2>", unsafe_allow_html=True)