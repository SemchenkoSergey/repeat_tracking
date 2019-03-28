#!/usr/bin/env python3
# coding: utf8

import re
import os
import time
import pickle
import MySQLdb
import datetime
import openpyxl
import csv
from resources import Incident
from concurrent.futures import ThreadPoolExecutor
from resources import Web
from resources import SQL
from resources import Settings
import warnings
warnings.filterwarnings("ignore")


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


def update_accounts_data(arguments):
    incidents = arguments[0]
    keys = arguments[1]
    prev_day = datetime.date.today() - datetime.timedelta(days=1)
    # Открытие соединения Onyma
    onyma = Web.connect_onyma()
    
    for incident in keys:
        if (incidents[incident].proc_date == datetime.date.today()) or (incidents[incident].bill is None):
            continue
        
        account_data = Web.get_account_data(onyma, incidents[incident],  prev_day)
        if not account_data:
            incidents[incident].hostname = None
            incidents[incident].board = None
            incidents[incident].port = None
            incidents[incident].session_count = None
            incidents[incident].proc_date = datetime.date.today()
            
            
            continue
        if (account_data['session_count'] > 0) and (account_data['hostname'] is None):
            print('Сессии были, но DSLAM не распознан: {}'.format(incidents[incident].account_name))
        incidents[incident].hostname = account_data['hostname']
        incidents[incident].board = account_data['board']
        incidents[incident].port = account_data['port']
        incidents[incident].session_count = account_data['session_count']
        incidents[incident].proc_date = datetime.date.today()        

        #print(incidents[incident].account_name, account_data)


def generate_report_file(incidents):
    # Подключение к MySQL
    connect = MySQLdb.connect(host=Settings.db_host, user=Settings.db_user, password=Settings.db_password, db=Settings.db_name, charset='utf8')
    cursor = connect.cursor()
    # Получение данных о абонентах из базы данных
    accounts_info = SQL.get_accounts_info(cursor)
    
    # Получение профилей линий с DSLAM
    data_profiles = SQL.get_data_profiles(cursor)

    # Сортировка инцидентов по дате
    incidents = sort_incidents(incidents)
    
    # Добавление информации к инцидентам
    for incident in incidents:
        if incident.account_name in accounts_info:
            incident.phone_number = accounts_info[incident.account_name]['phone_number']
            incident.tariff_speed = accounts_info[incident.account_name]['tariff_speed']
            incident.tv = accounts_info[incident.account_name]['tv']
        incident.day_count = (datetime.datetime.now() - incident.end_time).days
        speed = SQL.get_speed(cursor, incident)
        incident.min_speed = speed['min_speed']
        incident.avg_speed = speed['avg_speed']            
    
    #for account in accounts_info:
        #print(account, accounts_info[account])
        
    try:
        wb = openpyxl.load_workbook('resources' + os.sep + 'Template.xlsx')
    except Exception as ex:
        print('Не удалось прочитать файл - {}'.format(file))
        print(ex)
    else:
        break_key = False
        sh = wb['Данные']
        sh['B2'].value = 'Дата формирования отчета {}.  Данные в отчете за {}.'.format(datetime.datetime.now().strftime('%d-%m-%Y'), (datetime.datetime.now().date() - datetime.timedelta(days=1)).strftime('%d-%m-%Y'))
        for row in  range(6, sh.max_row + 1):
            while True:
                if len(incidents) > 0:
                    incident = incidents.pop(0)
                    if (incident.account_name is None) or (incident.session_count is None):
                        continue
                    else:
                        break
                else:
                    break_key = True
                    break
            if break_key:
                break
                
            #if len(incidents) > 0:
                #incident = incidents.pop(0)
            #else:
                #break
            sh['C{}'.format(row)].value = incident.area
            sh['D{}'.format(row)].value = incident.client_type
            sh['E{}'.format(row)].value = incident.incident_number
            sh['F{}'.format(row)].value = incident.account_name
            sh['G{}'.format(row)].value = incident.phone_number
            sh['H{}'.format(row)].value = incident.address
            sh['I{}'.format(row)].value = incident.end_time.strftime('%Y-%m-%d %H:%M')
            sh['J{}'.format(row)].value = incident.day_count
            sh['K{}'.format(row)].value = incident.tariff_speed
            sh['L{}'.format(row)].value = incident.tv
            sh['M{}'.format(row)].value = incident.session_count
            sh['N{}'.format(row)].value = incident.min_speed
            sh['O{}'.format(row)].value = incident.avg_speed
            try:
                sh['P{}'.format(row)].value = data_profiles['{}/{}/{}'.format(incident.hostname, incident.board, incident.port)]['profile_name']
                sh['Q{}'.format(row)].value = data_profiles['{}/{}/{}'.format(incident.hostname, incident.board, incident.port)]['dw_limit']
            except:
                pass
            sh['R{}'.format(row)].value = incident.hostname
            sh['S{}'.format(row)].value = incident.board
            sh['T{}'.format(row)].value = incident.port
        wb.save('files{}Край {}.xlsx'.format(os.sep, datetime.datetime.now().strftime('%Y-%m-%d')))

    # Закрытие подключения к MySQL
    connect.close()
    
    

def sort_incidents(incidents):
    result = []
    for incident in incidents:
        if len(result) == 0:
            result.append(incidents[incident])
            continue
        for idx, r in enumerate(result):
            if incidents[incident] < r:
                result.insert(idx, incidents[incident])
                break
            if idx == len(result) - 1:
                result.append(incidents[incident])
                break
    return result[::-1]


def main():
    print('Время запуска: {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M')))
    print('Загрузка сохраненных инцидентов...')
    incidents = load_incidents()
    
    arguments = [[incidents, list(incidents.keys())[x::Settings.threads_count]] for x in range(0, Settings.threads_count)]
    
    print('Получение данных из Онимы...')
    with ThreadPoolExecutor(max_workers=Settings.threads_count) as executor:
        executor.map(update_accounts_data, arguments)
    
    # Запись инцидентов в файл
    with open('resources{}incidents.db'.format(os.sep), 'bw') as file_dump:
        pickle.dump(incidents, file_dump)
    print('Время : {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M')))
    # Создание выходного файла
    print('Генерация файла отчета...')
    generate_report_file(incidents)
    
    print('Время окончания: {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M')))
    
    #for incident in incidents:
        #print(incidents[incident])



if __name__ == '__main__':
    cur_dir = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-1])
    os.chdir(cur_dir)
    main()