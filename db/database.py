"""
db/database.py — GoGenie Database Layer
SQLite with optional Supabase upgrade path.
Tables: customers, bookings (schema per assignment spec).
"""

import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Optional

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config
from db.models import Customer, Booking


# ── Connection ────────────────────────────────────────────────────────────────
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.SQLITE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ── Init ──────────────────────────────────────────────────────────────────────
def init_db():
    """Create tables if they don't exist. Called once on app start."""
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            email       TEXT NOT NULL UNIQUE,
            phone       TEXT NOT NULL,
            created_at  TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id              TEXT PRIMARY KEY,
            customer_id     TEXT NOT NULL,
            booking_type    TEXT,
            from_city       TEXT,
            to_city         TEXT,
            date            TEXT,
            time            TEXT,
            selected_option TEXT,
            status          TEXT DEFAULT 'confirmed',
            created_at      TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)

    conn.commit()
    conn.close()


# ── Customer CRUD ─────────────────────────────────────────────────────────────
def upsert_customer(customer: Customer) -> str:
    """Insert customer; if email exists, return existing ID."""
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("SELECT customer_id FROM customers WHERE email = ?", (customer.email,))
    row = cur.fetchone()

    if row:
        customer_id = row["customer_id"]
    else:
        customer_id = "CX-" + str(uuid.uuid4())[:6].upper()
        cur.execute("""
            INSERT INTO customers (customer_id, name, email, phone, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (customer_id, customer.name, customer.email, customer.phone,
              datetime.now().isoformat()))
        conn.commit()

    conn.close()
    return customer_id


# ── Booking CRUD ──────────────────────────────────────────────────────────────
def insert_booking(booking: Booking) -> str:
    """Insert a confirmed booking; returns booking_id."""
    conn = get_connection()
    cur  = conn.cursor()

    booking_id = "GG-" + str(uuid.uuid4())[:6].upper()
    cur.execute("""
        INSERT INTO bookings
            (id, customer_id, booking_type, from_city, to_city,
             date, time, selected_option, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        booking_id, booking.customer_id, booking.booking_type,
        booking.from_city, booking.to_city, booking.date, booking.time,
        booking.selected_option, booking.status, datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()
    return booking_id


def get_all_bookings() -> List[Dict]:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT b.*, c.name, c.email, c.phone
        FROM   bookings b
        LEFT JOIN customers c ON b.customer_id = c.customer_id
        ORDER BY b.created_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_bookings_by_email(email: str) -> List[Dict]:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT b.*, c.name, c.email, c.phone
        FROM   bookings b
        LEFT JOIN customers c ON b.customer_id = c.customer_id
        WHERE  LOWER(c.email) = LOWER(?)
        ORDER BY b.created_at DESC
    """, (email,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_bookings(query: str) -> List[Dict]:
    conn = get_connection()
    cur  = conn.cursor()
    q    = f"%{query}%"
    cur.execute("""
        SELECT b.*, c.name, c.email, c.phone
        FROM   bookings b
        LEFT JOIN customers c ON b.customer_id = c.customer_id
        WHERE  c.name LIKE ? OR c.email LIKE ?
            OR b.date  LIKE ? OR b.id    LIKE ?
            OR b.from_city LIKE ? OR b.to_city LIKE ?
        ORDER BY b.created_at DESC
    """, (q, q, q, q, q, q))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_booking_status(booking_id: str, status: str):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))
    conn.commit()
    conn.close()


def delete_booking(booking_id: str):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
