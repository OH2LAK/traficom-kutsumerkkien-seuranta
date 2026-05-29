import os
import mysql.connector
from mysql.connector import pooling

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "traficom"),
    "password": os.getenv("DB_PASSWORD", "changeme"),
    "database": os.getenv("DB_NAME", "traficom_tracker"),
}

_pool = pooling.MySQLConnectionPool(pool_name="traficom", pool_size=5, **DB_CONFIG)

def get_conn():
    return _pool.get_connection()

def init_db():
    conn = get_conn()
    cur  = conn.cursor()

    statements = [
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id         BIGINT AUTO_INCREMENT PRIMARY KEY,
            fetched_at DATETIME NOT NULL,
            callsign   VARCHAR(20) NOT NULL,
            status     VARCHAR(20) NOT NULL,
            INDEX idx_date (fetched_at),
            INDEX idx_call (callsign)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS daily_changes (
            id          BIGINT AUTO_INCREMENT PRIMARY KEY,
            change_date DATE NOT NULL,
            callsign    VARCHAR(20) NOT NULL,
            change_type ENUM('added','removed') NOT NULL,
            category    ENUM('new','renewal','genuine_remove','pending')
                        NOT NULL DEFAULT 'pending',
            INDEX idx_date     (change_date),
            INDEX idx_call     (callsign),
            INDEX idx_category (category)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS daily_stats (
            stat_date       DATE PRIMARY KEY,
            total           INT NOT NULL,
            added           INT NOT NULL DEFAULT 0,
            removed         INT NOT NULL DEFAULT 0,
            new_callsigns   INT NOT NULL DEFAULT 0,
            renewals        INT NOT NULL DEFAULT 0,
            genuine_removes INT NOT NULL DEFAULT 0,
            pending_removes INT NOT NULL DEFAULT 0
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ]

    for stmt in statements:
        cur.execute(stmt)

    # Migraatio vanhoille asennuksille – lisää sarakkeet jos puuttuu
    migrations = [
        "ALTER TABLE daily_changes ADD COLUMN IF NOT EXISTS category "
        "ENUM('new','renewal','genuine_remove','pending') NOT NULL DEFAULT 'pending'",

        "ALTER TABLE daily_changes ADD INDEX IF NOT EXISTS idx_category (category)",

        "ALTER TABLE daily_stats ADD COLUMN IF NOT EXISTS new_callsigns   INT NOT NULL DEFAULT 0",
        "ALTER TABLE daily_stats ADD COLUMN IF NOT EXISTS renewals         INT NOT NULL DEFAULT 0",
        "ALTER TABLE daily_stats ADD COLUMN IF NOT EXISTS genuine_removes  INT NOT NULL DEFAULT 0",
        "ALTER TABLE daily_stats ADD COLUMN IF NOT EXISTS pending_removes  INT NOT NULL DEFAULT 0",
    ]
    for stmt in migrations:
        try:
            cur.execute(stmt)
        except Exception:
            pass   # vanhempi MariaDB ei tue IF NOT EXISTS – ok

    conn.commit()
    cur.close()
    conn.close()
    print("Database initialised.")
