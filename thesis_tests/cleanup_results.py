# python3 cleanup_results.py 1_Pattern_100_files_timing.txt placeholder

import datetime
import sys
import time
import os

from mig.shared.serial import load

def mean(l):
    return sum(l)/len(l)

def cleanline(line):
    return line[:line.index(' grid_events')]

def get_job(line):
    return line[line.index(': ')+2:line.index(' is the')] +'.mRSL'

def datetimeline_to_timestamp(dtl):
    date_time_str = cleanline(dtl)
    date_time_obj = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S,%f')
    return time.mktime(date_time_obj.timetuple()) + float(date_time_obj.microsecond)/1000000 

def get_raw(raw_path):
    os.system("grep schedule_job /home/mig/state/log/events.log >> "+ raw_path)


def cleanup(file_in, file_out, base_time, gen_time, execution=False):
    with open(file_in, 'r') as f_in:
        data = f_in.readlines()

    first = (datetimeline_to_timestamp(data[0]), cleanline(data[0]))
    last = (datetimeline_to_timestamp(data[0]), cleanline(data[0]))

    jobs = []
    for l in data:
        jobs.append(get_job(l))
        dt = datetimeline_to_timestamp(l)
        if dt < first[0]:
            first = (dt, cleanline(l))
        if dt > last[0]:
            last = (dt, cleanline(l))

    #dt = datetime.datetime.fromtimestamp(os.path.getctime(base_time), datetime.timezone(datetime.timedelta(hours=0)))
    dt = datetime.datetime.fromtimestamp(os.path.getctime(base_time))

    mrsl_dir = '/home/mig/state/mrsl_files/+C=DK+ST=NA+L=NA+O=Test_Org+OU=NA+CN=Test_User+emailAddress=test@migrid.test'

    if execution:
        queue_times = []
        execution_times = []
        for j in jobs:
            mrsl_dict = load(os.path.join(mrsl_dir, j))

            queue_times.append(time.mktime(mrsl_dict['EXECUTING_TIMESTAMP']) - time.mktime(mrsl_dict['QUEUED_TIMESTAMP']))
            execution_times.append(time.mktime(mrsl_dict['FINISHED_TIMESTAMP']) - time.mktime(mrsl_dict['EXECUTING_TIMESTAMP']))

    with open(file_out, 'w') as f_out:
        f_out.write("Job count: "+ str(len(data)) +"\n")
        f_out.write("Generation time: "+ str(round(gen_time, 5)) +"\n")
        f_out.write("First trigger: "+ str(dt) +"\n")
        f_out.write("First scheduling datetime: "+ str(first[1]) +"\n")
        f_out.write("Last scheduling datetime: "+ str(last[1]) +"\n")
        f_out.write("First scheduling unixtime: "+ str(first[0]) +"\n")
        f_out.write("First scheduling unixtime: "+ str(last[0]) +"\n")
        f_out.write("Scheduling difference (seconds): "+ str(round(last[0] - first[0], 3)) +"\n")
        f_out.write("Initial scheduling delay (seconds): "+ str(round(first[0] - os.path.getctime(base_time) + 3600, 3)) +"\n")
        total_time = round(last[0] - os.path.getctime(base_time) + 3600, 3)
        f_out.write("Total scheduling delay (seconds): "+ str(total_time) +"\n")

        if execution:
            f_out.write("Average execution time (seconds): "+ str(round(mean(execution_times), 3)) +"\n")
            f_out.write("Max execution time (seconds): "+ str(round(max(execution_times), 3)) +"\n")
            f_out.write("Min execution time (seconds): "+ str(round(min(execution_times), 3)) +"\n")

            f_out.write("Average queueing delay (seconds): "+ str(round(mean(queue_times), 3)) +"\n")
            f_out.write("Max queueing delay (seconds): "+ str(round(max(queue_times), 3)) +"\n")
            f_out.write("Min queueing delay (seconds): "+ str(round(min(queue_times), 3)) +"\n")

            queue_times.remove(max(queue_times))
            f_out.write("Average excluded queueing delay (seconds): "+ str(round(mean(queue_times), 3)) +"\n")

    return total_time

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) < 3:
        print('Not enough args')
        exit()

    file_in = args[0]
    file_out = args[1]
    base_time = args[2]

    _ = cleanup(file_in, file_out, base_time)
