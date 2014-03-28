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

from base64 import b64encode
from univention.umc.util import require_authentication


# TODO: break API: remove files after request is done
class Upload(Resource):

	def __init__(self, command):
		Resource.__init__(self)
		self.command_dispatcher = command

	def getChild(self, path, request):
		if not path:
			return self
		return self.command_dispatcher

	@require_authentication
	def render(self, request):
		return dict(result=[self._get_result(body) for body in request.options])

	def _get_result(self, body):
		with open(body['tmpfile']) as fd:
			content = b64encode(fd.read())
			return dict(
				filename=body['filename'],
				name=body['name'],
				content=content
			)
