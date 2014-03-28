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

from urllib import urlencode

from twisted.web.resource import Resource

from univention.umc.util import CORE


class SingleSignOn(Resource):

	isLeaf = True

	def render(self, request):
		request.single_sign_on(request.args.get('loginToken'))

		targeturl = '/univention-management-console/'
		query = dict((arg, value) for arg, value in request.args.iteritems() if arg not in ('loginToken', 'username', 'password'))
		if query:
			# HTTP FIXME: Location header does not allow a querystring in its URI
			# command/lib/sso should be fixed to add e.g. language settings
			targeturl += '?%s' % urlencode(query)

		CORE.info('Redirecting to %s' % (targeturl))
		request.responseHeaders.addRawHeader('Location', targeturl)
		request.setResponseCode(303)
