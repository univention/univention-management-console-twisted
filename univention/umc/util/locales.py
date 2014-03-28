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

from locale import setlocale, getlocale, getdefaultlocale, LC_MESSAGES, Error as LocaleError

from univention.management.console.locales import I18N_Manager, I18N

from univention.lib.i18n import Translation as uTranslation, Locale, I18N_Error
from univention.umc import Translation as ITranslation, implements

from univention.umc.util.log import CORE


# TODO: raise Exception instead of return value?
class Translation(object):
	implements(ITranslation)

	def __init__(self, session):
		self.core_i18n = uTranslation('univention-management-console')
		self.i18n = I18N_Manager()
		self.i18n['umc-core'] = I18N()
		self._ = self.i18n._

	def set_language(self, language):
		success = True
		for language in [language, 'C']:
			CORE.info('Setting language: %s' % (language,))
			try:
				self.core_i18n.set_language(language)
				self.i18n.set_locale(language)
			except (I18N_Error, AttributeError, TypeError):
				CORE.warn('Setting locale to specified locale failed (%s)' % (language,))
				success = False
		return success

	def get_language(self):
		return bytes(self.i18n.locale)


def set_locale(locale):
	try:
		locale = str(Locale(locale))
		setlocale(LC_MESSAGES, locale)
		CORE.info("Setting specified locale (%s)" % (locale,))
	except LocaleError:
		CORE.warn("Specified locale is not available (%s)" % (locale,))
		CORE.warn("Falling back to C")
		setlocale(LC_MESSAGES, 'C')
		return False
	else:
		return True


def change_locale(locale):
	if get_locale() != locale:
		return set_locale(locale)
	return True


def get_locale():
	lang, encoding = getlocale(LC_MESSAGES)
	if not lang:
		lang, encoding = getdefaultlocale(['LC_MESSAGES'])
	return lang
