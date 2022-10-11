#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Поиск хостов которые не освобождают лицензии 1с.
Поиск производится с помощью утилиты HaspMonitor.exe
Программа запускается в планировщике задач cron (crontab -e).
Правило запуска:
*/5 * * * * python3 /home/user/prg/find_fail_1c_licenses/find_fail_1c_licenses.py --debug 1>/home/user/prg/stdout_find_fail_1c_licenses.log 2>/home/user/prg/error_find_fail_1c_licenses.log

Запуск:

        python3 find_fail_1c_licenses.py [параметры командной строки]

Параметры командной строки:

    [Помощь и отладка]
        --help|-h|-?        Помощь
        --version|-v        Версия программы
        --debug|-d          Включить сообщения отладки

"""

import sys
import getopt
import os
import os.path
import locale
import traceback
import datetime
import subprocess

__version__ = (0, 0, 0, 1)

DEBUG_MODE = False

# Домашняя папка
# HOME_PATH = os.environ['HOME'] if 'HOME' in os.environ else (os.environ.get('HOMEDRIVE',
#                                                                             '') + os.environ.get('HOMEPATH', ''))
SAVE_DIRNAME = os.path.dirname(__file__) if __file__ else ''

# Наименование результирующего файла по умолчанию
DEFAULT_PREV_FILENAME = 'hasp_monitor.prev'
DEFAULT_CUR_FILENAME = 'hasp_monitor.cur'
DEFAULT_FIND_FILENAME = 'hasp_monitor.find'

# Полное наименование результирующего файла
PREV_FILENAME = os.path.join(SAVE_DIRNAME, DEFAULT_PREV_FILENAME)
CUR_FILENAME = os.path.join(SAVE_DIRNAME, DEFAULT_CUR_FILENAME)
FIND_FILENAME = os.path.join(SAVE_DIRNAME, DEFAULT_FIND_FILENAME)

DATETIME_FMT = '%Y-%m-%d %H:%M:%S'

#
CUR_DIRNAME = os.path.dirname(__file__) if __file__ else '.'
GET_LICENSE_SERVER_INFO_CMD = ('wine', os.path.join(CUR_DIRNAME, 'HaspMonitor.exe'), 'SET CONFIG,FILENAME=./NETHASP.INI', 'SCAN SERVERS', 'GET SERVERS')
GET_LICENSES_INFO_CMD = ('wine', os.path.join(CUR_DIRNAME, 'HaspMonitor.exe'), 'SET CONFIG,FILENAME=./NETHASP.INI', 'SCAN SERVERS', 'GET LOGINS,HS,ID=,MA=1')
GET_LICENSE_PARAM_FMT = 'GET LOGINS,HS,ID=%s,MA=1'
INFO_SIGNATURE = 'HS,'
INFO_DELIMETER = ','
PARAM_DELIMETER = '='

# Разделитель
DEFAULT_DELIMETER = ';\t'
ALTER_DELIMETER = u',\t'
# COMMENT_SIGNATURE = '#'

# Кодировка командной оболочки по умолчанию
DEFAULT_ENCODING = sys.stdout.encoding if sys.platform.startswith('win') else locale.getpreferredencoding()

# Цвета в консоли
RED_COLOR_TEXT = '\x1b[31;1m'       # red
GREEN_COLOR_TEXT = '\x1b[32m'       # green
YELLOW_COLOR_TEXT = '\x1b[33;1m'    # yellow
BLUE_COLOR_TEXT = '\x1b[34m'        # blue
PURPLE_COLOR_TEXT = '\x1b[35m'      # purple
CYAN_COLOR_TEXT = '\x1b[36m'        # cyan
WHITE_COLOR_TEXT = '\x1b[37m'       # white
NORMAL_COLOR_TEXT = '\x1b[0m'       # normal


def get_default_encoding():
    """
    Определить актуальную кодировку для вывода текста.

    :return: Актуальная кодировка для вывода текста.
    """
    return DEFAULT_ENCODING


def print_color_txt(txt, color=NORMAL_COLOR_TEXT):
    """
    Печать цветного текста.

    :param txt: Текст.
    :param color: Консольный цвет.
    """
    if sys.platform.startswith('win'):
        # Для Windows систем цветовая раскраска отключена
        txt = txt
    else:
        # Добавление цветовой раскраски
        txt = color + txt + NORMAL_COLOR_TEXT
    print(txt)


def debug(message=u''):
    """
    Вывести ОТЛАДОЧНУЮ информацию.

    :param message: Текстовое сообщение.
    """
    print_color_txt('DEBUG. ' + message, BLUE_COLOR_TEXT)


def info(message=u''):
    """
    Вывести ТЕКСТОВУЮ информацию.

    :param message: Текстовое сообщение.
    """
    print_color_txt('INFO. ' + message, GREEN_COLOR_TEXT)


def error(message=u''):
    """
    Вывести информацию ОБ ОШИБКЕ.

    :param message: Текстовое сообщение.
    """
    print_color_txt('ERROR. ' + message, RED_COLOR_TEXT)


def warning(message=u''):
    """
    Вывести информацию ОБ ПРЕДУПРЕЖДЕНИИ.

    :param message: Текстовое сообщение.
    """
    print_color_txt('WARNING. ' + message, YELLOW_COLOR_TEXT)


def fatal(message=u''):
    """
    Вывести информацию ОБ ОШИБКЕ.

    :param message: Текстовое сообщение.
    """
    trace_txt = traceback.format_exc()

    try:
        msg = message + u'\n' + trace_txt
    except UnicodeDecodeError:
        if not isinstance(message, str):
            message = str(message)
        if not isinstance(trace_txt, str):
            trace_txt = str(trace_txt)
        msg = message + u'\n' + trace_txt

    print_color_txt('FATAL. ' + msg, RED_COLOR_TEXT)


def toUnicode(value, code_page='utf-8'):
    """
    Convert any value to unicode.

    :param value: Value.
    :param code_page: Code page.
    """
    if isinstance(value, str):
        return value
    elif isinstance(value, bytes):
        return value.decode(code_page)
    return str(value)


def replaceInText(text, replacements):
    """
    Make a number of replacements in the text.

    :param text: Text.
    :param replacements: Replacements.
        Can be specified as a dictionary or a list of tuples.
        Dictionary:
            {
            'source replace': 'destination replace', ...
            }
        List of tuples (used when the order of replacements is important ):
            [
            ('source replace', 'destination replace'), ...
            ]
    :return: The text with all the replacements made, or the original text in case of an error.
    """
    result_text = text
    try:
        if isinstance(replacements, dict):
            for src_txt, dst_txt in replacements.items():
                result_text = result_text.replace(src_txt, dst_txt)
        elif isinstance(replacements, list) or isinstance(replacements, tuple):
            for src_txt, dst_txt in replacements:
                result_text = result_text.replace(src_txt, dst_txt)
        else:
            # Incorrect type
            return text
        return result_text
    except:
        fatal(u'Error replace in text')
        return text


def saveTextFile(txt_filename, txt='', rewrite=True):
    """
    Save text file.

    :param txt_filename: Text file name.
    :param txt: Body text file as unicode.
    :param rewrite: Rewrite file if it exists?
    :return: True/False.
    """
    global DEBUG_MODE

    if not isinstance(txt, str):
        txt = str(txt)

    file_obj = None
    try:
        if rewrite and os.path.exists(txt_filename):
            os.remove(txt_filename)
            if DEBUG_MODE:
                info(u'Remove file <%s>' % txt_filename)
        if not rewrite and os.path.exists(txt_filename):
            if DEBUG_MODE:
                warning(u'File <%s> not saved' % txt_filename)
            return False

        # Check path
        txt_dirname = os.path.dirname(txt_filename)
        if not os.path.exists(txt_dirname):
            os.makedirs(txt_dirname)

        file_obj = open(txt_filename, 'wt')
        file_obj.write(txt)
        file_obj.close()
        return True
    except:
        if file_obj:
            file_obj.close()
        if DEBUG_MODE:
            fatal(u'Save text file <%s> error' % txt_filename)
    return False


def readTextFileLines(txt_filename, auto_strip_line=True):
    """
    Read text file as lines.

    :param txt_filename: Text filename.
    :param auto_strip_line: Strip text file lines automatic?
    :return: Text file lines.
    """
    file_obj = None
    lines = list()

    if not os.path.exists(txt_filename):
        # If not exists file then create it
        if DEBUG_MODE:
            warning(u'File <%s> not found' % txt_filename)

        try:
            file_obj = open(txt_filename, 'wt')
            file_obj.close()
            if DEBUG_MODE:
                info(u'Create text file <%s>' % txt_filename)
        except:
            if file_obj:
                file_obj.close()
            if DEBUG_MODE:
                fatal(u'Error create text file <%s>' % txt_filename)
        return lines

    try:
        file_obj = open(txt_filename, 'rt')
        lines = file_obj.readlines()
        if auto_strip_line:
            lines = [filename.strip() for filename in lines]
        file_obj.close()
        file_obj = None
    except:
        if file_obj:
            file_obj.close()
        if DEBUG_MODE:
            fatal(u'Error read text file <%s>' % txt_filename)
    return list(lines)


def appendTextFileLine(line, txt_filename=None, add_linesep=True):
    """
    Add new line in text file.

    :param line: Line as string.
    :param txt_filename: Text filename.
    :param add_linesep: Add line separator / carriage return?
    :return: True/False.
    """
    file_obj = None
    try:
        # Check path
        txt_dirname = os.path.dirname(txt_filename)
        if not os.path.exists(txt_dirname):
            os.makedirs(txt_dirname)
            if DEBUG_MODE:
                debug(u'Create directory <%s>' % txt_dirname)

        file_obj = open(txt_filename, 'at+')
        file_obj.write(str(line))
        if add_linesep:
            file_obj.write(os.linesep)
        file_obj.close()
        return True
    except:
        if file_obj:
            file_obj.close()
        if DEBUG_MODE:
            fatal(u'Error add line in text file <%s>' % txt_filename)
    return False


def exec_sys_cmd(command, split_lines=False):
    """
    Выполнить системную комманду и получить результат ее выполнения.

    :param command: Системная комманда.
    :param split_lines: Произвести разделение на линии?
    :return: Если нет разделения по линиям, то возвращается текст который
        отображается в консоли.
        При разбитии по линиям возвращается список выводимых строк.
        В случае ошибки возвращается None.
    """
    try:
        if isinstance(command, str):
            cmd = command.strip().split(' ')
        elif isinstance(command, (list, tuple)):
            cmd = command
        else:
            if DEBUG_MODE:
                error(u'Ошибка формата командной строки %s' % command)
            return None

        console_encoding = locale.getpreferredencoding()
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        if split_lines:
            b_lines = process.stdout.readlines()
            lines = [line.decode(console_encoding).strip() for line in b_lines]
            return lines
        else:
            b_text = process.stdout.read()
            text = b_text.decode(console_encoding)
            return text
    except:
        fatal(u'Ошибка выполнения системной комманды <%s>' % command)
    return None


def parse_license_server_id(line):
    """
    Распарсить идентификатор сервера лицензий.

    :param line: Информация о сервере лицензий.
    :return: Идентификатор сервера лицензий.
    """
    params = line.strip().split(INFO_DELIMETER)
    id_params = [param[3:].strip() for param in params if param.startswith('ID=')]
    if id_params:
        return id_params[0]
    else:
        if DEBUG_MODE:
            warning(u'Ошибка формата информации о сервере лицензий <%s>' % line)
    return None


def parse_license(line):
    """
    Распарсить информацию о лицензии.

    :param line: Информация о лицензии.
    :return: Описание лицензии.
    """
    params = line.strip().split(INFO_DELIMETER)
    params = dict([(param.strip().split(PARAM_DELIMETER)[0], eval(param.strip().split(PARAM_DELIMETER)[1])) for param in params if PARAM_DELIMETER in param])
    if params:
        return params
    else:
        if DEBUG_MODE:
            warning(u'Ошибка формата информации о сервере лицензий <%s>' % line)
    return None


def get_license_server_id():
    """
    Определяем идентификатор сервера лицензий.

    :return:
    """
    lines = exec_sys_cmd(GET_LICENSE_SERVER_INFO_CMD, split_lines=True)
    if isinstance(lines, list):
        lines = [line for line in lines if line.startswith(INFO_SIGNATURE)]
        if len(lines) == 1:
            id = parse_license_server_id(lines[0])
            return id
        elif len(lines) > 1:
            ids = [parse_license_server_id(line) for line in lines]
            return ids
        else:
            if DEBUG_MODE:
                warning(u'Нет данных о серверах')
    else:
        if DEBUG_MODE:
            error(u'Ошибка выполнения команды <%s>' % GET_LICENSE_SERVER_INFO_CMD)
    return None


def get_licenses(server_id):
    """
    Определяем идентификатор сервера лицензий.

    :param server_id: Идентификатор сервера лицензий.
    :return: Список строк лицензий.
    """
    param = GET_LICENSE_PARAM_FMT % server_id
    cmd = list(GET_LICENSES_INFO_CMD)
    cmd[-1] = param

    lines = exec_sys_cmd(cmd, split_lines=True)
    if isinstance(lines, list):
        lines = [line for line in lines if line.startswith(INFO_SIGNATURE)]
        if len(lines) > 0:
            info = [parse_license(line) for line in lines]
            return info
        else:
            if DEBUG_MODE:
                warning(u'Нет данных о лицензиях')
    else:
        if DEBUG_MODE:
            error(u'Ошибка выполнения команды <%s>' % cmd)
    return None


def _run(id):
    """
    Функция скрипта.
    """
    # Определяем информацию по лицензиям
    licenses = get_licenses(server_id=id)
    if not licenses:
        if DEBUG_MODE:
            warning(u'Идентификатор сервера лицензий [%s]. Лицензии не найдены' % id)
        return
    else:
        if DEBUG_MODE:
            debug(u'Идентификатор сервера лицензий [%s]. Найдены лицензии:' % id)
            for license in licenses:
                debug(u'\t%s' % license)

    # Проверяем есть файл предыдущий
    dst_filename = None
    if not os.path.exists(PREV_FILENAME):
        dst_filename = PREV_FILENAME
    else:
        if not os.path.exists(CUR_FILENAME):
            dst_filename = CUR_FILENAME
        else:
            os.remove(PREV_FILENAME)
            os.rename(CUR_FILENAME, PREV_FILENAME)
            dst_filename = CUR_FILENAME
    # Сохраняем результат
    if dst_filename:
        txt = os.linesep.join(
            [DEFAULT_DELIMETER.join((license['NAME'], license['PROT'], str(license['TIMEOUT']))) for license in
             licenses])
        saveTextFile(dst_filename, txt)

    # Производим анализ
    if os.path.exists(PREV_FILENAME) and os.path.exists(CUR_FILENAME):
        prev_lines = [line.split(DEFAULT_DELIMETER) for line in readTextFileLines(PREV_FILENAME)]
        cur_lines = [line.split(DEFAULT_DELIMETER) for line in readTextFileLines(CUR_FILENAME)]
        for line in cur_lines:
            if not line[0].strip():
                find_line = [prev_line for prev_line in prev_lines if prev_line[1] == line[1] and prev_line[0].strip()]
                if find_line:
                    txt_line = datetime.datetime.now().strftime(DATETIME_FMT) + u'\t' + DEFAULT_DELIMETER.join(
                        find_line[0])
                    appendTextFileLine(txt_line, FIND_FILENAME)


def run():
    """
    Функция скрипта.
    """
    global DEBUG_MODE

    result = False

    # Определяем идентификатор сервера лицензий
    id = get_license_server_id()

    if isinstance(id, str):
        _run(id)
    elif isinstance(id, (list, tuple)):
        for srv_id in id:
            _run(srv_id)
    else:
        if DEBUG_MODE:
            warning(u'Ошибка данных для сохранения')
    return result


def main(*argv):
    """
    Главная запускаемая функция.

    :param argv: Параметры коммандной строки.
    :return:
    """
    global DEBUG_MODE

    documents = list()

    try:
        options, args = getopt.getopt(argv, 'h?vd',
                                      ['help', 'version', 'debug'])
    except getopt.error as msg:
        error(str(msg))
        info(__doc__)
        sys.exit(2)

    for option, arg in options:
        if option in ('-h', '--help', '-?'):
            info(__doc__)
            sys.exit(0)
        elif option in ('-v', '--version'):
            str_version = 'Версия: %s' % '.'.join([str(sign) for sign in __version__])
            info(str_version)
            sys.exit(0)
        elif option in ('-d', '--debug'):
            DEBUG_MODE = True
            info(u'Включен режим отладки')
        else:
            if DEBUG_MODE:
                msg = u'Не поддерживаемый параметр командной строки <%s>' % option
                error(msg)

    try:
        run()
    except:
        if DEBUG_MODE:
            fatal(u'Ошибка выполнения:')


if __name__ == '__main__':
    main(*sys.argv[1:])
