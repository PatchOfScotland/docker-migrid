import logging
from ldap3.utils.log import set_library_log_detail_level, EXTENDED, BASIC
from ldap3 import Server, Connection, ObjectDef, BASE, ALL_ATTRIBUTES, ALL_OPERATIONAL_ATTRIBUTES


def rec_create_containers(containers):
    container = containers.pop(0)
    if containers:
        rec_create_containers(containers)


if __name__ == '__main__':
    logging.basicConfig(filename='client_apllication.log', level=logging.DEBUG)
    set_library_log_detail_level(EXTENDED)

    server = Server('127.0.0.1')
    conn = Connection(server, user='cn=admin,dc=example,dc=org', password="admin")
    connected = conn.bind()

    cn = "/C=NA/ST=NA/L=NA/O=NA/OU=NA/CN=User Name/emailAddress=email@address.com"
    parsed_cn = cn.replace('/', '+').lstrip('+')
    parsed_cn += 'cn=admin,dc=example,dc=org'
#     return_value = conn.add(parsed_cn, 'x-certsdn')
    return_value = conn.search("cn=subschema", '(objectClass=PosixAccount)',
                               search_scope=BASE, attributes=ALL_ATTRIBUTES)
    print(return_value)
    print(conn.response)
    conn.unbind()
# ldapsearch -x -h 127.0.0.1 -w admin -D "cn=admin,dc=example,dc=org" -b "cn=subschema"
# -s base objectclasses | grep posix
