from ldap3 import Server, Connection
from .user import create


class ConnectionManager:

    def __init__(self, url):
        self.url = url
        self.connection = None


    def connect(self):
        pass


def setup_ldap_user(spawner):
    spawner.log.info("Hello from pre_spawn")
    try:
        user = spawner.user
    except AttributeError as err:
        spawner.log.error("The spawner instance had no user attribute: {}".format(err))
        return None

    if not user:
        spawner.log.error("The spawner had a None user object instance")
        return None

    if 'data' not in user:
        spawner.log.error("The user has no data instance that should contain the ldap_server_url")
        return None

    if 'ldap_server_url' not in user.data:
        spawner.log.error("The user's data attribute has no ldap_server_url")
        return None

    conn_manager = ConnectionManager(spawner.data.ldap_server_url)
    conn_manager.connect()
    create(user, conn_manager)
