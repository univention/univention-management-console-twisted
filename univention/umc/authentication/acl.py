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

from univention.management.console.acl import ACLs, LDAP_ACLs

from univention.umc import implements, ACLs as IACLs, User
from univention.umc.util import ucr, get_machine_connection

__all__ = ['ACLs', 'LdapACLs']


class LdapACLs(object):  # FIXME: parameter aren't nice for an interface
	implements(IACLs)

	def __init__(self, session):
		self.session = session
		self.acls = None
		self.__allowed_commands = {}
		self._read_acls()

	def _read_acls(self):
		user = User(self.session)
		lo, po = get_machine_connection()
		self.acls = LDAP_ACLs(lo, user.username, ucr['ldap/base'])
		self.__permitted_commands = None

	def is_command_allowed(self, request, command):
		kwargs = {}
		content_type = request.getHeader('Content-Type') or ''
		if content_type.startswith('application/json'):
			kwargs.update(dict(
				options=request.options,
				flavor=request.getHeader('X-UMC-Flavor')
			))

		return self.acls.is_command_allowed(command, **kwargs)

	def get_permitted_commands(self, moduleManager):
		if self.__permitted_commands is None:
			# fixes performance leak?
			self.__permitted_commands = moduleManager.permitted_commands(ucr['hostname'], self.acls)
		return self.__permitted_commands

	def get_module_providing(self, moduleManager, command):
		permitted_commands = self.get_permitted_commands(moduleManager)
		return moduleManager.module_providing(permitted_commands, command)

	def get_method_name(self, moduleManager, module_name, command):
		module = self.get_permitted_commands(moduleManager)[module_name]
		methods = (cmd.method for cmd in module.commands if cmd.name == command)
		for method in methods:
			return method

	def json(self):
		return json.dumps(self.acls.json())
