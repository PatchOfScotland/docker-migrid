#!/opt/conda/bin/python3.7
import os
import subprocess

local_py2_base = os.environ.get('JUPYTER_KERNEL_PYTHON2_ENV_PYTHONUSERBASE',
                                None)
local_py3_base = os.environ.get('JUPYTER_KERNEL_PYTHON3_ENV_PYTHONUSERBASE',
                                None)

aliases = []
if local_py2_base:
    pip2 = 'alias pip2="PYTHONUSERBASE={} pip2"'.format(local_py2_base)
    pip27 = 'alias pip2.7="PYTHONUSERBASE={} pip2.7"'.format(local_py2_base)
    python2 = 'alias python2="PYTHONUSERBASE={} python2"'.format(
        local_py2_base)
    python27 = 'alias python2.7="PYTHONUSERBASE={} python2.7"'.format(
        local_py2_base)
    aliases.extend([pip2, pip27, python2, python27])

if local_py3_base:
    pip = 'alias pip="PYTHONUSERBASE={} pip"'.format(local_py3_base)
    pip3 = 'alias pip3="PYTHONUSERBASE={} pip3"'.format(local_py3_base)

    python = 'alias python="PYTHONUSERBASE={} python"'.format(local_py3_base)
    python3 = 'alias python3="PYTHONUSERBASE={} python3"'.format(
        local_py3_base)
    python37 = 'alias python3.7="PYTHONUSERBASE={} python3.7"'.format(
        local_py3_base)
    python37m = 'alias python3.7m="PYTHONUSERBASE={} python3.7m"'.format(
        local_py3_base)
    aliases.extend([pip, pip3, python, python3, python37, python37m])

home = os.environ.get('HOME', None)
if aliases and home:
    alias_path = os.path.join(home, '.bash_aliases')
    if not os.path.exists(alias_path):
        os.mknod(alias_path, mode=0o664)

    for alias in aliases:
        subprocess.run(
            ['echo \'{}\' >> {}/.bash_aliases'.format(alias, home)],
            shell=True)
