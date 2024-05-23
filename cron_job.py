#!/usr/bin/python3

from datetime import datetime, timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://Darshit:Darshit_123@localhost/telegram_bot'
db = SQLAlchemy(app)

class UserDetails(db.Model):
    __tablename__ = "user_details"
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer)
    user_entry_date = db.Column(db.TIMESTAMP)
    is_limit_reached = db.Column(db.Boolean, default=False)
    no_of_questions = db.Column(db.Integer, default=0)
    no_of_documents = db.Column(db.Integer, default=0)
    is_user = db.Column(db.Boolean, default=False)

def delete_api():
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    with app.app_context():
        time_for_deletion = datetime.now() - timedelta(hours=24)
        user_time_checked = UserDetails.query.filter(UserDetails.user_entry_date<=time_for_deletion).all()
        for user in user_time_checked:
            user.no_of_documents=0
            user.no_of_questions=0
            user.is_time_reached=False
            db.session.commit()
        non_user_time_checked = UserDetails.query.all()
        for user in non_user_time_checked:
            if not user.is_user:
                if user.no_of_documents >= 2 or user.no_of_questions >= 10:
                    user.is_limit_reached = True
                    
                    db.session.commit()
                else:
                    user.is_limit_reached = False
                    db.session.commit()
            else:
                user.is_time_reached = False


delete_api()
    
