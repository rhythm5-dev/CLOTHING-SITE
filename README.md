# THRESHOLD — Clothing Store (Flask demo)

A full working e-commerce storefront built with **Python + Flask**, inspired by
sites like Myntra: home page, browsable/filterable catalog, product pages,
cart, checkout, order confirmation, About, and a Policies page (refunds,
shipping, sizing, pricing, privacy).

Since you already know Python, this is built the most Python-friendly way
possible: Flask for the web server, and Python's built-in `sqlite3` module
for the database — no extra database software or ORM to learn.

## 1. Install requirements

You need Python 3.9+ installed. Then, in this folder, run:

```bash
pip install -r requirements.txt
```

This installs Flask (the only real dependency — the database uses Python's
built-in `sqlite3` module, nothing extra needed).

## 2. Run the site

```bash
python app.py
```

You'll see something like `Running on http://127.0.0.1:5000`. Open that
address in your browser. A `store.db` SQLite file is created automatically
the first time you run it, pre-loaded with 12 sample products.

## 3. How it's organized

```
app.py                 → all routes/logic (home, catalog, cart, checkout...)
templates/              → HTML pages (Jinja2 templates)
  base.html             → shared header/footer/nav used by every page
  index.html            → home page
  catalog.html          → product listing with filters + sort
  product.html           → single product page (size, qty, add to bag)
  cart.html              → shopping bag
  checkout.html          → shipping form + mock payment
  confirmation.html      → "order placed" page
  about.html, policies.html, contact.html
static/css/style.css    → all styling (single stylesheet)
static/js/script.js     → mobile menu toggle + flash message auto-dismiss
```

## 4. How the shopping flow works

- Products live in a SQLite table, seeded automatically on first run.
- The cart is stored in the Flask **session** (a cookie), as
  `{"product_id::size": quantity}`. No login is required to add to bag.
- Checkout collects shipping details and writes an `order` row to the
  database, then clears the cart.
- **Payment is simulated** — there's no real payment gateway wired up.
  See section 6 below for how to add one.

## 5. Things you'll likely want to change

- **Product images**: currently placeholder images from picsum.photos.
  Replace the `image` URLs in the `items` list inside `app.py`
  (`init_db()` function) with your own product photo URLs, or serve local
  images from a `static/images/` folder.
- **Brand name/copy**: search for "THRESHOLD" across `templates/` and
  `app.py` and replace with your brand name.
- **Colors/fonts**: all in `static/css/style.css`, defined as CSS variables
  at the top of the file (`--ink`, `--olive`, `--gold`, etc.) — change those
  and the whole site re-themes.
- **Products**: edit the `items` list in `app.py`'s `init_db()` function,
  or write a small admin script that inserts rows into the `product` table.

## 6. Adding real payments (when you're ready to launch)

This demo intentionally does **not** move real money — that requires a
registered business account with a payment gateway. When you're ready:

- In India: **Razorpay** or **Cashfree** are common choices, both have
  Python SDKs and step-by-step Flask integration guides.
- Internationally: **Stripe** has excellent Python docs.
- The integration point is the `checkout()` view in `app.py` — that's
  where you'd create a payment order with the gateway's API and redirect
  the user to their hosted checkout page, then verify the payment on the
  gateway's webhook before marking the order as paid.

## 7. Putting this online

For real users to access the site (not just on your own computer), you'll
need to deploy it somewhere. Beginner-friendly options that work well with
Flask + SQLite: **Render**, **Railway**, or **PythonAnywhere**. For a
production deployment, you'd also want to switch to a proper database
(PostgreSQL) since SQLite doesn't handle concurrent writes well at scale —
but for learning and early testing, this setup is fine.

## 8. Security note before going live

- Change `app.config["SECRET_KEY"]` in `app.py` to a long random value
  (don't commit it to version control — load it from an environment
  variable instead).
- Never store real card details yourself; a payment gateway handles that.
- Run with `debug=False` in production.
