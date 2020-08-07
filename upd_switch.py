#!/usr/bin/env python3
# coding: utf8

import csv
import re
import pickle
import os

def separation(info):
    try:
        if re.search(r'\[(.+)\]', info).group(1):
            ip = re.search(r'\[(.+)\]', info).group(1)
            hostname = re.search(r'^(.*?)(\(|\[)', info).group(1)
            #print(hostname, ': ', info)
    except Exception as ex:
        #print(ex, ': ', info)
        return None
    else:
        return {'hostname': hostname, 'ip': ip}


file = 'files{}Отчет по оборудованию FTTX с ЗО.csv'.format(os.sep)
switchs = {}
with open(file,  encoding='windows-1251') as f:
    reader = csv.reader((line.replace('\0','') for line in f), delimiter=';')
    idx = 0
    for row in reader:
        idx += 1
        if idx < 3:
            continue
        try:
            if 'Готов' not in row[8]:
                continue
            switch = separation(row[3].replace('"', '').replace('=', ''))
            if switch is None:
                continue
            switchs.setdefault(switch['hostname'], {})
            switchs[switch['hostname']]['ip'] = switch['ip']
            switchs[switch['hostname']]['manufacture'] = row[4].replace('"', '').replace('=', '')
            switchs[switch['hostname']]['model'] = row[5].replace('"', '').replace('=', '')
        except:
            break
        
with open('resources{}switchs.db'.format(os.sep), 'bw') as file_dump:
    pickle.dump(switchs, file_dump)

print('Найдено коммутаторов: {} '.format(len(switchs)))