#!/opt/conda/bin/python3.7
import os

# Setup Renviron file
env_name = 'R_ENVIRON_USER'
r_environ_user = os.environ.get(env_name, None)
if r_environ_user:
    print("{} is not set, exiting without error".format(env_name))
    exit(0)

# Ensure that the libs path exist
if not os.path.exists(r_environ_user):
    print("creating {} dir: {}".format(env_name, r_environ_user))
    try:
        os.makedirs(r_environ_user)
    except IOError as err:
        print("Failed to create {} dir: {}, err: {}".format(
            env_name, r_environ_user, err))
        exit(1)

print("{} dir: {} exists".format(env_name, r_environ_user))

# Find Renviron template in descending order
search_paths = []
r_environ_path = None
# System
search_paths.append(os.path.join('etc', 'R'))

# R_PATH
r_path_env = os.environ.get('R_PATH', None)
if r_path_env:
    search_paths.append(r_path_env)
    search_paths.append(os.path.join(r_path_env, 'etc'))
    search_paths.append(os.path.join(r_path_env, 'lib', 'R', 'etc'))

# Home
home = os.path.expanduser('~')
search_paths.append(home)

# Current dir
cur_path = os.getcwd()
if os.path.exists(cur_path):
    search_paths.append(cur_path)

for search_path in search_paths:
    if os.path.exists(search_path):
        full_path = os.path.join(search_path, 'Renviron')
        if os.path.exists(full_path):
            r_environ_path = full_path

# Found template to
if r_environ_path:


if not r_environ_path:
    print("Failed to find a Renviron file in {}".format(search_paths))
else:
    os.environ[env_name] = r_environ_path
    print("Set {} to load Renviron from {}".format(env_name, r_environ_path))



# {'config_name': 'migrid-service_r_environ_config',
#  'filename': '/opt/conda/envs/r/lib/R/etc/Renviron',
#  'uid': '1000',
#  'gid': '100',
#  'mode': 0o440},