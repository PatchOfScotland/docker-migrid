from ldap3 import Server, Connection

def rec_create_containers(containers):
    container = containers.pop(0)
    
    if containers:
        rec_create_containers(containers)


if __name__ == '__main__':
    server = Server('127.0.0.1')
    conn = Connection(server, 'cn=admin,dc=example,dc=org', password="admin")
    connected = conn.bind()
    print(conn)
    print("Hello")

    # cn = "/C=DK/ST=NA/L=NA/O=live/OU=NA/CN=Rasmus Munk/emailAddress=munk1@live.dk"
    # split_cn = cn.split('/')
    # containers, user = split_cn[1:-1], split_cn[-1]

    conn.add('ou=ldap1,ou=ldap2,ou=ldap3,dc=example,dc=org,cn=admin', 'organizationalUnit')

    # Need following structure
    # Country -> ST -> L -> O -> OU -> CN -> email

    # Might work with
    # conn.add('cn=email+commonName+.....,dc=)

    conn.unbind()

