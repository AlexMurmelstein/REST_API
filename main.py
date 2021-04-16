#Imports
from flask import Flask, jsonify, request, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_migrate import Migrate
from datetime import datetime as dt
from dotenv import load_dotenv
import os
from sqlalchemy import ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

#Set .ENV
load_dotenv()
SECRET_KEY = os.getenv("key")

#Start flask, connect to db
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///messages_api.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_SORT_KEYS'] = False
db = SQLAlchemy(app)
Migrate(app,db)

#LOGIN-app
login_manager = LoginManager()

@login_manager.user_loader
def load_user(id):
    return User.query.get(id)

login_manager.init_app(app)


##CONFIGURE TABLES


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(5), nullable=False)
    password = db.Column(db.String(250), nullable=False)
    messages = relationship("Message", back_populates="user")

class Message(UserMixin, db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(100), nullable=False)
    receiver = db.Column(db.String(5), nullable=False)
    message = db.Column(db.String(1000), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    date = db.Column(db.DateTime, default=dt.utcnow, nullable=False)
    read=db.Column(db.Boolean, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = relationship("User", back_populates="messages")


    def to_dict(self):
        dictionary = {}
        for column in self.__table__.columns:
            dictionary[column.name] = getattr(self, column.name)
        return dictionary


#Functions

#DECORATOR FUNCTION for login:
def login_required(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            try:
                current_user.id
            except:
                abort(403)
            else:
                if current_user.id:
                    return function(*args, **kwargs)
                else:
                    abort(403)
        return wrapper


#Search function for double use, outside @app.route
def get_all(unread=False):
    receiver=current_user.name
    all_msgs = Message.query.filter_by(receiver=receiver).all()
    err_msg="No such receiver"
    if unread:
        all_msgs = Message.query.filter_by(receiver=receiver, read=False).all()
        err_msg = "No unread messages for this receiver"

    empt = []
    if all_msgs!=[]:
        for msg in all_msgs:
            if msg.read == False:
                msg.read = True
                db.session.commit()
            empt.append(msg.to_dict())
        return jsonify(empt)
    else:
        return jsonify({"error": {"not found": err_msg}}), 404


#Authentication-related functions

@app.route('/register', methods=["POST"])
def register_user():
        password=request.args.get("pwd")
        pwd2=generate_password_hash(password=password, method='pbkdf2:sha256', salt_length=1)
        new_user=User(
            name=request.args.get("name"),
            password=pwd2
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return jsonify({"response": {"success": "Successfully registered user"}})


@app.route('/login', methods=["POST"])
def login():
    if current_user.is_authenticated:
        logout_user()
    user_name=request.args.get("name")
    user_pwd=request.args.get("pwd")
    target_user = User.query.filter_by(name=user_name).first()
    if target_user is not None and check_password_hash(target_user.password, user_pwd)==True:
        login_user(target_user)
        return jsonify({"response": {"success": "Successfully logged-in"}})
    elif target_user is None:
        return jsonify({"response": {"Error": "No such user! Perhaps you should check for typos"}}), 404
    elif target_user.password!=user_pwd:
        return jsonify({"response": {"Error": "Wrong password!"}}), 403


@app.route('/logout', methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"response": {"success": "Successfully logged-out"}})

#DB handling functions
@app.route("/write", methods=["GET", "POST"])
@login_required
def write_message():
    new_msg = Message(
        sender=current_user.name,
        receiver=request.args.get("receiver"),
        message=request.args.get("message"),
        subject=request.args.get("subject"),
        read=False,
        user=current_user
    )
    db.session.add(new_msg)
    db.session.commit()
    return jsonify({"response": {"success": "Successfully sent message"}})

#HTTP GET-Get *all* messages for a specific *receiver*, as clarified by client
@app.route("/all")
@login_required
def get_all_msgs():
    return get_all()


#HTTP GET-Get *all unread* messages for a specific receiver
@app.route("/all_unread")
@login_required
def get_all_unread():
    return get_all(unread=True)


# HTTP GET - Read Record
@app.route("/read_one/")
@login_required
def get_one_message():
    #Check "id" on Postman to enable id-search; if not checked, will return last unread msg
    def process(msg):
        if msg.read==False:
            msg.read=True
            db.session.commit()
        new_msg = msg.to_dict()
        return jsonify(new_msg)

    id = request.args.get("id")
    if id is not None:
        msg_by_id = Message.query.filter_by(id=id).first()
        if msg_by_id:
            msg_by_user = Message.query.filter_by(id=id, receiver=current_user.name).first()
            if msg_by_user:
                return process(msg_by_user)
            else:
                return jsonify({"Error": {"Forbidden": "You do not have access to this message"}}), 403
        else:
            return jsonify({"error": {"not found": "No message with that id"}}), 404
    else:
        msg_rnd = Message.query.filter_by(read=False, receiver=current_user.name).first()
        if msg_rnd:
            return process(msg_rnd)
        else:
            return jsonify({"error": {"not found": "No unread message available for logged-in user"}}), 404



## HTTP DELETE - Delete Record
@app.route("/delete/<id>", methods=["DELETE"])
@login_required
def delete(id):
    target = Message.query.get(id)
    if target is None:
            return jsonify({"response": {"Error": "No such Message"}}), 404
    else:
        msg = Message.query.filter_by(id=id, receiver=current_user.name).first()
        msg2= Message.query.filter_by(id=id, sender=current_user.name).first()
        if msg or msg2:
            db.session.delete(target)
            db.session.commit()
            return jsonify({"response": {"DELETED": "Successfully deleted message"}})
        else:
            return jsonify({"error": {"Forbidden": "You are neither the owner nor receiver of this message, you cannot delete it!"}}), 403



if __name__ == "__main__":
    app.run(debug=False)