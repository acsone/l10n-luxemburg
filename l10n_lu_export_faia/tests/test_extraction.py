# -*- coding: utf-8 -*-
##############################################################################
#
#     This file is part of l10n_lu_export_faia, an Odoo module.
#
#     Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
#
#     l10n_lu_export_faia is free software: you can redistribute it and/or
#     modify it under the terms of the GNU Affero General Public License
#     as published by the Free Software Foundation, either version 3 of
#     the License, or (at your option) any later version.
#
#     l10n_lu_export_faia is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the
#     GNU Affero General Public License
#     along with l10n_lu_export_faia.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import openerp.tests.common as common
import logging
import os

_logger = logging.getLogger(__name__)


class TestExtraction(common.TransactionCase):

    def setUp(self):
        super(TestExtraction, self).setUp()
        self.fiscalyear_id = self.ref('account.data_fiscalyear')
        self.fiscalyear_model = self.env['account.fiscalyear']

    def test_simple_extraction(self):
        fiscalyear = self.fiscalyear_model.browse(self.fiscalyear_id)

        force_date = '2015-06-13'
        force_year = '2015'

        test_data = fiscalyear.with_context(
            force_date_faia_export=force_date,
            force_year_faia_export=force_year).get_faia_data()[0]

        # Write the result on debug mode
        if _logger.isEnabledFor(logging.DEBUG):
            path = os.path.join(os.path.dirname(__file__),
                                'data', 'test_simple_extract_res.xml')
            fo = open(path, "w")
            fo.write(test_data)
            fo.close()

        path = os.path.join(os.path.dirname(__file__),
                            'data', 'test_simple_extract_ref.xml')
        fo = open(path, "r")
        ref_file_content = fo.read()

        self.assertEqual(test_data, ref_file_content)
