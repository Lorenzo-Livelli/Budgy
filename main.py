import streamlit as st
import pandas as pd
import utils
import plotly.graph_objects as go
from sqlalchemy import text
from datetime import datetime


# Connect to the database
conn = st.connection("transactions_db")

st.sidebar.selectbox("Select time period", ["Last 7 days", "Last 30 days", "All time"], key="time_period") 

transaction_df = utils.load_transactions(conn, st.session_state.time_period)

st.title("Budgy")

# Formated dataframe to display
df_to_display = utils.format_database(transaction_df)


# Display dataframe
st.data_editor(
    df_to_display,
    hide_index=True,
    disabled=True,
    use_container_width=True,
    column_config={
        "Description": st.column_config.TextColumn(
            "Description",
            width="large"
        )
    }
)

# display the total balance
total_balance = st.session_state.transactions["Amount"].sum()
st.markdown(f"<h3 style='text-align: right; color: {'#54b86d' if total_balance >= 0 else '#bf2817'};'>Total Balance: {total_balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €</h3>", unsafe_allow_html=True)
# Generate line chart
general_fig = go.Figure()
general_fig.add_trace(go.Scatter(x=st.session_state.transactions["Date"], y=st.session_state.transactions["Amount"].cumsum(), mode='lines+markers', line_color='#54b86d' if total_balance >= 0 else '#bf2817'))

# add a horizontal line at y=0
general_fig.add_shape(type='line', x0=st.session_state.transactions["Date"].min(), x1=pd.Timestamp.now(), y0=0, y1=0, line=dict(color='white', width=1), opacity=0.5)

# Calculate cumulative amounts once to use in the loop
cumulative_amounts = st.session_state.transactions["Amount"].cumsum()

# Add a vertical line at each transaction date (from 0 to that day's cumulative amount)
for date, cum_amount in zip(st.session_state.transactions["Date"], cumulative_amounts):
    general_fig.add_shape(
        type='line', 
        x0=date, 
        x1=date, 
        y0=0, 
        y1=cum_amount, 
        line=dict(color='white', width=0.5, dash='dot'), 
        opacity=0.2
    )

# Add a vertical line at the current date (spanning the entire height of the graph)
general_fig.add_shape(
    type='line', 
    x0=pd.Timestamp.now(), 
    x1=pd.Timestamp.now(), 
    y0=0, 
    y1=1, 
    yref='paper',  # This tells Plotly to use the plot's relative height, where 0 is bottom and 1 is top
    line=dict(color='blue', width=1), 
    opacity=0.5
)

# Plot line chart
general_fig.update_layout(title=dict(text="Cumulative Balance Over Time", font=dict(size=22)), xaxis_title="Date", yaxis_title="Cumulative Balance", showlegend=False)
general_fig.update_xaxes(tickformat="%d/%m/%Y")
st.plotly_chart(general_fig, use_container_width=True)

# Pie chart of Expenses by Type (mind the negative values in the Amount column, we need to convert them to positive for the pie chart), using the same colors as in the table for consistency, and add a hole in the middle for better aesthetics.
expenses_by_type = st.session_state.transactions[st.session_state.transactions["Income/Expense"] == "Expense"].groupby("Type")["Amount"].sum().abs()
pie_fig = go.Figure(data=[go.Pie(labels=expenses_by_type.index, values= expenses_by_type.values, hole=0.4, marker_colors=[utils.type_colors(t).split(":")[-1][:-1] for t in expenses_by_type.index], textfont=dict(color='white'))])
pie_fig.update_layout(title=dict(text="Expenses by Type", font=dict(size=22)))
st.plotly_chart(pie_fig, use_container_width=True)

# Total expenses for each type, using the same colors as in the table.
for t in expenses_by_type.index:
    st.markdown(f"<p style='color: {utils.type_colors(t).split(':')[-1][:-1]}; font-size: 18px;'>{t}: {expenses_by_type[t]:,.2f} €</p>", unsafe_allow_html=True)


# add some space between the table and the form
st.markdown("<br><br>", unsafe_allow_html=True)

# Add new transaction
with st.sidebar.container(border=True):
    st.markdown('<p style="font-size:14px;"><strong>Add a new transaction:</strong></p>', unsafe_allow_html=True)
    amount = st.number_input("Amount", value=None, format="%.2f")
    Type = st.selectbox("Type", ["Salary", "Groceries", "Rent", "Entertainment","Travel","Mobility", "Other"])
    date = st.date_input("Date", format="DD/MM/YYYY")
    description = st.text_input("Description")


    if st.button("Add Transaction", width=200):

        if amount is None:
            st.warning("Please enter an amount.")
        else:
            ex_in = "Income" if amount >= 0 else "Expense"
                
            new_transaction = {
                "Amount": amount,
                "Type": Type,
                "Date": date,
                "Income/Expense": ex_in,
                "Description": description
            }

            with conn.session as s:
                s.execute(
                    text("""
                        INSERT INTO transactions (amount, Type, date, ex_in, description)
                        VALUES (:amount, :type, :date, :ex_in, :description)
                    """),
                    {
                        "amount": amount,
                        "type": Type,
                        "date": date.strftime("%Y-%m-%d"),
                        "ex_in": ex_in,
                        "description": description,
                    },
                )
                s.commit()
        
        st.session_state.pop("transactions")  # Clear cached transactions to force reload
        st.success("Transaction added!")
        st.rerun()

# Remove a transaction
with st.sidebar.container(border=True):

    st.markdown('<p style="font-size:14px;"><strong>Remove a transaction:</strong></p>', unsafe_allow_html=True)

    transaction_to_remove = st.selectbox("Transactions", st.session_state.transactions["Type"] + " | " + st.session_state.transactions["Date"].apply(lambda x: datetime.strptime(x, "%Y-%m-%d").strftime("%d/%m/%Y")) + " | " + st.session_state.transactions["Amount"].apply(lambda x: f"({x:,.2f}) ")+ st.session_state.transactions["Description"].apply(lambda x: f" - {x}" if x is not "" else "") + st.session_state.transactions["id"].apply(lambda x: f" (id: {x})"), key="transaction_to_remove")

    if st.button("Remove Transaction"):
        if transaction_to_remove is not None:
            transaction_id = int(transaction_to_remove.split(" (id: ")[-1][:-1])  # Extract the ID from the selected string
            with conn.session as s:
                s.execute(text("DELETE FROM transactions WHERE id = :id"), {"id": transaction_id})
                s.commit()
            
            st.session_state.pop("transactions")
            st.success("Transaction removed!")
            st.rerun()


