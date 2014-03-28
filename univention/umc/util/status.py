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

from univention.management.console.protocol.definitions import (
	status_description,
	SUCCESS, SUCCESS_MESSAGE, SUCCESS_PARTIAL, SUCCESS_SHUTDOWN,
	MODULE_ERR, MODULE_ERR_COMMAND_FAILED, BAD_REQUEST_NOT_FOUND,
	BAD_REQUEST_INVALID_OPTS, BAD_REQUEST_UNAVAILABLE_LOCALE,
	BAD_REQUEST_PASSWORD_EXPIRED, BAD_REQUEST_AUTH_FAILED,
	BAD_REQUEST_FORBIDDEN, BAD_REQUEST_UNAUTH
)

__all__ = (
	'status_description', 'SUCCESS', 'SUCCESS_MESSAGE', 'SUCCESS_PARTIAL',
	'SUCCESS_SHUTDOWN', 'MODULE_ERR', 'MODULE_ERR_COMMAND_FAILED', 'BAD_REQUEST_NOT_FOUND',
	'BAD_REQUEST_INVALID_OPTS', 'BAD_REQUEST_UNAVAILABLE_LOCALE', 'BAD_REQUEST_PASSWORD_EXPIRED',
	'BAD_REQUEST_AUTH_FAILED', 'BAD_REQUEST_FORBIDDEN', 'BAD_REQUEST_UNAUTH'
)
