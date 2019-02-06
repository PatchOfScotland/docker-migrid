def add_dn(dn, connection, **kwargs):
    return connection.add(dn, **kwargs)
    
def search_for(search_base, search_filter, connection, **kwargs):
    return connection.search(search_base, search_filter, **kwargs)
