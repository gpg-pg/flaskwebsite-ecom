import os, psycopg2
import re
from flask import Flask, jsonify, request, url_for
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import LoginManager, login_user, login_required, logout_user, current_user       
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadTimeSignature, SignatureExpired
from models import tempusers, users, usersinfo                             


app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.environ.get('SECRET')
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

DATABASE_URL = os.environ.get('DATABASE_URI')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
db = SQLAlchemy(app)

sender_email = os.environ.get('SENDER_EMAIL')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = sender_email
app.config['MAIL_PASSWORD'] = os.environ.get('SENDER_PASSWORD')
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return users.query.filter_by(int(user_id)).first()



@app.route("/register", methods=['GET', 'POST'])
def register():

    if request.method == 'POST' and 'username' in request.json and 'email' in request.json and 'password' in request.json:  
        email = request.json['email']
        username = request.json['username']
        password = generate_password_hash(request.json['password'], method='sha256')

        user_email = tempusers.query.filter_by(email=email).first()
        user_name = tempusers.query.filter_by(username=username).first()

        if user_email:
            msg = 'Account exist for %s' % email 
            return jsonify({'msg': msg})

        elif user_name:
            msg = 'username taken!'
            return jsonify({'msg': msg}) 
        
        token = serializer.dumps(email)
        link = url_for('verify',token=token,_external=True)
        msg = Message('Verification link',sender=('Gautham','sender_email'),recipients=[email, sender_email])
        msg.body = 'Congratulations! Your link is {}'.format(link)
        
        tempuser = tempusers(email = email, username =username, password = password)
        db.session.add(tempuser)
        db.session.commit()

        mail.send(msg)

        msg = "Please verify email to complete registration"
        return jsonify({'msg': msg, 'username': username, 'email': email, 'password': password, 'token':token})

    elif request.json == 'POST':
        msg = 'Please fill out the form!'
        return jsonify({'msg': msg})

    return jsonify({'msg': "redirect to register page"})

@app.route("/verify/<token>", methods=['GET', 'POST'])
def verify(token):
    email = serializer.loads(token)
    
    try:
        user_email = tempusers.query.filter_by(email= email).first()
        if email == user_email.email:

            user = users(email = email, username =user_email.username)
            db.session.add(user)
            db.session.commit()

            userinfo = usersinfo(email = email, password = user_email.password)
            db.session.add(userinfo)
            db.session.commit()

            msg = 'Registration successful!'
            return jsonify({'msg':msg, 'email': email})

        return jsonify({'msg': "invalid_token"})

    except BadTimeSignature:
        msg = 'Invalid token!'
        return jsonify({'msg':msg})

    except SignatureExpired:
        msg = 'Token expired!'
        return jsonify({'msg':msg})
    

@app.route("/login", methods=['GET','POST'])
def login():

    if request.method == 'POST' and 'email' in request.json and 'password' in request.json:
        user_email = users.query.filter_by(email=request.json['email']).first()

        if user_email:
            user_password = usersinfo.query.filter_by(email=user_email.email).first()
            user_password = check_password_hash(user_password.password,request.json['password'])

            if user_password:
                login_user(user_email.username)
                msg = 'Welcome back, %s' % user_email.username
                return jsonify({'msg': msg})

            msg = 'Invalid username or password'
            return jsonify({'msg': msg})

        msg = 'Invalid username or password'
        return jsonify({'msg': msg})

    elif request.json == 'POST': 
        msg = 'Please fill out the form!'
        return jsonify({'msg': msg})

    msg = 'Redirect to login page'
    return jsonify({'msg': msg})

@app.route("/logout")
@login_required
def logout():
    logout_user()
    msg = 'logged out'
    return jsonify({'msg': msg})

@app.route("/dashboard")
@login_required
def dashboard():
    msg = 'current user is, %s' %current_user.username 
    return jsonify({'msg': msg})

if __name__ == '__main__':
    app.run()