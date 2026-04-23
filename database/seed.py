def seed_all(conn, tenant_id: int):
    cursor = conn.cursor()

    print("Добавляем тестовые данные...")

    # OWNER
    cursor.execute("""
    INSERT INTO owners (name)
    VALUES ('Test Owner')
    """)
    owner_id = cursor.lastrowid

    # APARTMENT
    cursor.execute("""
    INSERT INTO apartments (name, owner_id)
    VALUES ('Apartment 101', ?)
    """, (owner_id,))
    apartment_id = cursor.lastrowid

    # BASE BOOKING
    cursor.execute("""
    INSERT INTO bookings (apartment_id, guest_name, check_in, check_out, total_amount)
    VALUES (?, 'John Doe', '2026-04-01', '2026-04-05', 500)
    """, (apartment_id,))
    booking_id = cursor.lastrowid

    # EXPENSE RULES
    cursor.execute("""
    INSERT INTO expense_rules (expense_type, responsible_party)
    VALUES ('cleaning', 'manager')
    """)
    cursor.execute("""
    INSERT INTO expense_rules (expense_type, responsible_party)
    VALUES ('ota_commission', 'manager')
    """)
    cursor.execute("""
    INSERT INTO expense_rules (expense_type, responsible_party)
    VALUES ('utilities', 'owner')
    """)
    cursor.execute("""
    INSERT INTO expense_rules (expense_type, responsible_party)
    VALUES ('guest_damage', 'guest')
    """)

    # EXPENSES FOR BOOKING 1
    cursor.execute("""
    INSERT INTO expenses (booking_id, expense_type, amount)
    VALUES (?, 'cleaning', 30)
    """, (booking_id,))
    cursor.execute("""
    INSERT INTO expenses (booking_id, expense_type, amount)
    VALUES (?, 'ota_commission', 50)
    """, (booking_id,))
    cursor.execute("""
    INSERT INTO expenses (booking_id, expense_type, amount)
    VALUES (?, 'utilities', 20)
    """, (booking_id,))

    # SPLIT RULES
    cursor.execute("""
    INSERT INTO split_rules (level, entity_id, owner_percent, manager_percent)
    VALUES ('owner', ?, 0.70, 0.30)
    """, (owner_id,))

    cursor.execute("""
    INSERT INTO split_rules (level, entity_id, owner_percent, manager_percent)
    VALUES ('apartment', ?, 0.65, 0.35)
    """, (apartment_id,))

    cursor.execute("""
    INSERT INTO split_rules (level, entity_id, owner_percent, manager_percent)
    VALUES ('booking', 2, 0.60, 0.40)
    """)

    conn.commit()

    print("Seed: тестовые данные добавлены")