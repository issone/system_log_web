# coding=utf-8

from public import app, socketio

from flask import render_template
from utils.command import ps_command, top_command, tail_command


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


@socketio.on('client', namespace="/shell")
def client_info(data):
    print('client data', data)
    _type = data.get('_type')
    if _type == 'tail':
        tail_command.background_thread()
    elif _type == 'ps':
        ps_command.background_thread()
    elif _type == 'top':
        top_command.background_thread()
    else:
        socketio.emit('response', {'text': '未知命令'}, namespace='/shell')


@socketio.on('leave', namespace="/shell")
def leave(data):
    print('leave data', data)
    _type = data.get('_type')
    if _type == 'tail':
        tail_command.leave()
    elif _type == 'ps':
        ps_command.leave()
    elif _type == 'top':
        top_command.leave()
    else:
        socketio.emit('response', {'text': '未知命令'}, namespace='/shell')


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000)
