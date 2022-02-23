# python generate_files.py 100 /home/mig/state/vgrid_files_home/test/testing/file_

import sys
import time

def generate(file_count, file_path, file_type='.txt'):
    first_filename = ''
    start = time.time()
    for i in range(int(file_count)):
        filename = file_path + str(i) + file_type
        if not first_filename:
            first_filename = filename
        with open(filename, 'w') as f:
            f.write('0')
    return first_filename, time.time() - start

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) < 2:
        print('Not enough args')
        exit()

    file_count = args[0]
    file_path = args[1]
    file_type = '.txt'
    if len(args) > 2:
        file_type = args[2]

    _, _ = generate(file_count, file_path, file_type)
