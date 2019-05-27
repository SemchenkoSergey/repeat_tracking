#!/usr/bin/env python3
# coding: utf8

import pickle
import os



def main():
    with open('resources{}incidents.db'.format(os.sep), 'br') as file_load:
            incidents = pickle.load(file_load)
    for incident in incidents:
        incidents[incident].proc_date = None
    with open('resources{}incidents.db'.format(os.sep), 'bw') as file_dump:
        pickle.dump(incidents, file_dump)    

if __name__ == '__main__':
    cur_dir = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-1])
    os.chdir(cur_dir)
    main()