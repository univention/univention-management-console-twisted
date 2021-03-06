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

__all__ = [
	'implements', 'Translation',
	'User', 'ACLs', 'ModuleProcess',
	'NotAuthenticated', 'AuthenticationFailed',
	'PasswordExpired', 'PasswordChangeFailed'
]

from univention.umc.interfaces import (
	implements, Translation, User, ACLs, ModuleProcess,
	NotAuthenticated, AuthenticationFailed,
	PasswordExpired, PasswordChangeFailed,
	CouldNotConnect
)

def main():
	import sys
	import os.path
	from univention.umc.server import ServerDaemon
	from univention.umc.module import ModuleDaemon

	name = os.path.basename(sys.argv[0])
	try:
		Daemon = {
			'umc-server': ServerDaemon,
			'univention-management-console-server': ServerDaemon,
			'umc-module': ModuleDaemon,
			'univention-management-console-module': ModuleDaemon,
		}[name]
	except KeyError:
		import sys
		raise SystemExit('use umc-server or umc-module! not %s' % sys.argv[0])
	else:
		Daemon()


if __name__ == '__main__':
	try:
		main()
	except (SystemExit, KeyboardInterrupt):
		raise
	except:
		import traceback
		from univention.umc.util import CORE
		CORE.error(traceback.format_exc())
		raise
