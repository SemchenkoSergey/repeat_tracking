#!/usr/bin/env python3
# coding: utf8

import datetime
import os
import pickle
import time
from concurrent.futures import ThreadPoolExecutor
from resources import Web_manual
from resources import Settings
import warnings
warnings.filterwarnings("ignore")


def get_onyma_params(arguments):
    
    # Открытие соединений Onyma и Argus
    onyma = Web_manual.connect_onyma_requests()
    argus = Web_manual.connect_argus_requests()
    argus_browser = Web_manual.connect_argus_firefox()
    
    try:
        print('запуск потока обработки инцидентов...')
        count = 0
        incidents = arguments[0]
        keys = arguments[1]
        thread_number = arguments[2]
        
        for incident in keys:
            count += 1
            # Если параметры уже установлены
            if incidents[incident].bill is not None:
                continue
            # Если нет
            #print('Поток {}, обработка инцидента {}'.format(thread_number, incident))
            params = False        
            if incidents[incident].account_name:
                # Если номер карты есть, но параметры еще не определены
                print('Новая попытка получить параметры для {}'.format(incidents[incident].account_name))
                params = Web_manual.find_login_param_requests(onyma, account_name=incidents[incident].account_name)
                if params:
                    if not params['bill']:
                        print('Не удалось найти параметры для {}'.format(incidents[incident].account_name))
            else:
                problem_number = Web_manual.get_problem_number_requests(argus, incidents[incident].incident_number)
                account_name = Web_manual.get_account_firefox(argus_browser, problem_number, incidents[incident].incident_number)

                if account_name:
                    params = Web_manual.find_login_param_requests(onyma, account_name=account_name)
                else:
                    print('Не удалось найти номер карты для {}'.format(incidents[incident].incident_number))
                    continue
            if params:
                incidents[incident].account_name = params['account_name']
                incidents[incident].bill = params['bill']
                incidents[incident].dmid = params['dmid']
                incidents[incident].tmid = params['tmid']
                if params['bill']:
                    print('Найдены параметры для услуги {}: account_name - {}, bill - {}, dmid - {}, tmid - {}'.format(incident, params['account_name'], params['bill'], params['dmid'], params['tmid']))
            else:
                continue     
        return count
    except Exception as ex:          
        print(ex)
        print('В потоке {} обработано {} инцидентов.'.format(thread_number, count))
    finally:
        # Закрытие соединений
        onyma.close()
        argus.close()
        argus_browser.quit()           

            

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
    print_report(incidents)
    #read_argus_file(incidents)
    #print_report(incidents)
    arguments = [[incidents, list(incidents.keys())[x::Settings.threads_count], x] for x in range(0, Settings.threads_count)]
    
    # Получение параметров для Онимы
    while True:
        with ThreadPoolExecutor(max_workers=Settings.threads_count) as executor:
            count = list(executor.map(get_onyma_params, arguments))
        
        if None not in count:
            print('\nОбработано инцидентов по потокам: ', count)
            break
        print('Возникла ошибка, обработано: {}\nЗапуск новой попытки через 5 минут...'.format(count))
        time.sleep(300)
        
    
    # Запись инцидентов в файл
    with open('resources{}incidents.db'.format(os.sep), 'bw') as file_dump:
        pickle.dump(incidents, file_dump)
        
    print_report(incidents)
    print('Время окончания: {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M')))


if __name__ == '__main__':
    cur_dir = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-1])
    os.chdir(cur_dir)
    main()