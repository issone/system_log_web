# coding=utf-8


from flask import Flask
from flask_socketio import SocketIO
from config import SECRET_KEY

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(app)
# 和Vue-socketio配合使用时，使用下面的，避免跨域
# socketio = SocketIO(app , cors_allowed_origins="*")
