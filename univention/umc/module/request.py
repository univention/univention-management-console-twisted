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
import simplejson
import traceback

from twisted.web.server import Request

from univention.management.console.modules import (
	UMC_CommandError, UMC_OptionMissing,
	UMC_OptionTypeError, UMC_OptionSanitizeError
)
from univention.management.console.protocol.message import Request as UmcpRequest

from univention.umc import Translation
from univention.umc.util import MODULE_ERR_COMMAND_FAILED, MODULE, change_locale
from univention.umc.authentication.acl import ACLs  # TODO: don't use internals


class ModuleRequest(Request):

	def __init__(self, *a, **kw):
		Request.__init__(self, *a, **kw)
		self.__initialized = False

	def get_umcp_request(self, umcptype, command):
		options = simplejson.load(self.content)
		flavor = self.getHeader('X-UMC-Flavor')
		mimetype = self.getHeader('Content-Type')
		method = self.getHeader('X-UMC-Method')
		umcprequest = UmcpRequest(umcptype, [command], options, mimetype)
		umcprequest.flavor = flavor

		self.site.handler._Base__requests[umcprequest.id] = (umcprequest, method)
		self.site.requests[umcprequest.id] = self

		return umcprequest

	def render(self, resource):
		message = None
		result = ''
		method = self.getHeader('X-UMC-Method')
		_ = self.getSession(Translation)._  # TODO: this runs in the module process so it can be a global
		try:
			self.initialize()
			return Request.render(self, resource)
		except UMC_OptionSanitizeError as exc:
			self.setResponseCode(409)  # Conflict  # HTTP FIXME
			message = exc.message
			result = exc.body
		except (UMC_OptionTypeError, UMC_OptionMissing, UMC_CommandError) as exc:
			self.setResponseCode(400)
			message = {
				UMC_OptionTypeError: _('An option passed to %s has the wrong type: %s') % (method, exc),
				UMC_OptionMissing: _('One or more options to %s are missing: %s') % (method, exc),
				UMC_CommandError: _('The command has failed: %s') % (exc, )
			}.get(exc.__class__)  # TODO: subclasses?
		except BaseException as exc:
			self.setResponseCode(MODULE_ERR_COMMAND_FAILED)  # HTTP FIXME
			message = _("Execution of command '%(command)s' has failed:\n\n%(text)s") % {
				'command': self.path,
				'text': unicode(traceback.format_exc())
			}

		if isinstance(message, unicode):
			message = message.encode('UTF-8')
		message = json.dumps(message)
		result = json.dumps(result)

		MODULE.process(message)
		self.setHeader('X-UMC-Message', message)
		self.setHeader('Content-Length', b'%d' % len(result))
		self.write(result)
		self.finish()

	def initialize(self):
		self.set_language()

		if self.__initialized:
			return

		handler = self.site.handler
		handler.username = self.getUser()
		handler.password = self.getPassword()
		handler.user_dn = self.getHeader('X-User-Dn')
		handler.acls = ACLs(acls=json.loads(self.getHeader('X-UMC-Acls')))  # TODO: load ACL's from filename

		self.__initialized = True
		handler.init()

	def set_language(self):
		locale = self.getHeader('Accept-Language')
		if not change_locale(locale):
			locale = 'C'
		self.site.handler.set_language(locale)
