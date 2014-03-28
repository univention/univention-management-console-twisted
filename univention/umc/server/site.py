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

from signal import signal, SIGUSR1, SIGUSR2, SIGHUP

from twisted.web.server import Site

from univention.umc.util import (
	CORE, RESOURCES, set_log_level, ucr,
	get_current_log_level, category, module
)
from univention.umc.server.request import UMCRequest
from univention.umc.server.root import ServerRoot


class ServerSite(Site):

	@property
	def debug_level(self):
		return int(ucr.get('umc/server/debug/level', 2))

	def __init__(self, root, logPath=None, timeout=43200):
		Site.__init__(self, root, logPath, timeout)
		self.categoryManager = category.Manager()
		self.moduleManager = module.Manager()
		self.reload()
		self.add_signal_handler()

	def add_signal_handler(self):
		signal(SIGUSR1, lambda signo, stack: self.increase_log_level(1))
		signal(SIGUSR2, lambda signo, stack: self.increase_log_level(-1))
		signal(SIGHUP, lambda signo, stack: self.reload(True))

	def increase_log_level(self, delta=1):
		level = get_current_log_level()
		level += delta
		self.set_log_level(level)

	def set_log_level(self, level):
		CORE.process('Set log level to %d' % level)
		set_log_level(level)

	def reset_log_level(self):
		self.set_log_level(self.debug_level)

	def reload(self, reset_log_level=False):
		"""Reloads resources like module and category definitions"""
		RESOURCES.info('Reloading resources: modules, categories')
		self.moduleManager.load()
		self.categoryManager.load()
		RESOURCES.info('Reloading UCR variables')
		ucr.load()
		if reset_log_level:
			RESOURCES.info('Reset log level.')
			self.reset_log_level()
		# TODO: may reload_ldap_connections()  (not necessary due to ReloadingLDAPConnection)
		# TODO: maybe it would be nice to have something like notify_on_reload


class Server(ServerSite):

	@property
	def timeout(self):
		return max(15, int(ucr.get('umc/http/session/timeout', 600)))

	def __init__(self):
		ServerSite.__init__(self, ServerRoot(), timeout=self.timeout)
		self.register_factories()

	def register_factories(self):
		self.requestFactory = UMCRequest
