import utils
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
import random
from typing import Literal

def format_it_number(value):
    return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_it_number(value):
    """
    Converts:
    '123,45'    -> 123.45
    '1.234,56'  -> 1234.56
    """
    value = str(value).strip()

    if not value:
        raise ValueError("Empty value")

    value = value.replace(".", "").replace(",", ".")
    return round(float(value), 2)

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


def style_buttons(widget_key, color, text_color):
    st.markdown(f"""
    <style>
    /* Selected button only inside the segmented control with key="{widget_key}" */
    .st-key-{widget_key} button[data-testid="stBaseButton-segmented_controlActive"] {{
        background-color: {color} !important;
        color: {text_color} !important;
        border-color: {color} !important;
    }}

    .st-key-{widget_key} button[data-testid="stBaseButton-segmented_controlActive"]:hover,
    .st-key-{widget_key} button[data-testid="stBaseButton-segmented_controlActive"]:focus {{
        background-color: {color} !important;
        color: {text_color} !important;
        border-color: {color} !important;
    }}
    </style>
    """, unsafe_allow_html=True)


WidgetPart = Literal[
    "label",
    "option_text",
    "button",
    "selected_button",
    "selected_text",
    "hover_button",
    "container",
]


def style_streamlit_widget(
    widget_key: str,
    part: WidgetPart,
    **css_properties,
):
    """
    Style a specific part of a Streamlit widget using its key.

    Parameters
    ----------
    widget_key:
        The key of the Streamlit widget.

    part:
        Which part of the widget to style.

    css_properties:
        CSS properties written as Python keyword arguments.

    Example
    -------
    style_streamlit_widget(
        "time_period",
        part="label",
        font_size="22px",
        font_weight="700",
        color="white",
    )
    """

    selectors = {
        "label": f"""
            .st-key-{widget_key} label p,
            .st-key-{widget_key} [data-testid="stWidgetLabel"] p
        """,

        "option_text": f"""
            .st-key-{widget_key} button p
        """,

        "button": f"""
            .st-key-{widget_key} button
        """,

        "selected_button": f"""
            .st-key-{widget_key} button[data-testid="stBaseButton-segmented_controlActive"]
        """,

        "selected_text": f"""
            .st-key-{widget_key} button[data-testid="stBaseButton-segmented_controlActive"] p
        """,

        "hover_button": f"""
            .st-key-{widget_key} button:hover,
            .st-key-{widget_key} button:focus
        """,

        "container": f"""
            .st-key-{widget_key}
        """,
    }

    selector = selectors[part]

    css_lines = []
    for property_name, value in css_properties.items():
        css_name = property_name.replace("_", "-")
        css_lines.append(f"{css_name}: {value} !important;")

    css = "\n".join(css_lines)

    st.markdown(f"""
    <style>
    {selector} {{
        {css}
    }}
    </style>
    """, unsafe_allow_html=True)

@st.dialog("Are you sure you want to delete this type?", width="medium")
def delete_type_dialog(conn, type_id, type_name, user_id):
    with st.container(horizontal_alignment="center"):
        st.write(f"Delete type **{type_name}**?")

    col1, col2 = st.columns(2)

    with col1:
        with st.container(horizontal_alignment="right"):
            if st.button("Yes", key=f"delete_yes_button_{type_id}"):
                with conn.session as s:
                    s.execute(
                        text("""
                            DELETE FROM type_characteristics
                            WHERE id = :id AND user_id = :user_id
                        """),
                        {
                            "id": type_id,
                            "user_id": user_id
                        }
                    )
                    s.commit()

                st.session_state["type_deleted_success"] = f"Type '{type_name}' deleted."
                st.session_state.type_table_key += 1
                st.rerun()

    with col2:
        with st.container(horizontal_alignment="left"):
            if st.button("No", key=f"delete_no_button_{type_id}"):
                st.rerun()

@st.dialog("What do you want to edit?", width="medium", on_dismiss= lambda: setattr(st.session_state, "edit_type_dialog_open", False) or setattr(st.session_state, "active_type_edit_field", None))
def edit_type_dialog(conn, type_id, type_name, user_id):

    if "active_type_edit_field" not in st.session_state:
        st.session_state.active_type_edit_field = None

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Name", key=f"edit_name_button_{type_id}"):
            st.session_state.active_type_edit_field = "name"

    with col2:
        if st.button("Color", key=f"edit_color_button_{type_id}"):
            st.session_state.active_type_edit_field = "color"

    with col3:
        if st.button("Direction", key=f"edit_direction_button_{type_id}"):
            st.session_state.active_type_edit_field = "direction"

    st.divider()

    if st.session_state.active_type_edit_field == "name":
        new_name = st.text_input(
            "New name:",
            value=type_name,
            key=f"edit_name_input_{type_id}"
        )
        with st.container(horizontal_alignment="right"):
            if st.button("Save", key=f"save_name_button_{type_id}"):
                with conn.session as s:
                    s.execute(
                        text("""
                            UPDATE type_characteristics
                            SET type = :new_name
                            WHERE id = :id AND user_id = :user_id
                        """),
                        {
                            "new_name": new_name,
                            "id": type_id,
                            "user_id": user_id
                        }
                    )
                    s.commit()

                st.session_state["type_updated_success"] = f"Type '{type_name}' updated."
                st.session_state.edit_type_dialog_open = False
                st.session_state.active_type_edit_field = None
                st.session_state.type_table_key += 1
                st.rerun()

    elif st.session_state.active_type_edit_field == "color":
        new_color = st.color_picker(
            "New color:",
            key=f"edit_color_input_{type_id}"
        )

        with st.container(horizontal_alignment="right"):
            if st.button("Save", key=f"save_color_button_{type_id}"):
                with conn.session as s:
                    s.execute(
                        text("""
                            UPDATE type_characteristics
                            SET color = :new_color
                            WHERE id = :id AND user_id = :user_id
                        """),
                        {
                            "new_color": new_color,
                            "id": type_id,
                            "user_id": user_id
                        }
                    )
                    s.commit()

                st.session_state["type_updated_success"] = f"Color for '{type_name}' updated."
                st.session_state.edit_type_dialog_open = False
                st.session_state.active_type_edit_field = None
                st.session_state.type_table_key += 1
                st.rerun()

    elif st.session_state.active_type_edit_field == "direction":
        new_direction = st.selectbox(
            "New direction:",
            ["Income", "Expense"],
            key=f"edit_direction_input_{type_id}"
        )

        with st.container(horizontal_alignment="right"):
            if st.button("Save", key=f"save_direction_button_{type_id}"):
                with conn.session as s:
                    s.execute(
                        text("""
                            UPDATE type_characteristics
                            SET direction = :new_direction
                            WHERE id = :id AND user_id = :user_id
                        """),
                        {
                            "new_direction": new_direction,
                            "id": type_id,
                            "user_id": user_id
                        }
                    )
                    s.commit()

                st.session_state["type_updated_success"] = f"Direction for '{type_name}' updated."
                st.session_state.edit_type_dialog_open = False
                st.session_state.active_type_edit_field = None
                st.session_state.type_table_key += 1
                st.rerun()

