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

with conn.session as s:
    type_characteristics = s.execute(text('''SELECT id, type, color, direction FROM type_characteristics WHERE user_id = :user_id'''), {"user_id": st.session_state.user_id}).fetchall()
type_characteristics = pd.DataFrame(type_characteristics, columns=["id", "type", "color", "direction"])

with st.sidebar.container(border=False):
    if st.button("Return to main page",width="stretch", key="return_button", icon="🏠"):
        st.switch_page("pages/new_main.py")

st.title("Settings", text_alignment="center")

if st.session_state.get("type_deleted_success"):
    st.success(st.session_state["type_deleted_success"])
    del st.session_state["type_deleted_success"]

stylized_type_table = type_characteristics[["type", "color", "direction"]].copy()
def color_type_column(row):
    return [
        f"color: {row['color']}; font-weight: 600;" if col == "type" else ""
        for col in row.index
    ]

stylized_type_table = stylized_type_table.style.apply(color_type_column, axis=1)

if "type_table_key" not in st.session_state:
    st.session_state.type_table_key = 0

selected_style = st.dataframe(
    stylized_type_table,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "type": st.column_config.TextColumn("Type"),
        "color": st.column_config.TextColumn("Color", help="Hex color code for this type"),
        "direction": st.column_config.TextColumn("Direction", help="Whether this type is an income or an expense"),
    },
    hide_index=True,
    key=f"type_table_{st.session_state.type_table_key}"
)

selected_rows = selected_style["selection"]["rows"]

if "edit_type_dialog_open" not in st.session_state:
    st.session_state.edit_type_dialog_open = False

if selected_rows:
    selected_idx = selected_rows[0]

    if selected_idx < len(type_characteristics):
        selected_id = int(type_characteristics.iloc[selected_idx]["id"])
        selected_type = type_characteristics.iloc[selected_idx]["type"]

        col1, col2 = st.columns(2)

        with col1:
            with st.container(horizontal_alignment="right"):
                if st.button("Edit", key=f"edit_button_{selected_id}", width=100):
                    st.session_state.edit_type_dialog_open = True
                    st.session_state.editing_type_id = selected_id
                    st.session_state.editing_type_name = selected_type
                    st.session_state.active_type_edit_field = None

        with col2:
            if st.button("Delete", key=f"delete_button_{selected_id}", width=100):
                new_utils.delete_type_dialog(
                    conn=conn,
                    type_id=selected_id,
                    type_name=selected_type,
                    user_id=st.session_state.user_id
                )

if st.session_state.get("edit_type_dialog_open"):
    new_utils.edit_type_dialog(
        conn=conn,
        type_id=st.session_state.editing_type_id,
        type_name=st.session_state.editing_type_name,
        user_id=st.session_state.user_id
    )