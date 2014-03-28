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

from univention.umc import User, implements, NotAuthenticated
from univention.umc.util import get_userdn_by_username, get_user_object

from univention.umc.authentication.pam import PamAuth


class PAMAuthenticatedUser(object):
	implements(User)

	@property
	def user(self):
		# TODO: cache
		return get_user_object(self.userdn, self.password)

	def __init__(self, session):
		self.auth = PamAuth()
		self.__authenticated = False
		self.username = None
		self.password = None
		self.userdn = None
		self.ip = None

	def is_authenticated(self):
		if not self.__authenticated:
			raise NotAuthenticated()
		return True

	def authenticate(self, username, password):
		try:
			self.auth.authenticate(username, password)
		except:
			raise
		else:
			self.authenticated(username, password)

	def change_expired_password(self, username, old_password, new_password):
		self.auth.change_expired_password(username, old_password, new_password)
		self.authenticated(username, new_password)

	def authenticated(self, username, password):
		self.__authenticated = True
		self.username = username
		self.password = password
		self._init_user()

	def _init_user(self):
		self.userdn = get_userdn_by_username(self.username)
