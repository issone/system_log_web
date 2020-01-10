# coding=utf-8
import os
import re
from subprocess import PIPE, Popen
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
                                                                                            "").replace("\x1b[1m",
                                                                                                        "").replace(
        "\x1b[?1l\x1b>\x1b[47;1H", "")
    # 再处理一次，末尾可能还没清理完全
    top_output = re.sub('\x1b.*?\s', "", top_output)
    _html = ''
    for num, line in enumerate(top_output.split('\n')):
        if num >= 6:
            if num == 6:
                new_line = "<table><tbody><tr>"
            else:

                new_line = "<tr>"
            td_list = re.split(r" +", line)
            if td_list:
                first_td = td_list[0]  # 第一个td里当数字长度小于7位时为空，第12列及以后为COMMAND列，否则第11列及以后才是

                if len(first_td.strip()) < 7:
                    end_num = 12
                else:
                    end_num = 11
                for td_num, td in enumerate(td_list):
                    # print(td_num, repr(td))

                    if td_num < end_num:
                        if td.strip():
                            new_line += f"<td>{(8-len(td))*'&ensp;'+td}</td>"
                    else:
                        new_line += f"<td  style='text-align: left;padding-left: 10px'>{td}</td>"

            new_line += "</tr>"
        else:
            new_line = '<div>' + line.replace(' ', "&ensp;") + '</div>'

        _html += new_line
    _html += '</tbody></table>'
    return _html


def get_ps_aux_info(n=40):
    process = Popen(f"ps aux|head -n {n}", shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    output = process.stdout.read()
    _html = '<table>'
    for line in output.split('\n'):
        if line:
            td_list = re.split(r" +", line)
            new_line = '<tr>'
            for td_num, td in enumerate(td_list):
                if td.strip():
                    print(td_num, repr(td))
                    if td_num < 10:
                        new_line += f"<td>{(8-len(td))*'&ensp;'+td}</td>"
                    else:  # 第10行以后是command
                        new_line += f"<td  style='text-align: left;padding-left: 10px'>{td}</td>"

            new_line += "</tr>"
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


@app.route('/ps_aux', methods=['GET'])
def ps_aux_html():
    return render_template('ps_aux.html')


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


@socketio.on('handle_ps_aux', namespace="/shell")
def handle_ps_aux(message):
    print('received handle_ps_aux message: ' + message.get('data', ''))

    ps_aux_info = get_ps_aux_info()
    socketio.emit('ps_aux_response', {'text': ps_aux_info}, namespace='/shell')


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
