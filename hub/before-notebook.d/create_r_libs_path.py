#!/opt/conda/bin/python3.7
import os

# Set custom Rprofile configuration path

env_name = 'R_LIBS_USER'
r_libs_user = os.environ.get(env_name, None)

if not r_libs_user:
    print("{} is not set, exiting without error".format(env_name))
    exit(0)

# Ensure that the libs path exist
if not os.path.exists(r_libs_user):
    print("creating {} dir: {}".format(env_name, r_libs_user))
    try:
        os.makedirs(r_libs_user)
    except IOError as err:
        print("Failed to create {} dir: {}, err: {}".format(
            env_name, r_libs_user, err))
        exit(1)

print("{} dir: {} exists".format(env_name, r_libs_user))
