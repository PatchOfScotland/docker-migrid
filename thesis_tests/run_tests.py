
import time
import os
import sys
import nbformat

from cleanup_results import get_raw, cleanup, get_job
from generate_files import generate
from setupmeowdefs import clean, write_pattern, write_recipe
from vgrid import make_vgrid

from mig.shared.serial import load

VGRID = "test"
RESULTS_DIR = '/home/mig/results'

SINGLE_PATTERN_MULTIPLE_FILES = 'single_Pattern_multiple_files'
SINGLE_PATTERN_SINGLE_FILE_PARALLEL = 'single_Pattern_single_file_parallel_jobs'
SINGLE_PATTERN_SINGLE_FILE_SEQUENTIAL = 'single_Pattern_single_file_sequential_jobs'
MULTIPLE_PATTERNS_SINGLE_FILE = 'multiple_Patterns_single_file'
MULTIPLE_PATTERNS_MULTIPLE_FILES = 'multiple_Patterns_multiple_files'

REPEATS=10

JOB_COUNTS=[200, 250, 300]
#JOB_COUNTS=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 175, 200, 250, 300, 400, 500]


TESTS = [
    #SINGLE_PATTERN_MULTIPLE_FILES,
    MULTIPLE_PATTERNS_SINGLE_FILE,
    #SINGLE_PATTERN_SINGLE_FILE_PARALLEL,
    # These tests take ages, run them over a weeked
    MULTIPLE_PATTERNS_MULTIPLE_FILES,
    #SINGLE_PATTERN_SINGLE_FILE_SEQUENTIAL
]

def clean_mig(meow=True):
    if meow:
        clean()
    os.system("rm -r -f /home/mig/state/mrsl_files/+C=DK+ST=NA+L=NA+O=Test_Org+OU=NA+CN=Test_User+emailAddress=test@migrid.test/*")
    # Need to remove log file as it gets seriously massive. Doing it like this may be more harm than good though
    for filename in os.listdir("/home/mig/state/log"):
        open(os.path.join("/home/mig/state/log", filename), 'w').close()

def run_test(
    patterns={}, recipes={}, files_count=0, expected_job_count=0, repeats=0, 
    job_counter=0, requested_jobs=0, runtime_start=0, signature='', 
    execution=False, print_logging=False, errors=[]):

    make_vgrid(VGRID)

    if not os.path.exists(RESULTS_DIR):
        os.mkdir(RESULTS_DIR)

    for pattern in patterns:
        write_pattern(pattern)

    for recipe in recipes:
        write_recipe(recipe)

    for run in range(repeats):
        clean_mig(meow=False)

        print("Starting run %s of %s jobs from %s files for %s" % (run, expected_job_count, files_count, signature))

        # Ensure complete cleanup from previous run
        data_folder = "/home/mig/state/vgrid_files_home/test/testing"
        if not os.path.exists(data_folder):
            os.mkdir(data_folder)
        job_counter_path = '/home/mig/state/mig_system_files/job_id_counter'

        for filename in os.listdir(data_folder):
            os.remove(os.path.join(data_folder, filename))

	    # In small experiments the tail end of the above deletes may be getting tied into the creation evenst below, so separare them
        time.sleep(3)
        
        # Possible add some check here on all patterns and recipes created

        initial_job_count = 0
        if os.path.exists(job_counter_path):
            with open(job_counter_path, 'r') as f:
                initial_job_count = int(f.read())

        print('initial_job_count: ' + str(initial_job_count))

        time.sleep(3)
 
        first_filename, duration = generate(files_count, data_folder +"/file_")

        getting_jobs = 1
        miss_count = 0
        final_job_count = initial_job_count
        previous_job_count = -1
        total_jobs_found = 0
        sleepy_time = expected_job_count
        while getting_jobs:
            time.sleep(sleepy_time)
            sleepy_time = 3
        
            if os.path.exists(job_counter_path):
                with open(job_counter_path, 'r') as f:
                    final_job_count = int(f.read())

            print('Jobs: %s %s' % (previous_job_count, final_job_count))
            if previous_job_count == final_job_count:
                miss_count+=1
                if miss_count == 10:
                    getting_jobs = 0
            else:
                miss_count = 0
            previous_job_count = final_job_count

        total_jobs_found = final_job_count - initial_job_count
        print('Job queue settled with %s jobs' %  (total_jobs_found))

        miss_count = 0
        miss_limit = expected_job_count
        for job_id in range(initial_job_count, final_job_count):
            job_string = ": "+ str(job_id) +"_"
            checking_job = True
            while checking_job:
                status_code = os.system("grep '"+ job_string +"' /home/mig/state/log/events.log >/dev/null 2>&1")
                if status_code == 0:
                    checking_job = False
                    miss_count = 0
                else:
                    print("No entry found for "+ str(job_string))
                    miss_count += 1
                    if miss_count == miss_limit:
                        errors.append("Could not find job entry for %s." % str(job_id))
                        continue
                    time.sleep(5)

        if total_jobs_found < expected_job_count:
            errors.append("Not enough jobs for run %s of %s. Got %s but expected %s." % (run, signature, total_jobs_found, expected_job_count))

        if total_jobs_found > expected_job_count:
            errors.append("Too many jobs for run %s of %s. Got %s but expected %s." % (run, signature, total_jobs_found, expected_job_count))

        raw_dir = os.path.join(RESULTS_DIR, signature, str(expected_job_count), "raw")
        raw_path = os.path.join(raw_dir, str(run) +".txt")
        results_dir = os.path.join(RESULTS_DIR, signature, str(expected_job_count), "results")
        results_path = os.path.join(results_dir, str(run) +".txt")

        for d in [os.path.join(RESULTS_DIR, signature), os.path.join(RESULTS_DIR, signature, str(expected_job_count)), raw_dir, results_dir]:
            if not os.path.exists(d):
                os.mkdir(d)

        get_raw(raw_path)
        
        with open(raw_path, 'r') as f_in:
            data = f_in.readlines()

        print("data:" + str(len(data)))
        data = data[-total_jobs_found:]
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

        print(str(run+1) +"/"+ str(repeats) +" - Ran "+ str(total_jobs_found) +" jobs "+ str(initial_job_count) +" to "+ str(final_job_count) +". Generation: "+ str(round(duration, 5)) +"s Scheduling: "+ str(total_time) +"s")

        print("Completed scheduling run %s of %s/%s jobs for '%s' %s/%s (%ss)" % (run + 1, total_jobs_found, expected_job_count, signature, job_counter + expected_job_count*(run+1), requested_jobs,  round(time.time()-runtime_start, 3)))

    clean_mig()

def warmup(errors):
    warmup_jobs = 100

    patterns = [{
        'name': 'pattern_one',
        'vgrid': VGRID,
        'input_paths': ['testing/*'],
        'input_file': 'input',
        'output': {},
        'recipes': ['recipe_one'],
        'variables': {}
    }]

    notebook = nbformat.read('test.ipynb', nbformat.NO_CONVERT)
    recipes = [{
        'name': 'recipe_one',
        'vgrid': VGRID,
        'recipe': notebook,
        'source': 'test.ipynb'
    }]

    run_test(
        patterns=patterns, 
        recipes=recipes, 
        files_count=warmup_jobs, 
        expected_job_count=warmup_jobs,
        requested_jobs=warmup_jobs,
        runtime_start=0,
        repeats=1,
        job_counter=0, 
        errors=errors, 
        signature="Warmup",
        execution=False,
        print_logging=False
    )

def no_execution_tests(errors):
    requested_jobs=0
    for job_count in JOB_COUNTS:
        requested_jobs += job_count * REPEATS * len(TESTS)
    print("requested_jobs: %s" % requested_jobs)

    runtime_start=time.time()

    job_counter=0
    for job_count in JOB_COUNTS:

        if SINGLE_PATTERN_MULTIPLE_FILES in TESTS:

            patterns = [{
                'name': 'pattern_one',
                'vgrid': VGRID,
                'input_paths': ['testing/*'],
                'input_file': 'input',
                'output': {},
                'recipes': ['recipe_one'],
                'variables': {}
            }]

            notebook = nbformat.read('test.ipynb', nbformat.NO_CONVERT)
            recipes = [{
                'name': 'recipe_one',
                'vgrid': VGRID,
                'recipe': notebook,
                'source': 'test.ipynb'
            }]

            run_test(
                patterns=patterns, 
                recipes=recipes, 
                files_count=job_count, 
                expected_job_count=job_count,
                requested_jobs=requested_jobs,
                runtime_start=runtime_start,
                repeats=REPEATS,
                job_counter=job_counter, 
                errors=errors, 
                signature="single_Pattern_multiple_files",
                execution=False,
                print_logging=False
            )

            job_counter += job_count * REPEATS
        
        if MULTIPLE_PATTERNS_SINGLE_FILE in TESTS:

            patterns = []
            for i in range(job_count):
                patterns.append({
                    'name': 'pattern_'+ str(i),
                    'vgrid': VGRID,
                    'input_paths': ['testing/*'],
                    'input_file': 'input',
                    'output': {},
                    'recipes': ['recipe_one'],
                    'variables': {}
                })

            notebook = nbformat.read('test.ipynb', nbformat.NO_CONVERT)
            recipes = [{
                'name': 'recipe_one',
                'vgrid': VGRID,
                'recipe': notebook,
                'source': 'test.ipynb'
            }]

            run_test(
                patterns=patterns, 
                recipes=recipes, 
                files_count=1, 
                expected_job_count=job_count,
                requested_jobs=requested_jobs,
                runtime_start=runtime_start,
                repeats=REPEATS,
                job_counter=job_counter, 
                errors=errors, 
                signature="multiple_Patterns_single_file",
                execution=False,
                print_logging=False
            )

            job_counter += job_count * REPEATS

        if MULTIPLE_PATTERNS_MULTIPLE_FILES in TESTS:

            patterns = []
            for i in range(job_count):
                patterns.append({
                    'name': 'pattern_'+ str(i),
                    'vgrid': VGRID,
                    'input_paths': ['testing/file_'+ str(i) +'.txt'],
                    'input_file': 'input',
                    'output': {},
                    'recipes': ['recipe_one'],
                    'variables': {}
                })

            notebook = nbformat.read('test.ipynb', nbformat.NO_CONVERT)
            recipes = [{
                'name': 'recipe_one',
                'vgrid': VGRID,
                'recipe': notebook,
                'source': 'test.ipynb'
            }]

            run_test(
                patterns=patterns, 
                recipes=recipes, 
                files_count=job_count, 
                expected_job_count=job_count,
                requested_jobs=requested_jobs,
                runtime_start=runtime_start,
                repeats=REPEATS,
                job_counter=job_counter, 
                errors=errors, 
                signature="multiple_Patterns_multiple_files",
                execution=False,
                print_logging=False
            )

            job_counter += job_count * REPEATS

        if SINGLE_PATTERN_SINGLE_FILE_PARALLEL in TESTS:

            patterns = [{
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
                        'stop': job_count
                    }
                }    
            }]

            notebook = nbformat.read('sequential.ipynb', nbformat.NO_CONVERT)
            recipes = [{
                'name': 'recipe_one',
                'vgrid': VGRID,
                'recipe': notebook,
                'source': 'sequential.ipynb'
            }]

            run_test(
                patterns=patterns, 
                recipes=recipes, 
                files_count=1, 
                expected_job_count=job_count,
                requested_jobs=requested_jobs,
                runtime_start=runtime_start,
                repeats=REPEATS,
                job_counter=job_counter, 
                errors=errors, 
                signature="single_Pattern_single_file_parallel",
                execution=False,
                print_logging=False
            )

            job_counter += job_count * REPEATS

    print("All tests completed in: %s" % str(time.time()-runtime_start))

if __name__ == '__main__':
    args = sys.argv[1:]

    errors = []

    if args and args[0] == "warmup":
        warmup(errors)

    if args and args[0] == "tests":
#        sequential_tests(errors)
        pass

    else:
        no_execution_tests(errors)

    if errors:
        for error in errors:
            print(error)
    else:
        print('No errors to report')
