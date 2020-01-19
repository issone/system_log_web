# coding=utf-8
import os
import re
import platform
from subprocess import PIPE, Popen
from threading import Lock
from config import LOG_FILE, EVENT_NAME, NAMESPACE

from public import socketio


class Command:

    def __init__(self, cmd_name, event_name=None, name_space=None, *args, **kwargs):
        '''

        :param cmd_name: 命令名称
        :param event_name: socketio 事件名称
        :param name_space: socketio 名称空间
        '''
        self.lock = self.get_lock()
        self.close_thread = False
        self.thread = None
        self.client_num = 0  # 连入数量
        self.event_name = event_name
        self.namespace = name_space
        self.cmd_name = cmd_name

    def get_lock(self):
        return Lock()

    def stop(self):
        with self.lock:
            self.close_thread = True

    def incr(self, num=1):
        with self.lock:
            self.client_num += num
            if self.client_num < 0:
                self.client_num = 0
                self.close_thread = True

    def send_response(self, text):
        socketio.emit(self.event_name, {'text': text, '_type': self.cmd_name}, namespace=self.namespace)

    def sleep(self, seconds):
        socketio.sleep(seconds)

    def leave(self):
        self.incr(num=-1)
        print(f'离开{self.cmd_name},客户端还剩', self.client_num)


class TopCommand(Command):

    def top_n(self, html=False):
        if 'freebsd' in platform.platform().lower():
            top_pipe = os.popen('top -d 1')
        else:
            top_pipe = os.popen('top -n 1')
        try:
            top_output = top_pipe.read()
        finally:
            top_pipe.close()

        # 用print输出top_output看着没问题，但是用repr输出会发现有很多其他字符，这些字符会被发往前端，导致页面上数据混乱
        # 暂时先直接替换处理
        top_output = top_output.replace("\x1b(B\x1b[m", "").replace("\x1b(B\x1b[m\x1b[39;49m\x1b[K", "").replace(
            "\x1b[?1h\x1b=\x1b[?25l\x1b[H\x1b[2J", "").replace("\x1b[39;49m\x1b[1m", "").replace("\x1b[39;49m\x1b[K",
                                                                                                 "").replace(
            "\x1b[39;49m",
            "").replace(
            "\x1b[K", "").replace("\x1b[7m", "").replace("\x1b[?1l\x1b>\x1b[45;1H", "").replace("\x1b[?12l\x1b[?25h",
                                                                                                "").replace("\x1b[1m",
                                                                                                            "").replace(
            "\x1b[?1l\x1b>\x1b[47;1H", "")
        # 再处理一次，末尾可能还没清理完全
        top_output = re.sub('\x1b.*?\s', "", top_output)
        if not html:
            return top_output
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

    def background_thread(self):
        self.incr()
        print('有客户端进入top页面，当前页面客户端数量为', self.client_num)
        with self.lock:
            if self.thread is None:
                self.close_thread = False
                self.thread = socketio.start_background_task(target=self.top)

    def top(self, interval=3):
        '''
        :param interval: 刷新间隔
        :return:
        '''
        while self.client_num and not self.close_thread:
            top_info = self.top_n(html=True)

            self.send_response(top_info)
            self.sleep(interval)
        print('离开top,客户端还剩', self.client_num)


class TailCommand(Command):
    def get_result(self, html=False):
        if 'freebsd' in platform.platform().lower():
            top_pipe = os.popen('top -d 1')
        else:
            top_pipe = os.popen('top -n 1')
        try:
            top_output = top_pipe.read()
        finally:
            top_pipe.close()

        # 用print输出top_output看着没问题，但是用repr输出会发现有很多其他字符，这些字符会被发往前端，导致页面上数据混乱
        # 暂时先直接替换处理
        top_output = top_output.replace("\x1b(B\x1b[m", "").replace("\x1b(B\x1b[m\x1b[39;49m\x1b[K", "").replace(
            "\x1b[?1h\x1b=\x1b[?25l\x1b[H\x1b[2J", "").replace("\x1b[39;49m\x1b[1m", "").replace("\x1b[39;49m\x1b[K",
                                                                                                 "").replace(
            "\x1b[39;49m",
            "").replace(
            "\x1b[K", "").replace("\x1b[7m", "").replace("\x1b[?1l\x1b>\x1b[45;1H", "").replace("\x1b[?12l\x1b[?25h",
                                                                                                "").replace("\x1b[1m",
                                                                                                            "").replace(
            "\x1b[?1l\x1b>\x1b[47;1H", "")
        # 再处理一次，末尾可能还没清理完全
        top_output = re.sub('\x1b.*?\s', "", top_output)
        if not html:
            return top_output
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

    def background_thread(self):
        self.incr()
        print('有客户端进入tail页面，当前页面客户端数量为', self.client_num)
        with self.lock:
            if self.thread is None:
                self.close_thread = False
                self.thread = socketio.start_background_task(target=self.tail_f)

    def tail_f(self, log_path=LOG_FILE):

        try:
            tail_pipe = os.popen('tail -f ' + log_path)
        except:
            print('文件不存在')
            return
        else:
            while not self.close_thread:
                tail_output = tail_pipe.readline()
                if tail_output.strip():
                    self.send_response(tail_output)
            tail_pipe.close()
            print('离开tail,客户端还剩', self.client_num)


class PsCommand(Command):
    def ps_aux(self, n=35, html=False):
        '''
        查看ps aux命令前n行的结果
        :param n: 行数
        :return:
        '''
        process = Popen(f"ps aux|head -n {n}", shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        output = process.stdout.read()
        if not html:
            return output
        _html = '<table>'
        for line in output.split('\n'):
            if line:
                td_list = re.split(r" +", line)
                new_line = '<tr>'
                for td_num, td in enumerate(td_list):
                    if td.strip():
                        if td_num < 10:
                            new_line += f"<td>{(8-len(td))*'&ensp;'+td}</td>"
                        else:  # 第10行以后是command
                            new_line += f"<td  style='text-align: left;padding-left: 10px'>{td}</td>"

                new_line += "</tr>"
                _html += new_line
        _html += '</table>'
        return _html

    def background_thread(self):
        self.incr()
        print('有客户端进入ps_aux页面，当前页面客户端数量为', self.client_num)
        with self.lock:
            if self.thread is None:
                self.close_thread = False
                self.thread = socketio.start_background_task(target=self.watch_ps_aux)

    def watch_ps_aux(self, n=35, interval=2):
        '''
        :param n: 显示行数
        :param interval: 刷新间隔
        :return:
        '''
        while self.client_num and not self.close_thread:
            ps_aux_info = self.ps_aux(n=n, html=True)

            self.send_response(ps_aux_info)
            self.sleep(interval)
        print('离开ps,客户端还剩', self.client_num)


top_command = TopCommand(cmd_name='top', event_name=EVENT_NAME, name_space=NAMESPACE)
tail_command = TailCommand(cmd_name='tail', event_name=EVENT_NAME, name_space=NAMESPACE)
ps_command = PsCommand(cmd_name='ps', event_name=EVENT_NAME, name_space=NAMESPACE)
