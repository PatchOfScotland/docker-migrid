# Example config
import os
from jhub.mount import SSHFSMounter
from jhubauthenticators import RegexUsernameParser, JSONParser

c = get_config()

c.JupyterHub.ip = '0.0.0.0'
c.JupyterHub.hub_ip = '0.0.0.0'
c.JupyterHub.port = 80
c.JupyterHub.base_url = '/dag'

# Spawner setup
c.JupyterHub.spawner_class = 'jhub.SwarmSpawner'
c.SwarmSpawner.jupyterhub_service_name = 'migrid-service_dag'
c.SwarmSpawner.start_timeout = 60 * 10
c.SwarmSpawner.networks = ['migrid-service_default']
c.SwarmSpawner.use_user_options = True

# Paths
home_path = os.path.join(os.sep, 'home', 'jovyan')
work_path = os.path.join(home_path, 'work')
dag_config_path = os.path.join(work_path, '__dag_config__')
r_libs_path = os.path.join(dag_config_path, 'R', 'libs')
python2_path = os.path.join(dag_config_path, 'python2')
python3_path = os.path.join(dag_config_path, 'python3')

conda_path = os.path.join(os.sep, 'opt', 'conda')
before_notebook_path = os.path.join(os.sep, 'usr', 'local', 'bin',
                                    'before-notebook.d')
r_env_path = os.path.join(conda_path, 'envs', 'r')
r_environ_path = os.path.join(r_env_path, 'lib', 'R', 'etc', 'Renviron')
jupyter_share_path = os.path.join(conda_path, 'share', 'jupyter')

user_uid = '1000'
user_gid = '100'

configs = [{'config_name': 'migrid-service_extensions_config',
            'filename': os.path.join(jupyter_share_path, 'lab', 'settings',
                                     'page_config.json'),
            'uid': user_uid,
            'gid': user_gid,
            'mode': 0o440},
           {'config_name': 'migrid-service_create_ipython_start_configs',
            'filename': os.path.join(before_notebook_path,
                                     'create_ipython_profile_start.py'),
            'uid': user_uid,
            'gid': user_gid,
            'mode': 0o555},
           {'config_name': 'migrid-service_create_r_libs_path_config',
            'filename': os.path.join(before_notebook_path,
                                     'create_r_libs_path_config.py'),
            'uid': user_uid,
            'gid': user_gid,
            'mode': 0o555},
           {'config_name': 'migrid-service_set_jupyter_kernels_config',
            'filename': os.path.join(before_notebook_path,
                                     'set_jupyter_kernels.py'),
            'uid': user_uid,
            'gid': user_gid,
            'mode': 0o555},
           {'config_name': 'migrid-service_set_python_pip_aliases_config',
            'filename': os.path.join(before_notebook_path,
                                     'set_pip_aliases.py'),
            'uid': user_uid,
            'gid': user_gid,
            'mode': 0o555},
           {'config_name': 'migrid-service_r_environ_config',
            'filename': r_environ_path,
            'uid': user_uid,
            'gid': user_gid,
            'mode': 0o440},
           {'config_name': 'migrid-service_r_server_config',
            'filename': os.path.join(os.sep, 'etc', 'rstudio', 'rserver.conf'),
            'uid': user_uid,
            'gid': user_gid,
            'mode': 0o440},
           {'config_name': 'migrid-service_update_path_env_config',
            'filename': os.path.join(os.sep, 'jupyter_startup_files',
                                     'update_path_env.py'),
            'uid': user_uid,
            'gid': user_gid,
            'mode': 0o555}]

c.SwarmSpawner.configs = configs

mounts = [SSHFSMounter({
    'type': 'volume',
    'driver_config': 'rasmunk/sshfs:latest',
    'driver_options': {'sshcmd': '{sshcmd}', 'id_rsa': '{id_rsa}',
                       'one_time': 'True',
                       'allow_other': '', 'reconnect': '', 'port': '{port}'},
    'source': '',
    'target': work_path})]

c.SwarmSpawner.container_spec = {
    'env': {'JUPYTER_ENABLE_LAB': '1',
            'NOTEBOOK_DIR': work_path,
            'R_LIBS_USER': r_libs_path,
            'R_ENVIRON_USER': r_environ_path,
            'IPYTHON_STARTUP_DIR': '/jupyter_startup_files',
            'JUPYTER_KERNEL_PYTHON2_ENV_PYTHONUSERBASE': python2_path,
            'JUPYTER_KERNEL_PYTHON3_ENV_PYTHONUSERBASE': python3_path},
    'mounts': mounts
}

c.SwarmSpawner.dockerimages = [
    {'image': 'nielsbohr/base-notebook:latest',
     'name': 'Base Notebook'},
    {'image': 'nielsbohr/python-notebook:latest',
     'name': 'Python Notebook'},
    {'image': 'nielsbohr/r-notebook:edge',
     'name': 'R Notebook'},
    {'image': 'nielsbohr/tensorflow-notebook:latest',
     'name': 'Tensorflow Notebook'}
]

# Authenticator setup
c.JupyterHub.authenticator_class = 'jhubauthenticators.HeaderAuthenticator'
c.HeaderAuthenticator.enable_auth_state = True
c.HeaderAuthenticator.allowed_headers = {'auth': 'Remote-User'}
c.HeaderAuthenticator.header_parser_classes = {'auth': RegexUsernameParser}
c.HeaderAuthenticator.user_external_allow_attributes = ['data']

# Email regex
RegexUsernameParser.username_extract_regex = '([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)'
RegexUsernameParser.replace_extract_chars = {'@': '_', '.': '_'}
