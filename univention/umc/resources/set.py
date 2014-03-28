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
from types import StringTypes

from twisted.web.resource import Resource

import univention.admin.uexceptions as udm_errors

from univention.umc import User, Translation
from univention.umc.util import (
	CORE, BAD_REQUEST_INVALID_OPTS,
	BAD_REQUEST_UNAVAILABLE_LOCALE,
	require_authentication
)


class Set(Resource):

	isLeaf = True

	def __init__(self):
		Resource.__init__(self)
		self.putChild('locale', Locale())
		self.putChild('user', UserPreferences())

	def render(self, request):
		for path in request.options:
			return self.getChildWithDefault(path, request).render(request)


class Locale(Resource):

	@require_authentication
	def render(self, request):
		translation = Translation(request.getSession())
		locale = request.options['locale']
		if not translation.set_language(locale):
			request.setResponseCode(BAD_REQUEST_UNAVAILABLE_LOCALE)  # HTTP FIXME


class UserPreferences(Resource):

	@require_authentication
	def render(self, request):
		user = request.getSession(User).user
		if not user:
			request.setResponseCode(BAD_REQUEST_INVALID_OPTS)  # HTTP FIXME
			return

		preferences = dict(self._get_preferences(request))
		new_preferences = dict(user.info.get('umcProperty', []))
		new_preferences.update(preferences)
		user.info['umcProperty'] = new_preferences.items()

		try:
			user.modify()
		except (udm_errors.base) as err:
			CORE.warn('Could not set given option: %s' % err)
			request.setResponseCode(BAD_REQUEST_INVALID_OPTS)  # HTTP FIXME

	def _get_preferences(self, request):
		preferences = dict(request.options['user']['preferences'])
		for key, value in preferences.iteritems():
			if not isinstance(value, StringTypes):
				value = json.dumps(value).decode('ascii')
			yield unicode(key).encode('UTF-8'), value.encode('UTF-8')
