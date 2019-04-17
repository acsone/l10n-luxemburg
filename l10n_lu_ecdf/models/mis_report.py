# -*- coding: utf-8 -*-
# Copyright 2016-2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MisReport(models.Model):
    _inherit = 'mis.report'

    @api.multi
    def declare_and_compute_period(self, kpi_matrix,
                                   col_key,
                                   col_label,
                                   col_description,
                                   aep,
                                   date_from, date_to,
                                   target_move,
                                   subkpis_filter=None,
                                   get_additional_move_line_filter=None,
                                   get_additional_query_filter=None,
                                   locals_dict=None,
                                   aml_model=None,
                                   no_auto_expand_accounts=False):
        '''
        If the mis report instance is linked to a ecdf.vat.report,
        The manual inputs are added to the locals_dict
        '''
        if locals_dict is None:
            locals_dict = {}
        if get_additional_query_filter:
            if get_additional_query_filter.im_self and get_additional_query_filter.im_self.report_instance_id:
                vat_report = self.env['ecdf.vat.report'].search(
                    [('mis_instance_id', '=', get_additional_query_filter.im_self.report_instance_id.id)])
                if vat_report and vat_report.manual_ids:
                    manuals = {}
                    for manual_input in vat_report.manual_ids:
                        manuals[manual_input.name] = manual_input.value
                    locals_dict.update({'manuals': manuals})

        return super(MisReport, self).declare_and_compute_period(kpi_matrix,
                                 col_key,
                                 col_label,
                                 col_description,
                                 aep,
                                 date_from, date_to,
                                 target_move,
                                 subkpis_filter,
                                 get_additional_move_line_filter,
                                 get_additional_query_filter,
                                 locals_dict,
                                 aml_model,
                                 no_auto_expand_accounts)
