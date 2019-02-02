# Example config
from ldap_spawner_hooks import setup_ldap_user
c = get_config()

c.JupyterHub.ip = '0.0.0.0'
c.JupyterHub.hub_ip = '0.0.0.0'
c.JupyterHub.port = 80
c.JupyterHub.base_url = '/modi'
c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'

c.DockerSpawner.image = 'nielsbohr/base-notebook:latest'
c.DockerSpawner.remove_containers = True

c.DockerSpawner.network_name = 'docker-migrid_default'

c.JupyterHub.authenticator_class = 'jhubauthenticators.DataRemoteUserAuthenticator'
c.DataRemoteUserAuthenticator.data_headers = ['Mount', 'User-ID']
c.Authenticator.enable_auth_state = True

c.Spawner.pre_spawn_hook = setup_ldap_user
 