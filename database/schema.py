# database/schema.py


def _get_existing_columns(conn, table_name: str) -> set[str]:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    rows = cursor.fetchall()
    return {row[1] for row in rows}


def _ensure_column(conn, table_name: str, column_name: str, column_sql: str) -> None:
    existing_columns = _get_existing_columns(conn, table_name)
    if column_name not in existing_columns:
        cursor = conn.cursor()
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql};")
        conn.commit()


def _create_indexes(conn) -> None:
    cursor = conn.cursor()

    # Базовые индексы
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_apartments_owner_id ON apartments(owner_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_apartments_complex_id ON apartments(complex_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_apartment_id ON bookings(apartment_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_check_in ON bookings(check_in);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_check_out ON bookings(check_out);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_booking_id ON expenses(booking_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_owner_payouts_booking_id ON owner_payouts(booking_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_owner_payouts_owner_id ON owner_payouts(owner_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_debts_booking_id ON debts(booking_id);")

    # Акторы
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_actors_is_active ON app_actors(is_active);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_actor_roles_actor_id ON actor_roles(actor_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_actor_roles_role_code ON actor_roles(role_code);")

    # Контракты
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_owner_contract_profiles_owner_id "
        "ON owner_contract_profiles(owner_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_owner_contract_profiles_is_active "
        "ON owner_contract_profiles(is_active);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_contract_split_rules_profile_id "
        "ON contract_split_rules(contract_profile_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_contract_split_rules_stay_type "
        "ON contract_split_rules(stay_type);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_contract_expense_rules_profile_id "
        "ON contract_expense_rules(contract_profile_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_contract_expense_rules_expense_type "
        "ON contract_expense_rules(expense_type_code);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_contract_apartments_profile_id "
        "ON contract_apartments(contract_profile_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_contract_apartments_apartment_id "
        "ON contract_apartments(apartment_id);"
    )

    # Брони / финансы
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_bookings_contract_profile_id "
        "ON bookings(contract_profile_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_bookings_checkin_actor_id "
        "ON bookings(checkin_actor_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_bookings_manager_commission_actor_id "
        "ON bookings(manager_commission_actor_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_bookings_finance_status "
        "ON bookings(finance_status);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_booking_finance_snapshots_booking_id "
        "ON booking_finance_snapshots(booking_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_booking_finance_snapshots_status "
        "ON booking_finance_snapshots(snapshot_status);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_booking_finance_snapshots_locked_at "
        "ON booking_finance_snapshots(locked_at);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_booking_profit_splits_booking_id "
        "ON booking_profit_splits(booking_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_booking_profit_splits_actor_id "
        "ON booking_profit_splits(actor_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_guest_payments_booking_id "
        "ON guest_payments(booking_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_guest_payments_status "
        "ON guest_payments(status);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_expenses_status "
        "ON expenses(status);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_expenses_created_by_actor_id "
        "ON expenses(created_by_actor_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_expenses_approved_by_actor_id "
        "ON expenses(approved_by_actor_id);"
    )

    conn.commit()


def create_all(conn):
    cursor = conn.cursor()

    # ------------------------------------------------------------------
    # БАЗОВЫЕ ТАБЛИЦЫ
    # ------------------------------------------------------------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS complexes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS owners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS apartments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        owner_id INTEGER,
        complex_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES owners(id),
        FOREIGN KEY (complex_id) REFERENCES complexes(id)
    );
    """)

    # ------------------------------------------------------------------
    # АКТОРЫ
    # ------------------------------------------------------------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_actors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        display_name TEXT,
        actor_type TEXT NOT NULL DEFAULT 'employee',
        default_manager_commission_pct REAL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_by INTEGER,
        updated_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES app_actors(id),
        FOREIGN KEY (updated_by) REFERENCES app_actors(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS actor_roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_id INTEGER NOT NULL,
        role_code TEXT NOT NULL,
        is_primary INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (actor_id) REFERENCES app_actors(id)
    );
    """)

    # ------------------------------------------------------------------
    # КОНТРАКТЫ
    # ------------------------------------------------------------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS owner_contract_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        profile_name TEXT NOT NULL,

        pricing_model TEXT NOT NULL DEFAULT 'management',

        settlement_base_mode TEXT DEFAULT 'from_guest_price',
        profit_mode TEXT DEFAULT 'gross_split',

        owner_percent REAL DEFAULT 0,
        company_percent REAL DEFAULT 0,

        fixed_rent_type TEXT,
        fixed_rent_value REAL DEFAULT 0,
        fixed_rent_currency TEXT DEFAULT 'GEL',

        ota_cost_mode TEXT NOT NULL DEFAULT 'company_only',
        expense_mode TEXT NOT NULL DEFAULT 'rule_based',

        notes TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,

        created_by INTEGER,
        updated_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (owner_id) REFERENCES owners(id),
        FOREIGN KEY (created_by) REFERENCES app_actors(id),
        FOREIGN KEY (updated_by) REFERENCES app_actors(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contract_apartments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_profile_id INTEGER NOT NULL,
        apartment_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(contract_profile_id, apartment_id),
        FOREIGN KEY (contract_profile_id) REFERENCES owner_contract_profiles(id),
        FOREIGN KEY (apartment_id) REFERENCES apartments(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contract_split_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_profile_id INTEGER NOT NULL,
        stay_type TEXT NOT NULL DEFAULT 'all',
        owner_percent REAL NOT NULL,
        company_percent REAL NOT NULL,
        split_basis TEXT NOT NULL DEFAULT 'owner_price',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (contract_profile_id) REFERENCES owner_contract_profiles(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contract_expense_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_profile_id INTEGER NOT NULL,
        expense_type_code TEXT NOT NULL,
        responsibility_mode TEXT NOT NULL DEFAULT 'company',
        owner_pct REAL DEFAULT 0,
        company_pct REAL DEFAULT 0,
        guest_pct REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (contract_profile_id) REFERENCES owner_contract_profiles(id)
    );
    """)

    # ------------------------------------------------------------------
    # БРОНИ
    # ------------------------------------------------------------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        apartment_id INTEGER,
        guest_name TEXT,
        check_in TEXT,
        check_out TEXT,
        total_amount REAL,

        guest_price REAL,
        settlement_base_amount REAL,
        tax_base_price REAL,

        source_channel TEXT,
        ota_account_name TEXT,
        ota_commission_pct REAL,
        ota_vat_pct REAL,

        pricing_model TEXT DEFAULT 'management',
        fixed_rent_type TEXT,
        fixed_rent_value REAL,

        contract_profile_id INTEGER,
        stay_type TEXT DEFAULT 'short_term',

        settlement_base_mode_snapshot TEXT,
        profit_mode_snapshot TEXT,
        owner_percent_snapshot REAL,
        company_percent_snapshot REAL,
        fixed_rent_type_snapshot TEXT,
        fixed_rent_value_snapshot REAL,
        fixed_rent_currency_snapshot TEXT,
        ota_cost_mode_snapshot TEXT,
        expense_mode_snapshot TEXT,

        checkin_actor_id INTEGER,
        manager_commission_actor_id INTEGER,
        manager_commission_pct_snapshot REAL,

        finance_status TEXT DEFAULT 'draft',
        finance_locked_at TEXT,
        finance_locked_by INTEGER,

        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (apartment_id) REFERENCES apartments(id),
        FOREIGN KEY (contract_profile_id) REFERENCES owner_contract_profiles(id),
        FOREIGN KEY (checkin_actor_id) REFERENCES app_actors(id),
        FOREIGN KEY (manager_commission_actor_id) REFERENCES app_actors(id),
        FOREIGN KEY (finance_locked_by) REFERENCES app_actors(id)
    );
    """)

    # legacy слой
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS split_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT NOT NULL,
        entity_id INTEGER NOT NULL,
        stay_type TEXT DEFAULT 'all',
        owner_percent REAL NOT NULL,
        manager_percent REAL NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # legacy слой
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expense_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_type TEXT NOT NULL UNIQUE,
        responsible_party TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # ------------------------------------------------------------------
    # РАСХОДЫ / ВЫПЛАТЫ / ДОЛГИ
    # ------------------------------------------------------------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        expense_type TEXT NOT NULL,
        amount REAL NOT NULL,

        responsibility_mode_snapshot TEXT,
        owner_share_gel REAL DEFAULT 0,
        company_share_gel REAL DEFAULT 0,
        guest_share_gel REAL DEFAULT 0,

        status TEXT DEFAULT 'draft',
        created_by_actor_id INTEGER,
        approved_by_actor_id INTEGER,
        approved_at TEXT,

        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (booking_id) REFERENCES bookings(id),
        FOREIGN KEY (created_by_actor_id) REFERENCES app_actors(id),
        FOREIGN KEY (approved_by_actor_id) REFERENCES app_actors(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS owner_payouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        booking_id INTEGER NOT NULL,

        amount REAL,
        status TEXT NOT NULL,

        amount_due_gel REAL DEFAULT 0,
        amount_paid_gel REAL DEFAULT 0,
        amount_original REAL,
        currency_code TEXT DEFAULT 'GEL',
        fx_rate_to_gel REAL DEFAULT 1,
        due_date TEXT,
        paid_date TEXT,

        created_by_actor_id INTEGER,
        approved_by_actor_id INTEGER,

        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (owner_id) REFERENCES owners(id),
        FOREIGN KEY (booking_id) REFERENCES bookings(id),
        FOREIGN KEY (created_by_actor_id) REFERENCES app_actors(id),
        FOREIGN KEY (approved_by_actor_id) REFERENCES app_actors(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS debts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        counterparty_type TEXT NOT NULL,
        counterparty_id INTEGER NOT NULL,
        booking_id INTEGER,
        related_payout_id INTEGER,
        amount REAL NOT NULL,
        status TEXT NOT NULL,
        description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (booking_id) REFERENCES bookings(id),
        FOREIGN KEY (related_payout_id) REFERENCES owner_payouts(id)
    );
    """)

    # ------------------------------------------------------------------
    # FINANCE SNAPSHOTS
    # ------------------------------------------------------------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS booking_finance_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        version_no INTEGER NOT NULL DEFAULT 1,
        snapshot_status TEXT NOT NULL DEFAULT 'draft',

        pricing_model_snapshot TEXT,
        stay_type_snapshot TEXT,

        contract_profile_id_snapshot INTEGER,
        settlement_base_mode_snapshot TEXT,
        profit_mode_snapshot TEXT,
        owner_percent_snapshot REAL DEFAULT 0,
        company_percent_snapshot REAL DEFAULT 0,
        ota_cost_mode_snapshot TEXT,
        expense_mode_snapshot TEXT,

        guest_price_snapshot REAL DEFAULT 0,
        settlement_base_amount_snapshot REAL DEFAULT 0,
        tax_base_price_snapshot REAL DEFAULT 0,

        ota_commission_pct_snapshot REAL DEFAULT 0,
        ota_vat_pct_snapshot REAL DEFAULT 0,
        ota_commission_amount REAL DEFAULT 0,
        ota_vat_amount REAL DEFAULT 0,
        ota_total_amount REAL DEFAULT 0,

        fixed_rent_type_snapshot TEXT,
        fixed_rent_value_snapshot REAL DEFAULT 0,
        fixed_rent_currency_snapshot TEXT DEFAULT 'GEL',
        fixed_rent_amount_gel REAL DEFAULT 0,

        owner_amount_due REAL DEFAULT 0,
        company_gross_before_ota REAL DEFAULT 0,
        company_after_ota REAL DEFAULT 0,
        company_expenses_total REAL DEFAULT 0,
        company_before_manager REAL DEFAULT 0,
        manager_commission_amount REAL DEFAULT 0,
        distributable_profit_amount REAL DEFAULT 0,

        currency_code TEXT DEFAULT 'GEL',
        fx_rate_to_gel REAL DEFAULT 1,
        gel_total_amount REAL DEFAULT 0,

        lock_reason TEXT,
        locked_at TEXT,
        locked_by INTEGER,

        created_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (booking_id) REFERENCES bookings(id),
        FOREIGN KEY (locked_by) REFERENCES app_actors(id),
        FOREIGN KEY (created_by) REFERENCES app_actors(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS booking_profit_splits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        finance_snapshot_id INTEGER,
        actor_id INTEGER NOT NULL,

        role_snapshot TEXT,
        percent_snapshot REAL NOT NULL DEFAULT 0,
        basis_amount_snapshot REAL NOT NULL DEFAULT 0,
        amount_snapshot REAL NOT NULL DEFAULT 0,

        is_manager_commission INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (booking_id) REFERENCES bookings(id),
        FOREIGN KEY (finance_snapshot_id) REFERENCES booking_finance_snapshots(id),
        FOREIGN KEY (actor_id) REFERENCES app_actors(id)
    );
    """)

    # ------------------------------------------------------------------
    # CASH LAYER
    # ------------------------------------------------------------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guest_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        payment_date TEXT,
        payment_method TEXT,

        amount_original REAL NOT NULL DEFAULT 0,
        currency_code TEXT NOT NULL DEFAULT 'GEL',
        fx_rate_to_gel REAL NOT NULL DEFAULT 1,
        amount_gel REAL NOT NULL DEFAULT 0,

        status TEXT NOT NULL DEFAULT 'pending',
        notes TEXT,

        created_by_actor_id INTEGER,
        approved_by_actor_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (booking_id) REFERENCES bookings(id),
        FOREIGN KEY (created_by_actor_id) REFERENCES app_actors(id),
        FOREIGN KEY (approved_by_actor_id) REFERENCES app_actors(id)
    );
    """)

    conn.commit()

    # ------------------------------------------------------------------
    # SAFE UPGRADE ДЛЯ УЖЕ СУЩЕСТВУЮЩЕЙ БАЗЫ
    # ------------------------------------------------------------------

    _ensure_column(conn, "apartments", "complex_id", "complex_id INTEGER")

    # owner_contract_profiles
    _ensure_column(conn, "owner_contract_profiles", "settlement_base_mode", "settlement_base_mode TEXT DEFAULT 'from_guest_price'")
    _ensure_column(conn, "owner_contract_profiles", "profit_mode", "profit_mode TEXT DEFAULT 'gross_split'")
    _ensure_column(conn, "owner_contract_profiles", "owner_percent", "owner_percent REAL DEFAULT 0")
    _ensure_column(conn, "owner_contract_profiles", "company_percent", "company_percent REAL DEFAULT 0")
    _ensure_column(conn, "owner_contract_profiles", "fixed_rent_type", "fixed_rent_type TEXT")
    _ensure_column(conn, "owner_contract_profiles", "fixed_rent_value", "fixed_rent_value REAL DEFAULT 0")
    _ensure_column(conn, "owner_contract_profiles", "fixed_rent_currency", "fixed_rent_currency TEXT DEFAULT 'GEL'")

    # legacy compatibility
    _ensure_column(conn, "owner_contract_profiles", "sublease_cost_type", "sublease_cost_type TEXT")
    _ensure_column(conn, "owner_contract_profiles", "sublease_cost_value", "sublease_cost_value REAL DEFAULT 0")
    _ensure_column(conn, "owner_contract_profiles", "sublease_currency", "sublease_currency TEXT DEFAULT 'GEL'")

    # contract_apartments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contract_apartments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_profile_id INTEGER NOT NULL,
        apartment_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(contract_profile_id, apartment_id),
        FOREIGN KEY (contract_profile_id) REFERENCES owner_contract_profiles(id),
        FOREIGN KEY (apartment_id) REFERENCES apartments(id)
    );
    """)
    conn.commit()

    # bookings
    _ensure_column(conn, "bookings", "guest_price", "guest_price REAL")
    _ensure_column(conn, "bookings", "settlement_base_amount", "settlement_base_amount REAL")
    _ensure_column(conn, "bookings", "tax_base_price", "tax_base_price REAL")

    _ensure_column(conn, "bookings", "source_channel", "source_channel TEXT")
    _ensure_column(conn, "bookings", "ota_account_name", "ota_account_name TEXT")
    _ensure_column(conn, "bookings", "ota_commission_pct", "ota_commission_pct REAL")
    _ensure_column(conn, "bookings", "ota_vat_pct", "ota_vat_pct REAL")

    _ensure_column(conn, "bookings", "pricing_model", "pricing_model TEXT DEFAULT 'management'")
    _ensure_column(conn, "bookings", "fixed_rent_type", "fixed_rent_type TEXT")
    _ensure_column(conn, "bookings", "fixed_rent_value", "fixed_rent_value REAL")

    _ensure_column(conn, "bookings", "contract_profile_id", "contract_profile_id INTEGER")
    _ensure_column(conn, "bookings", "stay_type", "stay_type TEXT DEFAULT 'short_term'")

    _ensure_column(conn, "bookings", "settlement_base_mode_snapshot", "settlement_base_mode_snapshot TEXT")
    _ensure_column(conn, "bookings", "profit_mode_snapshot", "profit_mode_snapshot TEXT")
    _ensure_column(conn, "bookings", "owner_percent_snapshot", "owner_percent_snapshot REAL")
    _ensure_column(conn, "bookings", "company_percent_snapshot", "company_percent_snapshot REAL")
    _ensure_column(conn, "bookings", "fixed_rent_type_snapshot", "fixed_rent_type_snapshot TEXT")
    _ensure_column(conn, "bookings", "fixed_rent_value_snapshot", "fixed_rent_value_snapshot REAL")
    _ensure_column(conn, "bookings", "fixed_rent_currency_snapshot", "fixed_rent_currency_snapshot TEXT")
    _ensure_column(conn, "bookings", "ota_cost_mode_snapshot", "ota_cost_mode_snapshot TEXT")
    _ensure_column(conn, "bookings", "expense_mode_snapshot", "expense_mode_snapshot TEXT")

    _ensure_column(conn, "bookings", "checkin_actor_id", "checkin_actor_id INTEGER")
    _ensure_column(conn, "bookings", "manager_commission_actor_id", "manager_commission_actor_id INTEGER")
    _ensure_column(conn, "bookings", "manager_commission_pct_snapshot", "manager_commission_pct_snapshot REAL")
    _ensure_column(conn, "bookings", "finance_status", "finance_status TEXT DEFAULT 'draft'")
    _ensure_column(conn, "bookings", "finance_locked_at", "finance_locked_at TEXT")
    _ensure_column(conn, "bookings", "finance_locked_by", "finance_locked_by INTEGER")

    # legacy compatibility
    _ensure_column(conn, "bookings", "owner_price", "owner_price REAL")
    _ensure_column(conn, "bookings", "sublease_cost_type", "sublease_cost_type TEXT")
    _ensure_column(conn, "bookings", "sublease_cost_value", "sublease_cost_value REAL")

    # split_rules legacy
    _ensure_column(conn, "split_rules", "stay_type", "stay_type TEXT DEFAULT 'all'")

    # expenses
    _ensure_column(conn, "expenses", "responsibility_mode_snapshot", "responsibility_mode_snapshot TEXT")
    _ensure_column(conn, "expenses", "owner_share_gel", "owner_share_gel REAL DEFAULT 0")
    _ensure_column(conn, "expenses", "company_share_gel", "company_share_gel REAL DEFAULT 0")
    _ensure_column(conn, "expenses", "guest_share_gel", "guest_share_gel REAL DEFAULT 0")
    _ensure_column(conn, "expenses", "status", "status TEXT DEFAULT 'draft'")
    _ensure_column(conn, "expenses", "created_by_actor_id", "created_by_actor_id INTEGER")
    _ensure_column(conn, "expenses", "approved_by_actor_id", "approved_by_actor_id INTEGER")
    _ensure_column(conn, "expenses", "approved_at", "approved_at TEXT")

    # owner_payouts
    _ensure_column(conn, "owner_payouts", "amount_due_gel", "amount_due_gel REAL DEFAULT 0")
    _ensure_column(conn, "owner_payouts", "amount_paid_gel", "amount_paid_gel REAL DEFAULT 0")
    _ensure_column(conn, "owner_payouts", "amount_original", "amount_original REAL")
    _ensure_column(conn, "owner_payouts", "currency_code", "currency_code TEXT DEFAULT 'GEL'")
    _ensure_column(conn, "owner_payouts", "fx_rate_to_gel", "fx_rate_to_gel REAL DEFAULT 1")
    _ensure_column(conn, "owner_payouts", "due_date", "due_date TEXT")
    _ensure_column(conn, "owner_payouts", "paid_date", "paid_date TEXT")
    _ensure_column(conn, "owner_payouts", "created_by_actor_id", "created_by_actor_id INTEGER")
    _ensure_column(conn, "owner_payouts", "approved_by_actor_id", "approved_by_actor_id INTEGER")

    # finance snapshots
    _ensure_column(conn, "booking_finance_snapshots", "settlement_base_mode_snapshot", "settlement_base_mode_snapshot TEXT")
    _ensure_column(conn, "booking_finance_snapshots", "profit_mode_snapshot", "profit_mode_snapshot TEXT")
    _ensure_column(conn, "booking_finance_snapshots", "owner_percent_snapshot", "owner_percent_snapshot REAL DEFAULT 0")
    _ensure_column(conn, "booking_finance_snapshots", "company_percent_snapshot", "company_percent_snapshot REAL DEFAULT 0")
    _ensure_column(conn, "booking_finance_snapshots", "guest_price_snapshot", "guest_price_snapshot REAL DEFAULT 0")
    _ensure_column(conn, "booking_finance_snapshots", "settlement_base_amount_snapshot", "settlement_base_amount_snapshot REAL DEFAULT 0")
    _ensure_column(conn, "booking_finance_snapshots", "tax_base_price_snapshot", "tax_base_price_snapshot REAL DEFAULT 0")
    _ensure_column(conn, "booking_finance_snapshots", "fixed_rent_type_snapshot", "fixed_rent_type_snapshot TEXT")
    _ensure_column(conn, "booking_finance_snapshots", "fixed_rent_value_snapshot", "fixed_rent_value_snapshot REAL DEFAULT 0")
    _ensure_column(conn, "booking_finance_snapshots", "fixed_rent_currency_snapshot", "fixed_rent_currency_snapshot TEXT DEFAULT 'GEL'")
    _ensure_column(conn, "booking_finance_snapshots", "fixed_rent_amount_gel", "fixed_rent_amount_gel REAL DEFAULT 0")

    # legacy compatibility
    _ensure_column(conn, "booking_finance_snapshots", "sublease_cost_type_snapshot", "sublease_cost_type_snapshot TEXT")
    _ensure_column(conn, "booking_finance_snapshots", "sublease_cost_value_snapshot", "sublease_cost_value_snapshot REAL DEFAULT 0")
    _ensure_column(conn, "booking_finance_snapshots", "sublease_cost_currency_snapshot", "sublease_cost_currency_snapshot TEXT DEFAULT 'GEL'")
    _ensure_column(conn, "booking_finance_snapshots", "sublease_cost_amount_gel", "sublease_cost_amount_gel REAL DEFAULT 0")

    _create_indexes(conn)