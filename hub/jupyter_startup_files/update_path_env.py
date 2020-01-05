import os
# Ensure that the IPython sessions have the correct search paths for commands

home = os.environ.get('HOME', None)
if not home:
    print("HOME env is required to run {}".format(__file__))
    exit(1)

if not os.path.exists(home):
    print("Directory specified by HOME env does not exist: {}".format(home))
    exit(2)

bin_dir = os.path.join(home, ".local/bin")
if not os.path.exists(bin_dir):
    print("local bin directory is not present, PATH is not altered")
    exit(3)
os.environ['PATH'] = bin_dir + ":/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
