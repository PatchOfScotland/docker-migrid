import logging
from ldap3.utils.log import set_library_log_detail_level, EXTENDED, BASIC
from ldap3 import Server, Connection, ObjectDef

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
    parsed_cn += ',dc=example,dc=org'
    return_value = conn.add(parsed_cn, 'x-certsdn')

    conn.unbind()
