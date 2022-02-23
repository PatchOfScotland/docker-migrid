import nbformat
import os
import sys
import time

from cleanup_results import cleanup, get_raw, get_job
from generate_files import generate
from setupmeowdefs import clean, VGRID, write_pattern, write_recipe
from vgrid import make_vgrid, remove_vgrid

from mig.shared.serial import load

REPEATS = 10

def run_test(patterns, recipes, files, jobs, errors, signature='', execution=False):

    make_vgrid(VGRID)

    clean()

    for pattern in patterns:
        write_pattern(pattern)

    for recipe in recipes:
        write_recipe(recipe)

    time.sleep(3)

    for run in range(REPEATS):
        data_folder = "/home/mig/state/vgrid_files_home/test/testing"
        job_counter_path = '/home/mig/state/mig_system_files/job_id_counter'
        for filename in os.listdir(data_folder):
            os.remove(os.path.join(data_folder, filename))
        time.sleep(1)

        initial_job_count = -1
        while initial_job_count == -1:
            time.sleep(1)
            if os.path.exists(job_counter_path):
                with open(job_counter_path, 'r') as f:
                    initial_job_count = int(f.read())
            else:
                initial_job_count = 0

        print("Starting execution from: "+ str(initial_job_count))

        first_filename, duration = generate(files, data_folder +"/file_")

        final_job_count = initial_job_count
        prev_count = 0
        job_count = -1
        miss_count = 0
        miss_limit = jobs * 2
        if execution:
            miss_limit = 100
        if not signature:
            signature = str(len(patterns)) +"_"+ str(files)  +"_"+ str(jobs)
        while job_count == -1:
            time.sleep(15 + max(files, len(patterns))/20)
            if not miss_count and not os.path.exists(job_counter_path):
                miss_count += 1
            else:
                with open(job_counter_path, 'r') as f:
                    final_job_count = int(f.read())
                    if prev_count == final_job_count:
                        if final_job_count - initial_job_count == jobs:
                            job_count = final_job_count - initial_job_count
                        elif final_job_count - initial_job_count > jobs:
                            job_count = final_job_count - initial_job_count
                            errors.append(signature +" - Too many jobs scheduled between "+ str(initial_job_count) +" and "+ str(final_job_count) +", count: "+ str(final_job_count - initial_job_count))
                        else:
                            miss_count += 1
                    if final_job_count > prev_count:
                        miss_count = 0
                    prev_count = final_job_count
            if miss_count == miss_limit:
                job_count = final_job_count - initial_job_count
                print('got to miss limit at ' + str(final_job_count))
                errors.append(signature +" - Not enough jobs scheduled between "+ str(initial_job_count) +" and "+ str(final_job_count) +", count: "+ str(final_job_count - initial_job_count))

        print("job count:" + str(final_job_count))
        print("job count:" + str(job_count))

        raw_dir = os.path.join(signature, "raw")
        raw_path = os.path.join(raw_dir, str(run) +".txt")
        results_dir = os.path.join(signature, "results")
        results_path = os.path.join(results_dir, str(run) +".txt")

        for d in [signature, raw_dir, results_dir]:
            if not os.path.exists(d):
                os.mkdir(d)

        get_raw(raw_path)

        with open(raw_path, 'r') as f_in:
            data = f_in.readlines()

        print("data:" + str(len(data)))
        data = data[-job_count:]
        print("data:" + str(len(data)))

        with open(raw_path, 'w') as f_out:
            f_out.writelines(data)

        jobs_list = []
        for l in data:
            jobs_list.append(get_job(l))
        print("jobs list:" + str(len(jobs_list)))

        test_count = 0
        if execution:
            while len(jobs_list) > 0:
                time.sleep(60)
                mrsl_dir = '/home/mig/state/mrsl_files/+C=DK+ST=NA+L=NA+O=Test_Org+OU=NA+CN=Test_User+emailAddress=test@migrid.test'
                to_test = jobs_list
                for j in to_test:
                    mrsl_dict = load(os.path.join(mrsl_dir, j))
                    if 'EXECUTING_TIMESTAMP' in mrsl_dict:
                        jobs_list.remove(j) 
                test_count += 1
                if test_count == 10:
                    print(to_test)
                    errors.append("one or more jobs did not complete as expected."+ str(len(jobs_list)))
                    execution = False

        total_time = cleanup(raw_path, results_path, first_filename, duration, execution=execution)

        print(str(run+1) +"/"+ str(REPEATS) +" - Ran "+ str(job_count) +" jobs "+ str(initial_job_count) +" to "+ str(final_job_count) +". Generation: "+ str(round(duration, 5)) +"s Scheduling: "+ str(total_time) +"s")

    clean()

def no_execution_tests(errors):
    expected_jobs = 100

    single_boring_pattern = [{
        'name': 'pattern_one',
        'vgrid': VGRID,
        'input_paths': ['testing/*'],
        'input_file': 'input',
        'output': {},
        'recipes': ['recipe_one'],
        'variables': {}
    }]

    notebook = nbformat.read('test.ipynb', nbformat.NO_CONVERT)
    single_recipe = [{
        'name': 'recipe_one',
        'vgrid': VGRID,
        'recipe': notebook,
        'source': 'test.ipynb'
    }]

    run_test(
        single_boring_pattern, 
        single_recipe, 
        100, 
        expected_jobs, 
        errors, 
        signature="1_Patterns_100_files"
    )
    
    hundered_identical_patterns = []
    for i in range(expected_jobs):
        hundered_identical_patterns.append({
            'name': 'pattern_'+ str(i),
            'vgrid': VGRID,
            'input_paths': ['testing/*'],
            'input_file': 'input',
            'output': {},
            'recipes': ['recipe_one'],
            'variables': {}
        })

    run_test(
        hundered_identical_patterns, 
        single_recipe, 
        1, 
        expected_jobs, 
        errors, 
        signature="100_Patterns_1_file"
    )

    hundered_different_patterns = []
    for i in range(expected_jobs):
        hundered_different_patterns.append({
            'name': 'pattern_'+ str(i),
            'vgrid': VGRID,
            'input_paths': ['testing/file_'+ str(i) +'.txt'],
            'input_file': 'input',
            'output': {},
            'recipes': ['recipe_one'],
            'variables': {}
        })

    run_test(
        hundered_different_patterns, 
        single_recipe, 
        100, 
        expected_jobs, 
        errors, 
        signature="100_Patterns_100_files"
    )

    single_exciting_pattern = [{
        'name': 'pattern_one',
        'vgrid': VGRID,
        'input_paths': ['testing/*'],
        'input_file': 'input',
        'output': {},
        'recipes': ['recipe_one'],
        'variables': {},
        'parameterize_over': {
            'var': {
                'increment': 1,
                'start': 1,
                'stop': 100
            }
        }    
    }]

    run_test(
        single_exciting_pattern, 
        single_recipe, 
        1, 
        expected_jobs, 
        errors,
        signature="1_Pattern_1_file"
    )    

def sequential_tests(errors):
    to_run = 100

    expected_jobs = to_run

    single_pattern = [{
        'name': 'pattern_one',
        'vgrid': VGRID,
        'input_paths': ['testing/*'],
        'input_file': 'INPUT_FILE',
        'output': {},
        'recipes': ['recipe_one'],
        'variables': {
            'MAX_COUNT': to_run
        }
    }]

    notebook = nbformat.read('sequential.ipynb', nbformat.NO_CONVERT)
    single_recipe = [{
        'name': 'recipe_one',
        'vgrid': VGRID,
        'recipe': notebook,
        'source': 'sequential.ipynb'
    }]

    run_test(
        single_pattern, 
        single_recipe, 
        1, 
        expected_jobs, 
        errors, 
        signature="1_Patterns_"+ str(to_run) +"_sequential_files",
        execution=True
    )

def warmup(errors):
    expected_jobs = 100

    single_boring_pattern = [{
        'name': 'pattern_one',
        'vgrid': VGRID,
        'input_paths': ['testing/*'],
        'input_file': 'input',
        'output': {},
        'recipes': ['recipe_one'],
        'variables': {}
    }]

    notebook = nbformat.read('test.ipynb', nbformat.NO_CONVERT)
    single_recipe = [{
        'name': 'recipe_one',
        'vgrid': VGRID,
        'recipe': notebook,
        'source': 'test.ipynb'
    }]

    run_test(
        single_boring_pattern, 
        single_recipe, 
        100, 
        expected_jobs, 
        errors, 
        signature="Warmup"
    )

if __name__ == '__main__':
    args = sys.argv[1:]

    errors = []

    if args and args[0] == "warmup":
        warmup(errors)

    if args and args[0] == "seq":
        sequential_tests(errors)

    else:
        no_execution_tests(errors)

    if errors:
        for error in errors:
            print(error)
    else:
        print('No errors to report')
