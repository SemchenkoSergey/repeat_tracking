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


def get_all_speed(cursor):
    today = '{} 23:59:59'.format(datetime.datetime.now().strftime('%Y-%m-%d'))
    yesterday = '{} 00:00:00'.format((datetime.datetime.now().date() - datetime.timedelta(days=1)).strftime('%Y-%m-%d'))
    result = {}
    command = '''
            SELECT
                hostname,
                board,
                port,
                ROUND(MIN(max_dw_rate)),
                ROUND(AVG(max_dw_rate)),
                MIN(up_snr),
                MIN(dw_snr)
            FROM
                data_dsl
            WHERE
                datetime BETWEEN STR_TO_DATE('{}', '%Y-%m-%d %H:%i:%s')
                AND STR_TO_DATE('{}', '%Y-%m-%d %H:%i:%s')
            GROUP BY hostname, board, port
    '''.format(yesterday, today)
    cursor.execute(command)
    data = cursor.fetchall()
    for port in data:
        result['{}/{}/{}'.format(port[0], port[1], port[2])] = {'min_speed':  port[3], 'avg_speed': port[4], 'up_snr': port[5], 'dw_snr': port[6]}    
    return result