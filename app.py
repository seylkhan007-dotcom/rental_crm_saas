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

page = st.sidebar.radio(
    "Разделы",
    [
        "Дашборд",
        "Отчёты и аналитика",
        "Календарь бронирований",
        "Собственники",
        "Отчёт по собственнику",
        "Комплексы",
        "Квартиры",
        "Сотрудники и участники",
        "Лиды",
        "Контракты",
        "Бронирования и финансы",
        "Расходы",
        "Выплаты",
        "Платежи гостей",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption("Архитектура: UI → Service → Repository → DB")

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

conn.close()