from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = "banking-secret"
DB = "bank.db"

def db():
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    connection = db()
    connection.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT UNIQUE,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL,
            balance REAL DEFAULT 0
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT,
            type TEXT,
            amount REAL,
            description TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Demo account
    existing = connection.execute(
        "SELECT * FROM accounts WHERE account_number = ?",
        ("1001",)
    ).fetchone()

    if not existing:

        connection.execute("""
            INSERT INTO accounts
            (account_number, name, email, phone, password, balance)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "1001",
            "Atul",
            "atul@example.com",
            "9999999999",
            "1234",
            10000
        ))

    connection.commit()
    connection.close()

# HOME 
@app.route("/")
def home():

    if "account" in session:
        return redirect("/dashboard")

    return render_template("login.html")

# LOGIN 
@app.route("/login", methods=["POST"])
def login():
    account_number = request.form["account_number"]
    password = request.form["password"]

    connection = db()

    account = connection.execute("""
        SELECT *
        FROM accounts
        WHERE account_number = ?
        AND password = ?
    """, (
        account_number,
        password
    )).fetchone()

    connection.close()

    if not account:

        return render_template(
            "login.html",
            error="Invalid account number or password"
        )

    session["account"] = account_number

    return redirect("/dashboard")

# REGISTER 
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    account_number = request.form["account_number"]
    name = request.form["name"]
    email = request.form["email"]
    phone = request.form["phone"]
    password = request.form["password"]

    if not all([
        account_number,
        name,
        email,
        phone,
        password
    ]):

        return render_template(
            "register.html",
            error="Please fill all fields"
        )

    connection = db()

    try:

        connection.execute("""
            INSERT INTO accounts
            (account_number, name, email, phone, password)
            VALUES (?, ?, ?, ?, ?)
        """, (
            account_number,
            name,
            email,
            phone,
            password
        ))

        connection.commit()
        connection.close()

        return redirect("/")

    except sqlite3.IntegrityError:

        connection.close()

        return render_template(
            "register.html",
            error="Account number already exists"
        )

# DASHBOARD
@app.route("/dashboard")
def dashboard():

    if "account" not in session:
        return redirect("/")
    connection = db()

    account = connection.execute("""
        SELECT *
        FROM accounts
        WHERE account_number = ?
    """, (
        session["account"],
    )).fetchone()

    connection.close()
    return render_template(
        "dashboard.html",
        account=account
    )


# DEPOSIT
@app.route("/deposit", methods=["POST"])
def deposit():

    if "account" not in session:
        return jsonify({
            "message": "Please login first"
        })
    amount = float(request.form["amount"])
    if amount <= 0:

        return jsonify({
            "message": "Enter a valid amount"
        })

    account_number = session["account"]
    connection = db()
    connection.execute("""
        UPDATE accounts
        SET balance = balance + ?
        WHERE account_number = ?
    """, (
        amount,
        account_number
    ))
    connection.execute("""
        INSERT INTO transactions
        (account_number, type, amount, description)
        VALUES (?, ?, ?, ?)
    """, (
        account_number,
        "Deposit",
        amount,
        "Money deposited"
    ))

    connection.commit()
    connection.close()

    return jsonify({
        "message": "Deposit successful"
    })

# WITHDRAW
@app.route("/withdraw", methods=["POST"])
def withdraw():

    if "account" not in session:
        return jsonify({
            "message": "Please login first"
        })

    amount = float(request.form["amount"])

    account_number = session["account"]

    connection = db()

    account = connection.execute("""
        SELECT balance
        FROM accounts
        WHERE account_number = ?
    """, (
        account_number,
    )).fetchone()

    if amount <= 0:

        connection.close()

        return jsonify({
            "message": "Enter a valid amount"
        })

    if amount > account["balance"]:

        connection.close()

        return jsonify({
            "message": "Insufficient balance"
        })

    connection.execute("""
        UPDATE accounts
        SET balance = balance - ?
        WHERE account_number = ?
    """, (
        amount,
        account_number
    ))

    connection.execute("""
        INSERT INTO transactions
        (account_number, type, amount, description)
        VALUES (?, ?, ?, ?)
    """, (
        account_number,
        "Withdrawal",
        amount,
        "Money withdrawn"
    ))

    connection.commit()
    connection.close()

    return jsonify({
        "message": "Withdrawal successful"
    })


# TRANSFER
@app.route("/transfer", methods=["POST"])
def transfer():
    if "account" not in session:
        return jsonify({
            "message": "Please login first"
        })
    receiver = request.form["receiver"]
    amount = float(request.form["amount"])

    sender = session["account"]

    if sender == receiver:

        return jsonify({
            "message": "Cannot transfer to yourself"
        })

    if amount <= 0:

        return jsonify({
            "message": "Enter a valid amount"
        })
    connection = db()
    sender_account = connection.execute("""
        SELECT balance
        FROM accounts
        WHERE account_number = ?
    """, (
        sender,
    )).fetchone()

    receiver_account = connection.execute("""
        SELECT *
        FROM accounts
        WHERE account_number = ?
    """, (
        receiver,
    )).fetchone()

    if not receiver_account:

        connection.close()

        return jsonify({
            "message": "Receiver account not found"
        })

    if amount > sender_account["balance"]:

        connection.close()

        return jsonify({
            "message": "Insufficient balance"
        })

    connection.execute("""
        UPDATE accounts
        SET balance = balance - ?
        WHERE account_number = ?
    """, (
        amount,
        sender
    ))

    connection.execute("""
        UPDATE accounts
        SET balance = balance + ?
        WHERE account_number = ?
    """, (
        amount,
        receiver
    ))

    connection.execute("""
        INSERT INTO transactions
        (account_number, type, amount, description)
        VALUES (?, ?, ?, ?)
    """, (
        sender,
        "Transfer",
        amount,
        "Transferred to " + receiver
    ))

    connection.execute("""
        INSERT INTO transactions
        (account_number, type, amount, description)
        VALUES (?, ?, ?, ?)
    """, (
        receiver,
        "Received",
        amount,
        "Received from " + sender
    ))

    connection.commit()
    connection.close()

    return jsonify({
        "message": "Transfer successful"
    })

# TRANSACTIONS
@app.route("/transactions")
def transactions():

    if "account" not in session:
        return jsonify([])

    connection = db()

    data = connection.execute("""
        SELECT *
        FROM transactions
        WHERE account_number = ?
        ORDER BY id DESC
    """, (
        session["account"],
    )).fetchall()

    connection.close()

    return jsonify([
        dict(row)
        for row in data
    ])


# PROFILE 
@app.route("/profile", methods=["POST"])
def profile():
    if "account" not in session:
        return jsonify({
            "message": "Please login first"
        })

    name = request.form["name"]
    email = request.form["email"]
    phone = request.form["phone"]

    connection = db()

    connection.execute("""
        UPDATE accounts
        SET name = ?,
            email = ?,
            phone = ?
        WHERE account_number = ?
    """, (
        name,
        email,
        phone,
        session["account"]
    ))

    connection.commit()
    connection.close()

    return jsonify({
        "message": "Profile updated successfully"
    })


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


#  START
if __name__ == "__main__":
    init_db()
    app.run(
        host="0.0.0.0",
        port=5000
    )
