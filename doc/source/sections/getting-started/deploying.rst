Deploying
=========

To deploy the MiGrid service, the Docker MiGrid package makes use of Docker-Compose as introduced in the prerequisites section.

The easiest way to deploy the Docker MiGrid services, is to execute the following command::

    docker-compose up -d


To stop the services, execute the following command::

    docker-compose down

After this command has been executed succesfully it should have launched the 4 following containers::

    CONTAINER ID   IMAGE                            COMMAND                  CREATED         STATUS         PORTS                                                                                                                                                                                                                                            NAMES
    419e4ede2af3   nielsbohr/migrid:basic           "/tini -- /app/docke…"   4 minutes ago   Up 4 minutes   80/tcp, 0.0.0.0:2222->2222/tcp, :::2222->2222/tcp, 0.0.0.0:4443->4443/tcp, :::4443->4443/tcp, 0.0.0.0:8021->8021/tcp, :::8021->8021/tcp, 0.0.0.0:8443->8443/tcp, :::8443->8443/tcp, 443-448/tcp, 0.0.0.0:22222->22222/tcp, :::22222->22222/tcp   migrid-io
    c06b70410fa7   jwilder/nginx-proxy              "/app/docker-entrypo…"   4 minutes ago   Up 4 minutes   0.0.0.0:80->80/tcp, :::80->80/tcp, 0.0.0.0:443-448->443-448/tcp, :::443-448->443-448/tcp                                                                                                                                                         nginx-proxy
    604bbebc6088   nielsbohr/migrid:basic           "/tini -- /app/docke…"   4 minutes ago   Up 4 minutes   80/tcp, 443-448/tcp, 2222/tcp, 4443/tcp, 8021/tcp, 22222/tcp                                                                                                                                                                                     migrid
    6df1818e879c   ruudud/devdns                    "/run.sh"                4 minutes ago   Up 4 minutes   127.0.0.1:53->53/udp                                                                                                                                                                                                                             devdns


Before your host will be able to discover the various migrid services on your localhost, it needs to know
that it should ask the `devdns` container for the IP associated with those service containers.
Therefore, you need to apply one of the options listed in the (Host Machine -> Containers) section at `DevDNS <https://github.com/ruudud/devdns>`_.

We recommend the least invasive method, namely to reconfigure the host machine's resolv.conf (in the case of a Unix-like system)
such that it asks the localhost devdns container as the **(IMPORTANT) first nameserver** before any other nameserver::

    #/etc/resolv.conf
    nameserver 127.0.0.1
    
    # Followed by your normal nameservers

Do note, that `resolv.conf` is often reset between reboots, and therefore the `nameserver 127.0.0.1`
resolv will likely have to be configured via your specific network manager or added again each time.

To test that this is working correctly, a simple ping test can be of great usage.
For instance, each of the following pings, should get an "instant" response from the default
docker network bridge (typically 172.17.0.1)::

    > ping migrid.test

    PING migrid.test (172.17.0.1) 56(84) bytes of data.
    64 bytes from hostname3056c770de6bbac891af62e0c4bb66d2.noval (172.17.0.1): icmp_seq=1 ttl=64 time=0.084 ms
    64 bytes from hostname3056c770de6bbac891af62e0c4bb66d2.noval (172.17.0.1): icmp_seq=2 ttl=64 time=0.099 ms

    > ping openid.migrid.test
    
    PING openid.migrid.test (172.17.0.1) 56(84) bytes of data.
    64 bytes from hostname3056c770de6bbac891af62e0c4bb66d2.noval (172.17.0.1): icmp_seq=1 ttl=64 time=0.137 ms
    64 bytes from hostname3056c770de6bbac891af62e0c4bb66d2.noval (172.17.0.1): icmp_seq=2 ttl=64 time=0.077 ms

After this is completed, you should be able to access the basic MiGrid page via the URL::

    https://migrid.test

If you are running `docker-migrid` on a remote server, this might give you a redirection error. If so try the following URL instead.
If neither of these two URLs takes you to the decribed OpenID login page. Please get in touch with us.::

    https://ext.migrid.test

This should take you to the default OpenID login page. The default development credentials for this is set in the `docker-compose.yml` file
under the `migrid` container `command` option::

    command: /app/docker-entry.sh -u test@migrid.test -p TestPw0rd -s "sftp ftps webdavs"

As shown here, the default user is set to `test@migrid.test` and with the password `TestPw0rd`.


.. image:: ../../res/images/getstart-authenticate.png

With these credentials, the authentication should redirect you to the Welcome page as shown below.

.. image:: ../../res/images/getstart-authenticated.png
