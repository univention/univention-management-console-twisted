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

import os
from os import umask
from os.path import join
from argparse import ArgumentParser
from daemon.daemon import DaemonContext

from twisted.web.server import Session
from twisted.internet import reactor, ssl
from twisted.python.components import registerAdapter

from univention.umc import Translation as ITranslation, User, ACLs
from univention.umc.util import log_init, ucr, Translation
from univention.umc.authentication import PAMAuthenticatedUser, LdapACLs
from univention.umc.server.site import Server


class Daemon(object):

	umask = 0

	def __init__(self):
		self.options = None
		self.main()
		self.listen()

	def main(self):
		self.parse_arguments()
		self.clear_environment()
		self.init_logging()
		self.set_umask()
		self.register_adapters()
		self.daemonize()

	def clear_environment(self):
		os.environ.clear()
		os.environ['PATH'] = '/bin:/sbin:/usr/bin:/usr/sbin'

	def init_logging(self):
		log_init(self.logfile, self.options.debug)

	def set_umask(self):
		umask(self.umask)

	def register_adapters(self):
		# TODO: move into ServerDaemon? (Module uses Translation)
		registerAdapter(PAMAuthenticatedUser, Session, User)
		registerAdapter(Translation, Session, ITranslation)
		registerAdapter(LdapACLs, Session, ACLs)

	def parse_arguments(self):  # pragma: no-cover
		raise NotImplementedError

	def listen(self):  # pragma: no-cover
		raise NotImplementedError

	def daemonize(self):  # pragma: no-cover
		pass
		#daemon = DaemonContext(detach_process=False, umask=0077)  # TODO: umask param? self.umask
		#daemon.open()


class ServerDaemon(Daemon):

	@property
	def default_locale(self):
		return ucr.get('locale/default', 'C').split(':')[0]

	@property
	def default_debug(self):
		return int(ucr.get('umc/server/debug/level', 2))

	@property
	def port(self):
		return int(ucr.get('umc/http/port', 6670))  # 8090

	@property
	def ssl_port(self):
		return int(ucr.get('umc/https/port', 8443))

	@property
	def interface(self):
		return ucr.get('umc/http/interface', '127.0.0.1')

	@property
	def logfile(self):
		return self.options.logfile

	def clear_environment(self):
		super(ServerDaemon, self).clear_environment()
		os.environ['LANG'] = self.default_locale

	def parse_arguments(self):
		# TODO: reimplement Daemon arguments
		parser = ArgumentParser()
		add = parser.add_argument
		add(
			'-n', '--no-daemon', default=True,
			action='store_false', dest='daemon_mode',
			help='if set the process will not fork into the background'
		)
		add(
			'-p', '--port', action='store', default=self.port,
			type=int, dest='port',
			help='defines an alternative port number [default %(default)s]'
		)
		add(
			'-l', '--language', default=self.default_locale,
			type=str, action='store', dest='language',
			help='defines the language to use [default: %(default)s]'
		)
		add(
			'-d', '--debug', default=self.default_debug,
			action='store', type=int, dest='debug',
			help='if given then debugging is activated and set to the specified level [default: %(default)s]'
		)
		add(
			'-L', '--log-file', default='management-console-server',
			action='store', dest='logfile',
			help='specifies an alternative log file [default: %(default)s]'
		)
		self.options = parser.parse_args()

	def daemonize(self):
		if self.options.daemon_mode:
			super(ServerDaemon, self).daemonize()

	def listen(self):
		server = Server()
		self.listen_ssl(server)
		reactor.listenTCP(self.options.port, server, interface=self.interface)
		reactor.run()

	def listen_ssl(self, server):
		# TODO: do we need also verified ssl connections (e.g. Single Sign On)?
		ssldir = '/etc/univention/ssl/%s.%s/' % (ucr['hostname'], ucr['domainname'])
		sslserver = ssl.DefaultOpenSSLContextFactory(join(ssldir, 'private.key'), join(ssldir, 'cert.pem'))
		reactor.listenSSL(self.ssl_port, server, sslserver, interface=self.interface)
