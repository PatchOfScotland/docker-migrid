from ldap3 import Server, Connection
from ldap3.utils.log import set_library_log_detail_level, EXTENDED, BASIC
from ldap3.core.exceptions import LDAPException
from traitlets import Unicode
from traitlets.config import LoggingConfigurable
from textwrap import dedent
from .ldap import add_dn, get_dn


class LDAP(LoggingConfigurable):

    url = Unicode(None, allow_none=False, config=True,
                  help=dedent("""
    URL/IP of the LDAP server.
    E.g. 127.0.0.1
    """))

    user = Unicode(None, allow_none=False, config=True,
                   help=dedent("""
    Distinguished Name that is used to connect to the LDAP server.
    E.g. cn=admin,dc=example,dc=org
    """))

    password = Unicode(None, allow_none=True, config=True,
                       help=dedent("""
    Password used to authenticate as auth_user.
    """))

    object_class = Unicode(None, allow_none=True, config=True,
                           help=dedent("""
    Which LDAP object class should be used to submit/setup the user.
    """))

    custom_name_attr = Unicode("", allow_none=False, config=True,
                               help=dedent("""
    A custom attribute override attribute that should be used 
    as the name to submit to the LDAP server instead of the default spawner.user.name
    """))


class ConnectionManager:

    def __init__(self, url, **connection_args):
        if url is None:
            raise TypeError("url argument must be provided")

        if not isinstance(url, str) or not url:
            raise ValueError("url must be a non zero length string")

        if connection_args and not isinstance(connection_args, dict):
            raise TypeError("connection_args must be a dictionary")

        self.url = url
        self.connection_args = connection_args
        self.connection = None
        self.connected = False

    def connect(self):
        server = Server(self.url)
        try:
            if self.connection_args:
                # Can be Anonymous if both 'user' and 'password' are None
                self.connection = Connection(server, **self.connection_args)
            else:
                # Anonymous login
                self.connection = Connection(server)
        except LDAPException:
            # TODO, setup debug logging for failed connection
            self.connected = False
            return
        self.connected = self.connection.bind()

    def is_connected(self):
        return self.connected

    def get_connection(self):
        return self.connection

    def change_connection_user(self, **user_args):
        self.connection.rebind(user_args)

    def disconnect(self):
        if self.connection.unbind():
            self.connected = False


def setup_ldap_user(spawner):
    if not hasattr(spawner, 'user'):
        spawner.log.error(
            "The spawner instance had no user attribute {}".format(spawner))
        return False
    user = spawner.user

    if not user:
        spawner.log.error("The spawner had a None user object instance")
        return False

    if not hasattr(user, 'name') or not isinstance(user.name, str) or not user.name:
        spawner.log.error(
            "The user's name attribute is either missing or not of str type: {}".format(user))
        return False

    submit_name = spawner.user.name

    if LDAP.custom_name_attr:
        if hasattr(user, LDAP.custom_name_attr):
            submit_name = getattr(user, LDAP.custom_name_attr)

    conn_manager = ConnectionManager(
        LDAP.url, user=LDAP.auth_user, password=LDAP.password)
    conn_manager.connect()

    entry = None
    if conn_manager.is_connected():
        success = add_dn(submit_name, conn_manager.get_connection(),
                         object_class=LDAP.object_class)
        if not success:
            spawner.log.error(
                "Failed to add {} to {}".format(submit_name, LDAP.url))
            return False
        # success, entry = get_dn(user.name, conn_manager.get_connection(), object_class=user_type)
        # if not success:
        #     spawner.log.error("Failed to get {} at {}".format(user.name, url))
        #     return False
    else:
        spawner.log.error("Failed to connect to {}".format(LDAP.url))
        return False

    spawner.log.info("Created {} at {} entry {}".format(
        user.name, LDAP.url, entry))
    return True
