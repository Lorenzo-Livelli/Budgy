import streamlit as st
import pandas as pd
import utils
import plotly.graph_objects as go
from sqlalchemy import text
from datetime import datetime


conn = st.connection("supabase", type="sql")

if "user_id" not in st.session_state:
    st.switch_page("login.py")

st.sidebar.markdown("<p style='font-size:38px;'><strong>Menu:</strong></p>", unsafe_allow_html=True)

st.sidebar.selectbox("Select time period", ["All time", "Last 30 days", "Last 7 days", "Custom"], key="time_period") 

transaction_df = utils.load_transactions(conn, st.session_state.time_period)

st.title("Budgy", text_alignment="center")

st.sidebar.markdown('<hr>', unsafe_allow_html=True)
st.sidebar.markdown('<p style="font-size:18px;"><strong>Order transactions:</strong></p>', unsafe_allow_html=True)
with st.sidebar.container(border=False):
    with st.expander("Order by", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("", ["Date", "Amount"], key="order_by", label_visibility="collapsed")
        with col2:
            st.selectbox("", ["⬆️", "⬇️" ], key="order_direction", label_visibility="collapsed")

        # order transactions by date or amount, in ascending or descending order, and update the dataframe accordingly
        if st.session_state.order_by == "Date":
            transaction_df = transaction_df.sort_values(by="Date", ascending=st.session_state.order_direction == "⬇️")
        elif st.session_state.order_by == "Amount":
            transaction_df = transaction_df.sort_values(by="Amount", ascending=st.session_state.order_direction == "⬇️")

        st.selectbox("Exclude incomes", ["No", "Yes"], key="exclude_incomes")
        if st.session_state.exclude_incomes == "Yes":
            transaction_df = transaction_df[transaction_df["Income/Expense"] == "Expense"]
    


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



# Display the period balance
period_balance = st.session_state.transactions["Amount"].sum()
if st.session_state.time_period != "All time":
    st.markdown(f"<p style='text-align: right;  color: {'#54b86d' if period_balance >= 0 else '#bf2817'}; font-size: 18px;'>Period: {period_balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " </p>", unsafe_allow_html=True)


# Display the total balance
total_balance = conn.session.execute("SELECT SUM(amount) FROM transactions").fetchone()[0] or 0
st.markdown(f"<p style='text-align: right; color: {'#54b86d' if total_balance >= 0 else '#bf2817'}; font-size: 24px;'>All time: {total_balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " </p>", unsafe_allow_html=True)


# Generate line chart
general_fig = go.Figure()
sorted_transactions = st.session_state.transactions.sort_values(by="Date")
general_fig.add_trace(go.Scatter(x=sorted_transactions["Date"], y=sorted_transactions["Amount"].cumsum(), mode='lines+markers', line_color='#54b86d' if period_balance >= 0 else '#bf2817'))

# add a horizontal line at y=0 that spans the entire width of the graph
general_fig.add_shape(
    type='line',
    xref='paper',   # use plot width instead of data coordinates
    x0=0,
    x1=1,
    yref='y',
    y0=0,
    y1=0,
    line=dict(color='white', width=1),
    opacity=0.5
)

# Calculate cumulative amounts once to use in the loop
cumulative_amounts = sorted_transactions["Amount"].cumsum()

# Add a vertical line at each transaction date (from 0 to that day's cumulative amount)
for date, cum_amount in zip(sorted_transactions["Date"], cumulative_amounts):
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

# Add new transaction
st.sidebar.markdown('<hr>', unsafe_allow_html=True)
st.sidebar.markdown('<p style="font-size:18px;"><strong>Add a new transaction:</strong></p>', unsafe_allow_html=True)

# Get the types from the database to populate the selectbox
with conn.session as s:
    result = s.execute(text("SELECT DISTINCT Type FROM transactions"))
    types_in_db = [row[0] for row in result]
    # Add the default types if they are not already in the database
    default_types = ["Salary", "Groceries", "Rent", "Entertainment","Travel","Mobility", "Other"]
    for t in default_types:
        if t not in types_in_db:
            types_in_db.append(t)

# Order types_in_db alphabetically, but keep "Other" at the end of the list
types_in_db = sorted([t for t in types_in_db if t != "Other"]) + [t for t in types_in_db if t == "Other"]

with st.sidebar.container(border=False):
    with st.expander("Transaction details", expanded=False):
        amount = st.number_input("Amount", value=None, format="%.2f")
        Type = st.selectbox("Type", types_in_db)
        if Type == "Other":
            Type = st.text_input("Specify the new type")
            # capitalize the first letter of the type and make the rest lowercase
            Type = Type.capitalize()


        date_placeholder = st.empty()

        description = st.text_input("Description")

        recurring_bool = st.checkbox("Recurring transaction")

        if not recurring_bool:
            with date_placeholder:
                date = st.date_input("Date", format="DD/MM/YYYY")

        if recurring_bool:
            recurring_frequency = st.selectbox(
                "Frequency",
                ["Daily", "Weekly", "Monthly", "Yearly"]
            )

            starting_date = st.date_input(
                "Starting date for recurring transaction",
                format="DD/MM/YYYY"
            )

            recurring_end_date = st.date_input(
                "End date for recurring transaction",
                format="DD/MM/YYYY"
            )

            
        

        if st.button("Add Transaction", width=200):

            if amount is None:
                st.warning("Please enter an amount.")
            else:
                ex_in = "Income" if amount >= 0 else "Expense"
            
                if amount >=0 and Type not in ["Salary"]:
                    st.warning("For an income transaction, the type must be 'Salary'. Please change the type or the amount.")
                    st.stop()
                if amount < 0 and Type in ["Salary"]:
                    st.warning("For an expense transaction, the type cannot be 'Salary'. Please change the type or the amount.")
                    st.stop()
                
                for date in ([date] if not recurring_bool else pd.date_range(starting_date, recurring_end_date, freq={"Daily": "D", "Weekly": "W", "Monthly": "M", "Yearly": "Y"}[recurring_frequency])):
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
st.sidebar.markdown('<hr>', unsafe_allow_html=True)
st.sidebar.markdown('<p style="font-size:18px;"><strong>Remove a transaction:</strong></p>', unsafe_allow_html=True)

with st.sidebar.container(border=True):

    transactions = st.session_state.transactions.copy()

    transactions["Date"] = pd.to_datetime(transactions["Date"]).dt.strftime("%d/%m/%Y")
    transactions["Description"] = transactions["Description"].fillna("")

    transactions["label"] = (
        transactions["Type"].astype(str)
        + " | "
        + transactions["Date"]
        + " | "
        + transactions["Amount"].apply(lambda x: f"({x:,.2f}) ")
        + transactions["Description"].apply(lambda x: f" - {x}" if x != "" else "")
        + transactions["id"].apply(lambda x: f" (id: {x})")
    )

    transaction_to_remove = st.selectbox(
        "Transactions",
        transactions["label"],
        key="transaction_to_remove"
    )

    if st.button("Remove Transaction"):
        if transaction_to_remove is not None:
            transaction_id = int(transaction_to_remove.split(" (id: ")[-1][:-1])  # Extract the ID from the selected string
            with conn.session as s:
                s.execute(text("DELETE FROM transactions WHERE id = :id"), {"id": transaction_id})
                s.commit()
            
            st.session_state.pop("transactions")
            st.success("Transaction removed!")
            st.rerun()

st.sidebar.markdown('<hr>', unsafe_allow_html=True)


# Set budget for each type
st.sidebar.markdown('<p style="font-size:18px;"><strong>Set monthly budget:</strong></p>', unsafe_allow_html=True)
with st.sidebar.expander("Budget by Type", expanded=False):
    for t in types_in_db:
        if t != "Salary" and t != "Other":  
            row = s.execute(
                text("SELECT amount FROM budgets WHERE type = :type"),
                {"type": t}
            ).fetchone()

            budget_value = float(row[0]) if row is not None else 0.0

            budget = st.number_input(
                f"{t}",
                value=budget_value,
                step=0.01,
                format="%.2f",
                key=f"budget_{t}"
            )
            # Check if the budget for the type is already in the database, if it is update it, if it is not insert it
            with conn.session as s:
                existing_budget = s.execute(text("SELECT amount FROM budgets WHERE Type = :type"), {"type": t}).fetchone()
                if existing_budget:
                    s.execute(text("UPDATE budgets SET amount = :amount WHERE Type = :type"), {"amount": budget, "type": t})
                else:
                    s.execute(text("INSERT INTO budgets (Type, amount) VALUES (:type, :amount)"), {"type": t, "amount": budget})
                s.commit()

st.markdown('<br>', unsafe_allow_html=True)
st.markdown("<h3 style='text-align: Left;'>Budget </h2>", unsafe_allow_html=True)
with st.container(border=True):
    
    # Select a month and a year
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            selected_month = st.selectbox("Select month", ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], key="selected_month")
        with col2:
            current_year = datetime.now().year
            selected_year = st.selectbox("Select year", options=[str(y) for y in range(current_year - 10, current_year + 1)], index=10,key="selected_year")

    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }


    # Generate a dataframe that sums up, for each type, the total expenses for the selected month and year, and display it in a table with the same color formatting as before.
    type_expenses_df = st.session_state.transactions[
        (pd.to_datetime(st.session_state.transactions["Date"]).dt.month == month_map[selected_month]) &
        (pd.to_datetime(st.session_state.transactions["Date"]).dt.year == int(selected_year))
    ].groupby("Type")["Amount"].sum().to_frame()

    for t in types_in_db:
        if t not in type_expenses_df.index:
            type_expenses_df.loc[t] = 0.0

    # # check if there are transactions for the selected month and year, if not display a message instead of the table
    # if type_expenses_df.empty:
    #     st.warning("No transactions for the selected month and year.")
    # else:

    # Rename amount to "Total Expenses"
    type_expenses_df = type_expenses_df.rename(columns={"Amount": "Total Expenses"})

    # Convert total expenses into float with two decimals
    type_expenses_df["Total Expenses"] = type_expenses_df["Total Expenses"].apply(lambda x: float(f"{x:.2f}"))

    # Add a colum "budget" and a column "remaining budget" to the dataframe
    type_expenses_df["Budget"] = type_expenses_df.index.map(lambda t: st.session_state.get(f"budget_{t}", 0.0))

    # Add a column "Budget" based on the budget table in the database
    with st.connection("supabase", type="sql").session as s:
        budgets = s.execute(text("SELECT Type, amount FROM budgets")).fetchall()
        budget_dict = {row[0]: row[1] for row in budgets}
    type_expenses_df["Budget"] = type_expenses_df.index.map(lambda t: budget_dict.get(t, 0.0))


        # set the budget column to the value of the corresponding budget for each type as a float
    type_expenses_df["Budget"] = (
        pd.to_numeric(type_expenses_df["Budget"], errors="coerce")
        .fillna(0.0)
        .astype(float)
    )

    type_expenses_df["Total Expenses"] = (
        pd.to_numeric(type_expenses_df["Total Expenses"], errors="coerce")
        .fillna(0.0)
        .astype(float)
    )

    type_expenses_df["Remaining Budget"] = (
        type_expenses_df["Budget"] + type_expenses_df["Total Expenses"]
    )
    type_expenses_df["Remaining Budget"] = type_expenses_df["Budget"] + type_expenses_df["Total Expenses"]

    # Remove the salary type from the dataframe
    if "Salary" in type_expenses_df.index:
        type_expenses_df = type_expenses_df.drop("Salary")

    # Remove the "Other" type from the dataframe
        type_expenses_df = type_expenses_df.drop("Other")

    # Add a row "Total" at the end of the dataframe that sums up the total expenses, the total budget and the total remaining budget for all types
    type_expenses_df.loc["Total"] = type_expenses_df.sum()

    # Format type as a column
    type_expenses_df = type_expenses_df.reset_index()

    def color_budget_values(val): 
        if val < 0:
            return 'color: red;'
        elif val > 0:
            return 'color: green;'
        return ''  # Leaves 0 or neutral values unchanged

    # Apply formatting and conditional mapping
    type_expenses_styled_df = type_expenses_df.style.format({
        "Total Expenses": utils.currency_formatter, 
        "Budget": utils.currency_formatter, 
        "Remaining Budget": utils.currency_formatter
    }).map(
        color_budget_values, 
        subset=["Total Expenses", "Remaining Budget", "Budget"]
    ).map(
        utils.type_colors,subset=["Type"])

    st.markdown("<br>", unsafe_allow_html=True)

    st.data_editor(
        type_expenses_styled_df,
        hide_index=True,
        disabled=True,
        use_container_width=True,
    )




