import streamlit as st

from services.owner_service import OwnerService
from services.booking_service import BookingService
from services.finance_service import FinanceService


def _safe(v):
    try:
        return round(float(v or 0), 2)
    except:
        return 0.0


def _get_apartment(conn, booking_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*
        FROM apartments a
        JOIN bookings b ON b.apartment_id = a.id
        WHERE b.id = ?
    """, (booking_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def _get_paid(conn, booking_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(SUM(amount_paid_gel), 0) as total
        FROM owner_payouts
        WHERE booking_id = ?
    """, (booking_id,))
    row = cursor.fetchone()
    return float(dict(row)["total"] or 0)


def render_owner_statement_page(conn):
    owner_service = OwnerService(conn)
    booking_service = BookingService(conn)
    finance_service = FinanceService(conn)

    st.subheader("Owner Statement")

    owners = owner_service.get_all_owners()
    bookings = booking_service.get_all_bookings()

    owner_options = {
        f"{o['id']} - {o['name']}": o["id"]
        for o in owners
    }

    selected = st.selectbox("Собственник", list(owner_options.keys()))
    owner_id = owner_options[selected]

    rows = []

    for b in bookings:
        apartment = _get_apartment(conn, b["id"])
        if not apartment:
            continue

        if apartment["owner_id"] != owner_id:
            continue

        f = finance_service.calculate_booking_finances(b["id"], False)

        accrued = _safe(f.get("owner_amount_due"))
        paid = _safe(_get_paid(conn, b["id"]))
        balance = _safe(accrued - paid)

        rows.append({
            "Бронь": b["id"],
            "Гость": b.get("guest_name"),
            "Заезд": b.get("check_in"),
            "Выезд": b.get("check_out"),
            "Начислено": accrued,
            "Выплачено": paid,
            "Остаток": balance
        })

    if rows:
        st.dataframe(rows, use_container_width=True)

        total_accrued = _safe(sum(r["Начислено"] for r in rows))
        total_paid = _safe(sum(r["Выплачено"] for r in rows))
        total_balance = _safe(sum(r["Остаток"] for r in rows))

        c1, c2, c3 = st.columns(3)
        c1.metric("Начислено", total_accrued)
        c2.metric("Выплачено", total_paid)
        c3.metric("Долг", total_balance)
    else:
        st.info("Нет данных")