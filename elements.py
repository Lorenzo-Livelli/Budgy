import streamlit as st
import pandas as pd
import new_utils
import plotly.graph_objects as go
from sqlalchemy import text
from datetime import datetime
import random as random

# SIDEBAR FUNCTIONS

def time_period_and_order(user_transactions):

    st.segmented_control("Select time period:", ["All time", "Last 30 days", "Last 7 days", "Custom"],width="content",default="All time", key="time_period") 
    transaction_dates = pd.to_datetime(user_transactions["date"])

    if st.session_state.time_period == "All time":
        user_transactions = user_transactions[transaction_dates <= pd.Timestamp.today().normalize()]
    elif st.session_state.time_period == "Last 30 days":
        user_transactions = user_transactions[transaction_dates >= pd.Timestamp.today().normalize() - pd.DateOffset(days=30)]
    elif st.session_state.time_period == "Last 7 days":
        user_transactions = user_transactions[transaction_dates >= pd.Timestamp.today().normalize() - pd.DateOffset(days=7)]
    elif st.session_state.time_period == "Custom":
        with st.container(border=True):
            start_date, end_date = st.slider("Select custom date range:", min_value=transaction_dates.min().date(), max_value=transaction_dates.max().date(), value=(transaction_dates.min().date(), transaction_dates.max().date()),format="DD/MM/YY", key="custom_date_range")

        if start_date > end_date:
            st.warning("Start date must be before end date.")
        else:
            user_transactions = user_transactions[
                (transaction_dates >= pd.to_datetime(start_date))
                & (transaction_dates <= pd.to_datetime(end_date))
            ]
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p style="font-size:18px;"><strong>Order transactions:</strong></p>', unsafe_allow_html=True)
    with st.container(border=False):
        with st.expander("Order by", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.selectbox("", ["Date", "Amount"], key="order_by", label_visibility="collapsed")
            with col2:
                st.selectbox("", ["⬆️", "⬇️" ], key="order_direction", label_visibility="collapsed")
            
            if st.session_state.order_by == "Date":
                user_transactions = user_transactions.sort_values(by="date", ascending=st.session_state.order_direction == "⬇️")
            elif st.session_state.order_by == "Amount":
                user_transactions = user_transactions.sort_values(by="amount", ascending=st.session_state.order_direction == "⬇️")
    
            st.checkbox("Exclude incomes", key="exclude_incomes")
            if st.session_state.exclude_incomes:
                user_transactions = user_transactions[user_transactions["ex_in"] == "Expense"]
    return user_transactions
    

def add_transaction(conn, user_type_characteristics):

    MAX_OCCURRENCES = 100

    st.markdown('<p style="font-size:18px;"><strong>Add a new transaction:</strong></p>', unsafe_allow_html=True)

    # extract types from user_type_characteristics
    type_options = user_type_characteristics["type"].unique().tolist()
    if "Salary" in type_options:
        type_options.remove("Salary")
    type_options = sorted(type_options)
    type_options.insert(0, "Salary")
    type_options.append("Other")

    with st.container(border=False):
        with st.expander("Add transaction", expanded=False):
            amount = st.number_input("Amount", value=0.0, step=0.01, key="new_transaction_amount")
            category = st.selectbox("Type", type_options, key="new_category")
            

            if category == "Other":
                # print type_options
                category = st.text_input("Specify the new type", key="new_category_input")
                # capitalize the first letter of the type and make the rest lowercase
                category = category.capitalize()
            
            
            date_placeholder = st.empty()

            description = st.text_input("Description", key="description")

            recurring_bool = st.checkbox("Recurring transaction")

            if not recurring_bool:
                with date_placeholder:
                    date = st.date_input("Date", format="DD/MM/YYYY", key="date")

            if recurring_bool:
                recurring_frequency = st.selectbox(
                    "Frequency",
                    ["Daily", "Weekly", "Monthly", "Yearly"],
                    key="recurring_frequency"
                )

                recurring_starting_date = st.date_input(
                    "Starting date for recurring transaction",
                    format="DD/MM/YYYY",
                    key="recurring_starting_date"
                )

                number_of_occurrences = st.number_input(
                    "Number of occurrences",
                    min_value=2,
                    value=2,
                    key="number_of_occurrences"
                )


            if st.button("Add transaction", width="stretch", key="add_transaction_button"):

                category = category.strip().capitalize()

                if not category:
                    st.warning("Please enter a valid type.")
                    return

                if amount == 0:
                    st.warning("Amount cannot be zero.")
                    return
                
                if amount< 0.01 and amount > -0.01:
                    st.warning("Amount cannot be too small.")
                    return
                
                amount = round(amount, 2)
                
                is_new_type = category not in user_type_characteristics["type"].values

                if is_new_type:
                    st.session_state.pending_transaction = {
                        "amount": amount,
                        "category": category,
                        "description": description,
                        "recurring_bool": recurring_bool,
                        "date": date if not recurring_bool else None,
                        "recurring_frequency": recurring_frequency if recurring_bool else None,
                        "recurring_starting_date": recurring_starting_date if recurring_bool else None,
                        "number_of_occurrences": number_of_occurrences if recurring_bool else None,
                    }

                    st.session_state.pending_type_direction = None

                    new_utils.transaction_type_categorization(category)
                    st.stop()

                else:
                    existing_direction = user_type_characteristics[user_type_characteristics["type"] == category]["direction"].iloc[0]

                    if amount < 0 and existing_direction == "Income":
                        st.warning("Income transactions cannot have a negative amount.")
                        return
                    
                    if amount > 0 and existing_direction == "Expense":
                        st.warning("Expense transactions cannot have a positive amount.")
                        return
                    
                    if number_of_occurrences > MAX_OCCURRENCES:
                        st.warning("Number of occurrences is too high")
                        return
                    
                    with conn.session as s:
                        if recurring_bool:
                            for i in range(number_of_occurrences):
                                if recurring_frequency == "Daily":
                                    transaction_date = recurring_starting_date + pd.DateOffset(days=i)
                                elif recurring_frequency == "Weekly":
                                    transaction_date = recurring_starting_date + pd.DateOffset(weeks=i)
                                elif recurring_frequency == "Monthly":
                                    transaction_date = recurring_starting_date + pd.DateOffset(months=i)
                                elif recurring_frequency == "Yearly":
                                    transaction_date = recurring_starting_date + pd.DateOffset(years=i)
                                
                                new_utils.insert_transaction(s, amount, category, transaction_date, description)
                            
                        else:
                            new_utils.insert_transaction(s, amount, category, date, description)
                        
                        s.commit()
                    
                    st.rerun()

            
            if ( "pending_transaction" in st.session_state
                and st.session_state.pending_transaction is not None
                and st.session_state.get("pending_type_direction") is not None
            ):
                pending = st.session_state.pending_transaction

                transaction_direction = st.session_state.pending_type_direction
                transaction_color = f"#{random.randint(0, 0xFFFFFF):06X}"

                with conn.session as s:
                    s.execute(
                        text("""
                            INSERT INTO type_characteristics 
                            (type, color, direction, user_id) 
                            VALUES (:type, :color, :direction, :user_id)
                        """),
                        {
                            "type": pending["category"],
                            "color": transaction_color,
                            "direction": transaction_direction,
                            "user_id": st.session_state.user_id,
                        }
                    )

                    if pending["recurring_bool"]:
                        for i in range(pending["number_of_occurrences"]):
                            if pending["recurring_frequency"] == "Daily":
                                transaction_date = pending["recurring_starting_date"] + pd.DateOffset(days=i)
                            elif pending["recurring_frequency"] == "Weekly":
                                transaction_date = pending["recurring_starting_date"] + pd.DateOffset(weeks=i)
                            elif pending["recurring_frequency"] == "Monthly":
                                transaction_date = pending["recurring_starting_date"] + pd.DateOffset(months=i)
                            elif pending["recurring_frequency"] == "Yearly":
                                transaction_date = pending["recurring_starting_date"] + pd.DateOffset(years=i)

                            new_utils.insert_transaction(
                                s,
                                pending["amount"],
                                pending["category"],
                                transaction_date,
                                pending["description"],
                            )
                    else:
                        new_utils.insert_transaction(
                            s,
                            pending["amount"],
                            pending["category"],
                            pending["date"],
                            pending["description"],
                        )

                    s.commit()

                st.session_state.pending_transaction = None
                st.session_state.pending_type_direction = None

                st.rerun()  


                    
def remove_transaction(conn, user_transactions):

    transaction_options = user_transactions["id"].tolist()

    labels_by_id = {
        row["id"]: f"{row['type']} | {row['amount']} | {pd.to_datetime(row['date']).strftime('%d/%m/%Y')}"
        for _, row in user_transactions.iterrows()
    }

    
    with st.container(border=True):

        transaction_id = st.selectbox(
        "Transactions",
        transaction_options,
        format_func=lambda transaction_id: labels_by_id[transaction_id],
        key="transaction_to_remove",
        )
    

        if st.button("Remove Transaction"):
            if transaction_id is not None:

                with conn.session as s:
                    s.execute(
                        text("""
                            DELETE FROM transactions
                            WHERE id = :id
                            AND user_id = :user_id
                        """),
                        {
                            "id": transaction_id,
                            "user_id": st.session_state.user_id,
                        },
                    )
                    s.commit()
                st.success("Transaction removed!")
                st.rerun()


def set_monthly_budget(conn, user_budget):
    # Keep type as a normal column, not as index
    original_df = user_budget[["type", "amount"]].copy().reset_index(drop=True)
    original_df["amount"] = original_df["amount"].astype(float).round(2)

    display_df = original_df.copy()
    display_df["amount"] = display_df["amount"].apply(new_utils.format_it_number)

    with st.container(border=True):
        edited_df = st.data_editor(
            display_df,
            num_rows="fixed",
            hide_index=True,
            disabled=["type"],
            column_order=["type", "amount"],
            column_config={
                "type": st.column_config.TextColumn(
                    "Type",
                ),
                "amount": st.column_config.TextColumn(
                    "Monthly Budget",
                    help="Use comma as decimal separator, e.g. 123,45",
                ),
            },
            key="budget_editor",
            width="stretch",
        )

    updates = []

    for idx, row in edited_df.iterrows():
        budget_type = row["type"]

        try:
            new_amount = new_utils.parse_it_number(row["amount"])
        except ValueError:
            st.warning(f"Invalid budget value for {budget_type}. Use a format like 123,45.")
            return

        old_amount = original_df.loc[idx, "amount"]

        new_amount = round(new_amount, 2)

        if new_amount != old_amount:
            updates.append({
                "type": budget_type,
                "amount": new_amount,
            })

    if updates:
        with conn.session as s:
            for update in updates:
                s.execute(
                    text("""
                        UPDATE budgets
                        SET amount = :amount
                        WHERE type = :type
                        AND user_id = :user_id
                    """),
                    {
                        "amount": update["amount"],
                        "type": update["type"],
                        "user_id": st.session_state.user_id,
                    }
                )

            s.commit()

        st.toast("Budget updated", icon="✅")
        st.rerun()
    
#############################################################################################################################################################################
# MAIN PAGE FUNCTIONS

def summary_table(table_data, user_type_characteristics,conn):

    if "colors_table" not in st.session_state:
        type_to_color = zip(user_type_characteristics["type"], user_type_characteristics["color"])
        st.session_state.colors_table = {}
        for type_, color in type_to_color:
            st.session_state.colors_table[type_] = f"color:{color};"

    to_show_data = table_data.drop(columns=["id"]).copy()
    to_show_data["date"] = pd.to_datetime(to_show_data["date"]).dt.strftime("%d/%m/%Y")
    

    styled_df = to_show_data.style.map(
        lambda x: 'color: #bf2817;'
        if x == 'Expense'
        else 'color: #54b86d ;',
        subset=['ex_in']
    ).map(
        lambda x: st.session_state.colors_table.get(x, "color:gray;"),
        subset=['type']
    ).map(
        lambda x: 'color: #bf2817;'
        if x < 0
        else 'color: #54b86d ;',
        subset=['amount']
    ).format(
        lambda x: new_utils.format_it_number(x) if isinstance(x, (int, float)) else x,
        subset=['amount']
    )
    

    transactions_to_remove = st.dataframe(styled_df,
                hide_index=True,
                use_container_width=True,
                on_select="rerun",
                selection_mode="multi-row",
                column_config={
                "amount": "Amount",
                "type": "Type",
                "date": "Date",
                "ex_in": "Income/Expense",
                "description": "Description",
                
    })

    
    if transactions_to_remove["selection"]["rows"] not in (None, []):
        rows_to_remove = transactions_to_remove["selection"]["rows"]
        id_to_remove = table_data.iloc[rows_to_remove]["id"].tolist()
        with st.container(border=False, horizontal_alignment="right"):
            if st.button("Remove selected transactions", key="remove_selected_transactions_button"):
                with conn.session as s:
                    s.execute(
                        text("""
                            DELETE FROM transactions
                            WHERE id = ANY(:ids)
                            AND user_id = :user_id
                        """),
                        {
                            "ids": id_to_remove,
                            "user_id": st.session_state.user_id,
                        },
                    )
                    s.commit()
                st.success("Selected transactions removed!")
                st.rerun()


def chart(transactions_df):
    # Generate line chart
    general_fig = go.Figure()
    sorted_transactions = transactions_df.sort_values(by="date")
    period_balance = sorted_transactions["amount"].sum()
    general_fig.add_trace(go.Scatter(x=sorted_transactions["date"], y=sorted_transactions["amount"].cumsum(), mode='lines+markers', line_color='#54b86d' if period_balance >= 0 else '#bf2817'))

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
    cumulative_amounts = sorted_transactions["amount"].cumsum()

    # Add a vertical line at each transaction date (from 0 to that day's cumulative amount)
    for date, cum_amount in zip(sorted_transactions["date"], cumulative_amounts):
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
    general_fig.update_layout(title=dict(text="Cumulative Balance Over Time", font=dict(size=22)),  xaxis_title="Date", yaxis_title="Cumulative Balance", showlegend=False)
    general_fig.update_xaxes(tickformat="%d/%m/%Y")
    st.plotly_chart(general_fig, use_container_width=True)

def pie_chart(user_transactions, user_type_characteristics):

    type_to_color = zip(user_type_characteristics["type"], user_type_characteristics["color"])
    colors_table = {}
    for type_, color in type_to_color:
        colors_table[type_] = f"color:{color};"

    # Pie chart of Expenses by Type (mind the negative values in the Amount column, we need to convert them to positive for the pie chart), using the same colors as in the table for consistency, and add a hole in the middle for better aesthetics.
    expenses_by_type = user_transactions[user_transactions["ex_in"] == "Expense"].groupby("type")["amount"].sum().abs()
    pie_fig = go.Figure(data=[go.Pie(labels=expenses_by_type.index, values= expenses_by_type.values, hole=0.4, marker_colors=[colors_table.get(t, 'gray').split(':')[-1][:-1] for t in expenses_by_type.index], textfont=dict(color='white'))])
    pie_fig.update_layout(title=dict(text="Expenses by Type", font=dict(size=22)))
    st.plotly_chart(pie_fig, use_container_width=True)

    # Total expenses for each type, using the same colors as in the table.
    for t in expenses_by_type.index:
        st.markdown(f"<p style='color: {colors_table.get(t, 'gray').split(':')[-1][:-1]}; font-size: 18px;'>{t}: {expenses_by_type[t]:,.2f} </p>", unsafe_allow_html=True)
    
    
def budget_vs_actuals(transactions, budget, type_characteristics):

    if "colors_table" not in st.session_state:
        type_to_color = zip(type_characteristics["type"], type_characteristics["color"])
        st.session_state.colors_table = {}
        for type_, color in type_to_color:
            st.session_state.colors_table[type_] = f"color:{color};"

    month_names = { 1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox(
            "Select month for comparison",
            options=range(1, 13),
            format_func=lambda x: month_names[x],
            key="budget_comparison_month"
            )
            
        with col2:
            st.selectbox("Select year for comparison", options=[str(y) for y in range(datetime.now().year - 10, datetime.now().year + 1)], index=10, key="budget_comparison_year")

    
    selected_month = st.session_state.budget_comparison_month
    selected_year = int(st.session_state.budget_comparison_year)

    transactions_temp = transactions.copy()

    transactions_temp["date"] = pd.to_datetime(transactions["date"]).copy()

    filtered_transactions = transactions_temp[
        (transactions_temp["date"].dt.month == selected_month) &
        (transactions_temp["date"].dt.year == selected_year)
    ]

    if filtered_transactions.empty:
        st.warning("No transactions found for the selected period.")
        return

    # Get the sum of expenses for each type in the selected month
    expenses_by_type = filtered_transactions[filtered_transactions["ex_in"] == "Expense"].groupby("type")["amount"].sum().to_frame()
    # fill missing types with 0 expenses. Fill only the types that in the ex_in column have expense as direction
    for t in type_characteristics[type_characteristics["direction"] == "Expense"]["type"]:
        if t not in expenses_by_type.index:
            expenses_by_type.loc[t] = 0.0
    
    # Rename columns amount_x and amount_y to actual and budget
    expenses_by_type = expenses_by_type.rename(columns={"amount": "expenses"})

    # Add a column for the budgeted amount for each type, matching by type and user_id
    expenses_by_type = expenses_by_type.merge(budget, on="type", how="left")
    expenses_by_type = expenses_by_type.rename(columns={"amount": "budget"})

    expenses_by_type["budget"] = expenses_by_type["budget"].fillna(0).astype(float)
    expenses_by_type["expenses"] = expenses_by_type["expenses"].fillna(0).astype(float)

    # Add a column that shows the difference between the actual expenses and the budgeted amount
    expenses_by_type["difference"] = expenses_by_type["budget"] + expenses_by_type["expenses"]



    # Add a row at the bottom that shows the total expenses, total budget, and total difference
    total_row = pd.DataFrame({
        "type": "Total",
        "expenses": expenses_by_type["expenses"].sum(),
        "budget": expenses_by_type["budget"].sum(),
        "difference": expenses_by_type["difference"].sum(),
    }, index=[len(expenses_by_type)])

    expenses_by_type = pd.concat([expenses_by_type, total_row], ignore_index=True)

    expenses_by_type[["budget", "expenses", "difference"]] = expenses_by_type[
    ["budget", "expenses", "difference"]
    ].round(2)

    # swap budget and expenses columns for better readability
    expenses_by_type = expenses_by_type[["type", "budget", "expenses", "difference"]]

    stylized_budget = expenses_by_type.style.format({
        "budget": new_utils.format_it_number,
        "expenses": new_utils.format_it_number,
        "difference": new_utils.format_it_number,
    }).map(
        lambda x: st.session_state.colors_table.get(x, "color:gray;"),
        subset=['type']
    ).apply(
        lambda row: ['background-color: #2b0101;' if row['difference'] < 0 else 'background-color:#092b01;' if row['difference'] > 0 else '' for _ in row.index],
        axis=1
    )


   

    st.dataframe(stylized_budget,hide_index=True, use_container_width=True, column_config={
        "type": st.column_config.TextColumn("Type"),
        "budget": st.column_config.TextColumn("Budget"),
        "expenses": st.column_config.TextColumn("Actual Expenses"),
        "difference": st.column_config.TextColumn("Difference"),
    })