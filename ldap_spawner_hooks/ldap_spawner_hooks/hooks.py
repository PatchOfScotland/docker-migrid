import logging
import copy
from tornado import gen
from ldap3 import Server, Connection, MODIFY_DELETE, MODIFY_ADD, BASE
from ldap3.utils.log import set_library_log_detail_level, BASIC
from ldap3.core.exceptions import LDAPException
from traitlets import Unicode, Dict, List, Tuple
from traitlets.config import LoggingConfigurable
from textwrap import dedent
from .ldap import add_dn, search_for, modify_dn
from .utils import recursive_format


LDAP_SEARCH_ATTRIBUTE = '1'
SPAWNER_LDAP_OBJECT_ATTRIBUTE = '2'
DYNAMIC_ATTRIBUTE_METHODS = (LDAP_SEARCH_ATTRIBUTE,
                             SPAWNER_LDAP_OBJECT_ATTRIBUTE)


class LDAP(LoggingConfigurable):

    url = Unicode("", allow_none=False, config=True,
                  help=dedent("""
    URL/IP of the LDAP server.
    E.g. 127.0.0.1
    """))

    user = Unicode(trait=Unicode(), allow_none=False, config=True,
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
    Which LDAP object classes should be used for the add operation.
    """))

    object_attributes = Dict(trait=Unicode(), traits={Unicode(): Unicode()},
                             default_value={},
                             help=dedent("""
    Which attributes should be attached to a specified LDAP object_class.
    """))

    unique_object_attributes = List(trait=Unicode(),
                                    default_value=[],
                                    help=dedent("""
    List of attributes inside the defined object_classes which are unique
     and can have duplicates in the DIT with the same object classes
    """))

    submit_spawner_attribute = Unicode(trait=Unicode(), allow_none=True,
                                       config=True,
                                       default_value=None,
                                       help=dedent("""
    The attribute string that is used to access the LDAP object string
     in the passed in spawner object.
    This string is subsequently processed by replace_object_with
     to prepared it to be submitted to the LDAP DIT.
    """))

    # submit_user_auth_state_key = Unicode(trait=Unicode(), allow_none=True,
    #                                      config=True,
    #                                      default_value=None,
    #                                      help=dedent("""
    # The key used to extract the data from the user objects auth_state dictionary.
    # This string is subsequently processed by replace_object_with
    #  to prepared it to be submitted to the LDAP DIT.
    # """))

    submit_user_auth_state_selector = Tuple(trait=Unicode(),
                                            allow_none=True,
                                            config=True,
                                            default_value=(),
                                            help=dedent("""
    A tuple of values that are used to select the object value that should be 
    submitted to the LDAP DIT in the user's auth_state dictionary.
    """))

    replace_object_with = Dict(trait=Unicode(), traits={Unicode(): Unicode()},
                               default_value={},
                               help=dedent("""
    A dictionary of key value pairs that should be used to prepare the submit
     object string

    E.g. {'/': '+'}
    Which translates the following distinguished name as:
        /C=NA/ST=NA/L=NA/O=NA/OU=NA/CN=User Name/emailAddress=email@address.com

        +C=NA+ST=NA+L=NA+O=NA+OU=NA+CN=User Name+emailAddress=email@address.com
    """))

    name_strip_chars = List(trait=Unicode(),
                            default_value=['/', '+', '*', ',', '.', '!', ' '],
                            help=dedent("""
    A list of characters that should be lstriped and rstriped from the submit name
    """))

    dynamic_attributes = Dict(trait=Unicode(), traits={Unicode(): Unicode()},
                              default_value={},
                              help=dedent("""
    A dict of dynamic attributes that is generated from one of
    DYNAMIC_ATTRIBUTE_METHODS methods to extract values.
    """))

    search_attribute_queries = List(trait=Dict(), traits=[{Unicode(): Unicode()}],
                                    default_value=[{}],
                                    help=dedent("""
    A list of expected variables to be extracted and prepared from the base_dn LDAP DIT,
    generates the attributes expected by LDAP_SEARCH_ATTRIBUTE
    """))

    set_spawner_attributes = Dict(trait=Unicode(), traits={Unicode(): Unicode()},
                                  default_value={},
                                  help=dedent("""
    A dict of attributes that should be set on the passed in spawner object
    """))


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


def rec_has_attr(obj, attr):
    attributes = attr.split('.')
    for attr in attributes:
        has_attr = hasattr(obj, attr)
        if not has_attr:
            return False
        obj = getattr(obj, attr)

    return True


def rec_get_attr(obj, attr):
    attributes = attr.split('.')
    for attr in attributes:
        has_attr = hasattr(obj, attr)
        if not has_attr:
            return False
        obj = getattr(obj, attr)

    return obj


def tuple_dict_select(select_tuple, select_dict):
    selected = {}
    for key in select_tuple:
        if selected and isinstance(selected, dict) and key in selected:
            selected = selected[key]
        else:
            selected = select_dict[key]
    return selected


@gen.coroutine
def setup_ldap_user(spawner):
    instance = LDAP()
    # spawner.log.info("LDAP - spawn config {}".format(instance.config.path))
    # loader = PyFileConfigLoader(filename, path=spawner.config.path)
    # Ensure default config is not overridden
    # for attr, _ in instance.class_own_traits().items():
    #     setattr(instance, attr, copy.deepcopy(getattr(instance, attr)))

    # TODO, copy entire default config options dynamically
    instance.dynamic_attributes = copy.deepcopy(instance.dynamic_attributes)
    instance.set_spawner_attributes = copy.deepcopy(instance.set_spawner_attributes)
    instance.object_attributes = copy.deepcopy(instance.object_attributes)

    logging.basicConfig(filename='client_application.log', level=logging.DEBUG)
    set_library_log_detail_level(BASIC)

    if not instance.submit_spawner_attribute and \
            not instance.submit_user_auth_state_selector:
        spawner.log.error(
            "LDAP - either submit_spawner_attribute or submit_user_auth_state_selector "
            "has to define the object which is to be submitted to the LDAP DIT"
        )
        return False

    if instance.submit_spawner_attribute and instance.submit_user_auth_state_selector:
        spawner.log.error(
            "LDAP - both submit_spawner_attribute and submit_user_auth_state_selector "
            "can't both be set, either has to define what object "
            "should be submitted to the LDAP DIT"
        )
        return False

    ldap_data = None
    if instance.submit_spawner_attribute:
        # Parse spawner username attribute
        ldap_data = rec_get_attr(spawner, instance.submit_spawner_attribute)
        if not ldap_data:
            spawner.log.error("LDAP - The spawner object: {} did not have "
                              "the specified attribute: {}".format(
                                  spawner, instance.submit_spawner_attribute))
            return False

    if instance.submit_user_auth_state_selector:
        auth_state = yield spawner.user.get_auth_state()
        if not auth_state:
            spawner.log.error("LDAP - The user's auth_state seems to not be "
                              "correctly configured, the state is: {}".format(auth_state)
                              )
            return False

        ldap_data = tuple_dict_select(instance.submit_user_auth_state_selector,
                                      auth_state)
        if not ldap_data:
            spawner.log.error("LDAP - Failed to use the submit_user_auth_state_selector: "
                              "{} to find a value in the user's auth_state "
                              "dictionary: {}".format(
                                  instance.submit_user_auth_state_selector,
                                  auth_state
                              ))
            return False
        # ldap_data = auth_state[instance.submit_user_auth_state_key]
        # if not ldap_data:
        #     spawner.log.error("LDAP - The auth_state dictionary contained the "
        #                       "key: {} but it's value is: {}".format(
        #                           instance.submit_user_auth_state_key,
        #                           ldap_data)
        #                       )
        #     return False

    # Parse spawner user LDAP string to be parsed for submission
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

        # Prepare ldap data
        spawner.log.info("LDAP - Submit data {}".format(ldap_data))
        spawner.log.info("LDAP - replace_object_with {}".format(
            instance.replace_object_with))

        for replace_key, replace_val in instance.replace_object_with.items():
            ldap_data = ldap_data.replace(replace_key, replace_val)

        for strip in instance.name_strip_chars:
            ldap_data = ldap_data.strip(strip)

        # Turn ldap data string into dict, split on =
        ldap_dict = {}
        for replace_key, replace_val in instance.replace_object_with.items():
            ldap_dict.update(dict(item.split('=')
                                  for item in ldap_data.split(replace_val)))

        spawner.log.info("LDAP - Prepared dn: {} for submission and dict: {} "
                         "for attribute setup".format(ldap_data, ldap_dict))

        # LDAP, check for unique attributes that should not be duplicated
        if instance.unique_object_attributes:
            search_filter = ''
            # objectclasses search filter
            if instance.object_classes:
                search_filter = '(&{})'.format(
                    ''.join(['(objectclass={})'.format(object_class)
                             for object_class in
                             instance.object_classes])
                )

            search_attributes = ''.join(['({}={})'.format(attr.lower(),
                                                          ldap_dict[attr])
                                         for attr in instance.unique_object_attributes
                                         if attr in ldap_dict])

            # unique attributes search filter
            if search_filter:
                # strip last )
                search_filter = search_filter[:-1]
                search_filter += search_attributes + ')'
            else:
                search_filter = '(&{})'.format(search_attributes)

            spawner.log.debug(
                "LDAP - unique_check, search_filter: {}".format(search_filter))
            # Check whether user already exists
            success = search_for(conn_manager.get_connection(),
                                 instance.base_dn,
                                 search_filter)
            if success:
                spawner.log.error("LDAP - {} already exist, response {}".format(
                    ldap_dict, conn_manager.get_response())
                )
                return False

        # Get extract variables
        for q in instance.search_attribute_queries:
            query = copy.deepcopy(q)
            spawner.log.debug("LDAP - extract attribute with query: {}".format(query))
            if 'search_base' not in query or 'search_filter' not in query:
                spawner.log.error("LDAP - search_base or search_filter is missing from "
                                  "search_attribute_queries: {}".format(query))
                return False
            success = search_for(conn_manager.get_connection(),
                                 query.pop('search_base', ''),
                                 query.pop('search_filter', ''),
                                 **query)
            if not success:
                spawner.log.error("LDAP - failed to use the query: {} "
                                  "for extracting attributes, response was: {}".format(
                                      query,
                                      conn_manager.get_response()))
                return False

            # get responses
            response = conn_manager.get_response()
            if response:
                spawner.log.info("LDAP - extract attributes "
                                 "search response {}".format(response))
                for entry in response:
                    spawner.log.debug("LDAP - search response entry {}".format(entry))
                    if 'attributes' in entry:
                        ldap_dict.update(entry['attributes'])

        if 'uidNumber' in ldap_dict:
            uidNumber = ldap_dict['uidNumber']
            nextUidNumber = ldap_dict['nextUidNumber'] = uidNumber + 1

            # Atomic increment uidNumber
            success = modify_dn(conn_manager.get_connection(),
                                ','.join(['cn=uidNext', instance.base_dn]),
                                {'uidNumber': [(MODIFY_DELETE, [uidNumber]),
                                               (MODIFY_ADD, [nextUidNumber])]})
            if not success:
                spawner.log.error("LDAP - failed to modify uidnumber")
                return False

        # Prepare required dynamic attributes
        for attr_key, attr_val in instance.dynamic_attributes.items():
            # expected user_dict attributes
            if attr_val == SPAWNER_LDAP_OBJECT_ATTRIBUTE:
                if attr_key not in ldap_dict:
                    spawner.log.error("LDAP - expected username attribute: {}"
                                      " was not present in username object {}".format(
                                          attr_key, ldap_dict
                                      ))
                    return False
                instance.dynamic_attributes[attr_key] = ldap_dict[attr_key]
            # expected ldap extracted attributes
            if attr_val == LDAP_SEARCH_ATTRIBUTE:
                if attr_key not in ldap_dict:
                    spawner.log.error("LDAP - expected ldap attribute: {}"
                                      " was not present in ldap search object {}".format(
                                          attr_key, ldap_dict
                                      ))
                    return False
                instance.dynamic_attributes[attr_key] = ldap_dict[attr_key]

        # Format user provided variables
        recursive_format(instance.set_spawner_attributes, instance.dynamic_attributes)
        recursive_format(instance.object_attributes, instance.dynamic_attributes)
        # for dyn_key, dyn_val in instance.dynamic_attributes.items():
        #     for spawn_attr_key, spawn_attr_val in instance.set_spawner_attributes.item()
        # :
        #         if '{' + dyn_key + '}' in spawn_attr_val and \
        #                 '{' + dyn_key + '}' in instance.set_spawner_attributes[dyn_key]:
        #             instance.set_spawner_attributes[dyn_key].format(
        #                 **{dyn_key: dyn_val}
        #             )

        #     if dyn_key in instance.object_attributes and \
        #             '{' + dyn_key + '}' in instance.object_attributes[dyn_key]:
        #         instance.object_attributes[dyn_key].format(
        #             **{dyn_key: dyn_val}
        #         )

        # for attr_key, attr_val in instance.object_attributes.items():
        #     for dyn_key, dyn_val in instance.dynamic_attributes.items():
        #         if dyn_val in DYNAMIC_ATTRIBUTE_METHODS:
        #             spawner.log.error("LDAP - dynamic attribute: {} was not replaced, "
        #                               " is still: {}".format(dyn_key, dyn_val))
        #             return False

        #         if '{' + dyn_key + '}' in attr_val:
        #             instance.object_attributes[attr_key] = attr_val.format(
        #                 **{dyn_key: dyn_val})
        spawner.log.debug("LDAP - prepared spawner attributes {}".format(
            instance.set_spawner_attributes
        ))
        spawner.log.debug("LDAP - prepared object attributes {}".format(
            instance.object_attributes
        ))

        # Add DN
        spawner.log.info("LDAP - submit object: {}, attributes: {} "
                         "dn: {}".format(instance.object_classes,
                                         instance.object_attributes,
                                         ldap_data))
        success = add_dn(conn_manager.get_connection(),
                         ','.join([ldap_data, instance.base_dn]),
                         object_class=instance.object_classes,
                         attributes=instance.object_attributes)
        if not success:
            result = conn_manager.get_result()
            spawner.log.error(
                "LDAP - Failed to add {} to {} err: {}".format(
                    ldap_data, instance.url, result))
            # If web enabled render result
            return False

        spawner.log.info("LDAP - User: {} created: {} "
                         "at: {} with response: {}".format(spawner.user.name,
                                                           ldap_data,
                                                           instance.url,
                                                           conn_manager.get_response()))
        # Check that it exists in the db
        search_base = instance.base_dn
        search_filter = '(&{}'.format(''.join(['(objectclass={})'.format(object_class)
                                               for object_class in
                                               instance.object_classes]))
        search_filter += '{})'.format(
            ''.join(['({}={})'.format(attr_key, attr_val)
                     for attr_key, attr_val in instance.object_attributes.items()])
        )
        spawner.log.debug("LDAP - search_for, "
                          "search_base {}, search_filter {}".format(search_base,
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
