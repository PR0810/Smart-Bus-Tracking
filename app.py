from urllib import response
import os
from flask import Flask, render_template, request, redirect, session, jsonify
from flask_mysqldb import MySQL
from flask_socketio import SocketIO, emit
import bcrypt
import requests
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=4)
chat_cache={}
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from sklearn.linear_model import LinearRegression
import numpy as np
import google.generativeai as genai
genai.configure(api_key=os.environ.get('GEMINI_API_KEY', ''))
from flask_mail import Mail, Message
import random
import random
from collections import defaultdict
import time
login_attempts = defaultdict(list)
from urllib.parse import urlparse
app = Flask(__name__)

mysql_url = os.environ.get('MYSQL_PUBLIC_URL', '')
if mysql_url:
    parsed = urlparse(mysql_url)
    app.config['MYSQL_HOST'] = parsed.hostname
    app.config['MYSQL_USER'] = parsed.username
    app.config['MYSQL_PASSWORD'] = parsed.password
    app.config['MYSQL_DB'] = parsed.path[1:]
    app.config['MYSQL_PORT'] = parsed.port
else:
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = '1234#Sahu'
    app.config['MYSQL_DB'] = 'bus_tracking'
    app.config['MYSQL_PORT'] = 3306
app.secret_key = 'bus123'
limiter = Limiter(get_remote_address,app=app, default_limits=["200 per day"])
app.config['JWT_SECRET_KEY'] = 'jwt-bus-tracking-secret'
jwt = JWTManager(app)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'prachisahu092006@gmail.com'
app.config['MAIL_PASSWORD'] = 'lmgr vhwe urdw qusv'
mail = Mail(app)
from datetime import datetime, timedelta
app.permanent_session_lifetime = timedelta(days=30)

mysql = MySQL(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

@app.route('/')
def home():
    return redirect ('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed=bcrypt.hashpw(password.encode('utf-8'),bcrypt.gensalt())
        role = request.form['role']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                    (name, email, hashed, role))
        mysql.connection.commit()
        cur.close()

        return redirect('/login')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        ip = request.remote_addr
        
        # Check attempts
        now = time.time()
        attempts = [t for t in login_attempts[ip] if now - t < 300]  # 5 min
        
        if len(attempts) >= 3:
            return render_template('login.html', lockout=True), 429
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
            login_attempts[ip] = []  # Reset on success
            session['user'] = email
            if request.form.get('remember'):
                session.permanent = True
            session['role'] = user[4]
            access_token = create_access_token(identity={'email': email, 'role': user[4]})
            session['token'] = access_token
            if user[4] == 'admin':
                return redirect('/admin')
            elif user[4] == 'driver':
                return redirect('/driver')
            else:
                return redirect('/passenger')
        else:
            login_attempts[ip].append(now)  # Count wrong attempt
            return render_template('login.html', error='Invalid Email or Password!')

    return render_template('login.html')

@app.route('/admin')
def admin():
    if 'user' not in session:
        return redirect('/login')
    if session.get('role') != 'admin':
        return redirect('/login')
    return render_template('admin.html')

@app.route('/driver')
def driver():
    if 'user' not in session:
        return redirect('/login')
    if session.get('role') != 'driver':
        return redirect('/login')
    return render_template('driver.html')

@app.route('/passenger')
def passenger():
    if 'user' not in session:
        return redirect('/login')
    if session.get('role') != 'passenger':
        return redirect('/login')
    return render_template('passenger.html')

@app.route('/search_bus')
def search_bus():
    from_place = request.args.get('from', '')
    to_place = request.args.get('to','').strip()
    cur = mysql.connection.cursor()
    cur.execute("""
    SELECT b.bus_number, b.bus_name, b.total_seats, b.current_passengers, r.route_name, r.start_point, r.end_point 
    FROM buses b 
    JOIN routes r ON b.id = r.bus_id
    WHERE(r.start_point LIKE %s AND r.end_point LIKE %s) 
    """, ('%'+from_place+'%', '%'+to_place+'%'))
    buses = cur.fetchall()
    cur.close()
    result = []
    for bus in buses:
        result.append({
            'bus_number': bus[0],
            'bus_name': bus[1],
            'total_seats': bus[2],
            'current_passengers': bus[3],
            'route_name': bus[4],
            'start_point': bus[5],
            'end_point': bus[6]
        })
    return jsonify(result)

@app.route('/get_buses')
def get_buses():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, bus_number, bus_name, total_seats, status FROM buses")
    buses = cur.fetchall()
    cur.close()
    return jsonify([{'id': b[0], 'bus_number': b[1], 'bus_name': b[2], 'total_seats': b[3], 'status': b[4]} for b in buses])
@app.route('/get_routes')
def get_routes():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT r.id, r.route_name, r.start_point, r.end_point, b.bus_number 
                   FROM routes r 
                   LEFT JOIN buses b ON r.bus_id = b.id""")
    routes = cur.fetchall()
    cur.close()
    return jsonify([{'id': r[0], 'route_name': r[1], 'start_point': r[2], 'end_point': r[3], 'bus_number': r[4]} for r in routes])

@app.route('/add_bus', methods=['POST'])
def add_bus():
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO buses (bus_number, bus_name, total_seats, status) VALUES (%s, %s, %s, 'active')",
                (data['bus_number'], data.get('bus_name'), data['total_seats']))
    mysql.connection.commit()
    cur.close()
    return jsonify({'status': 'ok'})

@app.route('/add_route', methods=['POST'])
def add_route():
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO routes (route_name, start_point, end_point,bus_id) VALUES (%s, %s, %s,%s)",
                (data['route_name'], data['start_point'], data['end_point'],data.get('bus_id')))
    mysql.connection.commit()
    cur.close()
    return jsonify({'status': 'ok'})

@app.route('/get_drivers')
def get_drivers():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT u.id, u.name, b.bus_number 
                   FROM users u 
                   LEFT JOIN buses b ON u.id = b.driver_id 
                   WHERE u.role='driver'""")
    drivers = cur.fetchall()
    cur.close()
    return jsonify([{'id': d[0], 'name': d[1], 'bus': d[2]} for d in drivers])

@app.route('/assign_driver', methods=['POST'])
def assign_driver():
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute("UPDATE buses SET driver_id=%s WHERE id=%s",
                (data['driver_id'], data['bus_id']))
    mysql.connection.commit()
    cur.close()
    return jsonify({'status': 'ok'})
@app.route('/delete_bus', methods=['POST'])
def delete_bus():
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM buses WHERE id=%s", (data['id'],))
    mysql.connection.commit()
    cur.close()
    return jsonify({'status': 'ok'})
@app.route('/delete_route', methods=['POST'])
def delete_route():
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM routes WHERE id=%s", (data['id'],))
    mysql.connection.commit()
    cur.close()
    return jsonify({'status': 'ok'})

@app.route('/remove_driver', methods=['POST'])
def remove_driver():
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute("UPDATE buses SET driver_id=NULL WHERE driver_id=%s", (data['id'],))
    mysql.connection.commit()
    cur.close()
    return jsonify({'status': 'ok'})
@app.route('/update_passengers', methods=['POST'])
def update_passengers():
    data = request.get_json()
    email = session.get('user')
    cur = mysql.connection.cursor()
    cur.execute("""UPDATE buses SET current_passengers=%s 
                   WHERE driver_id=(SELECT id FROM users WHERE email=%s)""",
                (data['count'], email))
    mysql.connection.commit()
    cur.close()
    socketio.emit('passenger_update', {'count': data['count']})
    return jsonify({'status': 'ok'})

@app.route('/toggle_bus', methods=['POST'])
def toggle_bus():
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute("UPDATE buses SET status=%s WHERE id=%s", (data['status'], data['id']))
    mysql.connection.commit()
    cur.close()
    return jsonify({'status': 'ok'})
@app.route('/get_my_bus')
def get_my_bus():
    email = session.get('user')
    cur = mysql.connection.cursor()
    cur.execute("""SELECT b.bus_number,b.bus_name, r.route_name, r.start_point, r.end_point, b.total_seats, b.current_passengers
                   FROM buses b 
                   JOIN users u ON b.driver_id = u.id 
                   LEFT JOIN routes r ON r.bus_id = b.id
                   WHERE u.email=%s""", (email,))
    bus = cur.fetchone()
    cur.close()
    if bus:
        return jsonify({'bus': bus[0],'bus_name':bus[1],'route': bus[2], 'from': bus[3], 'to': bus[4], 'total_seats': bus[5], 'current_passengers': bus[6]})
    return jsonify({'bus': None})
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        if user:
            otp = str(random.randint(100000, 999999))
            session['otp'] = otp
            session['reset_email'] = email
            msg = Message('Bus Tracking - OTP', sender='tumhari_gmail@gmail.com', recipients=[email])
            msg.body = f'Your OTP is: {otp}'
            mail.send(msg)
            return redirect('/verify_otp')
        return "Email not found!"
    return render_template('forgot_password.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        otp = request.form['otp']
        new_password = request.form['new_password']
        if otp == session.get('otp'):
            hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            cur = mysql.connection.cursor()
            cur.execute("UPDATE users SET password=%s WHERE email=%s",
                        (hashed, session.get('reset_email')))
            mysql.connection.commit()
            cur.close()
            return redirect('/login')
        return "Invalid OTP!"
    return render_template('verify_otp.html')
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    email = session.get('user')
    cur = mysql.connection.cursor()
    cur.execute("SELECT name, email, role FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    cur.close()
    return render_template('profile.html', name=user[0], email=user[1], role=user[2])

@app.route('/update_profile', methods=['POST'])
def update_profile():
    name = request.form['name']
    old_password = request.form['old_password']
    new_password = request.form['new_password']
    email = session.get('user')

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cur.fetchone()

    if user and bcrypt.checkpw(old_password.encode('utf-8'), user[3].encode('utf-8')):
        if name:
            cur.execute("UPDATE users SET name=%s WHERE email=%s", (name, email))
        if new_password:
            hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            cur.execute("UPDATE users SET password=%s WHERE email=%s", (hashed, email))
        mysql.connection.commit()
        cur.close()
        return render_template('profile.html', msg='Profile Updated!')
    cur.close()
    return render_template('profile.html', msg='Wrong Password!')
@app.route('/bus_history')
def bus_history():
    return render_template('bus_history.html')

@app.route('/get_history')
def get_history():
    bus_id = request.args.get('bus_id')
    cur = mysql.connection.cursor()
    cur.execute("""SELECT b.bus_number, h.latitude, h.longitude, h.timestamp 
                   FROM bus_history h 
                   JOIN buses b ON h.bus_id = b.id 
                   WHERE h.bus_id=%s 
                   ORDER BY h.timestamp DESC LIMIT 50""", (bus_id,))
    history = cur.fetchall()
    cur.close()
    return jsonify([{'bus_number':h[0], 'lat': float(h[1]), 'lng': float(h[2]), 'time': str(h[3])} for h in history])
@app.route('/reverse_geocode')
def reverse_geocode():
    import requests
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    try:
        r = requests.get(
            f'https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json',
            headers={'User-Agent': 'bus-tracking-app'},
            timeout=1
        )
        return jsonify(r.json())
    except:
        return jsonify({'display_name': f'{lat}, {lng}'})
@app.route('/get_schedules')
def get_schedules():
    bus_number = request.args.get('bus_number')
    cur = mysql.connection.cursor()
    if bus_number:
        cur.execute("""SELECT s.id, b.bus_number, s.departure_time, s.arrival_time, s.days 
                       FROM bus_schedule s JOIN buses b ON s.bus_id = b.id
                       WHERE b.bus_number=%s""", (bus_number,))
    else:
        cur.execute("""SELECT s.id, b.bus_number, s.departure_time, s.arrival_time, s.days 
                       FROM bus_schedule s JOIN buses b ON s.bus_id = b.id""")
    schedules = cur.fetchall()
    cur.close()
    return jsonify([{'id': s[0], 'bus_number': s[1], 'departure': str(s[2]), 'arrival': str(s[3]), 'days': s[4]} for s in schedules])
@app.route('/get_my_schedule')
def get_my_schedule():
    email = session.get('user')
    cur = mysql.connection.cursor()
    cur.execute("""SELECT s.departure_time, s.arrival_time, s.days 
                   FROM bus_schedule s 
                   JOIN buses b ON s.bus_id = b.id
                   JOIN users u ON b.driver_id = u.id
                   WHERE u.email=%s""", (email,))
    schedules = cur.fetchall()
    cur.close()
    return jsonify([{'departure': str(s[0]), 'arrival': str(s[1]), 'days': s[2]} for s in schedules])
@app.route('/add_schedule', methods=['POST'])
def add_schedule():
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO bus_schedule (bus_id, departure_time, arrival_time, days) VALUES (%s, %s, %s, %s)",
                (data['bus_id'], data['departure_time'], data['arrival_time'], data['days']))
    mysql.connection.commit()
    cur.close()
    return jsonify({'status': 'ok'})

@app.route('/delete_schedule', methods=['POST'])
def delete_schedule():
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM bus_schedule WHERE id=%s", (data['id'],))
    mysql.connection.commit()
    cur.close()
    return jsonify({'status': 'ok'}) 
@app.route('/chatbot', methods=['POST'])
def chatbot():
    try:
        data = request.get_json()
        user_message = data['message']
         #    Cache check
        if user_message in chat_cache:
            return jsonify({'reply': chat_cache[user_message]})

        cur = mysql.connection.cursor()
        cur = mysql.connection.cursor()
        cur.execute("""SELECT b.bus_number, b.bus_name, r.start_point, r.end_point, r.route_name, b.total_seats, b.current_passengers, b.status
                    FROM routes r JOIN buses b ON bus_id = b.id""")
        buses = cur.fetchall()
        
        cur.execute("""SELECT b.bus_number, s.departure_time, s.arrival_time, s.days 
                       FROM bus_schedule s JOIN buses b ON s.bus_id = b.id""")
        schedules = cur.fetchall()
        cur.close()
        bus_info = ""
        for bus in buses:
         seats_left = max(0, bus[5] - bus[6])
        bus_info += f"Bus: {bus[0]} ({bus[1]}), Route: {bus[2]} to {bus[3]}, Seats Left: {seats_left}, Status: {bus[7]}\n"
        print("bus info:" , bus_info)
        schedule_info = ""
        for s in schedules:
            schedule_info += f"Bus: {s[0]}, Departure: {s[1]}, Arrival: {s[2]}, Days: {s[3]}\n"
        
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(
         f"""You are a bus tracking assistant for a college bus system.
Available buses and routes:
{bus_info}
Schedules:
{schedule_info}
Important: Only use the above data to answer. Do not make up information.
Answer in Hindi/English. User asked: {user_message}"""
)
        chat_cache[user_message]=response.text
        return jsonify({'reply': response.text})
    except Exception as e:
       print("Chatbot error:",e)
    return jsonify({'reply': 'Sorry! Try again later.'})
@app.route('/list_models')
def list_models():
    models = genai.list_models()
    return jsonify([m.name for m in models])
@app.route('/predict_eta', methods=['POST'])
def predict_eta():
    data = request.get_json()
    distance = float(data['distance'])
    hour = datetime.now().hour
    
    # Simple prediction based on time of day
    if 8 <= hour <= 10 or 17 <= hour <= 19:  # Rush hours
        speed = 20  # km/h slow
    elif 22 <= hour or hour <= 5:  # Night
        speed = 50  # km/h fast
    else:
        speed = 35  # km/h normal
    
    eta_minutes = (distance / speed) * 60
    return jsonify({'eta': round(eta_minutes), 'speed': speed})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
@app.errorhandler(429)
def too_many_requests(e):
    return render_template('login.html', lockout=True), 429
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
@socketio.on('location_update')
def handle_location(data):
    data['driver'] = session.get('user')
    emit('bus_location', data, broadcast=True)
    
   # Save every 1 minute only
    from datetime import datetime, timedelta
    cur = mysql.connection.cursor()
    cur.execute("""SELECT timestamp FROM bus_history 
                   WHERE bus_id=(SELECT b.id FROM buses b JOIN users u ON b.driver_id=u.id WHERE u.email=%s)
                   ORDER BY timestamp DESC LIMIT 1""", (session.get('user'),))
    last = cur.fetchone()
    
    if not last or (datetime.now() - last[0]) > timedelta(minutes=1):
        cur.execute("""INSERT INTO bus_history (bus_id, latitude, longitude)
                       SELECT b.id, %s, %s FROM buses b 
                       JOIN users u ON b.driver_id = u.id 
                       WHERE u.email=%s""", 
                       (data['lat'], data['lng'], session.get('user')))
        mysql.connection.commit()
    cur.close()

if __name__ == '__main__':
  socketio.run(app, debug=True, host='0.0.0.0', port=5000)