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


import simplejson

from openerp.addons.web.http import Controller, route, request


class main(Controller):

    #docids corresponds to the active_ids in the context
    @route(['/report/export_faia_lu/<docids>'], type='http', auth='user')
    def report_faia(self, docids):
        docids = [int(i) for i in docids.split(',')]
        fiscalyear_model = request.registry.get('account.fiscalyear')

        result = fiscalyear_model.get_faia_data(
            request.cr, request.uid, docids, context=request.context)
        
        return request.make_response(result[0], headers=[
            ('Content-Type', 'application/xml'),
            ('Content-Disposition', 'attachment; filename=faia.xml;')
        ])