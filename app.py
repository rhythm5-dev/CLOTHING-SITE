"""
Irae — a clothing brand storefront
Flask + plain sqlite3 (Python's built-in database module). No ORM needed.

Run locally:
    pip install -r requirements.txt
    python3 app.py
Then open http://127.0.0.1:5000
"""

import os
import sqlite3
import random
import json
from datetime import datetime
from io import BytesIO
import base64
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from flask_mail import Mail, Message
import qrcode
from PIL import Image

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-to-something-random")
DATABASE = "store.db"

# ==================== EMAIL CONFIGURATION ====================
# REPLACE THESE with your actual credentials
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'iraeclothing.in@gmail.com'  # CHANGE THIS
app.config['MAIL_PASSWORD'] = os.environ.get('SENDGRID_API_KEY')    # CHANGE THIS - Gmail App Password
app.config['MAIL_DEFAULT_SENDER'] = ('IRAE Clothing', 'iraeclothing.in@gmail.com')  # CHANGE THIS

mail = Mail(app)

# Your brand email where you receive order notifications
BRAND_EMAIL = 'iraeclothing.in@gmail.com'  # CHANGE THIS

# Your UPI ID for receiving payments
UPI_ID = '8209944322@kotakbank'  # CHANGE THIS - your actual UPI ID

# ==================== DATABASE HELPERS ====================

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
            payment_status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM product").fetchone()[0]
    if count == 0:
        items = [
            ("KHATTI KAIRI Co-ord set", "Women", "Sets", 1599, 1599,
             "Elegant co-ord set with pinteresty vibes.",
             "/static/images/GREEN1.jpeg|/static/images/GREEN2.jpeg|/static/images/GREEN3.jpeg", "S,M,L,XL,XXL"),
            ("Cotton T-Shirt", "Men", "Shirts", 699, 699,
             "Crisp cotton shirt with a tailored slim fit, mother-of-pearl buttons, and a spread collar.",
             "/static/images/MEN1.jpeg|/static/images/MEN2.jpeg|/static/images/MEN3.jpeg", "S,M,L,XL"),
            ("BLACK SWAN Off shoulder dress", "Women", "Dresses", 1599, 1599,
             "Off-shoulder long dress in a bold black print, corset finsih, and flattering fit.",
             "/static/images/BLACK1.jpeg|/static/images/BLACK2.jpeg|/static/images/BLACK3.jpeg", "S,M,L,XL"),
            ("NURA cherry red dress", "Women", "Dresses", 1599, 1599,
             "Stunning cherry red dress with a fitted bodice and perfect fit.",
             "/static/images/red1.jpeg|/static/images/red2.jpeg|/static/images/red3.jpeg", "S,M,L,XL"),
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


def image_list(row):
    """Split the stored image field (may contain multiple paths separated by '|') into a list."""
    raw = row["image"]
    return [p.strip() for p in raw.split("|") if p.strip()]


def first_image(row):
    """Get just the first image, for use as a thumbnail in grids/cards."""
    imgs = image_list(row)
    return imgs[0] if imgs else ""


# ==================== EMAIL FUNCTIONS ====================

def send_order_emails(order_ref, name, email, phone, address, city, pincode, items_json, total):
    """Send confirmation emails to brand owner AND customer"""
    
    try:
        items = json.loads(items_json) if isinstance(items_json, str) else items_json
        
        # Build items HTML
        items_html = ""
        for item in items:
            items_html += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #eee;">{item['name']}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">{item.get('size', '-')}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">{item['qty']}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: right;">₹{item['price']}</td>
            </tr>
            """
        
        # ===== EMAIL TO BRAND OWNER (YOU) =====
        brand_msg = Message(
            subject=f'🛍️ NEW ORDER #{order_ref} - ₹{total}',
            recipients=[BRAND_EMAIL]
        )
        brand_msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #000; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 24px;">🛍️ NEW ORDER RECEIVED!</h1>
            </div>
            <div style="padding: 20px; border: 2px solid #000; border-top: none; border-radius: 0 0 8px 8px;">
                <h2 style="color: #333;">Order #{order_ref}</h2>
                <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                <p><strong>Total Amount:</strong> <span style="font-size: 28px; color: #28a745; font-weight: bold;">₹{total}</span></p>
                <p><strong>Payment Method:</strong> UPI</p>
                
                <hr style="margin: 20px 0;">
                
                <h3>📦 Customer Details</h3>
                <table style="width: 100%;">
                    <tr><td style="padding: 5px;"><strong>Name:</strong></td><td>{name}</td></tr>
                    <tr><td style="padding: 5px;"><strong>Email:</strong></td><td>{email}</td></tr>
                    <tr><td style="padding: 5px;"><strong>Phone:</strong></td><td>{phone}</td></tr>
                    <tr><td style="padding: 5px;"><strong>Address:</strong></td><td>{address}, {city} - {pincode}</td></tr>
                </table>
                
                <hr style="margin: 20px 0;">
                
                <h3>🛒 Order Items</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f8f9fa;">
                            <th style="padding: 12px; text-align: left;">Product</th>
                            <th style="padding: 12px; text-align: center;">Size</th>
                            <th style="padding: 12px; text-align: center;">Qty</th>
                            <th style="padding: 12px; text-align: right;">Price</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
                
                <div style="background: #fff3cd; padding: 15px; margin-top: 20px; border-radius: 5px;">
                    <p style="margin: 0; color: #856404; font-weight: bold;">⚡ ACTION REQUIRED: Process and ship this order!</p>
                </div>
            </div>
        </div>
        """
        mail.send(brand_msg)
        print(f"✅ Brand notification sent for Order #{order_ref}")
        
        # ===== EMAIL TO CUSTOMER =====
        customer_msg = Message(
            subject=f'✅ Order Confirmed - IRAE #{order_ref}',
            recipients=[email]
        )
        customer_msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #000; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 32px; letter-spacing: 3px;">IRAE</h1>
                <p style="margin: 5px 0 0 0;">Clothing for the Vibe that you are</p>
            </div>
            <div style="padding: 30px; border: 2px solid #000; border-top: none; border-radius: 0 0 8px 8px;">
                <h2 style="color: #28a745;">✅ Order Confirmed!</h2>
                <p>Thank you for shopping with us, <strong>{name}</strong>!</p>
                
                <div style="background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px;">
                    <p style="margin: 0;"><strong>Order Number:</strong> {order_ref}</p>
                    <p style="margin: 10px 0 0 0;"><strong>Total Paid:</strong> <span style="font-size: 24px; color: #28a745;">₹{total}</span></p>
                </div>
                
                <h3>Order Details:</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f8f9fa;">
                            <th style="padding: 10px; text-align: left;">Product</th>
                            <th style="padding: 10px; text-align: center;">Size</th>
                            <th style="padding: 10px; text-align: center;">Qty</th>
                            <th style="padding: 10px; text-align: right;">Price</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
                
                <hr style="margin: 20px 0;">
                
                <p><strong>Shipping to:</strong><br>
                {name}<br>
                {address}<br>
                {city} - {pincode}<br>
                Phone: {phone}</p>
                
                <div style="background: #f0f8ff; padding: 15px; margin-top: 20px; border-radius: 5px;">
                    <p style="margin: 0;">📦 We'll notify you when your order ships!</p>
                </div>
                
                <p style="color: #666; margin-top: 20px;">Questions? Contact us at {BRAND_EMAIL}</p>
            </div>
            <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
                <p>© {datetime.now().year} IRAE Clothing. All rights reserved.</p>
            </div>
        </div>
        """
        mail.send(customer_msg)
        print(f"✅ Customer confirmation sent for Order #{order_ref}")
        return True
        
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False


def generate_upi_qr(amount, order_ref):
    """Generate UPI payment QR code"""
    upi_url = f"upi://pay?pa={UPI_ID}&pn=IRAE%20Clothing&am={amount}&tr={order_ref}&tn=Order%20{order_ref}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return img_str


# ==================== CART HELPERS ====================

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
app.jinja_env.globals["image_list"] = image_list
app.jinja_env.globals["first_image"] = first_image


# ==================== ROUTES — PAGES ====================

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
    categories = ["All", "Men", "Women"]
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
        
        # Save order as pending payment
        db.execute(
            """INSERT INTO "order"
               (order_ref, name, email, phone, address, city, pincode, items_json, total, payment_method, payment_status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_ref, request.form["name"], request.form["email"], request.form["phone"],
             request.form["address"], request.form["city"], request.form["pincode"],
             json.dumps(items_summary), grand_total, "UPI", "pending",
             datetime.utcnow().isoformat()),
        )
        db.commit()
        
        # Generate QR code for payment
        qr_code = generate_upi_qr(grand_total, order_ref)
        
        # Store order_ref in session for payment confirmation
        session["pending_order_ref"] = order_ref
        session.modified = True
        
        return render_template("checkout.html", 
                             details=details, 
                             total=total,
                             shipping=shipping, 
                             grand_total=grand_total,
                             qr_code=qr_code,
                             order_ref=order_ref,
                             upi_id=UPI_ID)

    return render_template("checkout.html", details=details, total=total,
                            shipping=shipping, grand_total=grand_total)


@app.route("/confirm-payment", methods=["POST"])
def confirm_payment():
    """After customer pays via QR, they confirm and we send emails"""
    order_ref = request.form.get("order_ref")
    
    if not order_ref:
        flash("Invalid order reference.", "error")
        return redirect(url_for("home"))
    
    db = get_db()
    order = db.execute('SELECT * FROM "order" WHERE order_ref = ?', (order_ref,)).fetchone()
    
    if not order:
        flash("Order not found.", "error")
        return redirect(url_for("home"))
    
    # Update payment status
    db.execute('UPDATE "order" SET payment_status = ? WHERE order_ref = ?', 
              ("paid", order_ref))
    db.commit()
    
    # Send confirmation emails
    email_sent = send_order_emails(
        order_ref=order["order_ref"],
        name=order["name"],
        email=order["email"],
        phone=order["phone"],
        address=order["address"],
        city=order["city"],
        pincode=order["pincode"],
        items_json=order["items_json"],
        total=order["total"]
    )
    
    # Clear cart
    session["cart"] = {}
    session.pop("pending_order_ref", None)
    session.modified = True
    
    if email_sent:
        flash("Payment confirmed! Order confirmation sent to your email.", "success")
    else:
        flash("Payment confirmed! (Email notification delayed - we'll send it shortly)", "warning")
    
    return redirect(url_for("order_confirmation", order_ref=order_ref))


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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
