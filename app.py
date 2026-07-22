"""
Irae — a clothing brand storefront
Flask + plain sqlite3 (Python's built-in database module). No ORM needed.

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""

import sqlite3
import random
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, g

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-change-this-before-going-live"
DATABASE = "store.db"


# ---------------------------------------------------------------------------
# DATABASE HELPERS
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS product (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT NOT NULL,
            price INTEGER NOT NULL,
            mrp INTEGER NOT NULL,
            description TEXT NOT NULL,
            image TEXT NOT NULL,
            sizes TEXT NOT NULL,
            rating REAL DEFAULT 4.2
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS "order" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_ref TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            pincode TEXT NOT NULL,
            items_json TEXT NOT NULL,
            total INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM product").fetchone()[0]
    if count == 0:
        items = [
            ("KHATTI KAIRI Co-ord set", "Women", "Sets", 1499, 1499,
             "Elegant co-ord set with pinteresty vibes.",
             "/static/images/GREEN1.jpeg", "S,M,L,XL,XXL"),
            ("Cotton T-Shirt", "Men", "Shirts", 599, 599,
             "Crisp cotton shirt with a tailored slim fit, mother-of-pearl buttons, and a spread collar.",
             "/static/images/MEN1.jpeg", "S,M,L,XL"),
            ("BLACK SWAN Off shoulder dress", "Women", "Dresses", 1499, 1499,
             "Off-shoulder long dress in a bold black print, corset finsih, and flattering fit.",
             "/static/images/BLACK2.jpeg", "S,M,L,XL"),
            ("NURA cherry red dress", "Women", "Dresses", 1499, 1499,
             "Stunning cherry red dress with a fitted bodice and perfect fit.",
             "/static/images/red1.jpeg", "S,M,L,XL"),
        ]

        
        
        conn.executemany(
            "INSERT INTO product (name, category, subcategory, price, mrp, description, image, sizes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            items,
        )
        conn.commit()
    conn.close()


def discount_pct(row):
    if row["mrp"] <= row["price"]:
        return 0
    return round((row["mrp"] - row["price"]) / row["mrp"] * 100)


# ---------------------------------------------------------------------------
# CART HELPERS  (cart lives in session as {"product_id::size": qty})
# ---------------------------------------------------------------------------

def get_cart():
    return session.setdefault("cart", {})


def cart_details():
    db = get_db()
    cart = get_cart()
    details = []
    total = 0
    for key, qty in cart.items():
        pid, size = key.split("::")
        product = db.execute("SELECT * FROM product WHERE id = ?", (pid,)).fetchone()
        if not product:
            continue
        line_total = product["price"] * qty
        total += line_total
        details.append({"product": product, "size": size, "qty": qty, "line_total": line_total,
                         "discount_pct": discount_pct(product)})
    return details, total


@app.context_processor
def inject_cart_count():
    cart = session.get("cart", {})
    return {"cart_count": sum(cart.values())}


app.jinja_env.globals["discount_pct"] = discount_pct


# ---------------------------------------------------------------------------
# ROUTES — PAGES
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    db = get_db()
    featured = db.execute("SELECT * FROM product ORDER BY id DESC LIMIT 8").fetchall()
    return render_template("index.html", featured=featured)


@app.route("/catalog")
def catalog():
    db = get_db()
    category = request.args.get("category", "All")
    sub = request.args.get("sub", "All")
    sort = request.args.get("sort", "")
    q = request.args.get("q", "").strip()

    sql = "SELECT * FROM product WHERE 1=1"
    params = []
    if category != "All":
        sql += " AND category = ?"
        params.append(category)
    if sub != "All":
        sql += " AND subcategory = ?"
        params.append(sub)
    if q:
        sql += " AND name LIKE ?"
        params.append(f"%{q}%")

    if sort == "price_low":
        sql += " ORDER BY price ASC"
    elif sort == "price_high":
        sql += " ORDER BY price DESC"
    elif sort == "rating":
        sql += " ORDER BY rating DESC"

    products = db.execute(sql, params).fetchall()
    categories = ["All", "Men", "Women", "Unisex"]
    all_subs = db.execute("SELECT DISTINCT subcategory FROM product ORDER BY subcategory").fetchall()
    subcats = ["All"] + [r["subcategory"] for r in all_subs]
    return render_template("catalog.html", products=products, categories=categories,
                            subcats=subcats, current_category=category, current_sub=sub,
                            current_sort=sort, q=q)


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM product WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        return render_template("404.html"), 404
    related = db.execute(
        "SELECT * FROM product WHERE category = ? AND id != ? LIMIT 4",
        (product["category"], product_id),
    ).fetchall()
    return render_template("product.html", product=product, related=related)


@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM product WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        flash("That product no longer exists.", "error")
        return redirect(url_for("catalog"))
    size = request.form.get("size", product["sizes"].split(",")[0])
    qty = max(1, int(request.form.get("qty", 1)))
    cart = get_cart()
    key = f"{product_id}::{size}"
    cart[key] = cart.get(key, 0) + qty
    session.modified = True
    flash(f"Added {product['name']} ({size}) to your bag.", "success")
    return redirect(request.referrer or url_for("catalog"))


@app.route("/update-cart", methods=["POST"])
def update_cart():
    key = request.form["key"]
    action = request.form["action"]
    cart = get_cart()
    if key in cart:
        if action == "increase":
            cart[key] += 1
        elif action == "decrease":
            cart[key] -= 1
            if cart[key] <= 0:
                del cart[key]
        elif action == "remove":
            del cart[key]
    session.modified = True
    return redirect(url_for("cart_page"))


@app.route("/cart")
def cart_page():
    details, total = cart_details()
    shipping = 0 if total >= 1999 or total == 0 else 99
    return render_template("cart.html", details=details, total=total, shipping=shipping,
                            grand_total=total + shipping)


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    details, total = cart_details()
    if not details:
        flash("Your bag is empty — add something you love first.", "error")
        return redirect(url_for("catalog"))
    shipping = 0 if total >= 1999 else 99
    grand_total = total + shipping

    if request.method == "POST":
        db = get_db()
        order_ref = "TH" + str(random.randint(100000, 999999))
        items_summary = [{"name": d["product"]["name"], "size": d["size"], "qty": d["qty"],
                           "price": d["product"]["price"]} for d in details]
        db.execute(
            """INSERT INTO "order"
               (order_ref, name, email, phone, address, city, pincode, items_json, total, payment_method, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_ref, request.form["name"], request.form["email"], request.form["phone"],
             request.form["address"], request.form["city"], request.form["pincode"],
             json.dumps(items_summary), grand_total, request.form.get("payment_method", "COD"),
             datetime.utcnow().isoformat()),
        )
        db.commit()
        session["cart"] = {}
        session.modified = True
        return redirect(url_for("order_confirmation", order_ref=order_ref))

    return render_template("checkout.html", details=details, total=total,
                            shipping=shipping, grand_total=grand_total)


@app.route("/order-confirmation/<order_ref>")
def order_confirmation(order_ref):
    db = get_db()
    order = db.execute('SELECT * FROM "order" WHERE order_ref = ?', (order_ref,)).fetchone()
    if order is None:
        return render_template("404.html"), 404
    return render_template("confirmation.html", order=order)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/policies")
def policies():
    return render_template("policies.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
