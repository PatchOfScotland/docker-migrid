from ldap3 import Server, Connection


def create(user):

    server = Server()
    conn = Connection(server, auto_bind=True)
