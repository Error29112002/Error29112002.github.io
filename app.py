import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    holdings = db.execute(
        "SELECT symbol, SUM(shares) AS shares, price, stock_name, total FROM purchases WHERE user_id = ? GROUP BY symbol HAVING shares > 0", session["user_id"])
    user_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])  # Gives a list with a dict value
    print(user_cash[0])  # Prints out {'cash': 117.25999}
    # cash = dict(user_cash[0].values()) !!! MISTAKE !!!
    # print(cash) !!! MISTAKE !!!
    cash = user_cash[0]['cash']  # Prints the value of the dict with the key 'cash' i.e value of cash.
    print(cash)
    live_price = []
    for holding in holdings:
        stock = lookup(holding["symbol"])
        live_price.append({"symbol": stock["symbol"], "price": stock["price"]})
        for lp in live_price:
            if holding["symbol"] == lp["symbol"]:
                holding["price"] = lp["price"]

    cash_total = cash
    print(cash_total)
    for holding in holdings:
        cash_total += holding["price"] * holding["shares"]

    return render_template("index.html", holdings=holdings, cash=usd(cash), cash_total=usd(cash_total), usd=usd)
    # return apology("TODO")r


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        # Retrieve symbol of stock from form
        symbol = request.form.get("symbol").upper()
        if not symbol:      # If symbol is not entered in the form, give an error
            return apology("Please enter symbol", 400)
        # Use lookup to find the symbol in the database
        find_symbol = lookup(symbol)
        if find_symbol == None:  # If the symbol doesn't exist in the database, give an error
            return apology("Symbol does not exist", 400)

        # Retrieve no. of shares from form
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("Enter valid shares", 400)
        # try:
        #      #Convert the shares into integer values
        # except: #Give error if there is a non-integer value in the form.
        #     return apology("Please enter number of shares", 400)

        if shares < 0:
            return apology("Please enter valid no. of shares", 400)

        stock_name = find_symbol["name"]  # Retrieve the name of the symbol and index it in a var.
        stock_price = find_symbol["price"]  # Retrieve the price(current) of the symbol and index it in a var.
        total_price = shares * stock_price  # Total price of the transaction = no of shares * single_share price. store it in a var.

        # Create a Table called purchases into the finance.db WHERE YOU HAVE A
        # id PRIMARY ID, SYMBOL = symbol , Name = share_name, Shares = shares, Price = share_price, Total = total

        database_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        cash = database_cash[0]["cash"]

        if cash < total_price:
            return apology("Unable to purchase stock", 403)
        else:
            db.execute("INSERT INTO purchases(user_id, stock_name, symbol, price, shares, total) VALUES (?, ?, ?, ?, ?, ?)", session["user_id"], stock_name, symbol, stock_price, shares, total_price)

            # update cash value
            u_cash = cash - total_price
            db.execute("UPDATE users SET cash = ? WHERE id = ?", u_cash, session["user_id"])



        flash("Bought!")
        return redirect("/")


    else:
        return render_template("buy.html")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    data_from_db = db.execute("SELECT symbol, shares, price, time FROM purchases WHERE user_id = ?", session["user_id"])
    return render_template("history.html", purchases=data_from_db)
    # return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":

        return render_template("quote.html")

    else:
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Please enter symbol", 400)

        stock = lookup(symbol)
        if stock == None:
            return apology("Symbol Invalid", 400)


        return render_template("quoted.html", stock=stock)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        #Get the value of username from the form in register.html
        username = request.form.get("username")

        #Get the value of password from the form in register.html
        password = request.form.get("password")

        #Get the value of confirmation password from the form in register.html
        confirmation = request.form.get("confirmation")

        #Generate a hash of the password and store it in a variable
        hash = generate_password_hash(password)
        #Validate username
        if not username:
            return apology("must provide username", 400)
        # elif len(rows) != 1:
        #     return apology("invalid username", 403)

        #Validate password
        if not password:
            return apology("must provide password", 400)
        elif confirmation != password:
            return apology("Invalid password", 400)

        #Try to insert user entry into database, if already exists, provide apology
        try:
            user = db.execute("INSERT INTO users(username, hash) VALUES(?, ?);", username, hash)
        except:
            return apology("Username already exists", 400)

        # Remember which user has registered
        session["user_id"] = user

        #redirect the user to the login page for logging in to the home page
        return redirect("/login")

    #If request method is through GET redirect them back to register page
    return render_template("register.html")






@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        user_symbols = db.execute('SELECT symbol FROM purchases WHERE user_id = ? GROUP BY symbol', session["user_id"])
        return render_template("sell.html", symbols = [row["symbol"] for row in user_symbols])
    else:
        #Retrieve symbol of stock from form
        symbol = request.form.get("symbol")
        if not symbol:      #If symbol is not entered in the form, give an error
            return apology("Please enter symbol", 403)
        #Use lookup to find the symbol in the database
        find_symbol = lookup(symbol)
        if find_symbol == None: #If the symbol doesn't exist in the database, give an error
            return apology("Symbol does not exist", 403)

        shares = request.form.get("shares")
        if not shares:
            return apology("Please enter shares")

        stock_name = find_symbol["name"] #Retrieve the name of the symbol and index it in a var.
        stock_price = find_symbol["price"] #Retrieve the price(current) of the symbol and index it in a var.
        total_price = int(shares) * stock_price #Total price of the transaction = no of shares * single_share price. store it in a var.

        #Create a Table called purchases into the finance.db WHERE YOU HAVE A
        # id PRIMARY ID, SYMBOL = symbol , Name = share_name, Shares = shares, Price = share_price, Total = total

        database_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        cash = database_cash[0]["cash"]

        user_shares = db.execute(
            "SELECT symbol, SUM(shares) AS shares FROM purchases WHERE user_id = ? AND symbol = ? GROUP BY symbol HAVING shares > 0", session["user_id"], symbol)
        for share in user_shares:
            if symbol == share["symbol"]:
                if int(share["shares"]) >= int(shares):
                    continue
                else:
                    return apology("You Don't Own Enough Shares")

        # update cash value
        u_cash = cash + total_price
        db.execute("UPDATE users SET cash = ? WHERE id = ?", u_cash, session["user_id"])

        shares = int(shares) * -1
        # Purchase Stock
        db.execute("INSERT INTO purchases(user_id, stock_name, symbol, price, shares, total) VALUES (?, ?, ?, ?, ?, ?)",
                    session["user_id"], stock_name, symbol, stock_price, int(shares), total_price)

        flash("Sold!")
        return redirect("/")

