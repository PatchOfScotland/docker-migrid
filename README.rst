=============
docker-migrid
=============

.. |docsbadge| image:: https://readthedocs.org/projects/docker-migrid/badge/?version=latest
    :target: https://docker-migrid.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status
|docsbadge|

A containerized version of the middleware `Minimum Intrusion Grid (MiG) <https://sourceforge.net/projects/migrid/>`_ system.

-----------------------------
Documentation/Getting Started
-----------------------------

To get started with `docker-migrid`, the general documentation and introduction can be found by pressing the |docsbadge| badge.
This includes a general description for how one should get started with MiGrid and its various services, and how you can deploy it on a system.

etc/resolv.conf
    nameserver 127.0.0.1
docker-compose up -d
docker exec -it migrid bash
/usr/sbin/sshd
su mig, ssh 127.0.0.1
https://ext.migrid.test
add workgroup
add resource, update proxy
NOTEBOOK_PARAMETERIZER="$HOME/.local/bin/notebook_parameterizer"
PAPERMILL="$HOME/.local/bin/papermill"
SSHFS_MOUNT="/usr/bin/sshfs"
SSHFS_UMOUNT="/bin/fusermount -uz"
python setupmeowdefs setup

nohup python -u run_tests.py > output.txt &
