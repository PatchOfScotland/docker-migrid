
import os
import sys
import ConfigParser

from email.utils import parseaddr
from tempfile import NamedTemporaryFile

from mig.shared.base import valid_dir_input, client_id_dir, get_site_base_url, distinguished_name_to_user
from mig.shared.conf import get_configuration_object
from mig.shared.defaults import default_vgrid, all_vgrids, any_vgrid, keyword_members, _dot_vgrid
from mig.shared.fileio import delete_symlink, make_symlink, walk, delete_symlink, remove_rec
from mig.shared.safeeval import subprocess_call, subprocess_popen, subprocess_pipe, subprocess_stdout
from mig.shared.useradm import get_full_user_map
from mig.shared.vgrid import vgrid_create_allowed, vgrid_restrict_write_support, vgrid_flat_name, vgrid_is_owner, vgrid_settings, vgrid_set_owners, vgrid_set_members, vgrid_set_resources, vgrid_set_triggers, vgrid_set_settings, vgrid_set_workflow_jobs, vgrid_list_subvgrids, vgrid_members, vgrid_resources, vgrid_restrict_write_paths
from mig.shared.vgridaccess import unmap_vgrid
from mig.shared.vgridkeywords import get_settings_keywords_dict

from setupmeowdefs import USERNAME, VGRID

class Logger():
    def __init__(self):
        pass

    def debug(self, s):
        print("DEBUG: " + s)

    def error(self, s):
        print("ERROR: " + s)

    def info(self, s):
        print("INFO: " + s)

    def warning(self, s):
        print("WARNING: " + s)

def create_scm(
    configuration,
    client_id,
    vgrid_name,
    scm_dir,
    repair=False
):
    """Create new Mercurial SCM repository"""

    logger = Logger()
    kind = 'member'
    scm_alias = 'vgridscm'
    # TODO: we only really support scm cert access for now
    # NOTE: we default to MiG cert and fallback to ext cert
    server_url = configuration.migserver_https_mig_cert_url
    if not server_url:
        server_url = configuration.migserver_https_ext_cert_url
    if scm_dir.find('private') > -1:
        kind = 'owner'
        scm_alias = 'vgridownerscm'
    elif scm_dir.find('public') > -1:
        kind = 'public'
        scm_alias = 'vgridpublicscm'
        server_url = get_site_base_url(configuration)
    server_url_optional_port = ':'.join(server_url.split(':')[:2])
    cgi_template_script = os.path.join(configuration.hgweb_scripts,
                                       'hgweb.cgi')
    wsgi_template_script = os.path.join(configuration.hgweb_scripts,
                                        'hgweb.wsgi')

    # Depending on the Mercurial installation some of the
    # configuration strings may vary slightly.
    # We try to catch common variations with multiple targets

    script_template_name = 'repository name'
    script_template_repo = '/path/to/repo'
    script_template_repo_alt = '/path/to/repo/or/config'
    script_scm_name = '%s %s SCM repository' % (vgrid_name, kind)
    repo_base = 'repo'
    target_scm_repo = os.path.join(scm_dir, repo_base)
    repo_rc = os.path.join(target_scm_repo, '.hg', 'hgrc')
    repo_readme = os.path.join(target_scm_repo, 'readme')
    rc_text = '''
[web]
allow_push = *
allow_archive = gz, zip
description = The %s repository for %s participants
''' % (kind, vgrid_name)
    readme_text = '''This is the %(kind)s SCM repository for %(vgrid_name)s.

A web view of the repository is available on
%(server_url)s/%(scm_alias)s/%(vgrid_name)s
in any browser.
Access to non-public repositories is only granted if your user certificate
is imported in the browser.

For full access the repository you need a Mercurial client and the unpacked
user certificate files, that you received upon your certificate request.
Once again for non-public repositories you need client certificate support
in the client. Mercurial 1.3 and later is known to work with certificates,
but please refer to the documentation provided with your installation if you
have an older version. Installation of a newer version in user space should
be possible if case you do not have administrator privileges.

On the client a ~/.hgrc with something like:
[auth]
migserver.prefix = %(server_url_optional_port)s
migserver.key = /path/to/mig/key.pem
migserver.cert = /path/to/mig/cert.pem

# Disabled: we no longer rely on MiG CA signed server certificates
#[web]
#cacerts = /path/to/mig/cacert.pem

should allow access with your certificate.
In the above /path/to/mig is typically /home/USER/.mig where USER is
replaced by your login.

You can check out your own copy of the repository with:
hg clone %(server_url)s/%(scm_alias)s/%(vgrid_name)s [DESTINATION]

Please refer to the Mercurial documentation for further information about
the commands and work flows of this distributed SCM.
''' % {'vgrid_name': vgrid_name, 'kind': kind, 'scm_alias': scm_alias,
       'server_url': server_url,
       'server_url_optional_port': server_url_optional_port}

    cgi_scm_script = os.path.join(scm_dir, 'cgi-bin', 'hgweb.cgi')
    wsgi_scm_script = os.path.join(scm_dir, 'wsgi-bin', 'hgweb.wsgi')
    try:

        # Create scm directory

        if not repair or not os.path.isdir(scm_dir):
            os.mkdir(scm_dir)
        else:
            os.chmod(scm_dir, 0o755)

        # Create modified Mercurial Xgi scripts that use local scm repo.
        # In this way modification to one vgrid scm will not affect others.
        # WSGI script may or may not be included in hg installation.

        script_pairs = [(cgi_template_script, cgi_scm_script)]

        if os.path.exists(wsgi_template_script):
            script_pairs.append((wsgi_template_script, wsgi_scm_script))
        for (template_path, target_path) in script_pairs:
            if repair and os.path.isfile(target_path):
                continue
            target_dir = os.path.dirname(target_path)
            os.mkdir(target_dir)
            template_fd = open(template_path, 'r')
            template_script = template_fd.readlines()
            template_fd.close()
            script_lines = []

            for line in template_script:
                line = line.replace(script_template_name,
                                    script_scm_name)
                line = line.replace(script_template_repo_alt, target_scm_repo)
                line = line.replace(script_template_repo, target_scm_repo)
                script_lines.append(line)
            target_fd = open(target_path, 'w')
            target_fd.writelines(script_lines)
            target_fd.close()

            # IMPORTANT NOTE:
            # prevent users writing in Xgi-bin dirs to avoid remote execution
            # exploits

            os.chmod(target_path, 0o555)
            os.chmod(target_dir, 0o555)

        if not repair or not os.path.isdir(target_scm_repo):
            os.mkdir(target_scm_repo)
            os.chmod(target_scm_repo, 0o755)
            readme_fd = open(repo_readme, 'w')
            readme_fd.write(readme_text)
            readme_fd.close()
            # NOTE: set initial commit mail to server to avoid warning
            commit_email = '%s <%s@%s>' % (configuration.short_title,
                                           os.environ.get('USER', 'mig'),
                                           configuration.server_fqdn)
            # NOTE: we use command list here to avoid shell requirement
            subprocess_call([configuration.hg_path, 'init', target_scm_repo])
            subprocess_call([configuration.hg_path, 'add', repo_readme])
            subprocess_call([configuration.hg_path, 'commit', '-m"init"',
                             '-u"%s"' % commit_email, repo_readme])
        if not os.path.exists(repo_rc):
            open(repo_rc, 'w').close()
        os.chmod(repo_rc, 0o644)
        rc_fd = open(repo_rc, 'r+')
        rc_fd.seek(0, 2)
        rc_fd.write(rc_text)
        rc_fd.close()
        os.chmod(repo_rc, 0o444)

        os.chmod(scm_dir, 0o555)
        return True
    except Exception as exc:
        print('Could not create vgrid public_base directory: %s' % exc)
        return False


def create_tracker(
    configuration,
    client_id,
    vgrid_name,
    tracker_dir,
    scm_dir,
    repair=False
):
    """Create new Trac issue tracker bound to SCM repository if given"""

    logger = Logger()
    label = "%s" % configuration.site_vgrid_label
    kind = 'member'
    tracker_alias = 'vgridtracker'
    admin_user = distinguished_name_to_user(client_id)
    admin_email = admin_user.get('email', 'unknown@migrid.org')
    admin_id = admin_user.get(configuration.trac_id_field, 'unknown_id')
    # TODO: we only really support tracker cert access for now
    # NOTE: we default to MiG cert and fallback to ext cert
    server_url = configuration.migserver_https_mig_cert_url
    if not server_url:
        server_url = configuration.migserver_https_ext_cert_url
    if tracker_dir.find('private') > -1:
        kind = 'owner'
        tracker_alias = 'vgridownertracker'
    elif tracker_dir.find('public') > -1:
        kind = 'public'
        tracker_alias = 'vgridpublictracker'
        server_url = get_site_base_url(configuration)
    tracker_url = os.path.join(server_url, tracker_alias, vgrid_name)

    # Trac init is documented at http://trac.edgewall.org/wiki/TracAdmin
    target_tracker_var = os.path.join(tracker_dir, 'var')
    target_tracker_conf = os.path.join(target_tracker_var, 'conf')
    target_tracker_conf_file = os.path.join(target_tracker_conf, 'trac.ini')
    tracker_db = 'sqlite:db/trac.db'
    # NB: deploy command requires an empty directory target
    # We create a lib dir where it creates cgi-bin and htdocs subdirs
    # and we then symlink both a parent cgi-bin and wsgi-bin to it
    target_tracker_deploy = os.path.join(tracker_dir, 'lib')
    target_tracker_bin = os.path.join(target_tracker_deploy, 'cgi-bin')
    target_tracker_cgi_link = os.path.join(tracker_dir, 'cgi-bin')
    target_tracker_wsgi_link = os.path.join(tracker_dir, 'wsgi-bin')
    target_tracker_gvcache = os.path.join(target_tracker_var, 'gvcache')
    target_tracker_downloads = os.path.join(target_tracker_var, 'downloads')
    target_tracker_files = os.path.join(target_tracker_var, 'files')
    target_tracker_attachments = os.path.join(target_tracker_var,
                                              'files/attachments')
    target_tracker_log = os.path.join(target_tracker_var, 'log')
    target_tracker_log_file = os.path.join(target_tracker_log, 'trac.log')
    repo_base = 'repo'
    target_scm_repo = os.path.join(scm_dir, repo_base)
    project_name = '%s %s project tracker' % (vgrid_name, kind)
    create_cmd = None
    create_status = True
    # Trac requires tweaking for certain versions of setuptools
    # http://trac.edgewall.org/wiki/setuptools
    admin_env = {}
    # strip non-string args from env to avoid wsgi execv errors like
    # http://stackoverflow.com/questions/13213676
    for (key, val) in os.environ.items():
        if isinstance(val, basestring):
            admin_env[key] = val
    admin_env["PKG_RESOURCES_CACHE_ZIP_MANIFESTS"] = "1"

    try:

        # Create tracker directory

        if not repair or not os.path.isdir(tracker_dir):
            logger.info('create tracker dir: %s' % tracker_dir)
            os.mkdir(tracker_dir)
        else:
            logger.info('write enable tracker dir: %s' % tracker_dir)
            os.chmod(tracker_dir, 0o755)

        # Create Trac project that uses local storage.
        # In this way modification to one vgrid tracker will not affect others.

        if not repair or not os.path.isdir(target_tracker_var):
            # Init tracker with trac-admin command:
            # trac-admin tracker_dir initenv projectname db respostype repospath
            create_cmd = [configuration.trac_admin_path, target_tracker_var,
                          'initenv', vgrid_name, tracker_db, 'hg',
                          target_scm_repo]
            # Trac may fail silently if ini file is missing
            if configuration.trac_ini_path and \
                    os.path.exists(configuration.trac_ini_path):
                create_cmd.append('--inherit=%s' % configuration.trac_ini_path)

            # IMPORTANT: trac commands are quite verbose and will cause trouble
            # if the stdout/err is not handled (Popen vs call)
            logger.info('create tracker project: %s' % create_cmd)
            # NOTE: we use command list here to avoid shell requirement
            proc = subprocess_popen(create_cmd, stdout=subprocess_pipe,
                                    stderr=subprocess_stdout, env=admin_env)
            retval = proc.wait()
            if retval != 0:
                raise Exception("tracker creation %s failed: %s (%d)" %
                                (create_cmd, proc.stdout.read(), retval))

            # We want to customize generated project trac.ini with project info

            conf = ConfigParser.SafeConfigParser()
            conf.read(target_tracker_conf_file)

            conf_overrides = {
                'trac': {
                    'base_url': tracker_url,
                },
                'project': {
                    'admin': admin_email,
                    'descr': project_name,
                    'footer': "",
                    'url': tracker_url,
                },
                'header_logo': {
                    'height': -1,
                    'width': -1,
                    'src': os.path.join(server_url, 'images', 'site-logo.png'),
                    'link': '',
                },
            }
            if configuration.smtp_server:
                (from_name, from_addr) = parseaddr(configuration.smtp_sender)
                from_name += ": %s %s project tracker" % (vgrid_name, kind)
                conf_overrides['notification'] = {
                    'smtp_from': from_addr,
                    'smtp_from_name': from_name,
                    'smtp_server': configuration.smtp_server,
                    'smtp_enabled': True,
                }

            for (section, options) in conf_overrides.items():
                if not conf.has_section(section):
                    conf.add_section(section)
                for (key, val) in options.items():
                    conf.set(section, key, str(val))

            project_conf = open(target_tracker_conf_file, "w")
            project_conf.write("# -*- coding: utf-8 -*-\n")
            # dump entire conf file
            for section in conf.sections():
                project_conf.write("\n[%s]\n" % section)
                for option in conf.options(section):
                    project_conf.write("%s = %s\n" %
                                       (option, conf.get(section, option)))
            project_conf.close()

        if not repair or not os.path.isdir(target_tracker_deploy):
            # Some plugins require DB changes so we always force DB update here
            # Upgrade environment using trac-admin command:
            # trac-admin tracker_dir upgrade
            upgrade_cmd = [configuration.trac_admin_path, target_tracker_var,
                           'upgrade']
            logger.info('upgrade project tracker database: %s' % upgrade_cmd)
            # NOTE: we use command list here to avoid shell requirement
            proc = subprocess_popen(upgrade_cmd, stdout=subprocess_pipe,
                                    stderr=subprocess_stdout, env=admin_env)
            retval = proc.wait()
            if retval != 0:
                raise Exception("tracker 1st upgrade db %s failed: %s (%d)" %
                                (upgrade_cmd, proc.stdout.read(), retval))

            # Create cgi-bin with scripts using trac-admin command:
            # trac-admin tracker_dir deploy target_tracker_bin
            deploy_cmd = [configuration.trac_admin_path, target_tracker_var,
                          'deploy', target_tracker_deploy]
            logger.info('deploy tracker project: %s' % deploy_cmd)
            # NOTE: we use command list here to avoid shell requirement
            proc = subprocess_popen(deploy_cmd, stdout=subprocess_pipe,
                                    stderr=subprocess_stdout, env=admin_env)
            retval = proc.wait()
            if retval != 0:
                raise Exception("tracker deployment %s failed: %s (%d)" %
                                (deploy_cmd, proc.stdout.read(), retval))

        if not repair or not os.path.isdir(target_tracker_cgi_link):
            os.chmod(target_tracker_var, 0o755)
            os.symlink(target_tracker_bin, target_tracker_cgi_link)
        if not repair or not os.path.isdir(target_tracker_wsgi_link):
            os.chmod(target_tracker_var, 0o755)
            os.symlink(target_tracker_bin, target_tracker_wsgi_link)
        if not repair or not os.path.isdir(target_tracker_gvcache):
            os.chmod(target_tracker_var, 0o755)
            os.mkdir(target_tracker_gvcache)
        if not repair or not os.path.isdir(target_tracker_downloads):
            os.chmod(target_tracker_var, 0o755)
            os.mkdir(target_tracker_downloads)
        if not repair or not os.path.isdir(target_tracker_files):
            os.chmod(target_tracker_var, 0o755)
            os.mkdir(target_tracker_files)
        if not repair or not os.path.isdir(target_tracker_attachments):
            os.chmod(target_tracker_var, 0o755)
            os.mkdir(target_tracker_attachments)
        if not repair or not os.path.isfile(target_tracker_log_file):
            os.chmod(target_tracker_log, 0o755)
            open(target_tracker_log_file, 'w').close()

        if not repair or create_cmd:
            # Give admin rights to creator using trac-admin command:
            # trac-admin tracker_dir permission add ADMIN_ID PERMISSION
            perms_cmd = [configuration.trac_admin_path, target_tracker_var,
                         'permission', 'add', admin_id, 'TRAC_ADMIN']
            logger.info('provide admin rights to creator: %s' % perms_cmd)
            # NOTE: we use command list here to avoid shell requirement
            proc = subprocess_popen(perms_cmd, stdout=subprocess_pipe,
                                    stderr=subprocess_stdout, env=admin_env)
            retval = proc.wait()
            if retval != 0:
                raise Exception("tracker permissions %s failed: %s (%d)" %
                                (perms_cmd, proc.stdout.read(), retval))

            # Customize Wiki front page using trac-admin commands:
            # trac-admin tracker_dir wiki export WikiStart tracinfo.txt
            # trac-admin tracker_dir wiki import AboutTrac tracinfo.txt
            # trac-admin tracker_dir wiki import WikiStart welcome.txt
            # trac-admin tracker_dir wiki import SiteStyle style.txt

            settings = {'vgrid_name': vgrid_name, 'kind': kind, 'cap_kind':
                        kind.capitalize(), 'server_url':  server_url,
                        'css_wikipage': 'SiteStyle', '_label': label}
            if kind == 'public':
                settings['access_limit'] = "public"
                settings['login_info'] = """
This %(access_limit)s page requires you to register to get a login. The owners
of the %(_label)s will then need to give you access as they see fit.
""" % settings
            else:
                settings['access_limit'] = "private"
                settings['login_info'] = """
These %(access_limit)s pages use your certificate for login. This means that
you just need to click [/login login] to ''automatically'' sign in with your
certificate ID.

Owners of a %(_label)s can login and access the [/admin Admin] menu where they
can configure fine grained access permissions for all other users with access
to the tracker.

Please contact the owners of this %(_label)s if you require greater tracker
access.
""" % settings
            intro_text = \
                """= %(cap_kind)s %(vgrid_name)s Project Tracker =
Welcome to the ''%(access_limit)s'' %(kind)s project management site for the
'''%(vgrid_name)s''' %(_label)s. It interfaces with the corresponding code
repository for the %(_label)s and provides a number of tools to help software
development and project management.

== Quick Intro ==
This particular page is a Wiki page which means that all ''authorized''
%(vgrid_name)s users can edit it.

Generally wou need to [/login login] at the top of the page to get access to
most of the features here. The navigation menu provides buttons to access
 * this [/wiki Wiki] with customizable contents
 * a [/roadmap Project Roadmap] with goals and progress
 * the [/browser Code Browser] with access to the %(kind)s SCM repository
 * the [/report Ticket Overview] page with pending tasks or issues
 * ... and so on.
%(login_info)s

== Look and Feel ==
The look and feel of this project tracker can be customized with ordinary CSS
through the %(css_wikipage)s Wiki page. Simply create that page and go
ahead with style changes as you see fit.

== Limitations ==
For security reasons all project trackers are quite locked down to avoid abuse.
This implies a number of restrictions on the freedom to fully tweak them e.g.
by installing additional plugins or modifying the core configuration.  

== Further Information ==
Please see TitleIndex for a complete list of local wiki pages or refer to
TracIntro for additional information and help on using Trac.
""" % settings
            style_text = """/*
CSS settings for %(cap_kind)s %(vgrid_name)s project tracker.
Uncomment or add your style rules below to modify the look and feel of all the
tracker pages. The example rules target the major page sections, but you can
view the full page source to find additional style targets.
*/

/*
body {
  background: #ccc;
  background: transparent url('/images/pattern.png');
  color: #000;
  margin: 0;
  padding: 0;
}

#banner,#main,#footer {
  background: white;
  border: 1px solid black;
  border-radius: 4px;
  -moz-border-radius: 4px;
  padding: 8px;
  margin: 4px;
}

#main {
  /* Prevent footer overlap with menu */
  min-height: 500px;
}

#ctxnav,#mainnav {
  margin: 4px;
}

#header {
}

#logo img {
}
*/
""" % settings
            trac_fd, wiki_fd = NamedTemporaryFile(), NamedTemporaryFile()
            style_fd = NamedTemporaryFile()
            trac_tmp, wiki_tmp = trac_fd.name, wiki_fd.name
            style_tmp = style_fd.name
            trac_fd.close()
            wiki_fd.write(intro_text)
            wiki_fd.flush()
            style_fd.write(style_text)
            style_fd.flush()

            for (act, page, path) in [('export', 'WikiStart', trac_tmp),
                                      ('import', 'TracIntro', trac_tmp),
                                      ('import', 'WikiStart', wiki_tmp),
                                      ('import', 'SiteStyle', style_tmp)]:
                wiki_cmd = [configuration.trac_admin_path, target_tracker_var,
                            'wiki', act, page, path]
                logger.info('wiki %s %s: %s' % (act, page, wiki_cmd))
                # NOTE: we use command list here to avoid shell requirement
                proc = subprocess_popen(wiki_cmd, stdout=subprocess_pipe,
                                        stderr=subprocess_stdout,
                                        env=admin_env)
                retval = proc.wait()
                if retval != 0:
                    raise Exception("tracker wiki %s failed: %s (%d)" %
                                    (perms_cmd, proc.stdout.read(), retval))

            wiki_fd.close()

        # Some plugins require DB changes so we always force DB update here
        # Upgrade environment using trac-admin command:
        # trac-admin tracker_dir upgrade
        upgrade_cmd = [configuration.trac_admin_path, target_tracker_var,
                       'upgrade']
        logger.info('upgrade project tracker database: %s' % upgrade_cmd)
        # NOTE: we use command list here to avoid shell requirement
        proc = subprocess_popen(upgrade_cmd, stdout=subprocess_pipe,
                                stderr=subprocess_stdout, env=admin_env)
        retval = proc.wait()
        if retval != 0:
            raise Exception("tracker 2nd upgrade db %s failed: %s (%d)" %
                            (upgrade_cmd, proc.stdout.read(), retval))

        if repair:
            # Touch WSGI scripts to force reload of running instances
            for name in os.listdir(target_tracker_wsgi_link):
                os.utime(os.path.join(target_tracker_wsgi_link, name), None)
    except Exception as exc:
        create_status = False
        print('Could not create %s tracker: %s' % (label, exc))

    try:
        # IMPORTANT NOTE:
        # prevent users writing in cgi-bin, plugins and conf dirs to avoid
        # remote code execution exploits!
        #
        # We keep permissions at a minimum for the rest, but need to allow
        # writes to DB, attachments and log.

        logger.info('fix permissions on %s' % project_name)
        perms = {}
        for real_path in [os.path.join(target_tracker_var, i) for i in
                          ['db', 'attachments', 'files/attachments', 'log',
                           'gvcache', 'downloads']]:
            perms[real_path] = 0o755
        for real_path in [os.path.join(target_tracker_var, 'db', 'trac.db'),
                          target_tracker_log_file]:
            perms[real_path] = 0o644
        for real_path in [os.path.join(target_tracker_bin, i) for i in
                          ['trac.cgi', 'trac.wsgi']]:
            perms[real_path] = 0o555
        for (root, dirs, files) in walk(tracker_dir):
            for name in dirs + files:
                real_path = os.path.join(root, name)
                if real_path in perms:
                    logger.info('loosen permissions on %s' % real_path)
                    os.chmod(real_path, perms[real_path])
                elif name in dirs:
                    os.chmod(real_path, 0o555)
                else:
                    os.chmod(real_path, 0o444)
        os.chmod(tracker_dir, 0o555)
    except Exception as exc:
        create_status = False
        print('fix permissions on %s tracker failed: %s' % (label, exc))
        os.chmod(tracker_dir, 0000)
    return create_status


def create_forum(
    configuration,
    client_id,
    vgrid_name,
    forum_dir,
    repair=False
):
    """Create new forum - just the base dir"""
    try:
        if not repair or not os.path.isdir(forum_dir):
            os.mkdir(forum_dir)
        return True
    except Exception as exc:
        print('Could not create forum directory: %s' % exc)
        return False

def make_vgrid(vgrid_name):
    configuration = get_configuration_object()
    logger = Logger()
    client_id = USERNAME

    client_dir = client_id_dir(client_id)
    label = "%s" % configuration.site_vgrid_label

    reserved_names = (default_vgrid, any_vgrid, all_vgrids)
    if vgrid_name in reserved_names or not valid_dir_input(configuration.vgrid_home, vgrid_name):
        print('Illegal vgrid_name: %s' % vgrid_name)
        return

    user_map = get_full_user_map(configuration)
    user_dict = user_map.get(client_id, None)
    if not user_dict or not vgrid_create_allowed(configuration, user_dict):
        print("user %s is not allowed to create vgrids!" % client_id)
        return

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    vgrid_home_dir = os.path.abspath(os.path.join(configuration.vgrid_home, vgrid_name)) + os.sep
    public_files_dir = os.path.abspath(os.path.join(configuration.vgrid_public_base, vgrid_name)) + os.sep
    public_scm_dir = os.path.abspath(os.path.join(configuration.vgrid_public_base, vgrid_name, '.vgridscm')) + os.sep
    public_tracker_dir = os.path.abspath(os.path.join(configuration.vgrid_public_base, vgrid_name, '.vgridtracker')) + os.sep
    private_files_dir = os.path.abspath(os.path.join(configuration.vgrid_private_base, vgrid_name)) + os.sep
    private_scm_dir = os.path.abspath(os.path.join(configuration.vgrid_private_base, vgrid_name, '.vgridscm')) + os.sep
    private_tracker_dir = os.path.abspath(os.path.join(configuration.vgrid_private_base, vgrid_name, '.vgridtracker')) + os.sep
    private_forum_dir = os.path.abspath(os.path.join(configuration.vgrid_private_base, vgrid_name, '.vgridforum')) + os.sep
    vgrid_files_dir = os.path.abspath(os.path.join(configuration.vgrid_files_home, vgrid_name)) + os.sep
    vgrid_scm_dir = os.path.abspath(os.path.join(configuration.vgrid_files_home, vgrid_name, '.vgridscm')) + os.sep
    vgrid_tracker_dir = os.path.abspath(os.path.join(configuration.vgrid_files_home, vgrid_name, '.vgridtracker')) + os.sep
    vgrid_files_link = os.path.join(configuration.user_home, client_dir, vgrid_name)

    if vgrid_restrict_write_support(configuration):
        flat_vgrid = vgrid_flat_name(vgrid_name, configuration)
        vgrid_writable_dir = os.path.abspath(os.path.join(configuration.vgrid_files_writable, flat_vgrid)) + os.sep
    else:
        vgrid_writable_dir = None

    # does vgrid exist?

    if os.path.exists(vgrid_home_dir):
        print("user %s can't create vgrid %s - it exists!" % (client_id, vgrid_name))
        return

    # does a matching directory for vgrid share already exist?

    if os.path.exists(vgrid_files_link):
        print("user %s can't create vgrid %s - a folder shadows!" % (client_id, vgrid_name))
        return

    # verify that client is owner of imada or imada/topology if trying to
    # create imada/topology/test

    vgrid_name_list = vgrid_name.split('/')
    vgrid_name_parts = len(vgrid_name_list)
    if vgrid_name_parts <= 0:
        print('vgrid_name not specified?')
        return
    elif vgrid_name_parts == 1:

        # anyone can create base vgrid

        new_base_vgrid = True
    else:
        new_base_vgrid = False
        parent_vgrid_name = '/'.join(vgrid_name_list[0:vgrid_name_parts - 1])
        parent_files_base = os.path.dirname(vgrid_home_dir.rstrip(os.sep))
        if not os.path.isdir(parent_files_base):
            print("user %s can't create vgrid %s - no parent!" % (client_id, vgrid_name))
            return
        if not vgrid_is_owner(parent_vgrid_name, client_id, configuration):
            print("user %s can't create vgrid %s - not owner!" % (client_id, vgrid_name))
            return

        # Creating VGrid beneath a write restricted parent is not allowed

        (load_parent, parent_settings) = vgrid_settings(parent_vgrid_name, configuration, as_dict=True)
        if not load_parent:
            print('failed to load saved %s settings' % parent_vgrid_name)
            return

        # TODO: change this to support keyword_owners as well?
        #       at least then same write_shared_files MUST be forced on it
        if parent_settings.get('write_shared_files', keyword_members) != keyword_members:
            print("%s can't create vgrid %s - write limited parent!" % (client_id, vgrid_name))
            return

    # make sure all dirs can be created (that a file or directory with the same
    # name do not exist prior to the vgrid creation)

    try_again_string = """%s cannot be created, a file or directory exists with the same name, please try again with a new name!""" % label
    if os.path.exists(public_files_dir):
        print(try_again_string)
        return

    if os.path.exists(private_files_dir):
        print(try_again_string)
        return

    if os.path.exists(vgrid_files_dir):
        print(try_again_string)
        return

    # create directory to store vgrid files

    try:
        os.mkdir(vgrid_home_dir)
    except Exception as exc:
        print('Could not create vgrid base directory: %s' % exc)
        return

    # create directory to store vgrid public_base files

    try:
        os.mkdir(public_files_dir)
    except Exception as exc:
        print('Could not create vgrid public_base directory: %s' % exc)
        return

    # create directory to store vgrid private_base files

    try:
        os.mkdir(private_files_dir)
    except Exception as exc:
        print('Could not create vgrid private_base directory: %s' % exc)
        return

    # create directory in vgrid_files_home or vgrid_files_writable to contain
    # shared files for the new vgrid.

    try:
        if vgrid_writable_dir:
            os.mkdir(vgrid_writable_dir)
            make_symlink(vgrid_writable_dir.rstrip('/'), vgrid_files_dir.rstrip('/'), logger)
        else:
            os.mkdir(vgrid_files_dir)
    except Exception as exc:
        print('Could not create vgrid files directory: %s' % exc)
        return

    all_scm_dirs = ['', '', '']
    if configuration.hg_path and configuration.hgweb_scripts:

        # create participant scm repo in the vgrid shared dir
        # TODO: split further to save outside vgrid_files_dir?

        all_scm_dirs = [public_scm_dir, private_scm_dir, vgrid_scm_dir]
        for scm_dir in all_scm_dirs:
            if not create_scm(configuration, client_id, vgrid_name, scm_dir):
                print("couldn't create scm")
                return 

    all_tracker_dirs = ['', '', '']
    if configuration.trac_admin_path:

        # create participant tracker in the vgrid shared dir
        # TODO: split further to save outside vgrid_files_dir?

        all_tracker_dirs = [public_tracker_dir, private_tracker_dir,
                            vgrid_tracker_dir]
        for (tracker_dir, scm_dir) in zip(all_tracker_dirs, all_scm_dirs):
            if not create_tracker(configuration, client_id, vgrid_name, tracker_dir, scm_dir):
                print("couldn't create tracker")
                return 

    for forum_dir in [private_forum_dir]:
        if not create_forum(configuration, client_id, vgrid_name, forum_dir):
                print("couldn't create forum")
                return 

    # Create with client_id as owner but only add user in owners list
    # if new vgrid is a base vgrid (because symlinks to subdirs are not
    # necessary, and an owner is per definition owner of sub vgrids).

    owner_list = []
    if new_base_vgrid == True:
        owner_list.append(client_id)
        allow_empty = False
    else:
        allow_empty = True

    (owner_status, owner_msg) = vgrid_set_owners(configuration, vgrid_name, owner_list, allow_empty=allow_empty)
    if not owner_status:
        print('Could not save owner list: %s' % owner_msg)
        return

    # create empty pickled members list

    (member_status, member_msg) = vgrid_set_members(configuration, vgrid_name, [])
    if not member_status:
        print('Could not save member list: %s' % member_msg)
        return

    # create empty pickled resources list

    (resource_status, resource_msg) = vgrid_set_resources(configuration, vgrid_name, [])
    if not resource_status:
        print('Could not save resource list: %s' % resource_msg)
        return

    # create empty pickled triggers list

    (trigger_status, trigger_msg) = vgrid_set_triggers(configuration, vgrid_name, [])
    if not trigger_status:
        print('Could not save trigger list: %s' % trigger_msg)
        return

    # create default pickled settings list with only required values set to
    # leave all other fields for inheritance by default.

    init_settings = {}
    settings_specs = get_settings_keywords_dict(configuration)
    for (key, spec) in settings_specs.items():
        if spec['Required']:
            init_settings[key] = spec['Value']
    init_settings['vgrid_name'] = vgrid_name
    (settings_status, settings_msg) = vgrid_set_settings(configuration, vgrid_name, init_settings.items())
    if not settings_status:
        print('Could not save settings list: %s' % settings_msg)
        return

    # create empty job queue

    (queue_status, queue_msg) = vgrid_set_workflow_jobs(configuration, vgrid_name, [])
    if not queue_status:
        print('Could not save job queue: %s' % trigger_msg)
        return

    if new_base_vgrid:

        # create sym link from creators (client_id) home directory to directory
        # containing the vgrid files

        src = vgrid_files_dir
        if not make_symlink(src, vgrid_files_link, logger):
            print('Could not create link to %s files!' % label)
            return
        # make sure public_base dir exists in users home dir

        user_public_base = os.path.join(configuration.user_home, client_dir, 'public_base')
        try:
            if not os.path.isdir(user_public_base):
                os.mkdir(user_public_base)
        except:
            logger.warning("could not create %r!" % user_public_base)

        public_base_dst = os.path.join(user_public_base, vgrid_name)

        # create sym link for public_base

        if not make_symlink(public_files_dir, public_base_dst, logger):
            print('Could not create link to public_base dir!')
            return

        # make sure private_base dir exists in users home dir

        user_private_base = os.path.join(configuration.user_home, client_dir, 'private_base')
        try:
            if not os.path.isdir(user_private_base):
                os.mkdir(user_private_base)
        except:
            logger.warning("could not create %r!" % user_private_base)

        private_base_dst = os.path.join(user_private_base, vgrid_name)

        # create sym link for private_base

        if not make_symlink(private_files_dir, private_base_dst, logger):
            print('Could not create link to private_base dir!')
            return

        # create sym link to make public_base public by linking it to
        # wwwpublic/vgrid

        try:

            # make sure root dir exists

            os.mkdir(os.path.join(configuration.wwwpublic, 'vgrid'))
        except:

            # dir probably exists

            pass

        if not make_symlink(public_files_dir, os.path.join(configuration.wwwpublic, 'vgrid', vgrid_name), logger, force=True):
            print('Could not create link in wwwpublic/vgrid/%s' % vgrid_name)
            return

    return

def unlink_share(user_dir, vgrid):
    """Utility function to remove link to shared vgrid folder.

    user_dir: the full path to the user home where deletion should happen

    vgrid: the name of the vgrid to delete   

    Returns boolean success indicator and potential messages as a pair.

    Note: Removed links are hard-coded (as in other modules)
        user_dir/vgrid
    In case of a sub-vgrid, enclosing empty directories are removed as well.
    """
    success = True
    msg = ""
    path = os.path.join(user_dir, vgrid)
    try:
        if os.path.exists(path):
            os.remove(path)
            path = os.path.dirname(path)
            if os.path.isdir(path) and os.listdir(path) == []:
                os.removedirs(path)
    except Exception as err:
        success = False
        msg += "\nCould not remove link %s: %s" % (path, err)
    return (success, msg[1:])


def unlink_web_folders(user_dir, vgrid):
    """Utility function to remove links to shared vgrid web folders.

    user_dir: the full path to the user home where deletion should happen

    vgrid: the name of the vgrid to delete   

    Returns boolean success indicator and potential messages as a pair.

    Note: Removed links are hard-coded (as in other modules)
        user_dir/private_base/vgrid
        user_dir/public_base/vgrid
    In case of a sub-vgrid, enclosing empty directories are removed as well.
    """
    success = True
    msg = ""
    for infix in ["private_base", "public_base"]:
        path = os.path.join(user_dir, infix, vgrid)
        try:
            if os.path.exists(path):
                os.remove(path)
                path = os.path.dirname(path)
                if os.path.isdir(path) and os.listdir(path) == []:
                    os.removedirs(path)
        except Exception as err:
            success = False
            msg += "\nCould not remove link %s: %s" % (path, err)
    return (success, msg[1:])


def abandon_vgrid_files(vgrid, configuration):
    """Remove all files which belong to the given VGrid (parameter).
    This corresponds to the functionality in createvgrid.py, but we 
    can make our life easy by removing recursively, using a function
    in fileio.py for this purpose. The VGrid is assumed to be abandoned
    entirely.
    The function recursively removes the following directories: 
            configuration.vgrid_public_base/<vgrid>
            configuration.vgrid_private_base/<vgrid>
            configuration.vgrid_files_home/<vgrid>
    including any actual data for new flat format vgrids in
            configuration.vgrid_files_writable/<vgrid>
    and the soft link (if it is a link, not a directory)
            configuration.wwwpublic/vgrid/<vgrid>

    vgrid: The name of the VGrid to delete
    configuration: to determine the location of the directories 


    Note: the entry for the VGrid itself, configuration.vgrid_home/<vgrid>
            is removed separately, see remove_vgrid_entry
    Returns: Success indicator and potential messages.
    """

    _logger = Logger()
    _logger.debug('Deleting all files for vgrid %s' % vgrid)
    success = True
    msg = ""

    # removing this soft link may fail, since it is a directory for sub-VGrids

    try:
        os.remove(os.path.join(configuration.wwwpublic, 'vgrid', vgrid))
    except Exception as err:
        _logger.debug(
            'not removing soft link to public vgrids pages for %s: %s' %
            (vgrid, err))

    for prefix in [configuration.vgrid_public_base,
                   configuration.vgrid_private_base,
                   configuration.vgrid_files_home]:
        data_path = os.path.join(prefix, vgrid)
        # VGrids on flat format with readonly support has a link and a dir
        if os.path.islink(data_path):
            link_path = data_path
            data_path = os.path.realpath(link_path)
            _logger.debug('delete symlink: %s' % link_path)
            delete_symlink(link_path, _logger)
        _logger.debug('delete vgrid dir: %s' % data_path)
        success_here = remove_rec(data_path, configuration)
        if not success_here:
            kind = prefix.strip(os.sep).split(os.sep)[-1]
            msg += "Error while removing %s %s" % (vgrid, kind)
            success = False

    if msg:
        _logger.debug('Messages: %s.' % msg)

    return (success, msg)

def remove_vgrid_entry(vgrid, configuration):
    """Remove an entry for a VGrid in the vgrid configuration directory.
            configuration.vgrid_home/<vgrid>

    The VGrid contents (shared files and web pages) are assumed to either 
    be abandoned entirely, or become subdirectory of another vgrid (for 
    sub-vgrids). Wiki and SCM are deleted as well, as they would  be unusable
    and undeletable.

    vgrid: the name of the VGrid to delete
    configuration: to determine configuration.vgrid_home

    Returns: Success indicator and potential messages.
    """

    _logger = Logger()
    _logger.debug('Removing entry for vgrid %s' % vgrid)

    msg = ''
    success = remove_rec(os.path.join(configuration.vgrid_home, vgrid),
                         configuration)
    if not success:

        _logger.debug('Error while removing %s.' % vgrid)
        msg += "Error while removing entry for %s." % vgrid

    else:

        for prefix in [configuration.vgrid_public_base,
                       configuration.vgrid_private_base,
                       configuration.vgrid_files_home]:

            # Gracefully delete any public, member, and owner SCMs/Trackers/...
            # They may already have been wiped with parent dir if they existed

            for collab_dir in _dot_vgrid:
                collab_path = os.path.join(prefix, vgrid, collab_dir)
                if not os.path.exists(collab_path):
                    continue

                # Re-map to writable if collab_path points inside readonly dir
                if prefix == configuration.vgrid_files_home:
                    (_, _, rw_path, ro_path) = \
                        vgrid_restrict_write_paths(vgrid, configuration)
                    real_collab = os.path.realpath(collab_path)
                    if real_collab.startswith(ro_path):
                        collab_path = real_collab.replace(ro_path, rw_path)

                if not remove_rec(collab_path, configuration):
                    _logger.warning('Error while removing %s.' % collab_path)
                    collab_name = collab_dir.replace('.vgrid', '')
                    msg += "Error while removing %s for %s" % (collab_name,
                                                               vgrid)

    return (success, msg)

def remove_vgrid(vgrid_name):
    client_id = USERNAME
    cert_dir = client_id
    configuration = get_configuration_object()
    logger = Logger()

    # check if any resources participate or sub-vgrids depend on this one

    (list_status, subs) = vgrid_list_subvgrids(vgrid_name, configuration)

    if not list_status:
        logger.error('Error loading sub-vgrid for %s: %s)' % (vgrid_name, subs))
        return

    if len(subs) > 0:
        logger.debug('Cannot delete: still has sub-vgrids: %s' % subs)
        return

    # we consider the local members and resources here, not inherited ones

    (member_status, members_direct) = vgrid_members(vgrid_name, configuration, False)
    (resource_status, resources_direct) = vgrid_resources(vgrid_name, configuration, False)
    if not member_status or not resource_status:
        logger.warning('failed to load %s members or resources: %s %s' % (vgrid_name, members_direct, resources_direct))
        return
    if len(resources_direct) > 0:
        logger.debug('Cannot delete: still has direct resources %s.' % resources_direct)
        return

    if len(members_direct) > 0:
        logger.debug('Cannot delete: still has direct members %s.' % members_direct)
        return

    # Deleting write restricted VGrid is not allowed

    (load_status, saved_settings) = vgrid_settings(vgrid_name, configuration, recursive=True, as_dict=True)
    if not load_status:
        print('failed to load saved %s settings' % vgrid_name)
        return

    # NOTE: legacy vgrids may have setting False to mean full write
    if saved_settings.get('write_shared_files', keyword_members) not in [False, keyword_members]:
        logger.warning("%s can't delete vgrid %s - write limited!" % (client_id, vgrid_name))
        return

    # When reaching here, OK to remove the VGrid.
    #   if top-level: unlink, remove all files and directories,
    #   in all cases: remove configuration entry for the VGrid
    #   unlink and move new-style vgrid sub dir to parent

    logger.info('Deleting %s and all related data as requested' % vgrid_name)

    # owner owns this vgrid, direct ownership

    logger.debug('%s looks like a top-level vgrid.' % vgrid_name)
    logger.debug('Deleting all related files.')

    user_dir = os.path.abspath(os.path.join(configuration.user_home, cert_dir)) + os.sep
    (share_lnk, share_msg) = unlink_share(user_dir, vgrid_name)
    (web_lnk, web_msg) = unlink_web_folders(user_dir, vgrid_name)
    (files_act, files_msg) = abandon_vgrid_files(vgrid_name, configuration)

    (removed, entry_msg) = remove_vgrid_entry(vgrid_name, configuration)

    if not share_lnk or not web_lnk or not files_act or not removed:
        err = '\n'.join([share_msg, web_msg, files_msg, entry_msg])
        logger.error('Errors while removing %s:\n%s.' % (vgrid_name, err))
        return

    else:
        # Remove vgrid from vgrid cache (after deleting all)
        unmap_vgrid(configuration, vgrid_name)
        return

if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) < 2:
        print('Not enough args')

    if args[0] == 'make':
        make_vgrid(args[1])

    elif args[0] == 'remove':
        remove_vgrid(args[1])