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

from ldap import LDAPError

from twisted.web.resource import Resource

from univention.umc import Translation, User, ACLs
from univention.umc.util import (
	require_authentication, CORE, ucr, BAD_REQUEST_INVALID_OPTS,
	get_machine_connection, get_ucs_version, get_umc_version
)


class Get(Resource):

	def __init__(self):
		Resource.__init__(self)
		self.putChild('modules', Modules())
		self.putChild('categories', Categories())
		self.putChild('user', UserPreferences())
		self.putChild('hosts', Hosts())
		self.putChild('ucr', UCR())
		self.putChild('info', Info())


class Modules(Resource):
	#'/get/modules/list'

	isLeaf = True

	@require_authentication
	def render(self, request):
		_ = Translation(request.getSession())._
		acls = ACLs(request.getSession())

		moduleManager = request.site.moduleManager
		categoryManager = request.site.categoryManager
		moduleManager.load()
		categoryManager.load()
		permitted_commands = acls.get_permitted_commands(moduleManager).values()

		modules = [
			self._module_definition(module, _)
			for module in permitted_commands
			if not module.flavors
		]
		modules.extend([
			self._flavor_definition(module, flavor, _)
			for module in permitted_commands
			for flavor in module.flavors
		])

		categories = [
			self._category_definition(category, _)
			for category in categoryManager.values()
		]

		# TODO: break API: only return modules; categories should be fetched by "/get/categories/list"
		return dict(
			categories=categories,
			modules=modules
		)

	def _category_definition(self, category, _):
		ucrvars = dict(ucr.items())
		return {
			'id': category.id,
			'name': _(category.name, category.domain).format(**ucrvars),
			'priority': category.priority
		}

	def _module_definition(self, module, _):
		return {
			'id': module.id,
			'name': _(module.name, module.id),
			'description': _(module.description, module.id),
			'icon': module.icon,
			'categories': module.categories,
			'priority': module.priority,
			'keywords': list(set(module.keywords + [_(keyword, module.id) for keyword in module.keywords]))
		}

	def _flavor_definition(self, module, flavor, _):
		translationid = flavor.translationId or module.id
		return {
			'id': module.id,
			'flavor': flavor.id,
			'name': _(flavor.name, translationid),
			'description': _(flavor.description, translationid),
			'icon': flavor.icon,
			'categories': module.categories,
			'priority': flavor.priority,
			'keywords': list(set(flavor.keywords + [_(keyword, translationid) for keyword in flavor.keywords]))
		}


class Categories(Resource):
	#'/get/categories/list'

	isLeaf = True

	@require_authentication
	def render(self, request):
		categoryManager = request.site.categoryManager
		categoryManager.load()
		return dict(
			categories=categoryManager.all()
		)


class UserPreferences(Resource):
	#'/get/user/preferences'

	isLeaf = True

	@require_authentication
	def render(self, request):
		user = request.getSession(User).user

		if not user:
			request.setResponseCode(BAD_REQUEST_INVALID_OPTS)  # HTTP FIXME
			return

		return dict(
			preferences=dict(user.info.get('umcProperty', []))
		)


class Hosts(Resource):
	#'/get/hosts/list'

	isLeaf = True

	@require_authentication
	def render(self, request):
		lo, po = get_machine_connection()
		if not lo:
			# unjoined / no LDAP connection
			return []

		try:
			domaincontrollers = lo.search(filter="(objectClass=univentionDomainController)")
		except LDAPError as exc:
			CORE.warn('Could not search for domaincontrollers: %s' % (exc))
			return []

		hosts = [
			'%s.%s' % (computer['cn'][0], computer['associatedDomain'][0])
			for dn, computer in domaincontrollers
			if computer.get('associatedDomain')
		]
		hosts.sort()
		return dict(result=hosts)


class UCR(Resource):
	#'/get/ucr'

	@require_authentication
	def render(self, request):
		ucr.load()
		response = {}
		for key in request.options:
			if key.endswith('*'):
				response.update(self.get_values_for(key[:-1]))
			else:
				response[key] = ucr.get(key)
		return dict(result=response)

	def get_values_for(self, key):
		return dict((var, ucr.get(var)) for var in ucr.keys() if var.startswith(key))


class Info(Resource):
	#'/get/info'

	@require_authentication
	def render(self, request):
		hostname = ucr.get('hostname', '')
		domainname = ucr.get('domainname', '')
		server = '%s.%s' % (hostname, domainname)
		validity_host = int(ucr.get('ssl/validity/host', '0')) * 24 * 60 * 60 * 1000
		validity_root = int(ucr.get('ssl/validity/root', '0')) * 24 * 60 * 60 * 1000

		return dict(result=dict(
			umc_version=get_umc_version(),
			ucs_version=get_ucs_version(),
			server=server,
			ssl_validity_host=validity_host,
			ssl_validity_root=validity_root
		))
