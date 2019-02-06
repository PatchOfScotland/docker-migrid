import logging
from ldap3 import Server, Connection
from ldap3.utils.log import set_library_log_detail_level, EXTENDED, BASIC
from ldap3.core.exceptions import LDAPException
from traitlets import Unicode, Dict, List
from traitlets.config import SingletonConfigurable, LoggingConfigurable
from textwrap import dedent
from .ldap import add_dn


class LDAP(LoggingConfigurable):

    url = Unicode("", allow_none=False, config=True,
                  help=dedent("""
    URL/IP of the LDAP server.
    E.g. 127.0.0.1
    """))

    user = Unicode("", allow_none=False, config=True,
                   help=dedent("""
    Distinguished Name that is used to connect to the LDAP server.
    E.g. cn=admin,dc=example,dc=org
    """))

    password = Unicode(None, allow_none=True, config=True,
                       help=dedent("""
    Password used to authenticate as auth_user.
    """))


    base_dn = Unicode(None, allow_none=False, config=True,
                      help=dedent("""
        
    """))

    object_classes = List(trait=Unicode(), default_value=None, allow_none=False,
                          config=True, help=dedent("""
    Which LDAP object classes should be used to submit/setup the user.
    """))

    custom_name_attr = Unicode("", allow_none=False, config=True,
                               help=dedent("""
    A custom attribute override attribute that should be used 
    as the name to submit to the LDAP server instead of the default spawner.user.name
    """))

    replace_name_with = Dict(trait=Unicode(), traits={Unicode(): Unicode()}, default_value={},
                             help=dedent("""
    A dictionary of key value pairs that should be used to prepare the submit user name

    E.g. {'/': '+'}
    Which translates the following name as:
        /C=NA/ST=NA/L=NA/O=NA/OU=NA/CN=User Name/emailAddress=email@address.com

        +C=NA+ST=NA+L=NA+O=NA+OU=NA+CN=User Name+emailAddress=email@address.com
    """))

    name_strip_chars = List(trait=Unicode(), default_value=['/', '+', '*', ',', '.', '!', ' '],
                            help=dedent("""
    A list of characters that should be lstriped and rstriped from the submit name
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
    instance = LDAP()
    logging.basicConfig(filename='client_application.log', level=logging.DEBUG)
    set_library_log_detail_level(BASIC)

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

    if instance.custom_name_attr:
        # TODO, switch to only attribute lookup
        submit_name = ""
        if hasattr(user, instance.custom_name_attr):
            submit_name = getattr(user, instance.custom_name_attr)
        else:
            submit_name = user.data.get('User', {}).get('CERT', '')

    if not submit_name:
        spawner.log.error(
            "No valid submit_name was found {}".format(submit_name))
        return False

    conn_manager = ConnectionManager(
        instance.url, user=instance.auth_user, password=instance.password)
    conn_manager.connect()

    entry = None
    if conn_manager.is_connected():
        # Prepare submit name
        spawner.log.info("Submit name {}".format(submit_name))
        for replace_key, replace_val in instance.replace_name_with.items():
            submit_name = submit_name.replace(replace_key, replace_val)

        for strip in instance.name_strip_chars:
            submit_name = submit_name.strip(strip)

        spawner.log.info("Submit name {}".format(submit_name))
        success = add_dn(','.join([submit_name, instance.base_dn]),
                         conn_manager.get_connection(), object_class=instance.object_classes)
        if not success:
            spawner.log.error(
                "Failed to add {} to {}".format(submit_name, instance.url))
            return False
        # success, entry = get_dn(user.name, conn_manager.get_connection(), object_class=user_type)
        # if not success:
        #     spawner.log.error("Failed to get {} at {}".format(user.name, url))
        #     return False
    else:
        spawner.log.error("Failed to connect to {}".format(instance.url))
        return False

    spawner.log.info("Created {} at {} entry {}".format(
        user.name, instance.url, entry))
    return True
