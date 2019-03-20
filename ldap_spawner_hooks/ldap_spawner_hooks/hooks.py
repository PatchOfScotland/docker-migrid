import logging
import copy
from ldap3 import Server, Connection, MODIFY_DELETE, MODIFY_ADD, BASE
from ldap3.utils.log import set_library_log_detail_level, BASIC
from ldap3.core.exceptions import LDAPException
from traitlets import Unicode, Dict, List
from traitlets.config import LoggingConfigurable, PyFileConfigLoader
from textwrap import dedent
from .ldap import add_dn, search_for, modify_dn


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
                      help=dedent(""""""))

    object_classes = List(trait=Unicode(), default_value=None, allow_none=False,
                          config=True, help=dedent("""
    Which LDAP object classes should be used for the add operation.
    """))

    object_attributes = Dict(trait=Unicode(), traits={Unicode(): Unicode()},
                             default_value={}, read_only=True,
                             help=dedent("""
    Which attributes should be attached to a specified LDAP object_class.
    """))

    unique_object_attributes = List(trait=Unicode(),
                                    default_value=[],
                                    help=dedent("""
    List of attributes inside the defined object_classes which are unique
     and can have duplicates in the DIT with the same object classes
    """))

    custom_name_attr = Unicode("", allow_none=False, config=True,
                               help=dedent("""
    A custom attribute override attribute that should be used
     as the name to submit to the LDAP server instead of
     the default spawner.user.name
    """))

    replace_name_with = Dict(trait=Unicode(), traits={Unicode(): Unicode()},
                             default_value={},
                             help=dedent("""
    A dictionary of key value pairs that should be used to prepare the submit
     user name

    E.g. {'/': '+'}
    Which translates the following name as:
        /C=NA/ST=NA/L=NA/O=NA/OU=NA/CN=User Name/emailAddress=email@address.com

        +C=NA+ST=NA+L=NA+O=NA+OU=NA+CN=User Name+emailAddress=email@address.com
    """))

    name_strip_chars = List(trait=Unicode(),
                            default_value=['/', '+', '*', ',', '.', '!', ' '],
                            help=dedent("""
    A list of characters that should be lstriped and rstriped from the submit name
    """))

    user_provided_vars = List(trait=Unicode(),
                              default_value=[''],
                              help=dedent("""
    A list of expected variables to be provided
    by the user input, used for subsituting dynamic values
    """))

    extract_attribute_queries = List(trait=Dict(), traits=[{Unicode(): Unicode()}],
                                     default_value=[{}],
                                     help=dedent("""
    A list of expected variables to be extracted and prepared from the base_dn LDAP DIT
    """))

    # def __deepcopy__(self, memo):

    #     ldap = LDAP()
    #     ldap.url

    #     return LDAP()


class ConnectionManager:

    def __init__(self, url, logger=None, **connection_args):
        if url is None:
            raise TypeError("url argument must be provided")

        if not isinstance(url, str) or not url:
            raise ValueError("url must be a non zero length string")

        if connection_args and not isinstance(connection_args, dict):
            raise TypeError("con    nection_args must be a dictionary")

        self.url = url
        self.logger = logger
        self.connection_args = connection_args
        self.connection = None
        self.connected = False

    def connect(self, **kwargs):
        server = Server(self.url, **kwargs)
        try:
            if self.connection_args:
                # Can be Anonymous if both 'user' and 'password' are None
                self.connection = Connection(server, **self.connection_args)
            else:
                # Anonymous login
                self.connection = Connection(server)
        except LDAPException as err:
            self.connected = False
            if self.logger is not None and getattr(self.logger, 'error', None) \
                    and callable(self.logger.error):
                self.logger.error("LDAP - Failed to create a connection, "
                                  "exception: {}".format(err))
            return None

        try:
            self.connected = self.connection.bind()
            if not self.connected:
                if self.logger is not None and getattr(self.logger, 'error', None) \
                        and callable(self.logger.error):
                    self.logger.error("LDAP - bind executed without error, "
                                      "but bind still failed: {}".format(self.connected))
        except LDAPException as err:
            self.connected = False
            if self.logger is not None and getattr(self.logger, 'error', None) \
                    and callable(self.logger.error):
                self.logger.error("LDAP - Failed to bind connection, "
                                  "exception: {}".format(err))
            return None

    def is_connected(self):
        return self.connected

    def get_connection(self):
        return self.connection

    def change_connection_user(self, **user_args):
        try:
            self.connection = self.connection.rebind(user_args)
        except LDAPException as err:
            if self.logger is not None and getattr(self.logger, 'error', None) \
                    and callable(self.logger.error):
                self.logger.error("LDAP - Failed to rebind connection, "
                                  "exception: {}".format(err))

    def disconnect(self):
        if self.connection.unbind():
            self.connected = False

    def get_response(self):
        return self.connection.response

    def get_result(self):
        return self.connection.result


def setup_ldap_user(spawner):
    instance = LDAP()
    # spawner.log.info("LDAP - spawn config {}".format(instance.config.path))
    # loader = PyFileConfigLoader(filename, path=spawner.config.path)
    # Ensure default config is not overridden
    # for attr, _ in instance.class_own_traits().items():
    #     setattr(instance, attr, copy.deepcopy(getattr(instance, attr)))

    # TODO, copy entire default config options dynamically
    instance.object_attributes = copy.deepcopy(instance.object_attributes)
    logging.basicConfig(filename='client_application.log', level=logging.DEBUG)
    set_library_log_detail_level(BASIC)

    if not hasattr(spawner, 'user'):
        spawner.log.error(
            "LDAP - The spawner instance had no user attribute {}".format(spawner))
        return False
    user = spawner.user

    if not user:
        spawner.log.error("LDAP - The spawner had a None user object instance")
        return False

    if not hasattr(user, 'name') or not isinstance(user.name, str) or \
            not user.name:
        spawner.log.error(
            "LDAP - The user's name attribute is either missing"
            " or not of str type: {}".format(user))
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
            "LDAP - No valid submit_name was found {}".format(submit_name))
        return False

    conn_manager = ConnectionManager(instance.url,
                                     logger=spawner.log,
                                     user=instance.user,
                                     password=instance.password)
    conn_manager.connect()

    entry = None
    if conn_manager.is_connected():
        # Check objectclasses support
        success = search_for(conn_manager.get_connection(),
                             'cn=Subschema',
                             '(objectClass=Subschema)',
                             search_scope=BASE,
                             attributes=['objectClasses'])
        response = conn_manager.get_response()
        if not success:
            spawner.log.error("LDAP - failed to query for "
                              "supported objectClasses {}".format(response))
            return False

        # spawner.log.debug("LDAP - supported objectClasses {}".format(response))
        found = []
        for entry in response:
            object_classes = entry['attributes']['objectClasses']
            found = [req_obj_class for obj_class in object_classes
                     for req_obj_class in instance.object_classes
                     if req_obj_class.lower() in obj_class.lower()]

        missing = set(instance.object_classes) - set(found)
        if missing:
            spawner.log.error("LDAP - only found: {} required "
                              "supported objectclasses, missing: {}".format(
                                  found, missing
                              ))
            return False

        # Prepare submit name
        spawner.log.info("LDAP - Submit name {}".format(submit_name))
        for replace_key, replace_val in instance.replace_name_with.items():
            submit_name = submit_name.replace(replace_key, replace_val)

        for strip in instance.name_strip_chars:
            submit_name = submit_name.strip(strip)

        # Turn list into dict
        submit_name_dict = {}
        for replace_key, replace_val in instance.replace_name_with.items():
            submit_name_dict.update(dict(item.split('=')
                                         for item in submit_name.split(replace_val)))

        spawner.log.debug("LDAP - prepared object_attributes: "
                          "{}".format(instance.object_attributes))

        search_filter = ''
        # objectclasses search filter
        if instance.object_classes:
            search_filter = '(&{})'.format(''.join(['(objectclass={})'.format(ldap_object)
                                                    for ldap_object in
                                                    instance.object_classes]))

        if instance.unique_object_attributes:
            search_attributes = ''.join(['({}={})'.format(attr.lower(),
                                                          submit_name_dict[attr])
                                         for attr in instance.unique_object_attributes
                                         if attr in submit_name_dict])

            # unique attributes search filter
            if search_filter:
                # strip last )
                search_filter = search_filter[:-1]
                search_filter += search_attributes + ')'
            else:
                search_filter = '(&{})'.format(search_attributes)

        spawner.log.debug("LDAP - unique_check, search_filter: {}".format(search_filter))
        # Check whether user already exists
        success = search_for(conn_manager.get_connection(),
                             instance.base_dn,
                             search_filter)
        if success:
            spawner.log.error("LDAP - {} already exist, response {}".format(
                submit_name_dict, conn_manager.get_response())
            )
            return False

        # Get extract variables
        extracted_attributes = {}
        for q in instance.extract_attribute_queries:
            query = copy.deepcopy(q)
            spawner.log.debug("LDAP - extract attribute with query: {}".format(query))
            if 'search_base' not in query or 'search_filter' not in query:
                spawner.log.error("LDAP - search_base or search_filter is missing from "
                                  "extract_attribute_queries: {}".format(query))
                return False
            success = search_for(conn_manager.get_connection(),
                                 query.pop('search_base', ''),
                                 query.pop('search_filter', ''),
                                 **query)
            if not success:
                spawner.log.error("LDAP - failed to use the query {} "
                                  "for extracting attributes".format(query))
                return False

            # get responses
            response = conn_manager.get_response()
            if response:
                spawner.log.info("LDAP - extract attributes "
                                 "search response {}".format(response))
                for entry in response:
                    spawner.log.debug("LDAP - search response entry {}".format(entry))
                    if 'attributes' in entry:
                        extracted_attributes.update(entry['attributes'])

        if 'uidNumber' in extracted_attributes:
            uidNumber = extracted_attributes['uidNumber']
            nextUidNumber = extracted_attributes['nextUidNumber'] = uidNumber + 1

            # Atomic increment uidNumber
            success = modify_dn(conn_manager.get_connection(),
                                ','.join(['cn=uidNext', instance.base_dn]),
                                {'uidNumber': [(MODIFY_DELETE, [uidNumber]),
                                               (MODIFY_ADD, [nextUidNumber])]})
            if not success:
                spawner.log.error("LDAP - failed to modify uidnumber")
                return False

        # Format user provided variables
        for attr_key, attr_val in instance.object_attributes.items():
            for prov_val in instance.user_provided_vars:
                # Check submit_name_dict
                if "{" + prov_val + "}" in attr_val and prov_val in submit_name_dict:
                    instance.object_attributes[attr_key] = attr_val.format(
                        **{prov_val: submit_name_dict[prov_val]})

            for extract_key, extract_val in extracted_attributes.items():
                # Check extracted_attributes
                if "{" + extract_key + "}" in attr_val:
                    instance.object_attributes[attr_key] = attr_val.format(
                        **{extract_key: extract_val})

        # Add DN
        spawner.log.info("LDAP - submit object: {}, attributes: {} "
                         "dn: {}".format(instance.object_classes,
                                         instance.object_attributes,
                                         submit_name))
        success = add_dn(conn_manager.get_connection(),
                         ','.join([submit_name, instance.base_dn]),
                         object_class=instance.object_classes,
                         attributes=instance.object_attributes)
        if not success:
            result = conn_manager.get_result()
            spawner.log.error(
                "LDAP - Failed to add {} to {} err: {}".format(
                    submit_name, instance.url, result))
            # If web enabled render result
            return False

        spawner.log.info("LDAP - User: {} created: {} at: {} with response: {}".format(
            user.name, submit_name, instance.url, conn_manager.get_response()))

        # Check that it exists in the db
        search_base = instance.base_dn
        search_filter = '(&{}'.format(''.join(['(objectclass={})'.format(ldap_object)
                                               for ldap_object in
                                               instance.object_classes]))
        search_filter += '{})'.format(
            ''.join(['({}={})'.format(attr_key, attr_val)
                     for attr_key, attr_val in instance.object_attributes.items()])
        )
        spawner.log.debug("LDAP - search_for,"
                          " search_base {}, search_filter {}".format(search_base,
                                                                     search_filter))
        success = search_for(conn_manager.get_connection(),
                             search_base,
                             search_filter)
        if not success:
            spawner.log.error("Failed to find {} at {}".format(
                (search_base, search_filter), instance.url)
            )
            return False
        spawner.log.info("LDAP - found {} in {}".format(conn_manager.get_response(),
                                                        instance.url))

        return True
    else:
        spawner.log.error("LDAP - Failed to connect to {}".format(instance.url))
        return False

    return None
  
