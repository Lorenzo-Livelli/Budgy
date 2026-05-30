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
with st.sidebar:

    st.markdown("<p style='font-size:38px;'><strong>Menu:</strong></p>", unsafe_allow_html=True)

    new_utils.style_buttons("time_period", "#757575", "white")

    new_utils.style_streamlit_widget("time_period", part="label", font_size="18px", font_weight="bold")


    ordered_user_transactions = el.time_period_and_order(user_transactions)

    st.markdown('<hr>', unsafe_allow_html=True)

    el.add_transaction(conn, user_type_characteristics)

    # st.markdown('<hr>', unsafe_allow_html=True)
    # st.markdown('<p style="font-size:18px;"><strong>Remove a transaction:</strong></p>', unsafe_allow_html=True)

    # el.remove_transaction(conn, user_transactions)

    st.markdown('<hr>', unsafe_allow_html=True)

    st.markdown('<p style="font-size:18px;"><strong>Set monthly budget:</strong></p>', unsafe_allow_html=True)

    el.set_monthly_budget(conn, user_budget)

    st.markdown('<hr>', unsafe_allow_html=True)

    # Settings
    with st.container(border=False):
        if st.button("Settings",width="stretch", key="settings_button", icon="⚙️"):
            st.switch_page("pages/settings.py")

#####################################################################################################################################################################################

el.summary_table(ordered_user_transactions, user_type_characteristics, conn)

period_balance = ordered_user_transactions["amount"].sum()
if st.session_state.time_period != "All time":
    st.markdown(f"<p style='text-align: right;  color: {'#54b86d' if period_balance >= 0 else '#bf2817'}; font-size: 18px;'>Period: {period_balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " </p>", unsafe_allow_html=True)

# Display the total balance
total_balance = user_transactions["amount"].sum()
st.markdown(f"<p style='text-align: right; color: {'#54b86d' if total_balance >= 0 else '#bf2817'}; font-size: 24px;'>All time: {total_balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " </p>", unsafe_allow_html=True)

new_utils.style_buttons("widget_choice", "#757575", "white")

with st.container(border=False, horizontal_alignment="center"):
    st.session_state.view_mode = st.segmented_control(
        "",
        options=["Balance over time graph", "Pie chart of expenses", "Budget vs actuals"],
        default="Balance over time graph",
        key="widget_choice"
    )

if st.session_state.view_mode == "Balance over time graph":
    el.chart(ordered_user_transactions)
elif st.session_state.view_mode == "Pie chart of expenses":
    el.pie_chart(ordered_user_transactions, user_type_characteristics)
elif st.session_state.view_mode == "Budget vs actuals":
    el.budget_vs_actuals(user_transactions, user_budget, user_type_characteristics)

# st.markdown('<br>', unsafe_allow_html=True)
# st.markdown("<h3 style='text-align: Left;'>Budget </h2>", unsafe_allow_html=True)
