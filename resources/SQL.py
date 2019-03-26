# coding: utf-8
import datetime


def get_phone_number(cursor, port):
    cursor.execute('SELECT phone_number FROM abon_argus WHERE port = "{}"'.format(port))
    result = cursor.fetchone()
    if result is None:
        return False
    else:
        return result[0]
    

def get_account_name_phone(cursor, phone_number):
    cursor.execute('SELECT account_name FROM abon_onyma WHERE phone_number = "{}"'.format(phone_number))
    result = cursor.fetchone()
    if result is None:
        return False
    else:
        return result[0]


def get_accounts_info(cursor):
    result = {}
    cursor.execute('SELECT account_name, phone_number, hostname, board, port, tariff_speed, tv FROM abon_onyma WHERE hostname IS NOT NULL')
    data = cursor.fetchall()
    for account in data:
        result[account[0]] = {'phone_number': account[1], 'hostname': account[2], 'board': account[3], 'port': account[4], 'tariff_speed': account[5], 'tv': account[6]}
    return result


def get_data_profiles(cursor):
    result = {}
    cursor.execute('SELECT hostname, board, port, profile_name, dw_limit FROM data_profiles')
    data = cursor.fetchall()
    for port in data:
        result['{}/{}/{}'.format(port[0], port[1], port[2])] = {'profile_name':  port[3], 'dw_limit': port[4]}
    return result


def get_speed(cursor, incident):
    if incident.hostname is None:
        return {'min_speed': '-', 'avg_speed': '-'}
    between = get_between_str(incident)
    command = '''
            SELECT
                ROUND(MIN(max_dw_rate)),
                ROUND(AVG(max_dw_rate))
            FROM
                data_dsl
            WHERE
                hostname = '{}'
                AND board = {}
                AND port = {}
                AND datetime BETWEEN STR_TO_DATE('{}', '%Y-%m-%d %H:%i:%s')
                AND STR_TO_DATE('{}', '%Y-%m-%d %H:%i:%s')    
    '''.format(incident.hostname, incident.board, incident.port, between['start'], between['end'])
    cursor.execute(command)
    speed = cursor.fetchone()
    return {'min_speed': speed[0], 'avg_speed': speed[1]}


def get_between_str(incident):
    yesterday = datetime.datetime.now().date() - datetime.timedelta(days=1)
    delta = yesterday - incident.end_time.date()
    if delta.days > 0:
        start = '{} 00:00:00'.format(yesterday.strftime('%Y-%m-%d'))
    else:
        start = '{}:00:00'.format((incident.end_time + datetime.timedelta(seconds=3600)).strftime('%Y-%m-%d %H')) 
    return {'start': start, 'end': '{} 23:59:59'.format(datetime.datetime.now().strftime('%Y-%m-%d'))}