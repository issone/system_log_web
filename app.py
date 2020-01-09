# coding=utf-8
import os
import re
from threading import Lock

from flask import Flask, render_template
from flask_socketio import SocketIO
from config import LOG_FILE, SECRET_KEY

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(app)

# 和Vue-socketio配合使用时，使用下面的，避免跨域
# socketio = SocketIO(app , cors_allowed_origins="*")

close = False
thread = None
thread_lock = Lock()
client_num = 0  # tail页面连入数量


def get_tail_n_info(n):
    '''
    tail按行获取
    :param n: 行数
    :return:
    '''
    try:
        tail_pipe = os.popen(f'tail -n {n} {LOG_FILE} ')
    except:
        print('文件不存在')
        return ''
    else:

        tail_output = iter(tail_pipe.readlines())
        tail_pipe.close()

    return tail_output


def tail_close():
    with thread_lock:
        global close, thread, client_num
        client_num -= 1
        print('有客户端离开tail页面，当前页面客户端剩余数量为', client_num)

        if client_num <= 0:
            close = True
            client_num = 0
            thread = None
            print('tail页面客户端全部关闭')


def get_top_info():
    '''获取top命令结果，并做处理'''
    top_pipe = os.popen('top -n 1')
    try:
        top_output = top_pipe.read()
    finally:
        top_pipe.close()

    # 用print输出top_output看着没问题，但是用repr输出会发现有很多其他字符，这些字符会被发往前端，导致页面上数据混乱
    # 暂时先直接替换处理
    top_output = top_output.replace("\x1b(B\x1b[m", "").replace("\x1b(B\x1b[m\x1b[39;49m\x1b[K", "").replace(
        "\x1b[?1h\x1b=\x1b[?25l\x1b[H\x1b[2J", "").replace("\x1b[39;49m\x1b[1m", "").replace("\x1b[39;49m\x1b[K",
                                                                                             "").replace("\x1b[39;49m",
                                                                                                         "").replace(
        "\x1b[K", "").replace("\x1b[7m", "").replace("\x1b[?1l\x1b>\x1b[45;1H", "").replace("\x1b[?12l\x1b[?25h",
                                                                                            "").replace("\x1b[1m", "")

    _html = ''
    for num, line in enumerate(top_output.split('\n')):
        if num >= 6:
            if num == 6:
                new_line = "<table> <tr>"
            else:

                new_line = "<tr>"
            td_list = re.split(r" +", line)
            if len(td_list) > 1:

                for td in td_list:
                    if td.strip():
                        new_line += f"<td>{(8-len(td))*'&nbsp;'+td}</td>"

            new_line += "</tr>"
        else:
            new_line = '<div>' + line.replace(' ', "&nbsp;") + '</div>'

        _html += new_line
    _html += '</table>'
    return _html


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/tail', methods=['GET'])
def tail_html():
    return render_template('tail.html')


@app.route('/top', methods=['GET'])
def top_html():
    return render_template('top.html')


@socketio.on('connect', namespace="/shell")
def connect():
    print("connect..")


@socketio.on('disconnect', namespace="/shell")
def disconnect():
    print("disconnect..")


@socketio.on('open_tail', namespace="/shell")
def open_tail(message):
    print('received open_tail message: ' + message.get('data', ''))
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
                    socketio.emit('tail_response', {'text': line}, namespace='/shell')


@socketio.on('close_tail', namespace="/shell")
def close_tail(message):
    print('准备关闭tail', message.get('data', ''))
    tail_close()


@socketio.on('handle_top', namespace="/shell")
def handle_top(message):
    print('received handle_top message: ' + message.get('data', ''))

    top_info = get_top_info()
    socketio.emit('top_response', {'text': top_info}, namespace='/shell')


def background_thread():
    try:
        tail_pipe = os.popen('tail -f ' + LOG_FILE)
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
