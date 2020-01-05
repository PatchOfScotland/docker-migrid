#!/opt/conda/bin/python3.7
import json
import os
from fcntl import flock, LOCK_EX
from jupyter_client import kernelspec

PYTHON_LANGUAGE = 'python'
kernels = []
kernelspecs = kernelspec.find_kernel_specs()
for k_name in kernelspecs:
    kernels.append(
        {'name': k_name, 'spec': kernelspec.get_kernel_spec(k_name)})

# Update env to
for kernel in kernels:
    name = kernel['name']
    spec = kernel['spec']
    env_name = 'PYTHONUSERBASE'
    user_base = os.environ.get(
        'JUPYTER_KERNEL_{}_ENV_{}'.format(name.upper(), env_name), None)
    if user_base:
        if spec.language == PYTHON_LANGUAGE:
            spec.env.update({env_name: user_base})
            kernel_path = os.path.join(spec.resource_dir, 'kernel.json')
            kernel_lock_path = os.path.join(spec.resource_dir,
                                            'kernel.json.lock')
            with open(kernel_lock_path, 'a') as lock_file:
                flock(lock_file.fileno(), LOCK_EX)
                with open(kernel_path, 'w') as kernel_file:
                    kernel_dict = spec.to_dict()
                    json.dump(kernel_dict, kernel_file, indent=4)
