#!/usr/bin/env python3
# coding: utf8

import openpyxl
import datetime
import os
import MySQLdb
import re
import pickle
import csv
from resources import Incident
from concurrent.futures import ThreadPoolExecutor
from resources import Web
from resources import SQL
from resources import Settings
import warnings
warnings.filterwarnings("ignore")


def read_argus_file(incidents):
    file_list = ['files' + os.sep + x for x in os.listdir('files')]
    for file in file_list:
        if file.split('.')[-1] != 'xlsx':
            #os.remove(file)
            continue
        print('Обработка файла {}'.format(file))
        try:
            wb = openpyxl.load_workbook(file)
        except Exception as ex:
            print('Не удалось прочитать файл - {}'.format(file))
            print(ex)
            continue
        else:
            sh = wb.active
            if sh['A1'].value != 'Номер':
                continue
            for row in  range(2, sh.max_row + 1):
                technology = sh['P{}'.format(row)].value
                if technology != 'по технологии ADSL':
                    continue
                end_time = sh['U{}'.format(row)].value
                if (datetime.datetime.now() - end_time).days > Settings.days:
                    continue
                incident_number = sh['A{}'.format(row)].value
                service_number = sh['B{}'.format(row)].value
                fio = sh['V{}'.format(row)].value
                address = '{}, {}'.format(sh['W{}'.format(row)].value, sh['X{}'.format(row)].value)
                client_type = sh['K{}'.format(row)].value
                ldn =  sh['AB{}'.format(row)].value
                # Если инцидент уже есть, то обновляю дату закрытия
                if service_number in incidents:
                    if end_time <= incidents[service_number].end_time:
                        continue
                    else:
                        print('Обновлен инцидент {} - старое время: {}, новое время: {}'.format(service_number, incidents[service_number].end_time.strftime('%Y-%m-%d %H:%M'), end_time.strftime('%Y-%m-%d %H:%M')))
                        incidents[service_number].end_time = end_time
                else:
                    # Создание инцидента
                    incident = Incident.Incident(incident_number=incident_number,\
                                                 service_number=service_number,\
                                                 fio=fio,\
                                                 address=address,\
                                                 client_type=client_type,\
                                                 end_time=end_time,
                                                 ldn=ldn)                  
                    incidents[service_number] = incident   
        os.remove(file)


def get_onyma_params(arguments):
    print('запуск потока обработки инцидентов...')
    incidents = arguments[0]
    keys = arguments[1]
    thread_number = arguments[2]
    re_port = re.compile(r'(STV.+?)\[.*?\(Л\)\s+?-\s+?(.+?)-\s?(\d+)')
    # Подключение к MySQL
    connect = MySQLdb.connect(host=Settings.db_host, user=Settings.db_user, password=Settings.db_password, db=Settings.db_name, charset='utf8')
    cursor = connect.cursor()      
    # Открытие соединений Onyma и Argus
    onyma = Web.connect_onyma()
    argus = Web.connect_argus()
    
    for incident in keys:
        # Если параметры уже установлены
        if incidents[incident].bill is not None:
            continue
        # Если нет
        #print('Поток {}, обработка инцидента {}'.format(thread_number, incident))
        params = False
        if incidents[incident].account_name:
            # Если номер карты есть, но параметры еще не определены
            print('Новая попытка получить параметры для {}'.format(incidents[incident].account_name))
            params = Web.find_login_param(onyma, account_name=incidents[incident].account_name)
            if not params['bill']:
                print('не удалось найти параметры для {}'.format(incidents[incident].account_name))
        else:
            login = Web.get_login(argus, incidents[incident].incident_number)
            if login:
                params = Web.find_login_param(onyma, login=login)
            else:
                # В комментариях Argus нет логина
                try:
                    port = '{}-{}-{}'.format(re_port.search(incidents[incident].ldn).group(1).strip(), re_port.search(incidents[incident].ldn).group(2).strip(), re_port.search(incidents[incident].ldn).group(3).strip())
                except:
                    # Не удалось распознать порт DSLAM
                    print('В комментариях нет логина, порт DSLAM в линейных данных не распознан ({})'.format(incident))
                    continue
                phone_number = SQL.get_phone_number(cursor, port)
                if phone_number:
                    account_name = SQL.get_account_name_phone(cursor, phone_number)
                    if account_name:
                        params = Web.find_login_param(onyma, account_name=account_name)
                    else:
                        # Не удалось найти аккаунт по номеру телефона
                        print('Не удалось найти учетное имя по номеру телефона ({})'.format(incident))
                        continue
                else:
                    # Не удалось найти номер телефона по порту
                    print('Не удалось найти номер телефона по порту DSLAM ({})'.format(incident))
                    continue
        if params:
            incidents[incident].account_name = params['account_name']
            incidents[incident].bill = params['bill']
            incidents[incident].dmid = params['dmid']
            incidents[incident].tmid = params['tmid']
            if params['bill']:
                print('Найдены параметры для инцидента {}: account_name - {}, bill - {}, dmid - {}, tmid - {}'.format(incident, params['account_name'], params['bill'], params['dmid'], params['tmid']))
            else:
                print('Найдено имя аккаунта для {}: {}'.format(incident, params['account_name']))
        else:
            continue
    # Закрытие соединений
    connect.close()
    onyma.close()
    argus.close()
            

def print_report(incidents):
    bad_onyma = []
    bad_account = []
    for incident in incidents:
        if incidents[incident].account_name is None:
            bad_account.append(incidents[incident])
        if incidents[incident].bill is None:
            bad_onyma.append(incidents[incident])
    print('Всего инцидентов: {}'.format(len(incidents)))
    print('Без номера карты: {}'.format(len(bad_account)))
    print('Без параметров Онимы: {}'.format(len(bad_onyma)))


def load_incidents():
    result = {}
    try:
        with open('resources{}incidents.db'.format(os.sep), 'br') as file_load:
            incidents = pickle.load(file_load)
    except:
        return result
    for incident in incidents:
        if (datetime.datetime.now() - incidents[incident].end_time).days > Settings.days:
            continue
        else:
            result[incident] = incidents[incident]
            #result[incident].clean()              
    return result


def main():  
    print('Время запуска: {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M')))
    print('Загрузка сохраненных инцидентов')
    incidents = load_incidents()    
    read_argus_file(incidents)
    print_report(incidents)
    arguments = [[incidents, list(incidents.keys())[x::Settings.threads_count], x] for x in range(0, Settings.threads_count)]
    
    with ThreadPoolExecutor(max_workers=Settings.threads_count) as executor:
        executor.map(get_onyma_params, arguments) 
        
    # Запись инцидентов в файл
    with open('resources{}incidents.db'.format(os.sep), 'bw') as file_dump:
        pickle.dump(incidents, file_dump)
        
    print_report(incidents)

    print('Время окончания: {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M')))


if __name__ == '__main__':
    cur_dir = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-1])
    os.chdir(cur_dir)
    main()