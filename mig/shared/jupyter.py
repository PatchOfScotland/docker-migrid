#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jupyter - Helper functions for the jupyter service
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
#
# This file is part of MiG.
#
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

""" Jupyter service helper functions """


def gen_balancer_proxy_template(url, define, name, member_placeholder,
                                ws_member_placeholder):
    """ Generates an apache proxy balancer configuration section template
     for a particular jupyter service. Relies on the
     https://httpd.apache.org/docs/2.4/mod/mod_proxy_balancer.html module to
     generate the balancer proxy configuration.

    url: Setting the url_path to where the jupyter service is to be located.
    define: The name of the apache variable containing the 'url' value.
    name: The name of the jupyter service in question.
    member_placeholder: The unique identifiers that should be used to fill
     in balancer member defitions.
    ws_member_placeholder: The unique identifiers that should be used to fill
     in websocket balancer member defitions.
    """

    assert isinstance(url, basestring)
    assert isinstance(define, basestring)
    assert isinstance(name, basestring)
    assert isinstance(member_placeholder, basestring)
    assert isinstance(ws_member_placeholder, basestring)

    fill_helpers = {
        'url': url,
        'define': define,
        'name': name,
        'route_cookie': name.upper() + "_ROUTE_ID",
        'member_placeholder': member_placeholder,
        'ws_member_placeholder': ws_member_placeholder,
        'balancer_worker_env': '.%{BALANCER_WORKER_ROUTE}e',
        'remote_user_env': '%{PROXY_USER}e'
    }

    template = """
__JUPYTER_COMMENTED__ <IfDefine %(define)s>
__JUPYTER_COMMENTED__     Header add Set-Cookie "%(route_cookie)s=%(balancer_worker_env)s; path=%(url)s" env=BALANCER_ROUTE_CHANGED
__JUPYTER_COMMENTED__     <Proxy balancer://%(name)s_hosts>
__JUPYTER_COMMENTED__         %(member_placeholder)s
__JUPYTER_COMMENTED__         ProxySet stickysession=%(route_cookie)s
__JUPYTER_COMMENTED__     </Proxy>
__JUPYTER_COMMENTED__     # Websocket cluster
__JUPYTER_COMMENTED__     <Proxy balancer://ws_%(name)s_hosts>
__JUPYTER_COMMENTED__         %(ws_member_placeholder)s
__JUPYTER_COMMENTED__         ProxySet stickysession=%(route_cookie)s
__JUPYTER_COMMENTED__     </Proxy>
__JUPYTER_COMMENTED__     <Location %(url)s>
__JUPYTER_COMMENTED__         ProxyPreserveHost on
__JUPYTER_COMMENTED__         ProxyPass balancer://%(name)s_hosts%(url)s
__JUPYTER_COMMENTED__         ProxyPassReverse balancer://%(name)s_hosts%(url)s
__JUPYTER_COMMENTED__         RequestHeader set Remote-User %(remote_user_env)s
__JUPYTER_COMMENTED__     </Location>
__JUPYTER_COMMENTED__     <LocationMatch "%(url)s/(user/[^/]+)/(api/kernels/[^/]+/channels|terminals/websocket)/?">
__JUPYTER_COMMENTED__         ProxyPass   balancer://ws_%(name)s_hosts
__JUPYTER_COMMENTED__         ProxyPassReverse    balancer://ws_%(name)s_hosts
__JUPYTER_COMMENTED__     </LocationMatch>
__JUPYTER_COMMENTED__ </IfDefine>""" % fill_helpers
    return template


def gen_openid_template(url, define):
    """ Generates an openid apache configuration section template
     for a particular jupyter service.

    url: Setting the url_path to where the jupyter service is to be located.
    define: The name of the apache variable containing the 'url' value.
    """

    assert isinstance(url, basestring)
    assert isinstance(define, basestring)

    fill_helpers = {
        'url': url,
        'define': define
    }

    template = """
__JUPYTER_COMMENTED__ <IfDefine %(define)s>
__JUPYTER_COMMENTED__     <Location %(url)s>
__JUPYTER_COMMENTED__         # Pass SSL variables on
__JUPYTER_COMMENTED__         SSLOptions +StdEnvVars
__JUPYTER_COMMENTED__         AuthType OpenID
__JUPYTER_COMMENTED__         require valid-user
__JUPYTER_COMMENTED__     </Location>
__JUPYTER_COMMENTED__ </IfDefine>
""" % fill_helpers
    return template


def gen_rewrite_template(url, define):
    """ Generates an rewrite apache configuration section template
     for a particular jupyter service.

    url: Setting the url_path to where the jupyter service is to be located.
    define: The name of the apache variable containing the 'url' value.
    """

    assert isinstance(url, basestring)
    assert isinstance(define, basestring)

    fill_helpers = {
        'url': url,
        'define': define,
        'auth_phase_user': '%{LA-U:REMOTE_USER}',
        'uri': '%{REQUEST_URI}'
    }

    template = """
__JUPYTER_COMMENTED__ <IfDefine %(define)s>
__JUPYTER_COMMENTED__     <Location %(url)s>
__JUPYTER_COMMENTED__         RewriteCond %(auth_phase_user)s !^$
__JUPYTER_COMMENTED__         RewriteRule .* - [E=PROXY_USER:%(auth_phase_user)s,NS]
__JUPYTER_COMMENTED__     </Location>
__JUPYTER_COMMENTED__     RewriteCond %(uri)s ^%(url)s
__JUPYTER_COMMENTED__     RewriteRule ^ - [L]
__JUPYTER_COMMENTED__ </IfDefine>
""" % fill_helpers
    return template
