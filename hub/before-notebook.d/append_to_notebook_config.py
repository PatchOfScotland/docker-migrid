#!/opt/conda/bin/python3.7
import os

# This script is used to append configuration options to the
# jupyter_notebook_config.py which is provided by the base
# jupyter image

config_path = os.path.join(os.sep, 'etc', 'jupyter',
                           'jupyter_notebook_config.py')

# Variable declarations that should be appended to the config
content = {
    # code-server traitlet
    'c.ServerProxy.servers': {
        'code-server': {
            'command': [
                'code-server',
                '--auth',
                'none',
                '--disable-telemetry',
                '--allow-http',
                '--port={port}'
            ],
            'timeout': 20,
            'launcher_entry': {
                'title': 'VS Code'
            }
        }
    }
}

# Open in append mode
with open(config_path, 'a') as config:
    config.write('\n')
    for var, value in content.items():
        stmt = "{} = {}".format(var, value)
        config.write(stmt)
