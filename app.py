from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import uuid
import random, string
from datetime import datetime, timedelta


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "cargo_secret_key")

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "3125",
    "database": "cargo_db",
    "port": 5650  
}


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


# ---------- AUTH DECORATORS ----------
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please login first.", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("Access denied.", "danger")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


# ---------- UTILITIES ----------
def generate_tracking_id():
    return str(uuid.uuid4()).split("-")[0].upper()


# ---------- ROUTES ----------
@app.route("/")
def index():
    return render_template("index.html")


# ---------- AUTH ----------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        fullname = request.form.get("fullname")
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role", "customer")  # default role

        if not all([fullname, username, email, password]):
            flash("Please fill all required fields", "warning")
            return redirect(url_for("signup"))

        hashed_pw = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Check if username or email already exists
            cursor.execute("SELECT * FROM users WHERE username=%s OR email=%s", (username, email))
            existing = cursor.fetchone()
            if existing:
                if existing["username"] == username:
                    flash("Username already exists.", "danger")
                elif existing["email"] == email:
                    flash("Email already registered.", "danger")
                return redirect(url_for("signup"))

            # Insert into users table
            cursor.execute(
                """
                INSERT INTO users (full_name, username, email, password_hash, role, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (fullname, username, email, hashed_pw, role, "active")
            )
            user_id = cursor.lastrowid

            # Optional: insert into role-specific tables
            if role == "customer":
                cursor.execute("INSERT INTO customers (user_id) VALUES (%s)", (user_id,))
            elif role == "employee":
                cursor.execute("INSERT INTO employees (user_id) VALUES (%s)", (user_id,))

            conn.commit()
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))

        except Error as e:
            conn.rollback()
            flash(f"Error: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("userType")  # dropdown in login.html

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Check username + role
            cursor.execute("SELECT * FROM users WHERE username=%s AND role=%s", (username, role))
            user = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["user_id"]  # FIXED (your table uses user_id, not id)
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash("Logged in successfully", "success")

            # Redirect based on role
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user["role"] == "employee":
                return redirect(url_for("employee_dashboard"))
            else:
                return redirect(url_for("customer_dashboard"))
        else:
            flash("Invalid credentials or role", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))



# ---------- CUSTOMER ----------
@app.route("/customer/dashboard")
@login_required(role="customer")
def customer_dashboard():
    user_id = session.get("user_id")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
    SELECT cb.* 
    FROM cargo_bookings cb
    JOIN customers c ON cb.customer_id = c.customer_id
    WHERE c.user_id = %s
    ORDER BY cb.booking_date DESC
""", (user_id,))
    shipments = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("customer_dashboard.html", shipments=shipments)


def generate_tracking_id():
    return "TRK" + ''.join(random.choices(string.digits, k=8))

@app.route("/customer/book_cargo", methods=["GET", "POST"])
@login_required(role="customer")
def customer_book_cargo():
    if request.method == "POST":
        sender_name = request.form.get("sender_name")
        sender_address = request.form.get("sender_address")
        sender_phone = request.form.get("sender_phone")
        recipient_name = request.form.get("recipient_name")
        recipient_address = request.form.get("recipient_address")
        recipient_phone = request.form.get("recipient_phone")
        cargo_description = request.form.get("cargo_description")
        weight = request.form.get("weight")
        cargo_value = request.form.get("cargo_value")

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 1. Get customer_id from logged in user
            cursor.execute("SELECT customer_id FROM customers WHERE user_id=%s", (session.get("user_id"),))
            result = cursor.fetchone()
            if not result:
                flash("Customer profile not found!", "danger")
                return redirect(url_for("customer_dashboard"))
            customer_id = result[0]

            # 2. Generate tracking ID
            tracking_id = generate_tracking_id()

            # 3. Insert cargo booking
            cursor.execute("""
                INSERT INTO cargo_bookings 
                (tracking_id, customer_id, sender_name, sender_address, sender_phone, 
                 recipient_name, recipient_address, recipient_phone, cargo_description, 
                 weight, cargo_value, total_amount, status, expected_delivery_date)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                tracking_id, customer_id, sender_name, sender_address, sender_phone,
                recipient_name, recipient_address, recipient_phone, cargo_description,
                weight, cargo_value, cargo_value, "pending", datetime.now().date() + timedelta(days=5)
            ))

            booking_id = cursor.lastrowid

            # 4. Insert initial tracking update
            cursor.execute("""
                INSERT INTO tracking_updates (booking_id, status, location, notes) 
                VALUES (%s, %s, %s, %s)
            """, (booking_id, "pending", "Shipment Booked", "Shipment created by customer"))

            conn.commit()
            flash(f"Cargo booked successfully! Tracking ID: {tracking_id}", "success")
            return redirect(url_for("customer_dashboard"))

        except Exception as e:
            conn.rollback()
            flash(f"Error booking cargo: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template("customer_book_cargo.html")


@app.route("/customer/view_invoices")
@login_required(role="customer")
def customer_view_invoices():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Pull recipient details instead of non-existent destination_city
    cursor.execute("""
        SELECT i.*, 
               c.recipient_name, 
               c.recipient_address, 
               c.recipient_phone
        FROM invoices i
        JOIN cargo_bookings c ON i.booking_id = c.booking_id
        WHERE c.customer_id = (
            SELECT customer_id 
            FROM customers 
            WHERE user_id = %s
        )
        ORDER BY i.issue_date DESC
    """, (session.get("user_id"),))

    invoices = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("customer_view_invoices.html", invoices=invoices)


@app.route("/customer/support", methods=["GET", "POST"])
@login_required(role="customer")
def customer_support():
    if request.method == "POST":
        subject = request.form.get("subject")
        description = request.form.get("description")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Get customer_id from customers table using logged-in user's id
            cursor.execute("SELECT id FROM customers WHERE user_id=%s", (session.get("user_id"),))
            customer_row = cursor.fetchone()
            if customer_row:
                customer_id = customer_row[0]
                cursor.execute("""INSERT INTO support_tickets (ticket_number, customer_id, subject, description, status, category) VALUES (%s,%s,%s,%s,%s,%s)""", ("TKT"+str(uuid.uuid4())[:6], customer_id, subject, description, "open", "general_inquiry"))
                conn.commit()
                flash("Support ticket created", "success")
            else:
                flash("Customer not found.", "danger")
        except Error as e:
            conn.rollback()
            flash(f"Error creating ticket: {e}", "danger")
        finally:
            cursor.close()
            conn.close()
    return render_template("customer_support.html")


@app.route("/customer/profile")
@login_required(role="customer")
def customer_profile():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.*, c.* 
        FROM users u 
        LEFT JOIN customers c ON u.user_id = c.customer_id 
        WHERE u.user_id = %s
    """, (session.get("user_id"),))
    profile = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("customer_profile.html", profile=profile)

@app.route("/customer/change_password", methods=["POST"])
@login_required(role="customer")
def change_password():
    user_id = session.get("user_id")
    current_password = request.form.get("current-password")
    new_password = request.form.get("new-password")
    confirm_password = request.form.get("confirm-password")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch user with hashed password
    cursor.execute("SELECT password_hash FROM users WHERE user_id=%s", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        flash("User not found!", "error")
        return redirect(url_for("customer_profile"))

    # Check current password
    if not check_password_hash(user["password_hash"], current_password):
        cursor.close()
        conn.close()
        flash("Current password is incorrect", "error")
        return redirect(url_for("customer_profile"))

    # Match new passwords
    if new_password != confirm_password:
        flash("New passwords do not match", "error")
        return redirect(url_for("customer_profile"))

    # Hash and update new password
    new_hash = generate_password_hash(new_password)
    cursor.execute("UPDATE users SET password_hash=%s WHERE user_id=%s", (new_hash, user_id))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Password updated successfully!", "success")
    return redirect(url_for("customer_profile"))

# ---------- EMPLOYEE ----------
@app.route("/employee/dashboard")
@login_required(role="employee")
def employee_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cargo_bookings ORDER BY booking_date DESC LIMIT 50")
    bookings = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("employee_dashboard.html", bookings=bookings)


@app.route("/employee/update_status/<int:booking_id>", methods=["GET", "POST"])
@login_required(role="employee")
def employee_update_status(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == "POST":
        status = request.form.get("status")
        location = request.form.get("location")
        cursor.execute("UPDATE cargo_bookings SET status=%s WHERE id=%s", (status, booking_id))
        cursor.execute("INSERT INTO tracking_updates (booking_id, location, status) VALUES (%s,%s,%s)", (booking_id, location, status))
        conn.commit()
        flash("Status updated", "success")
        return redirect(url_for("employee_dashboard"))

    cursor.execute("SELECT * FROM cargo_bookings WHERE id=%s", (booking_id,))
    booking = cursor.fetchone()
    cursor.execute("SELECT * FROM tracking_updates WHERE booking_id=%s ORDER BY updated_timestamp DESC", (booking_id,))
    updates = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("employee_update_status.html", booking=booking, updates=updates)


# ---------- ADMIN ----------
@app.route("/admin/dashboard")
@login_required(role="admin")
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Stats
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='customer'")
    customers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='employee'")
    employees = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cargo_bookings")
    bookings = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return render_template(
        "admin_dashboard.html",
        customers=customers,
        employees=employees,
        bookings=bookings
    )

# Manage Customers
@app.route("/admin/manage_customers")
@login_required(role="admin")
def admin_manage_customers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.*, c.phone, c.address 
        FROM users u 
        LEFT JOIN customers c ON u.id=c.user_id 
        WHERE u.role='customer'
    """)
    customers = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin_manage_customers.html", customers=customers)

@app.route("/admin/customers/<int:id>/edit", methods=["GET", "POST"])
@login_required(role="admin")
def edit_customer(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == "POST":
        fullname = request.form.get("fullname")
        email = request.form.get("email")
        status = request.form.get("status")
        cursor.execute(
            "UPDATE users SET fullname=%s, email=%s, status=%s WHERE id=%s",
            (fullname, email, status, id)
        )
        conn.commit()
        flash("Customer updated successfully!", "success")
        return redirect(url_for("admin_manage_customers"))
    cursor.execute("SELECT * FROM users WHERE id=%s", (id,))
    customer = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("edit_customer.html", customer=customer)

@app.route("/admin/customers/<int:id>/view")
@login_required(role="admin")
def view_customer(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id=%s", (id,))
    customer = cursor.fetchone()
    cursor.close()
    conn.close()

    if not customer:
        flash("Customer not found", "warning")
        return redirect(url_for("admin_manage_customers"))

    return render_template("view_customer.html", customer=customer)

@app.route("/admin/customers/<int:id>/activate")
@login_required(role="admin")
def activate_customer(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status='Active' WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Customer activated", "success")
    return redirect(url_for("admin_manage_customers"))


@app.route("/admin/customers/<int:id>/suspend")
@login_required(role="admin")
def suspend_customer(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status='Suspended' WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Customer suspended", "info")
    return redirect(url_for("admin_manage_customers"))



# Manage Employees
@app.route("/admin/manage_employees")
@login_required(role="admin")
def admin_manage_employees():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.*, e.department, e.designation 
        FROM users u 
        LEFT JOIN employees e ON u.id=e.user_id 
        WHERE u.role='employee'
    """)
    employees = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin_manage_employees.html", employees=employees)

# Manage Cargo (was bookings)
@app.route("/admin/manage_cargo")
@login_required(role="admin")
def admin_manage_cargo():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT b.*, u.username 
        FROM cargo_bookings b 
        LEFT JOIN users u ON b.user_id=u.id 
        ORDER BY b.booking_date DESC
    """)
    bookings = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin_manage_cargo.html", bookings=bookings)

# Create Invoice
@app.route("/admin/create_invoice/<int:booking_id>", methods=["POST"])
@login_required(role="admin")
def admin_create_invoice(booking_id):
    amount = request.form.get("amount")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Get customer_id from cargo_bookings table
        cursor.execute("SELECT user_id FROM cargo_bookings WHERE id=%s", (booking_id,))
        result = cursor.fetchone()
        if not result:
            flash("Booking not found.", "danger")
            return redirect(url_for("admin_manage_cargo"))
        customer_id = result[0]

        cursor.execute("""
            INSERT INTO invoices (invoice_number, booking_id, customer_id, subtotal, tax_amount, total_amount, payment_status)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, ("INV"+str(uuid.uuid4())[:6], booking_id, customer_id, float(amount), float(amount)*0.18, float(amount)*1.18, "unpaid"))

        conn.commit()
        flash("Invoice created", "success")
    except Error as e:
        conn.rollback()
        flash(f"Error creating invoice: {e}", "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("admin_manage_cargo"))

# Track Shipments
@app.route("/admin/track_shipments", methods=["GET", "POST"])
@login_required(role="admin")
def admin_track_shipments():
    tracking_info = None
    if request.method == "POST":
        booking_id = request.form.get("booking_id")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM tracking_updates WHERE booking_id=%s ORDER BY updated_timestamp DESC",
            (booking_id,)
        )
        tracking_info = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template("admin_track_shipments.html", tracking_info=tracking_info)

# Generate Reports
@app.route("/admin/generate_reports")
@login_required(role="admin")
def admin_generate_reports():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT b.id, b.sender_name, b.recipient_name, b.origin_city, b.destination_city, 
               b.status, b.booking_date, u.username 
        FROM cargo_bookings b 
        LEFT JOIN users u ON b.user_id=u.id 
        ORDER BY b.booking_date DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # CSV response
    lines = ["id,sender,recipient,origin,destination,status,booking_date,username"]
    for r in rows:
        lines.append(",".join([
            str(r["id"]),
            r["sender_name"] or "",
            r["recipient_name"] or "",
            r["origin_city"] or "",
            r["destination_city"] or "",
            r["status"] or "",
            str(r["booking_date"]),
            r["username"] or ""
        ]))

    resp = "\n".join(lines)
    return (resp, 200, {
        "Content-Type": "text/csv",
        "Content-Disposition": "attachment; filename=bookings_report.csv"
    })


# ---------- START ----------
if __name__ == "__main__":
     app.run(debug=True, host="0.0.0.0", port=5000)