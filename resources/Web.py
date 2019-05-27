# coding: utf-8

import re
import os
import sys
import requests
from resources import Settings
from bs4 import BeautifulSoup as BS
#import Settings



def connect_argus():
    session = requests.Session()
    auth_url = 'https://argus.south.rt.ru/argus/views/system/inf/login/LoginView.xhtml'
    auth_payload = {'javax.faces.partial.ajax': 'true',
                    'javax.faces.source': 'login_form-submit',
                    'javax.faces.partial.execute': 'login_form',
                    'javax.faces.partial.render': 'login_form',
                    'login_form-submit': 'login_form-submit',
                    'login_form': 'login_form',
                    'login_form-username': Settings.argus_login,
                    'login_form-password': Settings.argus_password,
                    'javax.faces.ViewState': 'stateless'}
    
    html = session.post(auth_url, data=auth_payload, verify=False)
    if not html.ok:
        print('Не удалось получить данные с https://argus.south.rt.ru')
        exit()       
    if 'Неверный логин или пароль' in html.text:
        print('Неверный логин или пароль')
        exit()
    return session


def get_login(session, incident_number):
    number = incident_number.strip().split('-')[-1]
    find_url = 'https://argus.south.rt.ru/argus/views/system/inf/page/MenuStatelessActionView.xhtml'
    incident_payload = {
        'javax.faces.partial.ajax': 'true',
        'javax.faces.source': 'mmf-bi_search',
        'javax.faces.partial.execute': 'mmf-bi_search',
        'javax.faces.partial.render': 'mmf-bi_search',
        'javax.faces.behavior.event': 'query',
        'javax.faces.partial.event': 'query',
        'mmf-bi_search_query': number,
        'mmf-bi_search_input': number,
        'mmf-bi_search_hinput': number,
        'javax.faces.ViewState': 'stateless'}
    html = session.post(find_url, data=incident_payload, verify=False).text
    try:
        incident = re.search(r'data-item-value="(.+?)"', html).group(1)
    except:
        return False
    html = session.get('https://argus.south.rt.ru/argus/views/supportservice/problem/InstallationProblemView.xhtml?businessInteraction={}'.format(incident)).text
    
    trs = BS(html, 'lxml').find('tbody', id = 'history_tabs-history_form-history_table_data').find_all('tr')
    #comments = []
    for tr in trs:
        tds = tr.find_all('td')
        login = re.search(r'BRAS.+?\s(\S+)\s+\d\d\.\d\d\.\d\d\ \d\d\:\d\d', tds[3].text.strip())
        if login is not None:
            return login.group(1).replace('"', '')
    return False


def connect_onyma():
    session = requests.Session()
    auth_url = 'https://10.144.196.37/onyma/login.htms'
    auth_payload = {'LOGIN': Settings.onyma_login, 'PASSWD': Settings.onyma_password, 'enter': 'Вход'}
    try:
        result = session.post(auth_url, data=auth_payload, verify=False)
    except:
        print('https://10.144.196.37/onyma/login.htms не доступен. Проверьте соединение с сетью.')
        return None
    if 'AUTH_ERR' in result.text:
        print('Не верные логин/пароль!')
        return None
    return session


def find_login_param(onyma, login=None, account_name=None):
    url_ip = 'https://10.144.196.37'
    url_main = 'https://10.144.196.37/onyma/main/'
    try:
        if (account_name is None) and (login is not None):
            payload = {
                'prpoper1':  'Like',
                'prpv1': login,
                'prpc': '0',
                'search': 'Поиск'
            }
            html = onyma.post('https://10.144.196.37/onyma/main/dogsearch_ok.htms', data=payload, verify=False).text
            if '<title>Результаты поиска</title>' in html:
                url = BS(html, 'lxml').find('a', title=re.compile('-.+руб.')).get('href')
                html = onyma.get(url_main + url).text
    
            url = BS(html, 'lxml').find('a', title=re.compile('Договор')).get('href')
            html = onyma.get(url_ip + url).text
            
            # Поиск учетного имени
            links = BS(html, 'lxml').find_all('a')
            for link in links:
                url = link.get('href')
                if 'clsrv.htms' in url:
                    html = onyma.get(url_main + url).text
                    if login in html:
                        account_name = re.search(r'\]\. (\S+)', BS(html, 'lxml').find('title').text).group(1).strip()
            url = BS(html, 'lxml').find('a', id='menu4185').get('href')
            html = onyma.get(url_ip + url).text
            url = url_main + BS(html, 'lxml').find('td', class_='td1').find('a').get('href')
            html = onyma.get(url).text
        elif (login is None) and (account_name is not None):
            html = onyma.post('https://10.144.196.37/onyma/main/dogsearch_ok.htms', {'sitename': account_name, 'search': 'Поиск'}, verify=False).text
            url = BS(html, 'lxml').find('a', title=re.compile('Договор')).get('href')
            html = onyma.get(url_ip + url).text
            url = BS(html, 'lxml').find('a', id='menu4185').get('href')
            html = onyma.get(url_ip + url).text
            url = url_main + BS(html, 'lxml').find('td', class_='td1').find('a').get('href')
            html = onyma.get(url).text
        else:
            return False
        urls = []
        links = BS(html, 'lxml').find_all('a')
        for link in links:
            url = link.get('href')
            if ('service=201' in url) and (link.text == account_name):
                urls.append(url_main + url)
    except:
        return False
    result_url = ''
    result_date = 1
    for url in urls:
        try:
            html = onyma.get(url).text
            current_date = int(BS(html, 'lxml').find('td', class_='td1').find('a').text.split('.')[0])
        except:
            continue            
        if current_date >= result_date:
            result_date = current_date
            result_url = url
    if result_url != '':
        bill = re.search(r'bill=(\d+)', result_url).group(1)
        dmid = re.search(r'dmid=(\d+)', result_url).group(1)
        tmid = re.search(r'tmid=(\d+)', result_url).group(1)
        return {'account_name': account_name, 'bill': bill, 'dmid': dmid, 'tmid': tmid}
    elif account_name is not None:
        return {'account_name': account_name, 'bill': None, 'dmid': None, 'tmid': None}
    else:
        return False
    
    
def get_account_data(onyma, incident,  date):
    bill = incident.bill
    dmid = incident.dmid
    tmid = incident.tmid
    result = {}
    re_hostname =  r'ST: (\S+) atm 0/(\d+)/0/(\d+)'
    #re_hostname = r'(STV[\w-]+?) atm \d/(\d+)/\d/(\d+)'
    try:
        html = onyma.get("https://10.144.196.37/onyma/main/ddstat.htms?bill={}&dt={}&mon={}&year={}&service=201&dmid={}&tmid={}".format(bill,  date.day,  date.month, date.year,  dmid,  tmid))        
        #print("https://10.144.196.37/onyma/main/ddstat.htms?bill={}&dt={}&mon={}&year={}&service=201&dmid={}&tmid={}".format(bill,  date.day,  date.month, date.year,  dmid,  tmid))
        #print(html.text)
        result['session_count'] = int(re.search(r'<td class="foot">Все</td><td class="pgout" colspan="5">.+?<b>(\d+)</b>',  html.text.__repr__()).group(1))
        argus_data = re.search(re_hostname, html.text.__repr__())
        if argus_data:
            result['hostname'] = argus_data.group(1)
            result['board'] = int(argus_data.group(2))
            result['port'] = int(argus_data.group(3))
        else:
            result['hostname'] = None
            result['board'] = None
            result['port'] = None             
    except:
        return False
    return result

#onyma = connect_onyma()
#print(find_login_param(onyma, login='wrm3hherzp'))
#print(find_login_param(onyma, account_name='rtc0000070526'))
#onyma.close()