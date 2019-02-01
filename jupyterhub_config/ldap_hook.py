from ldap import create_user


def jhub_ldap_user_hook(spawner):
    try:
        user = spawner.user
    except AttributeError as err:
        spawner.log.error("The spawner instance had no user attribute: {}".format(err))
        return None

    if not user:
        spawner.log.error("The spawner had a None user object instance")
        return None

    # TODO
    # Spawner has to have information about target ldap server.
