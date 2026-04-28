import sqlite3
import streamlit as st

from database.schema import create_all

from ui.dashboard_page import render_dashboard_page
from ui.reports_page import render_reports_page
from ui.calendar_page import render_calendar_page
from ui.owners_page import render_owners_page
from ui.owner_statement_page import render_owner_statement_page
from ui.complexes_page import render_complexes_page
from ui.apartments_page import render_apartments_page
from ui.actors_page import render_actors_page
from ui.leads_page import render_leads_page
from ui.contracts_page import render_contracts_page
from ui.bookings_page import render_bookings_page
from ui.expenses_page import render_expenses_page
from ui.payouts_page import render_payouts_page
from ui.guest_payments_page import render_guest_payments_page
from ui.tasks_page import render_tasks_page


DB_PATH = "app.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


st.set_page_config(
    page_title="CRM управления квартирами",
    layout="wide",
)

st.title("🏠 CRM управления квартирами")
st.subheader("Квартиры, контракты, бронирования, финансы, отчёты и календарь")

conn = get_connection()
create_all(conn)

# =========================================================================
# SIDEBAR NAVIGATION
# =========================================================================

# Initialize navigation state
if "current_page" not in st.session_state:
    st.session_state.current_page = "Дашборд"

# Menu options with visual grouping using emojis
menu_options = [
    ("🏠 Дашборд", "Дашборд"),
    ("📅 Календарь бронирований", "Календарь бронирований"),
    ("🎯 Лиды", "Лиды"),
    ("💼 Бронирования и финансы", "Бронирования и финансы"),
    ("🏢 Квартиры", "Квартиры"),
    ("✅ Задачи", "Задачи"),
    ("💰 Расходы", "Расходы"),
    ("💳 Платежи гостей", "Платежи гостей"),
    ("📤 Выплаты", "Выплаты"),
    ("📊 Отчёты и аналитика", "Отчёты и аналитика"),
    ("👤 Отчёт по собственнику", "Отчёт по собственнику"),
    ("👥 Собственники", "Собственники"),
    ("🏘️ Комплексы", "Комплексы"),
    ("👨‍💼 Сотрудники и участники", "Сотрудники и участники"),
    ("📝 Контракты", "Контракты"),
]

display_names = [name for name, _ in menu_options]
page_names = [page for _, page in menu_options]

# Find current index
current_index = 0
if st.session_state.current_page in page_names:
    current_index = page_names.index(st.session_state.current_page)

# Render single stable radio button for navigation
selected_display = st.sidebar.radio(
    "Навигация",
    display_names,
    index=current_index,
    label_visibility="collapsed",
)

# Update current page based on selection
st.session_state.current_page = page_names[display_names.index(selected_display)]

st.sidebar.markdown("---")
st.sidebar.caption("Архитектура: UI → Service → Repository → DB")

page = st.session_state.current_page

# =========================================================================
# PAGE ROUTING
# =========================================================================

if page == "Дашборд":
    render_dashboard_page(conn)

elif page == "Отчёты и аналитика":
    render_reports_page(conn)

elif page == "Календарь бронирований":
    render_calendar_page(conn)

elif page == "Собственники":
    render_owners_page(conn)

elif page == "Отчёт по собственнику":
    render_owner_statement_page(conn)

elif page == "Комплексы":
    render_complexes_page(conn)

elif page == "Квартиры":
    render_apartments_page(conn)

elif page == "Сотрудники и участники":
    render_actors_page(conn)

elif page == "Лиды":
    render_leads_page(conn)

elif page == "Контракты":
    render_contracts_page(conn)

elif page == "Бронирования и финансы":
    render_bookings_page(conn)

elif page == "Расходы":
    render_expenses_page(conn)

elif page == "Выплаты":
    render_payouts_page(conn)

elif page == "Платежи гостей":
    render_guest_payments_page(conn)

elif page == "Задачи":
    render_tasks_page(conn)

conn.close()