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

import re

from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

from univention.umc.util import MODULE


class ModuleRoot(Resource):
	RE_COMMAND = re.compile('^/(command|upload)(/.*)$')

	isLeaf = True

	def render(self, request):
		request.setHeader('Content-Type', 'application/json')

		handler = request.site.handler
		method = request.getHeader('X-UMC-Method')
		umcptype, command = self.get_command(request.path)
		umcprequest = request.get_umcp_request(umcptype, command)

		MODULE.info('Executing %s' % command)
		try:
			func = getattr(handler, method)
		except AttributeError:
			MODULE.info('Method %s of command %s does not exists' % (method, command))
			request.setResponseCode(500)
			return ''

		func(umcprequest)
		return NOT_DONE_YET

	def get_command(self, path):
		try:
			match = self.RE_COMMAND.match(path)
			umcpcmd, command = match.groups()
			return umcpcmd.upper(), command
		except (ValueError, AttributeError):  # pragma: no-cover
			return ('COMMAND', '/')
