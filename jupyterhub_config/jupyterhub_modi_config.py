import os
from jhub.mount import SSHFSMounter
# Example config
c = get_config()

c.JupyterHub.ip = '0.0.0.0'
c.JupyterHub.hub_ip = '0.0.0.0'
c.JupyterHub.port = 80
c.JupyterHub.base_url = '/modi'
c.JupyterHub.spawner_class = 'jhub.SwarmSpawner'

notebook_dir = os.environ.get('NOTEBOOK_DIR') or '/home/jovyan/work'

mounts = [
    SSHFSMounter({
        'source': '',
        'target': notebook_dir,
        'type': 'volume',
        'driver_config': 'rasmunk/sshfs:latest',
        'driver_options': {'sshcmd': '{sshcmd}',
                           'id_rsa': '{id_rsa}',
                           'one_time': 'True',
                           'reconnect': '', 'big_writes': '', 'allow_other': ''}
    })
]

c.SwarmSpawner.use_user_options = True

c.SwarmSpawner.container_spec = {
    'args': ['/usr/local/bin/start-singleuser.sh',
             '--NotebookApp.ip=0.0.0.0',
             '--NotebookApp.port=8888'],
    'env': {'JUPYTER_ENABLE_LAB': '1',
            'TZ': 'Europe/Copenhagen'}
}

c.SwarmSpawner.dockerimages = [
    {
        'image': 'nielsbohr/base-notebook:latest',
        'mounts': mounts,
        'name': 'modi'
    }
]
c.SwarmSpawner.jupyterhub_service_name = 'modi'
c.SwarmSpawner.networks = ['docker-migrid_default']

c.JupyterHub.authenticator_class = 'jhubauthenticators.DataRemoteUserAuthenticator'
c.DataRemoteUserAuthenticator.data_headers = ['Mount']
c.Authenticator.enable_auth_state = True
