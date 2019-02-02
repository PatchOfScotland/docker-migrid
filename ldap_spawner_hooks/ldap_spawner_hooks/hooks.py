from ldap3 import Server, Connection
from .user import ldap_create


class ConnectionManager:

    def __init__(self, url, **connection_args):
        self.url = url
        self.connection = None
        self.connection_args = connection_args
        self.is_connected = False

    def connect(self):
        server = Server(self.url)
        self.connection = Connection(server, 'uid=admin,dc=example')
        self.is_connected = self.connection.bind()

    def is_connected(self):
        return self.is_connected

    def get_connection(self):
        return self.connection

    def change_connection_user(self, **user_args):
        self.connection.rebind(user_args)

    def disconnect(self):
        if self.connection.unbind():
            self.is_connected = False


def setup_ldap_user(spawner):
    try:
        user = spawner.user
    except AttributeError as err:
        spawner.log.error(
            "The spawner instance had no user attribute: {}".format(err))
        return None

    if not user:
        spawner.log.error("The spawner had a None user object instance")
        return None

    if 'data' not in user:
        spawner.log.error(
            "The user has no data instance that should contain the ldap_server_url")
        return None

    if 'ldap_server_url' not in user.data:
        spawner.log.error("The user's data attribute has no ldap_server_url")
        return None

    conn_manager = ConnectionManager(spawner.data.ldap_server_url, {''})
    conn_manager.connect()
    # if conn_manager.is_connected:
    #     ldap_create(user, conn_manager.get_connection())

    # Unicode characters must be base64 encoded

    # ALSO https://ldapwiki.com/wiki/Distinguished%20Names