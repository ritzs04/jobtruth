"""SQLite database for users and saved analyses."""
import os
import sqlite3
from pathlib import Path
from datetime import datetime

# Allow containers to place SQLite on a writable data directory while keeping
# the repository-local default for development.
DB_PATH = Path(os.environ.get("JOBTRUTH_DB_PATH", str(Path(__file__).resolve().parent.parent / "jobtruth.db")))


def init_db():
    """Create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            trust_score INTEGER NOT NULL,
            label TEXT NOT NULL,
            flags TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS scam_reports (
            id INTEGER PRIMARY KEY,
            domain TEXT NOT NULL,
            company_name TEXT,
            reason TEXT,
            reported_by TEXT,
            created_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS company_cache (
            id INTEGER PRIMARY KEY,
            company_name TEXT UNIQUE NOT NULL,
            is_real INTEGER,
            website TEXT,
            founded_year INTEGER,
            cached_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS salary_data (
            id INTEGER PRIMARY KEY,
            role TEXT NOT NULL,
            location TEXT NOT NULL,
            experience_level TEXT NOT NULL,
            median_salary INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS comparisons (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            analyses_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def get_user_by_email(email: str):
    """Fetch user by email."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None


def create_user(email: str, password_hash: str):
    """Create a new user."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email, password_hash, datetime.utcnow().isoformat())
        )
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


def save_analysis(user_id: int, text: str, trust_score: int, label: str, flags: str):
    """Save an analysis for a user."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO analyses (user_id, text, trust_score, label, flags, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, text, trust_score, label, flags, datetime.utcnow().isoformat())
    )
    conn.commit()
    analysis_id = c.lastrowid
    conn.close()
    return analysis_id


def get_user_analyses(user_id: int, limit: int = 50):
    """Fetch all analyses for a user."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT id, text, trust_score, label, created_at FROM analyses WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    analyses = [dict(row) for row in c.fetchall()]
    conn.close()
    return analyses


def report_scam(domain: str, company_name: str, reason: str, reported_by: str = None):
    """Report a scam domain."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO scam_reports (domain, company_name, reason, reported_by, created_at) VALUES (?, ?, ?, ?, ?)",
        (domain.lower(), company_name, reason, reported_by, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_scam_count(domain: str) -> int:
    """Get number of times a domain has been reported."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM scam_reports WHERE domain = ?", (domain.lower(),))
    count = c.fetchone()[0]
    conn.close()
    return count


def get_top_scams(limit: int = 20):
    """Get most reported scam domains."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT domain, company_name, COUNT(*) as count FROM scam_reports GROUP BY domain ORDER BY count DESC LIMIT ?",
        (limit,)
    )
    scams = [dict(row) for row in c.fetchall()]
    conn.close()
    return scams


def cache_company(company_name: str, is_real: int, website: str = None, founded_year: int = None):
    """Cache company verification result."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO company_cache (company_name, is_real, website, founded_year, cached_at) VALUES (?, ?, ?, ?, ?)",
            (company_name, is_real, website, founded_year, datetime.utcnow().isoformat())
        )
        conn.commit()
    except sqlite3.IntegrityError:
        c.execute(
            "UPDATE company_cache SET is_real=?, website=?, founded_year=?, cached_at=? WHERE company_name=?",
            (is_real, website, founded_year, datetime.utcnow().isoformat(), company_name)
        )
        conn.commit()
    conn.close()


def get_cached_company(company_name: str):
    """Get cached company info."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM company_cache WHERE company_name = ?", (company_name,))
    result = c.fetchone()
    conn.close()
    return dict(result) if result else None


def cache_salary(role: str, location: str, experience_level: str, median_salary: int):
    """Cache salary data."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO salary_data (role, location, experience_level, median_salary, updated_at) VALUES (?, ?, ?, ?, ?)",
        (role.lower(), location.lower(), experience_level.lower(), median_salary, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_salary_benchmark(role: str, location: str, experience_level: str):
    """Get salary benchmark for role/location/experience."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT median_salary FROM salary_data WHERE role = ? AND location = ? AND experience_level = ?",
        (role.lower(), location.lower(), experience_level.lower())
    )
    result = c.fetchone()
    conn.close()
    return result["median_salary"] if result else None


init_db()


def save_comparison(user_id: int, name: str, analyses_json: str):
    """Save a comparison of multiple analyses."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO comparisons (user_id, name, analyses_json, created_at) VALUES (?, ?, ?, ?)",
        (user_id, name, analyses_json, datetime.utcnow().isoformat())
    )
    conn.commit()
    comparison_id = c.lastrowid
    conn.close()
    return comparison_id


def get_user_comparisons(user_id: int, limit: int = 20):
    """Get all comparisons for a user."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT id, name, created_at FROM comparisons WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    comparisons = [dict(row) for row in c.fetchall()]
    conn.close()
    return comparisons


def get_comparison(comparison_id: int):
    """Get a specific comparison."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM comparisons WHERE id = ?", (comparison_id,))
    result = c.fetchone()
    conn.close()
    return dict(result) if result else None
