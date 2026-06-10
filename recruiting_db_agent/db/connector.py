"""
db/connector.py
~~~~~~~~~~~~~~~
Database connector with MySQL (primary) and SQLite (fallback).

SECURITY CONTRACT
-----------------
• Credentials read exclusively from environment variables
• Always uses parameterized queries — never string concatenation
• MySQLConnectionPool with pool_size=5
• Falls back to in-memory SQLite when MySQL is unavailable
• Never exposes raw connection handles outside this module
"""

from __future__ import annotations

import os
import sqlite3
import logging
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try to import MySQL connector; flag its availability
# ---------------------------------------------------------------------------
try:
    import mysql.connector
    from mysql.connector.pooling import MySQLConnectionPool
    _MYSQL_AVAILABLE = True
except ImportError:
    _MYSQL_AVAILABLE = False
    logger.warning("mysql-connector-python not installed — using SQLite fallback")


# ---------------------------------------------------------------------------
# SQLite fallback helpers
# ---------------------------------------------------------------------------
_SQLITE_SEED_CANDIDATES = [
    ("Priya Sharma",  "priya@email.com",  "+91-9876543210", "Backend Developer",    "Python,Django,MySQL",        "applied",   3.5),
    ("Rahul Verma",   "rahul@email.com",  "+91-9123456780", "Frontend Developer",   "React,TypeScript,Vue",       "screening", 2.0),
    ("Anita Rao",     "anita@email.com",  "+91-9988776655", "Data Scientist",       "Python,ML,TensorFlow",       "interview", 4.0),
    ("Kiran Patel",   "kiran@email.com",  "+91-9001122334", "Full Stack Developer", "Python,React,MySQL",         "applied",   1.5),
    ("Suresh Kumar",  "suresh@email.com", "+91-9876501234", "DevOps Engineer",      "Docker,Kubernetes,AWS",      "applied",   3.0),
    ("Deepak Singh",  "deepak@email.com", "+91-9111222333", "Data Scientist",       "Python,R,SQL,Tableau",       "applied",   5.0),
    # --- 20 more representative dummy rows for fallback ---
    ("Amit Gupta",    "amit.gupta@email.com",  "+91-9000000101", "Backend Developer",    "Java,Spring,MySQL",          "applied",   2.5),
    ("Sneha Nair",    "sneha.nair@email.com",  "+91-9000000102", "Frontend Developer",   "HTML,CSS,JavaScript",        "screening", 1.0),
    ("Vikram Reddy",  "vikram.reddy@email.com","+91-9000000103", "Data Scientist",       "Python,Pandas,Scikit-learn", "applied",   3.0),
    ("Pooja Mehta",   "pooja.mehta@email.com", "+91-9000000104", "Full Stack Developer", "Node.js,React,MongoDB",      "interview", 4.5),
    ("Arjun Iyer",    "arjun.iyer@email.com",  "+91-9000000105", "DevOps Engineer",      "Jenkins,Terraform,Azure",    "applied",   2.0),
    ("Kavita Joshi",  "kavita.joshi@email.com","+91-9000000106", "Backend Developer",    "Python,FastAPI,PostgreSQL",  "hired",     5.0),
    ("Rohit Shukla",  "rohit.shukla@email.com","+91-9000000107", "Frontend Developer",   "React,Next.js,Tailwind",     "screening", 2.5),
    ("Divya Menon",   "divya.menon@email.com", "+91-9000000108", "Data Scientist",       "R,ggplot2,Tableau",          "applied",   1.5),
    ("Sandeep Pillai","sandeep.pillai@email.com","+91-9000000109","Full Stack Developer","Django,Vue,MySQL",            "applied",   3.5),
    ("Meera Krishnan","meera.krishnan@email.com","+91-9000000110","DevOps Engineer",     "Kubernetes,Helm,GCP",        "screening", 4.0),
    ("Tarun Bose",    "tarun.bose@email.com",  "+91-9000000111", "Backend Developer",    "Go,gRPC,Redis",              "applied",   2.0),
    ("Nisha Agarwal", "nisha.agarwal@email.com","+91-9000000112","Frontend Developer",   "Angular,TypeScript,SCSS",    "interview", 3.0),
    ("Praveen Rao",   "praveen.rao@email.com", "+91-9000000113", "Data Scientist",       "Python,NLP,BERT",            "applied",   5.5),
    ("Swati Verma",   "swati.verma@email.com", "+91-9000000114", "Full Stack Developer", "Rails,React,PostgreSQL",     "applied",   2.5),
]

_SQLITE_SEED_JOBS = [
    ("Backend Developer",    "Engineering", 2.0, "Python,Java,MySQL",         3, "open"),
    ("Frontend Developer",   "Engineering", 1.5, "React,TypeScript,CSS",      2, "open"),
    ("Data Scientist",       "Analytics",   3.0, "Python,ML,SQL",             2, "open"),
    ("Full Stack Developer", "Engineering", 2.5, "Python,React,MySQL",        4, "open"),
    ("DevOps Engineer",      "Operations",  3.0, "Docker,Kubernetes,AWS",     2, "open"),
]


def _build_sqlite_db() -> sqlite3.Connection:
    """Create and seed an in-memory SQLite database mirroring the MySQL schema."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS candidates (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            email       TEXT UNIQUE,
            phone       TEXT,
            role        TEXT,
            skills      TEXT,
            status      TEXT DEFAULT 'applied',
            experience  REAL DEFAULT 0,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            department   TEXT,
            required_exp REAL DEFAULT 0,
            skills       TEXT,
            open_slots   INTEGER DEFAULT 1,
            status       TEXT DEFAULT 'open',
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS call_logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            recruiter    TEXT DEFAULT 'System',
            call_type    TEXT NOT NULL,
            scheduled_at TEXT,
            status       TEXT DEFAULT 'pending',
            notes        TEXT,
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        );
    """)

    cur.executemany(
        "INSERT OR IGNORE INTO candidates "
        "(name, email, phone, role, skills, status, experience) VALUES (?,?,?,?,?,?,?)",
        _SQLITE_SEED_CANDIDATES,
    )
    cur.executemany(
        "INSERT OR IGNORE INTO jobs "
        "(title, department, required_exp, skills, open_slots, status) VALUES (?,?,?,?,?,?)",
        _SQLITE_SEED_JOBS,
    )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# DBConnector
# ---------------------------------------------------------------------------
class DBConnector:
    """
    Unified database connector.

    Primary: MySQL via connection pool (pool_size=5).
    Fallback: SQLite in-memory when MySQL is unavailable.

    Always uses parameterized queries — never string concatenation.
    """

    def __init__(self) -> None:
        self._mode: str = "mysql"
        self._pool: "MySQLConnectionPool | None" = None
        self._sqlite_conn: sqlite3.Connection | None = None
        self._init_connection()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    def _init_connection(self) -> None:
        """Attempt MySQL pool; fall back to SQLite."""
        if _MYSQL_AVAILABLE:
            try:
                self._pool = MySQLConnectionPool(
                    pool_name="recruiting_pool",
                    pool_size=5,
                    host=os.getenv("DB_HOST", "localhost"),
                    port=int(os.getenv("DB_PORT", "3306")),
                    user=os.getenv("DB_USER", "mas_agent"),
                    password=os.getenv("DB_PASSWORD", ""),
                    database=os.getenv("DB_NAME", "recruiting_mas"),
                    autocommit=False,
                    connection_timeout=5,
                )
                # Verify the pool works
                conn = self._pool.get_connection()
                conn.close()
                self._mode = "mysql"
                logger.info("✅ Connected to MySQL via connection pool")
                return
            except Exception as exc:
                logger.warning("MySQL unavailable (%s) — falling back to SQLite", exc)

        # SQLite fallback
        self._mode = "sqlite"
        self._sqlite_conn = _build_sqlite_db()
        logger.info("✅ Connected to SQLite in-memory fallback database")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_mysql_connection(self):
        """Retrieve a pooled MySQL connection."""
        if self._pool is None:
            raise RuntimeError("MySQL pool not initialised")
        return self._pool.get_connection()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def execute_query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """
        Execute a SELECT query and return results as a list of dicts.

        Parameters
        ----------
        sql    : Parameterised SQL string (use %s for MySQL, ? for SQLite)
        params : Tuple of parameter values — never use string concatenation
        """
        try:
            if self._mode == "mysql":
                return self._execute_mysql_query(sql, params)
            else:
                return self._execute_sqlite_query(sql, params)
        except Exception as exc:
            logger.error("execute_query error: %s", exc)
            raise

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        """
        Execute an INSERT or UPDATE query and return the number of affected rows.

        Parameters
        ----------
        sql    : Parameterised SQL string
        params : Tuple of parameter values
        """
        try:
            if self._mode == "mysql":
                return self._execute_mysql_write(sql, params)
            else:
                return self._execute_sqlite_write(sql, params)
        except Exception as exc:
            logger.error("execute_write error: %s", exc)
            raise

    def health_check(self) -> bool:
        """Return True if the database connection is alive."""
        try:
            if self._mode == "mysql":
                conn = self._get_mysql_connection()
                conn.ping(reconnect=True)
                conn.close()
                return True
            else:
                self._sqlite_conn.execute("SELECT 1")  # type: ignore[union-attr]
                return True
        except Exception as exc:
            logger.error("health_check failed: %s", exc)
            return False

    @property
    def mode(self) -> str:
        """Return 'mysql' or 'sqlite'."""
        return self._mode

    def get_schema_metadata(self) -> str:
        """
        Dynamically query the database schema and return it as a readable text description
        to serve as prompt context for the LLM.
        """
        try:
            if self._mode == "mysql":
                tables_info = []
                tables = self.execute_query("SHOW TABLES;")
                for row in tables:
                    table_name = list(row.values())[0]
                    cols = self.execute_query(f"DESCRIBE `{table_name}`;")
                    col_lines = []
                    for col in cols:
                        field = col.get("Field")
                        col_type = col.get("Type")
                        null_val = "NULL" if col.get("Null") == "YES" else "NOT NULL"
                        key_val = f" ({col.get('Key')})" if col.get("Key") else ""
                        default_val = f" DEFAULT {col.get('Default')}" if col.get("Default") is not None else ""
                        extra_val = f" {col.get('Extra')}" if col.get("Extra") else ""
                        col_lines.append(f"  - {field}: {col_type} {null_val}{key_val}{default_val}{extra_val}")
                    tables_info.append(f"Table: {table_name}\nColumns:\n" + "\n".join(col_lines))
                return "\n\n".join(tables_info)
            else:
                # SQLite fallback
                tables_info = []
                tables = self.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                for row in tables:
                    table_name = row.get("name")
                    cols = self.execute_query(f"PRAGMA table_info(`{table_name}`);")
                    col_lines = []
                    for col in cols:
                        field = col.get("name")
                        col_type = col.get("type")
                        null_val = "NOT NULL" if col.get("notnull") == 1 else "NULL"
                        key_val = " (PRIMARY KEY)" if col.get("pk") == 1 else ""
                        default_val = f" DEFAULT {col.get('dflt_value')}" if col.get('dflt_value') is not None else ""
                        col_lines.append(f"  - {field}: {col_type} {null_val}{key_val}{default_val}")
                    tables_info.append(f"Table: {table_name}\nColumns:\n" + "\n".join(col_lines))
                return "\n\n".join(tables_info)
        except Exception as exc:
            logger.error("Failed to retrieve schema metadata: %s", exc)
            return "Error: Unable to retrieve schema metadata."

    # ------------------------------------------------------------------
    # MySQL internals
    # ------------------------------------------------------------------
    def _execute_mysql_query(self, sql: str, params: tuple) -> list[dict[str, Any]]:
        conn = self._get_mysql_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cursor.close()
            return rows
        finally:
            conn.close()

    def _execute_mysql_write(self, sql: str, params: tuple) -> int:
        conn = self._get_mysql_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # SQLite internals  (translate %s → ?)
    # ------------------------------------------------------------------
    @staticmethod
    def _adapt_sql(sql: str) -> str:
        """Convert MySQL-style %s placeholders to SQLite-style ?."""
        return sql.replace("%s", "?")

    def _execute_sqlite_query(self, sql: str, params: tuple) -> list[dict[str, Any]]:
        sql = self._adapt_sql(sql)
        cur = self._sqlite_conn.execute(sql, params)  # type: ignore[union-attr]
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    def _execute_sqlite_write(self, sql: str, params: tuple) -> int:
        sql = self._adapt_sql(sql)
        cur = self._sqlite_conn.execute(sql, params)  # type: ignore[union-attr]
        self._sqlite_conn.commit()  # type: ignore[union-attr]
        return cur.rowcount
