# -*- coding: utf-8 -*-
#
# Univention Management Console
#
# Copyright 2014 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

from __future__ import absolute_import

import sys
from os import getuid, umask
from os.path import basename
from argparse import ArgumentParser

import notifier
import notifier.log as nflog

from twisted.internet import reactor

from univention.umc.util import ucr, set_locale
from univention.umc.server import Daemon

from univention.umc.module.site import ModuleServer


class ModuleDaemon(Daemon):

	# TODO: break API: run with 0; Bug #33241
	umask = 0077

	@property
	def logfile(self):
		if not self.options.logfile.startswith('/dev'):
			return '%s-%s' % (self.options.logfile, self.options.module)
		return self.options.logfile

	@property
	def default_debug(self):
		return int(ucr.get('umc/module/debug/level', 2))

	def parse_arguments(self):
		parser = ArgumentParser()
		add = parser.add_argument
		add(
			'socket', type=str, action='store',
			help='defines the socket to bind to'
		)
		add(
			'module', type=str, action='store',
			help='set the UMC daemon module to load'
		)
		add(
			'-l', '--language', default='C',
			type=str, action='store', dest='language',
			help='defines the language to use'
		)
		add(
			'-n', '--notifier', default='generic',
			type=str, action='store', dest='notifier',
			help='defines the notifier implementation to use'
		)
		add(
			'-d', '--debug', default=self.default_debug,
			action='store', type=int, dest='debug',
			help='if given than debugging is activated and set to the specified level [default: %(default)s]'
		)
		add(
			'-L', '--log-file', default='management-console-module',
			action='store', dest='logfile',
			help='specifies an alternative log file [default: %(default)s-<module name>.log]'
		)
		add(
			'-a', '-acls',
			action='store', dest='acls',
			help='specifies the filename of the ACLs'
		)
		self.options = parser.parse_args()

		if getuid() != 0:
			parser.error('%s must be started as root' % basename(sys.argv[0]))

	def listen(self):
		server = ModuleServer(self.options.module)

		# ensure that the UNIX socket is only accessable by root
		old_umask = umask(0077)
		try:
			reactor.listenUNIX(self.options.socket, server)
		finally:
			umask(old_umask)

		notifier.loop()

	def main(self):
		super(ModuleDaemon, self).main()
		self.set_locale()
		self.init_notifier()

	def set_locale(self):
		set_locale(self.options.language)

	def init_notifier(self):
		# TODO: only do this, when it is really importet
		# import umcp; del sys.modules['notifier']; import module; sys.modules.get('notifier')
		# (but what if the importet module relies on notifier on import time?) → doesn't occur
		# TODO: break API: remove notifier

		# MUST be called after initializing the deamon
		implementation = self.options.notifier.lower()
		types = dict(
			qt=notifier.QT,
			generic=notifier.TWISTED
		)

		if implementation == 'qt':
			import PyQt4.Qt as qt
			qt.QCoreApplication(sys.argv)

		notifier.init(types[implementation])

		# disable notifier logging
		nflog.instance.handlers = []
		# to activate notifier logging
		nflog.set_level(nflog.DEBUG)
		nflog.open()
