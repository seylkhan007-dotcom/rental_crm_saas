import streamlit as st
from datetime import datetime, timedelta, date

from repositories.apartment_repository import ApartmentRepository
from services.booking_service import BookingService


def render_calendar_page(conn):
    """Страница календаря бронирований (простой MVP).
    
    Показывает таблицу:
    - Строки = квартиры
    - Колонки = следующие 7 дней
    - Ячейки = "✅" если занято, "—" если свободно
    """

    apartment_repo = ApartmentRepository(conn)
    booking_service = BookingService(conn)

    st.subheader("Календарь бронирований")
    st.caption("Обзор загрузки квартир на следующие 7 дней: ✅ = занято, — = свободно")

    # ---------------------------------------------------------
    # ЗАГРУЗКА ДАННЫХ
    # ---------------------------------------------------------
    try:
        apartments = apartment_repo.get_all()
        bookings = booking_service.get_all_bookings()
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return

    if not apartments:
        st.info("Пока нет квартир.")
        return

    # ---------------------------------------------------------
    # ПОДГОТОВКА КАЛЕНДАРЯ
    # ---------------------------------------------------------
    today = date.today()
    days = [today + timedelta(days=i) for i in range(7)]

    # Сортируем квартиры по ID
    apartments = sorted(apartments, key=lambda a: a.get("id", 0))

    # Построить таблицу
    calendar_data = []

    for apartment in apartments:
        apartment_id = apartment.get("id")
        apartment_name = apartment.get("name", f"Квартира {apartment_id}")

        row = {"Квартира": apartment_name}

        for day in days:
            # Проверяем, есть ли бронирование на эту дату
            is_occupied = False

            for booking in bookings:
                if booking.get("apartment_id") != apartment_id:
                    continue

                check_in_str = booking.get("check_in")
                check_out_str = booking.get("check_out")

                if not check_in_str or not check_out_str:
                    continue

                try:
                    check_in = datetime.fromisoformat(check_in_str).date()
                    check_out = datetime.fromisoformat(check_out_str).date()

                    # Дата занята если check_in <= день < check_out
                    if check_in <= day < check_out:
                        is_occupied = True
                        break
                except (ValueError, TypeError):
                    continue

            row[day.strftime("%d.%m")] = "✅" if is_occupied else "—"

        calendar_data.append(row)

    # ---------------------------------------------------------
    # ОТОБРАЖЕНИЕ
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown(f"### Период: {today.strftime('%d.%m.%Y')} — {days[-1].strftime('%d.%m.%Y')}")

    if calendar_data:
        st.dataframe(
            calendar_data,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Нет квартир для отображения.")

    st.markdown("---")
    st.caption("Легенда: ✅ = занято | — = свободно")