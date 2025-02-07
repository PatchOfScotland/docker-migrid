Introduction
============

Before we can get started with Docker MiGrid, a good place to start, is to get an understanding of the repository itself and how it is structured.

Docker MiGrid Structure
-----------------------

The Docker MiGrid is build up of several different components and services.
These have been seperated into two different categories, Associated services and MiGrid services.


Associated Services
-------------------

The Associated services, are services that makes it possible to host and run the MiGrid on your local machine.
These include the dynamic DNS service (devdns), and the Proxy service (nginx-proxy).

- devdns
    This service ensures that every container name is registered as an DNS entry in the devdns service under the `test` domain.
    In addition, it makes it possible for us to register additional aliases for each container, whereby they also can be reached.
    These additional aliases can be seen in the `docker-compose.yml` file.

- nginx-proxy
    The nginx-proxy service is responsible for forwarding HTTP/HTTPS requests to its designated url target.
    It is configured with the `nginx-proxy.conf` file, which is loaded upon launch.


MiGrid Services
---------------

The MiGrid services are composed of a number of different container services that each have their designated role.

.. _migrid_desc:

- migrid
    This is the main service that provides the basic MiGrid functionality, this includes the web interface and most of 
    its associated services. This includes features such as data management via the built-in filemanager, managing and creating WorkGroups,
    and establishing Share Links.

.. _migrid_io_desc:

- migrid-io
    The migrid-io services is responsible for bundling and exposing all io services, that are not part of the basic MiGrid service.
    This is in addition to it also providing the OpenID authentication services, which is also not part of the basic MiGrid service.
    In terms of io services, the `migrid-io` service supports the SFTP, WebDavs, and FTPS protocols.

.. _migrid_openid_desc:

- migrid-openid
    migrid-openid as the name indicates runs the OpenID service that can be used to authenticate on the MiGrid website.

.. _migrid_sftp_desc:

- migrid-sftp
    The migrid-sftp service host's and runs the SFTP service, which enables the user to conduct data management tasks against their
    MiGrid home directory.

.. _migrid_ftps_desc:

- migrid-ftps
    This is similar to the `migrid-sftp` other than it hosts and runs the FTPS service.

.. _migrid_webdavs_desc:

- migrid-webdavs
    WebDavs is like the SFTP and FTPS services, other than it enables io tasks via the HTTP protocol.

Deployment Profiles
~~~~~~~~~~~~~~~~~~~

The specified deployment profile in the `.env` file determines which of these service will be launch when the Docker MiGrid is deployed.
Currently, the available ones are `simplified` and `production`.

- simplified
    This profile launches Docker MiGrid as two containers. Namely the `migrid` and `migrid-io` services.
    This setup is intended to be used for trying out MiGrid on your own laptop, or running it on a single host.

- production
    With the production profile, Docker MiGrid is launched as several independent services. Currently, this 
    includes the `migrid`, `migrid-openid`, `migrid-sftp`, `migrid-ftps`, and `migrid-webdavs`.
    The point is to launch a production capable setup, where the MiGrid services can be launched across a span of hosts.


Simplified Profile Setup
~~~~~~~~~~~~~~~~~~~~~~~~
The `simplified` profile setup is made up of the following services:

    :ref:`migrid <migrid_desc>` and :ref:`migrid-io <migrid_io_desc>`

Production Profile Setup
~~~~~~~~~~~~~~~~~~~~~~~~~
The `production` profile setup is made up of the following services:

    :ref:`migrid <migrid_desc>`, :ref:`migrid-openid <migrid_openid_desc>`, :ref:`migrid-sftp <migrid_sftp_desc>`, :ref:`migrid-ftps <migrid_ftps_desc>`, and :ref:`migrid-webdavs <migrid_webdavs_desc>`

