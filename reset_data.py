#!/usr/bin/env python3
# coding: utf8

import pickle
import os
import datetime


def main():
    with open('resources{}incidents.db'.format(os.sep), 'br') as file_load:
            incidents = pickle.load(file_load)
    for incident in incidents:
        incidents[incident].proc_date = None
        #if (datetime.datetime.now() - incidents[incident].end_time).days < 0:
            #incidents[incident].end_time = datetime.datetime(2020,3,1)
    with open('resources{}incidents.db'.format(os.sep), 'bw') as file_dump:
        pickle.dump(incidents, file_dump)    

if __name__ == '__main__':
    cur_dir = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-1])
    os.chdir(cur_dir)
    main()