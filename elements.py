import streamlit as st
import pandas as pd
import new_utils
import plotly.graph_objects as go
from sqlalchemy import text
from datetime import datetime
import random as random

# SIDEBAR FUNCTIONS

def time_period_and_order(user_transactions):

    st.sidebar.selectbox("Select time period", ["All time", "Last 30 days", "Last 7 days", "Custom"], key="time_period") 
    transaction_dates = pd.to_datetime(user_transactions["date"])

    if st.session_state.time_period == "Last 30 days":
        user_transactions = user_transactions[transaction_dates >= pd.Timestamp.today().normalize() - pd.DateOffset(days=30)]
    elif st.session_state.time_period == "Last 7 days":
        user_transactions = user_transactions[transaction_dates >= pd.Timestamp.today().normalize() - pd.DateOffset(days=7)]
    elif st.session_state.time_period == "Custom":
        with st.sidebar.container(border=True):
            start_date = st.date_input("Start date", key="custom_start_date")
            end_date = st.date_input("End date", key="custom_end_date")

        if start_date > end_date:
            st.sidebar.warning("Start date must be before end date.")
        else:
            user_transactions = user_transactions[
                (transaction_dates >= pd.to_datetime(start_date))
                & (transaction_dates <= pd.to_datetime(end_date))
            ]
    
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.markdown('<p style="font-size:18px;"><strong>Order transactions:</strong></p>', unsafe_allow_html=True)
    with st.sidebar.container(border=False):
        with st.sidebar.expander("Order by", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.selectbox("", ["Date", "Amount"], key="order_by", label_visibility="collapsed")
            with col2:
                st.selectbox("", ["⬆️", "⬇️" ], key="order_direction", label_visibility="collapsed")
            
            if st.session_state.order_by == "Date":
                user_transactions = user_transactions.sort_values(by="date", ascending=st.session_state.order_direction == "⬇️")
            elif st.session_state.order_by == "Amount":
                user_transactions = user_transactions.sort_values(by="amount", ascending=st.session_state.order_direction == "⬇️")
    
            st.selectbox("Exclude incomes", ["No", "Yes"], key="exclude_incomes")
            if st.session_state.exclude_incomes == "Yes":
                user_transactions = user_transactions[user_transactions["ex_in"] == "Expense"]
    return user_transactions
    

def add_transaction(conn, user_type_characteristics):
    st.sidebar.markdown('<p style="font-size:18px;"><strong>Add a new transaction:</strong></p>', unsafe_allow_html=True)

    # extract types from user_type_characteristics
    type_options = user_type_characteristics["type"].unique().tolist()
    type_options.remove("Salary")
    type_options = sorted(type_options)
    type_options.insert(0, "Salary")
    type_options.append("Other")

    with st.sidebar.container(border=False):
        with st.sidebar.expander("Add transaction", expanded=False):
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

    
    with st.sidebar.container(border=True):

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

# def set_monthly_budget(conn, user_budget):

#     budget_types = user_budget["type"].tolist()
#     budget_types = sorted(budget_types)

#     with st.sidebar.container(border=True):

#         selected_type = st.selectbox("Select type", budget_types, key="budget_type")

#         st.session_state.current_amount = user_budget[user_budget["type"] == selected_type]["amount"].iloc[0]

#         new_amount = st.number_input("New monthly amount", value=float(st.session_state.current_amount), step=0.01, key="new_monthly_amount")

#         if st.button("Update monthly budget"):
#             with conn.session as s:
#                 s.execute(
#                     text("""
#                         UPDATE budgets
#                         SET amount = :amount
#                         WHERE type = :type
#                         AND user_id = :user_id
#                     """),
#                     {
#                         "amount": new_amount,
#                         "type": selected_type,
#                         "user_id": st.session_state.user_id,
#                     },
#                 )
#                 s.commit()
#             st.success("Monthly budget updated!")
#             st.rerun()

def set_monthly_budget(conn, user_budget):

    budget_types = user_budget["type"].tolist()
    budget_types = sorted(budget_types)

    with st.sidebar.container(border=True):

        for budget_type in budget_types:

            current_amount = user_budget[user_budget["type"] == budget_type]["amount"].iloc[0]

            st.markdown(
                f"<p style='font-size:24px;'><strong>{budget_type}</strong></p>",
                unsafe_allow_html=True,
            )

            new_amount = st.number_input(
                "Monthly budget",
                value=float(current_amount),
                step=0.01,
                key=f"new_monthly_amount_{budget_type}",
                label_visibility="collapsed",
            )

            if st.button(f"Update", key=f"update_button_{budget_type}"):
                with conn.session as s:
                    s.execute(
                        text("""
                            UPDATE budgets
                            SET amount = :amount
                            WHERE type = :type
                            AND user_id = :user_id
                        """),
                        {
                            "amount": new_amount,
                            "type": budget_type,
                            "user_id": st.session_state.user_id,
                        },
                    )
                    s.commit()
                st.success(f"{budget_type} monthly budget updated!")
                st.rerun()
#############################################################################################################################################################################
# MAIN PAGE FUNCTIONS

def summary_table(table_data, user_type_characteristics):

    type_to_color = zip(user_type_characteristics["type"], user_type_characteristics["color"])
    colors_table = {}
    for type_, color in type_to_color:
        colors_table[type_] = f"color:{color};"

    table_data = table_data.drop(columns=["id"]).copy()
    table_data["date"] = pd.to_datetime(table_data["date"]).dt.strftime("%d/%m/%Y")
    

    styled_df = table_data.style.map(
        lambda x: 'color: #bf2817;'
        if x == 'Expense'
         else 'color: #54b86d;',
        subset=['ex_in']
    ).map(
        lambda x: colors_table.get(x, "color:gray;"),
        subset=['type']
    ).map(
        lambda x: 'color: #bf2817;'
        if x == 'Expense'
         else 'color: #54b86d;',
        subset=['description']
    ).map(
        lambda x: 'color: #bf2817;'
        if x == 'Expense'
         else 'color: #54b86d;',
        subset=['amount']
    ).map(
        lambda x: 'color: #bf2817;'
        if x == 'Expense'
         else 'color: #54b86d;',
        subset=['ex_in']
    ).format(
        lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        subset=['amount']
    )
    

    st.dataframe(styled_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                "amount": "Amount",
                "type": "Type",
                "date": "Date",
                "ex_in": "Income/Expense",
                "description": "Description",
    })


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
    general_fig.update_layout(title=dict(text="Cumulative Balance Over Time", font=dict(size=22)), xaxis_title="Date", yaxis_title="Cumulative Balance", showlegend=False)
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

def show_budget(transactions, budget):
    
    print()