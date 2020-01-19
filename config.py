# coding=utf-8
import os

SECRET_KEY = os.urandom(24)
LOG_FILE = '/var/log/nginx/access.log'  # 日志文件路径
EVENT_NAME = 'response' # socketio 事件名称
NAMESPACE = '/shell'  # socketio 名称空间