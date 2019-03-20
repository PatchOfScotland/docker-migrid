# Example config
import os
from ldap_spawner_hooks import setup_ldap_user
from ldap_spawner_hooks import LDAP
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
c.DataRemoteUserAuthenticator.data_headers = ['Mount', 'User']
c.Authenticator.enable_auth_state = True

c.Spawner.pre_spawn_hook = setup_ldap_user

# Define LDAP options
LDAP.url = "openldap"
LDAP.user = "cn=admin,dc=migrid,dc=org"
LDAP.password = "dummyldap_password"
LDAP.base_dn = "dc=migrid,dc=org"

# Extract attributes
LDAP.user_provided_vars = ['emailAddress', 'CN']
LDAP.extract_attribute_queries = [{'search_base': LDAP.base_dn,
                                   'search_filter': '(objectclass=X-nextUserIdentifier)',
                                   'attributes': ['uidNumber']}]

LDAP.object_classes = ['X-certsDistinguishedName', 'PosixAccount']
LDAP.object_attributes = {'uid': '{emailAddress}',
                          'uidNumber': '{nextUidNumber}',
                          'gidNumber': '100',
                          'homeDirectory': '/home/{emailAddress}'}

LDAP.unique_object_attributes = ['emailAddress', 'CN']

# LDAP.attributes_range = {'uid': '10000-99999'}
LDAP.custom_name_attr = "CERT"
LDAP.replace_name_with = {'/': '+'}
