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

import os.path
from os import getpid, kill
from os.path import join
from time import time
from subprocess import Popen

from twisted.web.client import FileBodyProducer
from twisted.web.client import ProxyAgent
from twisted.web.http_headers import Headers
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.endpoints import UNIXClientEndpoint
from twisted.internet.task import LoopingCall

from univention.umc.util.log import MODULE
from univention.umc.util.config import ucr
from univention.umc import CouldNotConnect, ModuleProcess, Translation, implements

MODULE_COMMAND = '/usr/sbin/umc-module'
MODULE_SOCKET_PATH = '/var/run/univention-management-console/'


class UMCModuleProcess(object):
	implements(ModuleProcess)

	@property
	def running(self):
		return self.process and self.process.poll() is None  # FIXME: not None?

	@property
	def pid(self):
		return self.process and self.process.pid

	@property
	def module_debug_level(self):
		return int(ucr.get('umc/module/debug/level', 2))

	@property
	def module_locale(self):
		return Translation(self.session).get_language()

	def __init__(self, session, module=None):
		self.session = session
		self.module = module
		self.process = None
		self.socket = None
		self.proxy = None
		self._connected = None
		self._connection_attempts = 0
		self._max_connection_attempts = 200
		self.session.notifyOnExpire(self.on_session_expired)

	def request(self, method, uri, headers=None, body=None):
		response = Deferred()

		if body:
			body = FileBodyProducer(body)
		if headers:
			headers = Headers(dict(self.__headers(headers)))

		def success(result):
			if not self.proxy:
				MODULE.error('Waiting for socket creation timed out... %r' % (result,))
				raise CouldNotConnect('The ModuleProcess connection failed due to a internal timeout')
			return response.callback(result)

		def failed(failure):
			MODULE.error('Creating ModuleProcess failed...')
			return response.errback(failure.value)

		def request(_):
			MODULE.info('Passing request %r to module process' % (uri,))
			return self.proxy.request(method, uri, headers, body)

		connection = self.create()
		connection.addCallback(success)
		connection.addErrback(failed)
		response.addCallback(request)
		return response

	def __headers(self, headers):
		for k, v in headers.iteritems():
			if isinstance(v, unicode):
				v = v.encode('UTF-8')  # HTTP FIXME: must be ascii (or at least ISO8859-1)
			yield k, [v]

	def create(self):
		if self._connected is not None:
			return self._connected

		MODULE.info('Starting new module process: %s' % (self.module,))
		self.socket = self.get_socket_path()

		args = [
			MODULE_COMMAND, '-l', self.module_locale,
			'-d', str(self.module_debug_level), self.socket, self.module
		]

		MODULE.info('Module process: %s' % (' '.join(args)))
		self.process = Popen(args, executable=MODULE_COMMAND, shell=False)  # TODO: stdout, stderr

		connect = LoopingCall(self.connect)
		connect.a = (connect,)  # twisteds arguments
		self._connected = connect.start(0.05)
		return self._connected

	def connect(self, loop):
		if self.socket_exists():
			self.proxy = ProxyAgent(UNIXClientEndpoint(reactor, self.socket))
			loop.stop()
		else:
			self._connection_attempts += 1
			if not self.running or self._connection_attempts > self._max_connection_attempts:
				raise CouldNotConnect('Socket %s does not exists' % (self.socket,))

	def get_socket_path(self):
		return join(MODULE_SOCKET_PATH, '%u-%lu.socket' % (getpid(), long(time() * 1000)))

	def socket_exists(self):
		return os.path.exists(self.socket)

	def kill(self, signal=15):
		kill(self.pid, signal)

	def on_session_expired(self):
		if self.running:
			self.kill()
