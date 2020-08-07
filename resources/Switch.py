# coding: utf-8

import pexpect
import datetime
import time
import re
import os

class Switch():
    def __init__(self, ip, login, password):
        self.tn = pexpect.spawn('telnet {}'.format(ip))
        self.tn.timeout = 3
        try:
            self.tn.expect(':')
            self.tn.sendline(login)
            self.tn.expect(':')
            self.tn.sendline(password)
            num = self.tn.expect(['#', '>', ':'])
            if (num == 0) or (num == 1):
                #self.tn.sendline('enable')
                self.hostname = re.search(r'\n(.+)', self.tn.before.decode('utf-8')).group(1)
                self.pref = self.get_pref()
                #print('Создан коммутатор {}'.format(self.hostname))
                self.ok = True  
            else:
                self.ok = False
        except Exception as ex:
            print('Не удалось подключиться к {}'.format(ip))
            self.ok = False
        
        
    def read(self, command):
        result = ''
        self.tn.sendline(command)
        while True:
            num = self.tn.expect(['{}#'.format(self.hostname), 'More'])
            result += self.tn.before.decode('utf-8')
            if num == 0:
                break
            else:
                self.tn.send(' ')
        #result += self.tn.before.decode('utf-8')
        return result.replace(' ---- \x08\x08\x08\x08\x08\x08\x08\x08\x08\x08          \x08\x08\x08\x08\x08\x08\x08\x08\x08\x08', '')        


    def interface_info(self, interface):
        try:
            out = self.read('sh int eth {}{}'.format(self.pref, interface))
        except:
            return None
        if 'interface error' in out:
            return None
        input_errors = re.search(r'(\d+) input errors', out).group(1)
        crc = re.search(r'(\d+) CRC', out).group(1)
        state = re.search(r'line protocol is (.+?)\r', out).group(1)
        if state == 'up':
            speed = re.search(r'BW (\d+) Kbit', out).group(1)[:-3]
        else:
            speed = 'down'
        
        return {'input_errors': input_errors, 'crc': crc, 'state': state, 'speed': speed}

    def clear_counters(self, interface):
        self.read('clear counters interface ethernet {}{}'.format(self.pref, interface))
    
    
    
    def get_pref(self):
        out = self.read('sh int eth st')
        return re.search(r'\n(1.+?1) ', out).group(1)[:-1]


#ip = '172.26.194.9'
#login = 'semchenko-s-v'
#password = 'HG4w#$$ffg'

#tn = Switch(ip, login, password)
##if not tn.ok:
    ###print('Неверный login/password')
    ##exit()

###hostname = re.search(r'\n(.+)', tn.before.decode('utf-8')).group(1)
###pref= get_pref()

##print(tn.interface_info( 3))
###clear_counters(pref, 3)
###print(interface_info(pref, 3))
##print(tn.interface_info(11))

#print(tn.read('sh run'))
##print(tn.read('sh int eth st').__repr__())