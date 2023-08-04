import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required, order_id_generator

# Configure application
app = Flask(__name__)


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///shop.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            flash("You Should Enter Your Username", category='danger')
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("You Should Enter Your Username", category='danger')
            return render_template("login.html")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            flash("Username And/Or Password Is Incorect", category='danger')
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    name = request.form.get("username")
    password = request.form.get("password")
    confiramtion_passwrod = request.form.get("confirmation")

    # If method is post
    if request.method == "POST":
        # If username not implemented or already exist in db
        # If username not implemented
        if not name:
            flash("Must Provide username", category='danger')
            return render_template("register.html")
        # username already in use
        elif len(db.execute("SELECT * FROM users WHERE username = ?", name)) != 0:
            flash("Username Is Not Valid", category='danger')
            return render_template("register.html")
        # If confirmation password not equal password or either of confirmation password or password not implemented
        # If user didn't implement password
        if not password:
            flash("Must Provide Password", category='danger')
            return render_template("register.html")
        # If user didn't implement confirmation password
        elif not confiramtion_passwrod:
            flash("Must Provide Confirmation Password", category='danger')
            return render_template("register.html")
        # If Password not equal confirmation password
        elif password != confiramtion_passwrod:
            flash("Confirmation Password Not as Password", category='danger')
            return render_template("register.html")
        # Register user into db
        db.execute(
            "INSERT INTO users(username, hash) values(?, ?)",
            name,
            generate_password_hash(password),
        )
        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )
        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        # Redirect user to homepage
        return redirect("/")
    # User reached this via GET
    return render_template("register.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


# ---------------------------------- user ----------------------------------

@app.route("/")
@login_required
def index():
    """ rendering home page """
    products = db.execute("SELECT * FROM products")
    return render_template("index.html", products=products)


# ---- cart ----
@app.route("/add_to_cart", methods=["GET", "POST"])
@login_required
def add_to_cart():
    """ Add Products To Cart """

    # ensure cart exists
    if "cart" not in session:
        session["cart"] = []

    #  if method is post
    if request.method == "POST":
        id = request.form.get("product")
        if id:
            session["cart"].append(id)

    # return user to home
    return redirect("/")


@app.route("/cart")
@login_required
def cart():
    """ rendering cart and changing its products """
    if "cart" not in session or len(session["cart"]) == 0:
        return render_template("cart.html", total_price=0)
    # get cart total price
    total_price = db.execute("SELECT sum(price) FROM products WHERE id IN(?)", session["cart"])

    # get all items
    items = db.execute("SELECT * FROM products WHERE id IN(?)", session["cart"])

    return render_template("cart.html", items=items, total_price=total_price[0]["sum(price)"])


@app.route("/removeProduct")
@login_required
def remove_product():
    """ remove product """
    # user want to delete product
    if request.args.get("remove_product"):
        session["cart"].pop(int(request.args.get("remove_product")))
    return redirect("/cart")


@app.route("/buy")
@login_required
def buy():
    """ checkout """
    if len(session["cart"]) == 0:
        flash("you should add products".upper())
        return render_template("cart.html")
    # get user data
    user_data = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])[0]
    user_cash = user_data["cash"]

    # get cart total price
    cart_total_price = db.execute("SELECT sum(price) FROM products WHERE id IN(?)", session["cart"])[0]
    cart_total_price = cart_total_price["sum(price)"]
    # check if user have enough money
    if user_cash < cart_total_price:
        flash("You Don't Have Enough Money")
        return render_template("cart.html")

    # user have enough money
    order_id = order_id_generator()

    # update users cash
    db.execute("UPDATE users SET cash = ? WHERE id = ?", user_cash - cart_total_price, session["user_id"])

    # insert order in transactions table
    for item in session["cart"]:
        price = db.execute("SELECT price FROM products WHERE id = ?", item)[0]['price']
        db.execute("INSERT INTO transactions(order_id, product_id, user_id, price) VALUES(?, ?, ?, ?)", order_id, item, user_data["id"], price)

    # delete cart
    session["cart"].clear()
    flash("You checkout sucessfully", category='success')

    return redirect("/")


# ---- profile ----
@app.route("/profile")
@login_required
def profile():
    """ show user's data """
    user = db.execute("SELECT * FROM users WHERE id = ? ", session["user_id"])[0]
    print(user)
    return render_template("profile.html", user=user)


@app.route("/changeUserName", methods=["POST"])
@login_required
def change_user_name():
    """ change user's name """
    old_user_name = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])[0]["username"]
    # check if user had implemented user name
    if not request.form.get("new_user_name"):
        flash("you should enter user name".upper(), category='danger')
        return render_template("/profile.html")
    # check if new username is old username
    elif request.form.get("new_user_name") == old_user_name:
        flash("you should enter different user name".upper(), category='danger')
        return render_template("/profile.html")
    db.execute("UPDATE users SET username = ? WHERE id = ?", request.form.get("new_user_name"), session["user_id"])
    flash("Username Changed Succefuly", category='success')
    return redirect("/profile")


@app.route("/changePassword", methods=["POST"])
@login_required
def change_password():
    """ change user's password"""
    old_password = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])[0]["hash"]
    # check if user had implemented old password
    if not request.form.get("old_password"):
        flash("you should enter password".upper(), category='danger')
        return render_template("profile.html")
    # check if user had implemented password
    elif not request.form.get("new_password"):
        flash("you should enter the new password".upper(), category='danger')
        return render_template("profile.html")
    # check if user had implemented confirmation password
    elif not request.form.get("confirmation_new_password"):
        flash("you should enter confirmation password".upper(), category='danger')
        return render_template("profile.html")
    # check if new username is old username
    elif request.form.get("new_password") != request.form.get("confirmation_new_password"):
        flash("new username is same as old username".upper(), category='danger')
        return render_template("profile.html")
    # check if user implemented wrong password
    elif check_password_hash(request.form.get("old_password"), old_password):
        flash("Invalid password".upper(), category='danger')
        return render_template("profile.html")
    # check if user using same password
    elif check_password_hash(old_password, request.form.get("new_password")):
        flash("You already using this password".upper(), category='danger')
        return render_template("profile.html")
    db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(request.form.get("new_password")), session["user_id"])
    flash("Password Changed Succesfuly", category='success')
    return redirect("/logout")


@app.route("/addCash", methods=["POST"])
@login_required
def add_cash():
    """ Add cash """
    # check if user didn't implement the money
    if not request.form.get("cash"):
        flash("enter the amount of cash".upper(), category='danger')
        return render_template("profile.html")
    # validate the amount of cash
    try:
        cash = float(request.form.get("cash"))
    except:
        flash("you should enter positive number".upper(), category='danger')
        return render_template("profile.html")
    # check if user enter invalid amount of money
    if cash < 0:
        flash("you must enter positive amount of money".upper(), category='danger')
        return render_template("profile.html")
    db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", cash, session["user_id"])
    flash("You Added Money Succesfuly", category='success')
    return redirect("/profile")


# ---- history ----
@app.route("/history")
@login_required
def history():
    transaction_info = db.execute("SELECT SUM(products.price) as total_price, transactions.order_id, timestamp FROM transactions JOIN products ON transactions.product_id = products.id WHERE transactions.user_id = ? GROUP BY order_id ORDER BY timestamp DESC", session["user_id"])
    return render_template("history.html", transaction_info=transaction_info)