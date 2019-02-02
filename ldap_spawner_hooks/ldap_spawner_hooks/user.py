

def ldap_create_user(user, connection):
    connection.add('ou')


def ldap_create_dn(dn, connection):
    connection.add(dn)
