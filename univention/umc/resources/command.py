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
from io import BytesIO

from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET
from twisted.internet.protocol import Protocol

from univention.umc import User, ACLs, Translation
from univention.umc.util import (
	CORE, MODULE, BAD_REQUEST_FORBIDDEN, BAD_REQUEST_NOT_FOUND,
	require_authentication, UMCModuleProcess as ModuleProcess
)


class Command(Resource):

	processpool = dict()

	not_forwarded_headers = set(map(str.lower, (
		'Content-Length', 'Transfer-Encoding', 'Trailer',
		'Range', 'Date', 'Content-Encoding', 'Connection',
		'Server', 'Set-Cookie'
	)))

	def getChild(self, path, request):
		if path:
			return self
		return Resource.getChild(self, path, request)

	def get_process(self, session, module):
		self.processpool.setdefault(session, {})
		if module not in self.processpool[session]:
			self.processpool[session][module] = ModuleProcess(session, module)
		return self.processpool[session][module]

	@require_authentication
	def render(self, request):
		session = request.getSession()
		acls = ACLs(session)
		moduleManager = request.site.moduleManager

		command = '/'.join(request.prepath[1:])

		module_name = acls.get_module_providing(moduleManager, command)
		if not module_name:
			MODULE.warn('No module provides %s' % (command))
			request.setResponseCode(BAD_REQUEST_FORBIDDEN)
			return

		MODULE.info('Checking ACLs for %s (%s)' % (command, module_name))
		if not acls.is_command_allowed(request, command):
			MODULE.warn('Command %s is not allowed' % (command))
			request.setResponseCode(BAD_REQUEST_FORBIDDEN)
			return

		methodname = acls.get_method_name(moduleManager, module_name, command)
		if not methodname:
			MODULE.warn('Command %s does not exists' % (command))
			request.setResponseCode(BAD_REQUEST_NOT_FOUND)
			return

		headers = self.get_request_header(request, methodname)
		body = self.get_request_body(request)

		CORE.info('Passing new request to module %s' % (module_name,))
		process = self.get_process(session, module_name)

		urequest = process.request(request.method, request.uri, headers, body)
		urequest.addCallback(self.respond, request)
		urequest.addErrback(self.failed_request, request)

		return NOT_DONE_YET

	def get_request_header(self, request, methodname):
		session = request.getSession()
		user = User(session)
		translation = Translation(session)
		acls = ACLs(session)
		return {
			'Content-Type': 'application/json',
			'Accept-Language': translation.get_language(),
			'Accept': request.getHeader('Accept', ''),
			'User-Agent': request.getHeader('User-Agent', ''),
			'Authorization': 'basic %s' % ('%s:%s' % (user.username, user.password)).encode('base64').strip(),
			'X-Forwarded-For': request.getClientIP(),
			'X-UMC-Flavor': request.getHeader('X-UMC-Flavor', ''),
			'X-User-Dn': user.userdn or '',
			'X-UMC-Method': methodname,
			'X-UMC-Acls': acls.json(),  # TODO: remove, only send filename
		}

	def get_request_body(self, request):
		return BytesIO(json.dumps(request.options))

	def respond(self, response, request):
		request.setResponseCode(response.code)
		for header, value in response.headers.getAllRawHeaders():
			if header.lower() in self.not_forwarded_headers:
				continue
			request.responseHeaders.setRawHeaders(header, value)

		response.deliverBody(Into(request))

	def failed_request(self, failure, request):
		request.setResponseCode(500)
		request.setHeader('X-UMC-Message', json.dumps(failure.getTraceback()))
		request.respond(dict(result=failure.getErrorMessage()))
		CORE.error('failed_request: %s: %s' % (failure.getErrorMessage(), failure.getTraceback()))


class Into(Protocol):
	# yes, TwistedLikesItComplicated
	def __init__(self, request):
		self.request = request
		self.is_json = 'application/json' in request.responseHeaders.getRawHeaders('Content-Type', [])
		self.__buffer = bytearray()

	def dataReceived(self, bytes_):
		self.__buffer.extend(bytes_)

	def connectionLost(self, reason):
		back = bytes(self.__buffer)
		if self.is_json:
			self.request.respond(dict(result=json.loads(back)))
		else:
			self.request.write(back)
			self.request.finish()


#def _check_module_exists(modulename):
#    from imp import find_module
#    try:
#        umc = find_module('console', [find_module('management', [find_module('univention')[1]])[1])[1]
#        find_module(modulename, [umc])
#    except ImportError:
#        return False
#    else:
#        return True
