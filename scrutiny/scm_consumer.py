# -*- coding: utf-8 -*-
# scrutiny is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# scrutiny is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with scrutiny.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2013  Luke Macken <lmacken@redhat.com>
"""
scrutiny
========

Real-time source code auditing for Fedora
"""

import os
import git
import shutil
import subprocess

from moksha.hub.reactor import reactor
from fedmsg.consumers import FedmsgConsumer

# Where to clone the git repos
REPO_PATH = os.path.join(os.getcwd(), 'repos')

# Seconds between each print statement
PRINT_DELAY = 0.3

# Keep git repos & tarballs around, or clean them up after?
CLEAN = True


class SCMConsumer(FedmsgConsumer):

    topic = 'org.fedoraproject.prod.git.*'
    config_key = 'scrutiny'
    output = []

    def __init__(self, *args, **kw):
        super(SCMConsumer, self).__init__(*args, **kw)
        if not os.path.isdir(REPO_PATH):
            self.log.info('Creating %s' % REPO_PATH)
            os.mkdir(REPO_PATH)

    def consume(self, msg):
        if 'commit' not in msg['body']['msg']:
            return

        commit = msg['body']['msg']['commit']
        path = os.path.join(REPO_PATH, commit['repo'])
        if not os.path.isdir(path):
            self.clone_repo(commit['repo'], branch=commit['branch'])
        else:
            self.cmd('fedpkg switch-branch %s' % commit['branch'], cwd=path)
            self.cmd('git pull', cwd=path)

        self.cmd('git show --abbrev-commit --color %s' % commit['rev'],
                 cwd=path)
        if 'sources' in commit['stats']['files']:
            repo = git.Repo(path)
            self.diff_sources(repo, commit, path)
            self.diff_upstream(repo, commit, path)

        reactor.callLater(PRINT_DELAY, self.printer)

        if CLEAN:
            shutil.rmtree(path)

    def cmd(self, cmd, *args, **kw):
        self.log.info(cmd)
        p = subprocess.Popen(cmd, shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             *args, **kw)
        out, err = p.communicate()
        for line in out.split('\n') + err.split('\n'):
            self.output.append(line)

    def printer(self):
        "Slowly print stuff"
        if self.output:
            print(self.output.pop(0))
            reactor.callLater(PRINT_DELAY, self.printer)

    def clone_repo(self, repo, branch):
        url = 'git://pkgs.fedoraproject.org/%s' % repo
        self.cmd('git clone -b %s %s' % (branch, url), cwd=REPO_PATH)

    def diff_sources(self, repo, commit, path):
        "Diff the extracted sources of this commit and the previous"

        # Checkout and prep the previous commit
        repo.git.checkout('%s^' % commit['rev'], b='__old__')
        self.cmd('fedpkg --dist %s prep' % commit['branch'], cwd=path)
        old_source = self.find_source(repo, path)

        # Checkout and prep the most recent commit
        repo.git.checkout(commit['rev'], b='__new__')
        self.cmd('fedpkg --dist %s prep' % commit['branch'], cwd=path)
        new_source = self.find_source(repo, path, ignore=old_source)

        # Diff them
        self.cmd("diff -Nur '%s' '%s' | colordiff" % (old_source, new_source),
                 cwd=path)

        # Clean up
        repo.delete_head('__old__')
        repo.delete_head('__new__')
        self.cmd('fedpkg clean', cwd=path)

    def diff_upstream(self, repo, commit, path):
        "Diff the upstream tarball with what was uploaded to Fedora"
        self.log.info('Comparing against upstream tarball')
        self.cmd('spectool --get-files *.spec', cwd=path)
        upstream_src = self.find_source(repo, path)
        os.rename(upstream_src, upstream_src + '.upstream')
        upstream_src += '.upstream'
        self.cmd('fedpkg --dist %s prep' % commit['branch'], cwd=path)
        fedora_src = self.find_source(repo, path, ignore=upstream_src)
        self.cmd("diff -Nur '%s' '%s' | colordiff" % (upstream_src, fedora_src),
                 cwd=path)
        self.cmd('fedpkg clean', cwd=path)

    def find_source(self, repo, path, ignore=None):
        "Return the path to the expanded source tree in a given repo"
        if ignore:
            ignore = os.path.basename(ignore)
        for filename in repo.untracked_files:
            filename = os.path.dirname(filename)
            source = os.path.join(path, filename)
            if ignore and filename.startswith(ignore):
                continue
            if os.path.isdir(source):
                return source
