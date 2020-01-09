# coding=utf-8
import os

SECRET_KEY = os.urandom(24)
LOG_FILE = '/var/log/nginx/access.log'  # 日志文件路径
