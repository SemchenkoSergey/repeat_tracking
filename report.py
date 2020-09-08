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
import shutil
import random
from resources import Incident
from concurrent.futures import ThreadPoolExecutor
from resources import Web
from resources import SQL
from resources import Settings
from resources import Switch
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

def load_switchs():
    result = {}
    try:
        with open('resources{}switchs.db'.format(os.sep), 'br') as file_load:
            result = pickle.load(file_load)
    except:
        pass
    return result   

def update_accounts_data(arguments):
    incidents = arguments[0]
    keys = arguments[1]
    prev_day = datetime.date.today() - datetime.timedelta(days=1)
    # Открытие соединения Onyma
    onyma = Web.connect_onyma()
    if onyma is None:
        return False
    
    for key in keys:
        incident = incidents[key]
        if (incident.proc_date == datetime.date.today()) or (incident.bill is None):
            continue
        #if incident.technology == 'по технологии ADSL':
            #continue
        account_data = Web.get_account_data(onyma, incident,  prev_day)
        if not account_data:
            incident.hostname = None
            incident.board = None
            incident.port = None
            incident.etth_hostname = None
            incident.etth_port = None            
            incident.session_count = None
            incident.traffic = None
            incident.proc_date = datetime.date.today()
            continue
        #if (account_data['session_count'] > 0) and (account_data['hostname'] is None):
            #print('Сессии были, но устройство не распознано: {}'.format(incidents[incident].account_name))
        incident.session_count = account_data['session_count']
        incident.traffic = account_data['traffic']
        incident.proc_date = datetime.date.today()
        if (incident.technology == 'по технологии ADSL'):
            incident.hostname = account_data['hostname']
            incident.board = account_data['board']
            incident.port = account_data['port']
        elif (incident.technology == 'с использованием FTTx'):
            incident.etth_hostname =  account_data['etth_hostname']
            incident.etth_port = account_data['etth_port']
            

def update_etth_data(arguments):
    incidents = arguments[0]
    keys = arguments[1]
    #Загрузка списка коммутаторов
    switchs = load_switchs()
    
    for key in keys:
        incident = incidents[key]
        #if incident.area != 'Петровский р-н':
            #continue        
        if incident.technology == 'с использованием FTTx':
            if incident.etth_hostname is not None:
                try:
                    etth_port_info =  get_etth_port_info(incident, switchs)
                except Exception as ex:
                    print(ex)
                    continue
                if etth_port_info is None:
                    continue
                incident.etth_input_errors = etth_port_info['input_errors']
                incident.etth_crc = etth_port_info['crc']
                incident.etth_speed = etth_port_info['speed']
                print('Имя: {}, порт: {}, err: {}, crc: {}, speed: {}'.format(incident.etth_hostname, incident.etth_port,  incident.etth_input_errors, incident.etth_crc, incident.etth_speed))

            
    

        
def get_etth_port_info(incident, switchs):
    if incident.etth_hostname in switchs:
        manufacture = switchs[incident.etth_hostname]['manufacture']
        model = switchs[incident.etth_hostname]['model']
        
        if (manufacture != 'QTECH') or ('QSW-39' in model) or ('QSW-29' in model):
            print('Не обрабатывается. Производитель: {}, модель: {}'.format(manufacture, model))
            return None
        ip = switchs[incident.etth_hostname]['ip']
        for i in range(0, 3):    
            tn = Switch.Switch(ip, Settings.etth_login, Settings.etth_password)
            if tn.ok:
                break
            time.sleep(random.randint(2,7))
        if not tn.ok:
            return None
        incident.etth_ip = ip
        result = tn.interface_info(incident.etth_port)
        #tn.clear_counters(incident.etth_port)
        del tn
        return result
    else:
        return None
    
    
def generate_report_file(incidents):
    # Имя файла с отчетом
    report_file = 'files{}Край {}.xlsx'.format(os.sep, datetime.datetime.now().strftime('%Y-%m-%d'))
    # Подключение к MySQL
    connect = MySQLdb.connect(host=Settings.db_host, user=Settings.db_user, password=Settings.db_password, db=Settings.db_name, charset='utf8')
    cursor = connect.cursor()
    # Получение данных о абонентах из базы данных
    accounts_info = SQL.get_accounts_info(cursor)
    #for account in accounts_info:
        #print(account, accounts_info[account])    

    # Получение профилей линий с DSLAM
    data_profiles = SQL.get_data_profiles(cursor)
    
    #Получение  скоростей
    all_speed = SQL.get_all_speed(cursor)
    
    # Сортировка инцидентов по дате
    incidents = sort_incidents(incidents)
    
    # Добавление информации к инцидентам ADSL
    for incident in incidents:
        #if incident.area != 'Петровский р-н':
            #continue
        incident.day_count = (datetime.datetime.now() - incident.end_time).days
        if incident.technology == 'по технологии ADSL':
            #continue
            if incident.account_name in accounts_info:
                incident.phone_number = accounts_info[incident.account_name]['phone_number']
                incident.tariff_speed = accounts_info[incident.account_name]['tariff_speed']
                incident.tv = accounts_info[incident.account_name]['tv']
            speed = all_speed.get('{}/{}/{}'.format(incident.hostname, incident.board, incident.port),  {'min_speed':  '-', 'avg_speed': '-', 'up_snr': '-', 'dw_snr': '-'})
            incident.min_speed = speed['min_speed']
            incident.avg_speed = speed['avg_speed']
            incident.up_snr = speed['up_snr']
            incident.dw_snr = speed['dw_snr']
        
    try:
        wb = openpyxl.load_workbook('resources' + os.sep + 'Template.xlsx')
    except Exception as ex:
        print('Не удалось прочитать файл - {}'.format(file))
        print(ex)
    else:
        sh_adsl = wb['ADSL']
        sh_adsl['B2'].value = 'Дата формирования отчета {}.  Данные в отчете за {}.'.format(datetime.datetime.now().strftime('%d-%m-%Y'), (datetime.datetime.now().date() - datetime.timedelta(days=1)).strftime('%d-%m-%Y'))
        sh_fttx = wb['FTTX']
        sh_fttx['B2'].value = 'Дата формирования отчета {}.  Данные в отчете за {}.'.format(datetime.datetime.now().strftime('%d-%m-%Y'), (datetime.datetime.now().date() - datetime.timedelta(days=1)).strftime('%d-%m-%Y'))
        # ADSL
        fill_report(sh_adsl, incidents[:], 'по технологии ADSL', data_profiles)
        fill_report(sh_fttx, incidents[:], 'с использованием FTTx')
        wb.save(report_file)

    # Закрытие подключения к MySQL
    connect.close()
    
    # Копирование файла на сетевой диск
    if os.path.exists(report_file):
        try:
            shutil.copy(report_file, '{}{}{}'.format(Settings.path_name, os.sep, datetime.datetime.now().strftime('%Y-%m')))
        except Exception as ex:
            print('Ошибка копирования на сетевой диск')
            print(ex)
        else:
            print('Файл скопирован')
    else:
        print('Файл отчета не создан!')
        
def fill_report(sh, incidents, technology, data_profiles={}):
    break_key = False
    for row in  range(6, sh.max_row + 1):
        while True:
            if len(incidents) > 0:
                incident = incidents.pop(0)
                if (incident.technology != technology) or (incident.account_name is None) or (incident.session_count is None):
                    continue
                else:
                    break
            else:
                break_key = True
                break
        if break_key:
            break
        
        #Заполнение отчета                
        sh['C{}'.format(row)].value = incident.area
        sh['D{}'.format(row)].value = incident.client_type
        sh['E{}'.format(row)].value = incident.incident_number
        sh['F{}'.format(row)].value = incident.account_name                
        #ADSL
        if technology == 'по технологии ADSL':
            sh['G{}'.format(row)].value = incident.phone_number
            sh['H{}'.format(row)].value = incident.address
            sh['I{}'.format(row)].value = incident.end_time.strftime('%Y-%m-%d %H:%M')
            sh['J{}'.format(row)].value = incident.day_count
            sh['K{}'.format(row)].value = incident.tariff_speed
            sh['L{}'.format(row)].value = incident.tv
            sh['M{}'.format(row)].value = incident.session_count
            sh['N{}'.format(row)].value = incident.traffic
            sh['O{}'.format(row)].value = incident.min_speed
            sh['P{}'.format(row)].value = incident.avg_speed
            sh['Q{}'.format(row)].value = incident.up_snr
            sh['R{}'.format(row)].value = incident.dw_snr
            try:
                sh['S{}'.format(row)].value = data_profiles['{}/{}/{}'.format(incident.hostname, incident.board, incident.port)]['profile_name']
                sh['T{}'.format(row)].value = data_profiles['{}/{}/{}'.format(incident.hostname, incident.board, incident.port)]['dw_limit']
            except:
                pass
            sh['U{}'.format(row)].value = incident.hostname
            sh['V{}'.format(row)].value = incident.board
            sh['W{}'.format(row)].value = incident.port
        #ETTH
        elif  technology == 'с использованием FTTx':
            sh['G{}'.format(row)].value = incident.address
            sh['H{}'.format(row)].value = incident.end_time.strftime('%Y-%m-%d %H:%M')
            sh['I{}'.format(row)].value = incident.day_count
            sh['J{}'.format(row)].value = incident.etth_input_errors
            sh['K{}'.format(row)].value = incident.etth_crc
            sh['L{}'.format(row)].value = incident.etth_speed
            sh['M{}'.format(row)].value = incident.session_count
            sh['N{}'.format(row)].value = incident.traffic
            sh['O{}'.format(row)].value = incident.etth_hostname
            sh['P{}'.format(row)].value = incident.etth_ip
            sh['Q{}'.format(row)].value = incident.etth_port                    
    

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


def reset_data(incidents):
    for key in incidents:
        incident = incidents[key]
        incident.min_speed = None
        incident.avg_speed = None
        incident.up_snr = None
        incident.dw_snr = None        
        incident.etth_input_errors = None
        incident.etth_crc = None
        incident.etth_speed = None        
    

def main():
    print('Время запуска: {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M')))
    print('Загрузка сохраненных инцидентов...')
    incidents = load_incidents()
    
    
    print('Получение данных из Онимы...')
    arguments = [[incidents, list(incidents.keys())[x::Settings.threads_count]] for x in range(0, Settings.threads_count)]
    with ThreadPoolExecutor(max_workers=Settings.threads_count) as executor:
        executor.map(update_accounts_data, arguments)
    
    print('Получение данных с коммутаторов...')
    arguments = [[incidents, list(incidents.keys())[x::Settings.switch_count]] for x in range(0, Settings.switch_count)]
    with ThreadPoolExecutor(max_workers=Settings.switch_count) as executor:
        executor.map(update_etth_data, arguments)    
    

    print('Время : {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M')))
    # Создание выходного файла
    print('Генерация файла отчета...')
    generate_report_file(incidents)
    
    # Сброс информации в инцидентах
    reset_data(incidents)
    
    # Запись инцидентов в файл
    with open('resources{}incidents.db'.format(os.sep), 'bw') as file_dump:
        pickle.dump(incidents, file_dump)
        
    print('Время окончания: {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M')))
    
    #for incident in incidents:
        #print(incidents[incident])



if __name__ == '__main__':
    cur_dir = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-1])
    os.chdir(cur_dir)
    main()