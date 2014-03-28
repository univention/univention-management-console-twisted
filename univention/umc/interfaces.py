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

from zope.interface import Interface, Attribute, implements
# TODO: have a look if implements can be added afterwards

__all__ = ['implements', 'Translation', 'User', 'ACLs', 'ModuleProcess']


class NotAuthenticated(Exception):
	pass


class AuthenticationFailed(Exception):
	pass


class PasswordExpired(Exception):
	pass


class PasswordChangeFailed(Exception):
	pass


class CouldNotConnect(Exception):
	pass


class Translation(Interface):

	def set_language(locale):
		pass

	def get_language():
		pass

	def _(*args, **kwargs):
		pass


class User(Interface):

	userdn = Attribute("The DN of the user if the user exists in LDAP")
	user = Attribute("A udm.users.user instance if the user exists in LDAP")
	username = Attribute("The authenticated username or None")
	password = Attribute("The plaintext password which was used for authentication")
	ip = Attribute("The IP address of the client")

	def authenticate(username, password):
		pass

	def is_authenticated():
		pass

	def change_expired_password(username, old_password, new_password):
		pass


class ACLs(Interface):

	def is_command_allowed(command, hostname=None, options={}, flavor=None):
		return False

	def get_module_providing(moduleManager, command):
		pass

	def get_permitted_commands(moduleManager):
		pass

	def get_method_name(moduleManager, module_name, command):
		pass

	def json():
		return


class ModuleProcess(Interface):

	module = Attribute("The module name")
	socket = Attribute("The UNIX socket filename of the process")
	pid = Attribute("The process id")
	user = Attribute("The owner of the process")

	def connect():
		pass

	def request(request):
		pass

	def kill(signal):
		pass
