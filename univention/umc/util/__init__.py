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
import gzip
from functools import wraps

from univention.umc.util import module, category
from univention.umc.util.config import ucr
from univention.umc.util.locales import set_locale, Translation, change_locale
from univention.umc.util.process import UMCModuleProcess
from univention.umc.util.udm import get_userdn_by_username, get_user_object, get_machine_connection
from univention.umc.util.status import (
	status_description, BAD_REQUEST_UNAUTH,
	MODULE_ERR, SUCCESS, MODULE_ERR_COMMAND_FAILED,
	BAD_REQUEST_PASSWORD_EXPIRED, BAD_REQUEST_AUTH_FAILED,
	BAD_REQUEST_NOT_FOUND, BAD_REQUEST_FORBIDDEN,
	BAD_REQUEST_INVALID_OPTS, BAD_REQUEST_UNAVAILABLE_LOCALE
)
from univention.umc.util.log import (
	AUTH, CORE, MODULE, RESOURCES,
	log_init, set_log_level, get_current_log_level
)

__all__ = (
	'get_userdn_by_username', 'get_user_object', 'get_machine_connection',
	'status_description', 'BAD_REQUEST_UNAUTH', 'MODULE_ERR_COMMAND_FAILED', 'MODULE_ERR',
	'SUCCESS', 'ucr', 'AUTH', 'CORE', 'MODULE', 'set_locale', 'UMCModuleProcess'
)
UMC_CHANGELOG_FILE = '/usr/share/doc/univention-management-console-server/changelog.Debian.gz'


def get_ucs_version():
	version = ucr.get('version/version', '')
	patchlevel = ucr.get('version/patchlevel', '')
	erratalevel = ucr.get('version/erratalevel', '0')
	releasename = ucr.get('version/releasename', '')
	return '%s-%s errata%s (%s)' % (version, patchlevel, erratalevel, releasename)


def get_umc_version():
	try:
		line = gzip.open(UMC_CHANGELOG_FILE).readline()
	except IOError:
		return

	try:
		return get_umc_version.RE_CHANGELOG_VERSION.match(line).groups()[0]
	except AttributeError:
		return
get_umc_version.RE_CHANGELOG_VERSION = re.compile(r'^[^(]*\(([^)]*)\).*')


def require_authentication(func):
	@wraps(func)
	def _decorated(self, request):
		request.require_authentication()
		return func(self, request)

	return _decorated
