import os
import functools
from datetime import datetime
from flask import (
    Flask, render_template, request, session,
    redirect, url_for, flash
)
from database import UserDatabase
from config import PANEL_PASSWORD, PANEL_PORT, PANEL_SECRET_KEY

app = Flask(__name__)
app.secret_key = PANEL_SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

db = UserDatabase()
PANEL_START_TIME = datetime.now()


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def _calc_uptime():
    delta = datetime.now() - PANEL_START_TIME
    total = int(delta.total_seconds())
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m {seconds}s"


def _format_datetime(iso_str):
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y/%m/%d %H:%M")
    except Exception:
        return iso_str[:16]


app.jinja_env.filters['fmt_dt'] = _format_datetime


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if request.form.get('password') == PANEL_PASSWORD:
            session['logged_in'] = True
            session.permanent = True
            return redirect(url_for('dashboard'))
        flash('رمز عبور اشتباه است', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    search = request.args.get('q', '').strip()
    users = db.panel_get_all_users(search or None)
    stats = db.panel_get_stats()
    stats['uptime'] = _calc_uptime()
    return render_template('dashboard.html', users=users, stats=stats, search=search)


@app.route('/user/<int:telegram_id>')
@login_required
def user_detail(telegram_id):
    user = db.panel_get_user(telegram_id)
    if not user:
        flash('کاربر یافت نشد', 'error')
        return redirect(url_for('dashboard'))
    memory = db.panel_get_memory(telegram_id)
    history = db.panel_get_history(telegram_id)
    return render_template('user_detail.html', user=user, memory=memory, history=history)


if __name__ == '__main__':
    print(f"🌐 پنل مدیریت در آدرس http://0.0.0.0:{PANEL_PORT} راه‌اندازی شد")
    app.run(host='0.0.0.0', port=PANEL_PORT, debug=False)
