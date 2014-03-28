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

from twisted.web.resource import Resource

from univention.umc.resources.get import Get
from univention.umc.resources.set import Set
from univention.umc.resources.upload import Upload
from univention.umc.resources.command import Command
from univention.umc.resources.auth import Auth
from univention.umc.resources.sso import SingleSignOn
from univention.umc.resources.logout import Logout


class ServerRoot(Resource):

	def __init__(self):
		Resource.__init__(self)
		self.addChilds()

	def addChilds(self):
		command = Command()
		self.putChild('command', command)
		self.putChild('upload', Upload(command))
		self.putChild('auth', Auth())
		self.putChild('get', Get())
		self.putChild('set', Set())
		self.putChild('sso', SingleSignOn())
		self.putChild('logout', Logout())
		self.putChild('', self)
