
import os

from collections import Counter

jobs_dir = '/home/mig/state/mrsl_files/+C=DK+ST=NA+L=NA+O=Test_Org+OU=NA+CN=Test_User+emailAddress=test@migrid.test'
nums = {}
for filename in sorted(os.listdir(jobs_dir)):
    with open(os.path.join(jobs_dir, filename,), 'r') as f:
        data = f.readlines()
        for r in range(len(data)):
            if 'WORKFLOW_INPUT_PATH' in data[r]:
                input_line = data[r+1]
                input_line = input_line[input_line.index('file_')+5:input_line.index('.txt')]
                if input_line in nums:
                    nums[input_line].append(filename)
                else:
                    nums[input_line] = [filename]
                print(f"{filename}: {input_line}")

for k, v in nums.items():
    if len(v) > 1:
        print(k, v)
