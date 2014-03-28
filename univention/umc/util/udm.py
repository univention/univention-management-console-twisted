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
from ldap.filter import escape_filter_chars
import univention.admin.uldap as udm_uldap
import univention.admin.objects as udm_objects
import univention.admin.modules as udm_modules
import univention.admin.uexceptions as udm_errors

from univention.umc.util.log import CORE
from univention.umc.util.config import ucr

__udm_users_module_initialised = False
users_module = None
# TODO: can we cache the ldap connection?


def get_machine_connection():
	# TODO: find out and make a comment why ldap_master is False
	try:
		# get LDAP connection with machine account
		return udm_uldap.getMachineConnection(ldap_master=False)
	except (LDAPError, IOError) as exc:
		# problems connection to LDAP server or the server is not joined (machine.secret is missing)
		CORE.warn('An error occurred connecting to the LDAP server: %s' % exc)
		return None, None


def get_user_connection(userdn, password):
	__init_users_module()
	ucr.load()

	try:
		# open an LDAP connection with the user password and credentials
		return udm_uldap.access(
			host=ucr.get('ldap/server/name'),
			base=ucr.get('ldap/base'),
			port=int(ucr.get('ldap/server/port', 7389)),
			binddn=userdn,
			bindpw=password,
			follow_referral=True
		), udm_uldap.position(ucr.get('ldap/base'))
	except (udm_errors.base, LDAPError) as exc:
		CORE.warn('Failed to get ldap connection for UDM user object %s: %s' % (userdn, exc))
		return None, None


def get_user_object(userdn, password):
	lo, po = get_user_connection(userdn, password)
	if not lo:
		return
	try:
		# try to open the user object
		user = udm_objects.get(users_module, None, lo, po, userdn)
		if not user:
			raise udm_errors.noObject()
		user.open()
		return user
	except (udm_errors.base, LDAPError) as exc:
		CORE.warn('Failed to open UDM user object %s: %s' % (userdn, exc))


def get_userdn_by_username(username):
	lo, po = get_machine_connection()
	if lo:
		# get the LDAP DN of the authorized user
		ldap_dn = lo.searchDn('(&(uid=%s)(objectClass=posixAccount))' % escape_filter_chars(username))
		if not ldap_dn:
			CORE.info('The LDAP DN for user %s could not be found' % (username))
			return
		CORE.info('The LDAP DN for user %s is %s' % (username, ldap_dn))
		return ldap_dn[0]


def __set_users_module():
	global users_module
	if users_module:
		return
	try:
		# get the users/user UDM module
		udm_modules.update()
		users_module = udm_modules.get('users/user')
	except udm_errors.base as e:
		# UDM error, user module coule not be initiated
		CORE.warn('An error occurred getting the UDM users/user module: %s' % e)
__set_users_module()


def __init_users_module():
	__set_users_module()
	try:
		# make sure that the UDM users/user module could be initiated
		if not users_module:
			raise udm_errors.base('UDM module users/user could not be initiated')

		global __udm_users_module_initialised
		if not __udm_users_module_initialised:
			# initiate the users/user UDM module
			lo, po = get_machine_connection()
			udm_modules.init(lo, po, users_module)
			__udm_users_module_initialised = True
	except (udm_errors.base, LDAPError) as exc:
		CORE.warn('%s' % (exc,))
