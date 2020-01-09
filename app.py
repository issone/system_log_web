# coding=utf-8
import os
from flask import Flask, render_template
from flask_socketio import SocketIO
from threading import Lock

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app)

close = False
thread = None
thread_lock = Lock()
log_name = '/var/log/nginx/access.log'  # 日志文件名
client_num = 0  # tail页面连入数量


def close_tail():
    with thread_lock:
        global close, thread, client_num
        client_num -= 1
        print('有客户端离开tail页面，当前页面客户端剩余数量为', client_num)

        if client_num <= 0:
            close = True
            client_num = 0
            thread = None
            print('tail页面客户端全部关闭')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/tail_html', methods=['GET'])
def tail_html():
    return render_template('tail.html')


def get_tail_n_info(n):
    try:
        tail_pipe = os.popen(f'tail -n {n} {log_name} ')
    except:
        print('文件不存在')
        return ''
    else:

        tail_output = iter(tail_pipe.readlines())
        tail_pipe.close()

    return tail_output


@socketio.on('open_tail', namespace="/shell")
def handle_tail(message):
    global thread, close, client_num

    with thread_lock:
        client_num += 1
        print('有客户端进入tail页面，当前页面客户端数量为', client_num)
        if thread is None:
            close = False
            thread = socketio.start_background_task(target=background_thread)

        else:  # 有其他客户端正在使用时，则先发送最近30条过去

            for line in get_tail_n_info(n=30):
                if line.strip():
                    socketio.emit('tail_response', {'text': line}, namespace='/tail')
    print('received message: ' + message['data'])


@socketio.on('connect', namespace="/shell")
def connect():
    print("connect..")


@socketio.on('disconnect', namespace="/shell")
def disconnect():
    print("disconnect..")


def background_thread():
    try:
        tail_pipe = os.popen('tail -f ' + log_name)
    except:
        print('文件不存在')
        return
    else:
        while not close:
            tail_output = tail_pipe.readline()
            if tail_output.strip():
                socketio.emit('tail_response', {'text': tail_output}, namespace='/shell')

        tail_pipe.close()


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000)
