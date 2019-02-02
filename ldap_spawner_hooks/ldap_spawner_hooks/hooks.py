from .user import create


def setup_ldap_user(spawner):
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
    spawner.log.info("Hello from pre_spawn")
    