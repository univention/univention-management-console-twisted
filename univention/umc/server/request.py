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
from hashlib import sha256
from os import stat, statvfs
from datetime import datetime
from tempfile import NamedTemporaryFile
from types import FunctionType, CodeType
from cgi import FieldStorage

from twisted.web.http import _parseHeader
from twisted.web.server import Request, NOT_DONE_YET
from twisted.web.error import UnsupportedMethod
from twisted.internet import reactor, threads

from univention.umc import (
	User, AuthenticationFailed, NotAuthenticated,
	PasswordExpired, PasswordChangeFailed
)
from univention.umc.util import (
	ucr, CORE, get_ucs_version, get_umc_version,
	BAD_REQUEST_UNAUTH, BAD_REQUEST_PASSWORD_EXPIRED,
	AUTH, BAD_REQUEST_AUTH_FAILED
)

TEMPUPLOADDIR = '/var/tmp/univention-management-console-frontend'

_ERRSTATUSES = {
	PasswordExpired: BAD_REQUEST_PASSWORD_EXPIRED,  # HTTP FIXME
	AuthenticationFailed: BAD_REQUEST_AUTH_FAILED,  # HTTP FIXME
}


def get_expiration():
	# TODO: remove this old knowledge about cookie expiration from umc-web-server
	# TODO: move this into the general cookie as well?!
	# set the cookie once during successful authentication
	# force expiration of cookie in 5 years from now on...
	# IE does not support max-age
	expiration = datetime.now()
	expiration = expiration.replace(year=expiration.year + 5)
	return expiration.strftime("%a, %d-%b-%Y %H:%M:%S GMT")


class UMCRequest(Request):

	@property
	def sso_timeout(self):
		return int(ucr.get('umc/web/sso/timeout', 15))

	@property
	def options(self):
		return self.body.get('options', {})

	@property
	def max_upload_size(self):
		return int(ucr.get('umc/server/upload/max', 64)) * 1024

	@property
	def min_free_space(self):
		return int(ucr.get('umc/server/upload/min_free_space', 51200))  # kilobyte

	@property
	def is_iframe_upload(self):
		return self.args.get('iframe') not in ('false', False, 0, '0', None) and self.path.startswith('/upload')

	@property
	def content_length(self):
		try:
			return int(self.getHeader('content-length', '0'))
		except ValueError:  # pragma: no cover
			return 0

	def __init__(self, *args, **kwargs):
		Request.__init__(self, *args, **kwargs)
		self._authenticated_callbacks = []
		self.__fix_twisted()
		self.notify_on_authenticated(self.__store_ip_in_session)
		self.notify_on_authenticated(self.__add_sso_session)

	def single_sign_on(self, token):
		"""Authenticate the client by given single sign on token"""
		session = self.single_sign_on.sessions.pop(token, None)
		if not session:
			CORE.warn('Unknown SSO token: %r' % (token,))
			return False

		self.__store_ip_in_session()
		expiration = get_expiration()
		user = self.getSession(User)
		self.addCookie('UMCSessionId', session.uid, path='/', expires=expiration)
		self.addCookie('UMCUsername', user.username, path='/', expires=expiration)
		return True
	single_sign_on.sessions = dict()

	def getClientIP(self):
		"""Get the clients IP address. Evaluates allowed proxys (from localhost)"""
		ip = Request.getClientIP(self)
		if ip in ('::1', '127.0.0.1'):
			return self.requestHeaders.getRawHeaders('X-Forwarded-For', [ip])[-1]
		return ip

	def getHeader(self, name, default=None):
		"""Get a request header. If it is not defined use the default as fallback"""
		return Request.getHeader(self, name) or default

	def require_authentication(self):
		"""Raises NotAuthenticated if the client did not provide credentials"""
		self.getSession(User).is_authenticated()

	def authenticate(self, username, password, new_password=None):
		"""Authenticate the client. Change password if expired. Should be run in a thread."""
		user = self.getSession(User)

		AUTH.info('Trying to authenticate user %r' % (username,))
		try:
			user.authenticate(username, password)
		except AuthenticationFailed as auth_failed:
			AUTH.error(str(auth_failed))
			raise
		except PasswordExpired as pass_expired:
			AUTH.info(str(pass_expired))
			if new_password is None:
				raise

			try:
				user.change_expired_password(username, password, new_password)
			except PasswordChangeFailed as change_failed:
				AUTH.error(str(change_failed))
				raise
			else:
				AUTH.info('Password change for %r was successful' % (username,))
		else:
			AUTH.info('Authentication for %r was successful' % (username,))

	def getUser(self):
		user = Request.getUser(self)
		if not user and self.path.startswith('/auth'):
			user = self.options.get('username', u'').encode('UTF-8')
			self.user = user  # blame twisted
		return user

	def getPassword(self):
		password = Request.getPassword(self)
		if not password and self.path.startswith('/auth'):
			password = self.options.get('password', u'').encode('UTF-8')
			self.password = password  # blame twisted
		return password

	def getNewPassword(self):
		if self.path.startswith('/auth') and 'new_password' in self.options:
			return self.options['new_password'].encode('UTF-8')

	def requestReceived(self, command, path, version):
		"""Processes the self"""
		CORE.info('Receiving request...')
		try:
			# prevent twisted's processing by lowercasing method
			Request.requestReceived(self, command.lower(), path, version)
		finally:
			self.method = command

		# fix twisted's query string processing
		self.__fix_twisted_query_string()
		self.site = self.channel.site

		self._set_default_response_headers()

		try:
			CORE.info('Parse request body...')
			self._parse_request_payload()
		except ValueError as err:
			self.respond(bytes(err))
			return

		self._set_default_request_headers()

		CORE.info('Authenticate? ...')
		self._authenticate_and_process()

	def process(self):
		pass  # !! don't do anything! called by Request.requestReceived

	def _set_default_response_headers(self):
		self.setHeader('Content-Type', 'application/json')
		self.setHeader('X-UMC-Message', '""')

	def _set_default_request_headers(self):
		# flavor
		if not self.requestHeaders.hasHeader('X-UMC-Flavor'):
			flavor = self.body.get('flavor', u'').encode('ascii')
			self.requestHeaders.addRawHeader('X-UMC-Flavor', flavor)

	def _authenticate_and_process(self):
		def _continue_request():
			CORE.info('Dispatch request ...')
			Request.process(self)

		def failed(failure):
			self.setResponseCode(_ERRSTATUSES.get(type(failure.value), 500))
			self.setHeader('X-UMC-Message', json.dumps(bytes(failure.value)))
			self.respond(None)

		user = self.getSession(User)
		try:
			user.is_authenticated()
		except NotAuthenticated:
			username = self.getUser()
			password = self.getPassword()
			new_password = self.getNewPassword()

			if username and password:
				auth = threads.deferToThread(self.authenticate, username, password, new_password)
				auth.addCallback(lambda result: self.on_authenticated())
				auth.addCallback(lambda result: _continue_request())
				auth.addErrback(failed)
				return

		_continue_request()

	def render(self, resource):
		"""Renders identified resource and write response"""

		CORE.info('Rendering resource...')
		try:
			body = resource.render(self)
		except NotAuthenticated:
			body = None
			self.setResponseCode(BAD_REQUEST_UNAUTH)  # HTTP FIXME
		except UnsupportedMethod:
			Request.render(self, resource)  # use twisteds error handling
			return

		if body is NOT_DONE_YET:
			return

		self.respond(body)

	def respond(self, body):
		"""Write the response body to the client. Convert it into UMCP format."""

		CORE.info('Writing response...')
		message = self.responseHeaders.getRawHeaders('X-UMC-Message')
		message = json.loads(message and message[0] or '""')

		if not isinstance(body, dict):
			body = dict(result=body)

		data = dict(
			message=message,
			status=self.code,
		)
		data.update(body)

		body = json.dumps(data)
		self.setHeader('Content-Type', 'application/json')
		self.setHeader('Content-Length', '%d' % (len(body),))

		if self.is_iframe_upload:
			# this is a workaround to make iframe uploads work, they need the textarea field
			# TODO: break API: remove
			self.setHeader('Content-Type', 'text/html; charset=UTF-8')
			body = b'<html><body><textarea>%s</textarea></body></html>' % (body,)

		self.write(body)
		self.finish()

	def _parse_request_payload(self):
		content_type = self.getHeader('content-type', '')

		codecs = {
			'application/json': self.__parse_json,
			'multipart/form-data': self.__parse_file_upload,
			'application/x-www-form-urlencoded': self.__parse_urlencoded,
		}
		codec, params = _parseHeader(content_type)
		self.body = {}
		try:
			codec = codecs[codec]
		except KeyError:
			if self.content_length:
				self.setResponseCode(415)
				raise ValueError('Unknown or unsupported Content-Type.')
		else:
			self.body = codec(params)

	def __parse_json(self, params):
		if not self.content_length:
			self.setResponseCode(411)
			raise ValueError('Please provide Content-Length header.')

		try:
			content = json.load(self.content)
		except ValueError:
			self.setResponseCode(400)
			raise

		if not isinstance(content, dict):
			self.setResponseCode(400)
			raise ValueError('The message payload must be a dict/json-object.')

		return content

	def __parse_file_upload(self, params):
		# TODO: implement patch from Bug #31923
		if not self.path.startswith('/upload'):  # HTTP FIXME
			self.setResponseCode(415)
			raise ValueError('File uploads are currently only supported on /upload.')

		ucr.load()

		fields = FieldStorage(
			self.content,
			headers={'content-type': self.getHeader('Content-Type')},
			environ={'REQUEST_METHOD': 'POST'}
		).list

		body = dict((field.name, field.value) for field in fields if not field.filename)
		body['options'] = []

		for field in (field for field in fields if field.filename):
			name, filename, value = field.name, field.filename, field.value
			tmpfile = NamedTemporaryFile(dir=TEMPUPLOADDIR, delete=False)
			tmpfile.write(value)

			self.__check_max_file_size(tmpfile.name)
			self.__check_min_free_space_on_partition(tmpfile.name)

			# some security
			for c in ('<>/'):
				filename = filename.replace(c, '_')

			body['options'].append(dict(
				filename=filename,
				name=name,
				tmpfile=tmpfile.name
			))

		return body

	def __check_max_file_size(self, filename):
		st_size = stat(filename).st_size
		if st_size > self.max_upload_size:
			CORE.warn('File of size %d could not be uploaded' % (st_size))
			self.setResponseCode(400)  # HTTP FIXME: 413 entity too large
			raise ValueError('The size of the uploaded file is too large.')

	def __check_min_free_space_on_partition(self, filename):
		# check if enough free space is available
		sfs = statvfs(filename)
		free_disk_space = sfs.f_bavail * sfs.f_frsize / 1024  # kilobyte
		if free_disk_space < self.min_free_space:
			CORE.error('There is not enough free space to upload files.')
			self.setResponseCode(400)
			raise ValueError('There is not enough free space on disk.')

	# TODO: test GET
	def __parse_urlencoded(self, params):
		args = {'options': {}}
		if self.args.get('flavor'):
			args['flavor'] = self.args['flavor'][0]
		for name, value in self.args.iteritems():
			if value:
				args['options'][name] = value[0]
		return args

	def __store_ip_in_session(self):
		self.getSession(User).ip = self.getClientIP()

	def __add_sso_session(self):
		session = self.getSession()
		login_token = sha256(session.uid).hexdigest()
		self.single_sign_on.sessions[login_token] = session
		reactor.callLater(self.sso_timeout, self.__expire_sso_session, login_token)

	def __expire_sso_session(self, login_token):
		self.single_sign_on.sessions.pop(login_token, None)

	def notify_on_authenticated(self, callback):
		self._authenticated_callbacks.append(callback)

	def on_authenticated(self):
		for a in self._authenticated_callbacks:
			a()
		self._authenticated_callbacks = []

	def __fix_twisted(self):
		self.sitepath = []
		_replace_session_name()
		self.__replace_server_name()

	def __replace_server_name(self):
		"""replaces the default twisted Server header by UMC and UCS version"""
		Request.process.im_func.func_globals['version'] = 'UMC/%s UCS/%s' % (get_umc_version(), get_ucs_version())

	def __fix_twisted_query_string(self):
		for name, value in self.args.iteritems():
			if value:
				self.args[name] = value[0]


def _replace_session_name():
	# Replaces TWISTED_SESSION by UMCSessionId
	func = Request.getSession.im_func
	co = func.func_code
	consts = tuple(['UMCSessionId' if const == 'TWISTED_SESSION' else const for const in co.co_consts])
	code = CodeType(
		co.co_argcount, co.co_nlocals, co.co_stacksize,
		co.co_flags, co.co_code, consts, co.co_names,
		co.co_varnames, co.co_filename, co.co_name,
		co.co_firstlineno, co.co_lnotab,
		co.co_freevars, co.co_cellvars
	)
	Request.getSession = FunctionType(code, func.func_globals, func.func_name, func.func_defaults, func.func_closure)
	global _replace_session_name
	_replace_session_name = lambda: None
