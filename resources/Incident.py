# coding: utf-8


class Incident():
    
    def __init__(self, **kwargs):
        self.incident_number = kwargs['incident_number']
        self.service_number = kwargs['service_number']
        self.fio = kwargs['fio']
        self.address = kwargs['address']
        self.area = self.address.split(',')[0]
        self.client_type = kwargs['client_type']
        self.end_time = kwargs['end_time']
        self.ldn = kwargs['ldn']
        self.technology = kwargs['technology']
        self.account_name = None
        self.phone_number = None
        self.bill = None
        self.dmid = None
        self.tmid = None
        self.hostname = None
        self.board = None
        self.port = None        
        self.proc_date = None
        self.session_count = None
        self.traffic = None
        self.tariff_speed = None
        self.tv = None
        self.day_count = None
        self.min_speed = None
        self.avg_speed = None
        self.up_snr = None
        self.dw_snr = None
        self.etth_hostname = None
        self.etth_port = None
        self.etth_input_errors = None
        self.etth_crc = None
        self.etth_speed = None
        self.etth_ip = None
        
    
    def __gt__(self, other):
        return self.end_time > other.end_time
    
    
    def __lt__(self, other):
        return self.end_time < other.end_time
    
    
    def __str__(self):
        result = 'technology: {}\naccount_name: {}\nincident_number: {}\nservice_number: {}\nfio: {}\naddress: {}\nclient_type: {}\nend_time: {}\nldn: {}\n'.format(self.technology, self.account_name, self.incident_number, self.service_number, self.fio, self.address, self.client_type, self.end_time.strftime('%d.%m.%Y %H:%M'), self.ldn)
        if self.proc_date is not None:
            if self.technology == 'по технологии ADSL':
                result = result + 'hostname: {}\nboard: {}\nport: {}\nsession_count: {}\nproc_date: {}\n'.format(self.hostname, self.board, self.port, self.session_count, self.proc_date)
            elif self.technology == 'с использованием FTTx':
                result = result + 'hostname: {}\nport: {}\ninput_errors: {}\ncrc: {}\nsession_count: {}\nproc_date: {}\n'.format(self.etth_hostname, self.etth_port, self.etth_input_errors, self.etth_crc, self.session_count, self.proc_date)
        return result