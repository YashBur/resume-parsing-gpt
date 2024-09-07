from flask import Flask, render_template, request, redirect, url_for, session
import MySQLdb
import bcrypt

app = Flask(__name__)
app.secret_key = 'secret'

db = MySQLdb.connect("localhost", "root", "Yash2611", "flask_app")
cur = db.cursor()

def is_logged_in():
    return 'username' in session


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        db.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            if username == 'admin123' and password == 'major@123':
                session['username'] = username
                session['is_admin'] = True
                return redirect(url_for('admin_dashboard'))
            else:
                session['username'] = username
                session['is_admin'] = False
                return redirect(url_for('jobs'))
        else:
            return 'Invalid username/password'
    return render_template('login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'is_admin' in session and session['is_admin']:
        return render_template('admin_dashboard.html')
    else:
        return 'You are not authorized to access this page.'

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


