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

import json
from subprocess import call
from traceback import format_exc

from univention.umc.util import MODULE, ucr
from univention.umc.server.site import ServerSite
from univention.umc.module.root import ModuleRoot
from univention.umc.module.request import ModuleRequest


class ModuleServer(ServerSite):

	@property
	def timeout(self):
		return max(15, int(ucr.get('umc/module/timeout', 300) or 300))

	def __init__(self, module):
		ServerSite.__init__(self, ModuleRoot(), timeout=self.timeout)
		self.requestFactory = ModuleRequest
		# TODO: add timer which kills process when not receiving request anymore

		self.__initialized = False
		self.handler = None
		self.__module = module
		self.__load_module()

		self.requests = dict()
		self.handler.signal_connect('success', self.__umcp_respond)
		self.handler.signal_connect('failure', self.__umcp_respond)

	def initialize(self, request):
		request.set_language()

		if self.__initialized:
			return

		request.initialize()

		self.__initialized = True
		self.handler.init()

	def reload_server(self):
		try:
			call(['/usr/sbin/umc-server', 'reload'])
		except OSError:
			pass

	def __umcp_respond(self, response):
		MODULE.process('Responding to %r; status=%r' % (response.id, response.status))
		request = self.requests.pop(response.id)
		request.setResponseCode(response.status)
		request.setHeader('X-UMC-Message', json.dumps(response.message or ''))

		if response.mimetype != 'application/json':
			request.write(response.body)
		else:
			request.write(json.dumps(response.result))
		request.finish()

	def __load_module(self):
		modname = self.__module
		self.__module = None
		MODULE.info('Importing module %r' % (modname,))
		try:
			self.__import(modname)
		except ImportError as exc:
			MODULE.error('Failed to import module %s: %s\n%s' % (modname, exc, format_exc()))
			self.reload_server()  # TODO: should we check module existance in umc-server
			raise

		self.handler = self.__module.Instance()

	def __import(self, modname):
		file_ = 'univention.management.console.modules.%s' % (modname,)
		self.__module = __import__(file_, [], [], modname)

	def __destroy_handler(self):
		# TODO: register signal handler which calls handler destroyment
		if self.handler:
			self.handler.destroy()
			del self.handler
			self.handler = None

	def __del__(self):
		self.__destroy_handler()
