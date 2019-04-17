# -*- coding: utf-8 -*-
# Copyright 2016-2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

'''
This module provides a wizard able to generate XML annual financial reports
Generated files are ready for eCDF
Reports :
 - Profit & Loss (P&L)
 - Profit & Loss Abbreviated (P&L)
 - Balance Sheet (BS)
 - Balance Sheet Abbreviated (BS)
 - Chart of Accounts (CA)
Generation is based on MIS Builder
'''

import re
import time
from datetime import date
from lxml import etree

from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError, Warning as UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.addons.mis_builder.models.accounting_none import AccountingNone

templ = {
    'CA_PLANCOMPTA': 'l10n_lu_mis_reports.mis_report_ca',
    'CA_BILAN': 'l10n_lu_mis_reports.mis_report_bs_2016',
    'CA_BILANABR': 'l10n_lu_mis_reports.mis_report_abr_bs',
    'CA_COMPP': 'l10n_lu_mis_reports.mis_report_pl_2016',
    'CA_COMPPABR': 'l10n_lu_mis_reports.mis_report_abr_pl',
}

class EcdfReport(models.Model):
    '''
    This model allows to generate three types of financial reports :
        - Profit & Loss (P&L)
        - Balance Sheet (BS)
        - Chart of Accounts (CA)
    P&L and BS can be generated in abbreviated version or not
    The selected reports (max. 3) are written in a downloadable XML file
    ready for eCDF
    '''
    _name = 'ecdf.report'
    _description = 'Annual eCDF financial Report'
    _inherit = "ecdf.abstract"

    target_move = fields.Selection(
        [('posted', 'All Posted Entries'), ('all', 'All Entries')],
        string='Target Moves',
        required=True,
        default='posted'
    )
    with_pl = fields.Boolean('Profit & Loss',
                             default=True)
    with_bs = fields.Boolean('Balance Sheet',
                             default=True)
    with_ac = fields.Boolean('Chart of Accounts', default=True)
    reports_type = fields.Selection((('full', 'Full'),
                                     ('abbreviated', 'Abbreviated')),
                                    'Reports Type',
                                    default='full',
                                    required=True)
    date_from = fields.Date(string="Firscal Year From", required=True,
                            default=lambda *a: time.strftime('%Y-01-01'))
    date_to = fields.Date(string="Fiscal Year To", required=True,
                          default=lambda *a: time.strftime('%Y-12-31'))
    remarks = fields.Text('Comments')
    full_file_name = fields.Char('Full file name',
                                 size=28)
    xml_file = fields.Binary('XML File', readonly=True)

    @api.multi
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        '''
        Constraint : date_from < date_to
        '''
        for record in self:
            if record.date_from >= record.date_to:
                raise ValidationError(
                    _("The fiscal year dates aren't valid. Please check the From and To."))

    @api.multi
    def _append_fr_lines(self, data_curr, form_data, data_prev=None):
        '''
        Appends lines "NumericField" in the "form_data" node
        :param data_curr: data of the previous year
        :param form_data: XML node "form_data"
        :param data_prev: date of the previous year
        '''
        # Regex: group('current') : ecdf_code for current year
        #        group('previous') : ecdf_code for previous year
        exp = r"""^ecdf\_(?P<previous>\d*)\_(?P<current>\d*)"""
        rexp = re.compile(exp, re.X)
        for record in self:
            for report in data_curr:
                line_match = rexp.match(report['kpi_technical_name'])
                if line_match:
                    ecdf_code = line_match.group('current')
                    record._append_num_field(
                        form_data,
                        ecdf_code,
                        report['val'],
                        comment=" current - %s " % report['kpi_name']
                    )
            for report in data_prev:
                line_match = rexp.match(report['kpi_technical_name'])
                if line_match:
                    ecdf_code = line_match.group('previous')
                    record._append_num_field(
                        form_data,
                        ecdf_code,
                        report['val'],
                        comment=" previous - %s " % report['kpi_name']
                    )

    @api.multi
    def _get_finan_report(self, data_current, report_type, report_model,
                          data_previous=None):
        '''
        Generates a financial report (P&L or Balance Sheet) in XML format
        :param data_current: dictionary of data of the current year
        :param report_type: technical name of the report type
        :param data_previous: dictionary of data of the previous year
        :returns: XML node called "declaration"
        '''
        self.ensure_one()

        currency = self.company_id.currency_id
        declaration = etree.Element('Declaration',
                                    type=report_type,
                                    language=self.get_language(),
                                    model=report_model)
        date_from = fields.Date.from_string(self.date_from)
        date_to = fields.Date.from_string(self.date_to)
        year = etree.Element('Year')
        year.text = str(date_from.year)
        period = etree.Element('Period')
        period.text = '1'
        form_data = etree.Element('FormData')
        tfid = etree.Element('TextField', id='01')
        tfid.text = date_from.strftime("%d/%m/%Y")
        form_data.append(tfid)
        tfid = etree.Element('TextField', id='02')
        tfid.text = date_to.strftime("%d/%m/%Y")
        form_data.append(tfid)
        tfid = etree.Element('TextField', id='03')
        tfid.text = currency.name
        form_data.append(tfid)

        self._append_fr_lines(data_current,
                              form_data,
                              data_previous)

        declaration.append(year)
        declaration.append(period)
        declaration.append(form_data)

        return declaration

    @api.multi
    def _get_chart_ac(self, data, report_type, report_model):
        '''
        Generates the chart of accounts in XML format
        :param data: Dictionary of values (name, technical name, value)
        :param report_type: Technical name of the report type
        :returns: XML node called "declaration"
        '''
        self.ensure_one()
        # Regex : group('current') : ecdf_code for current year
        #         group('previous') : ecdf_code for previous year
        exp = r"""^ecdf\_(?P<debit>\d*)\_(?P<credit>\d*)"""
        rexp = re.compile(exp, re.X)

        declaration = etree.Element('Declaration',
                                    type=report_type,
                                    language=self.get_language(),
                                    model=report_model)

        date_from = fields.Date.from_string(self.date_from)
        date_to = fields.Date.from_string(self.date_to)
        year = etree.Element('Year')
        year.text = str(date_from.year)
        period = etree.Element('Period')
        period.text = '1'
        form_data = etree.Element('FormData')
        tfid = etree.Element('TextField', id='01')
        tfid.text = date_from.strftime("%d/%m/%Y")
        form_data.append(tfid)
        tfid = etree.Element('TextField', id='02')
        tfid.text = date_to.strftime("%d/%m/%Y")
        form_data.append(tfid)
        tfid = etree.Element('TextField', id='03')
        tfid.text = self.company_id.currency_id.name
        form_data.append(tfid)

        if self.remarks:  # add remarks in chart of accounts
            fid = etree.Element('TextField', id='2385')
            fid.text = self.remarks
            form_data.append(fid)

        for report in data:
            line_match = rexp.match(report['kpi_technical_name'])
            if line_match:
                if report['val'] not in (AccountingNone, None):
                    balance = round(report['val'], 2)
                    if balance <= 0:  # 0.0 must be in the credit column
                        ecdf_code = line_match.group('credit')
                        balance = abs(balance)
                        comment = 'credit'
                    else:
                        ecdf_code = line_match.group('debit')
                        comment = 'debit'

                    # code 106 appears 2 times in the chart of accounts
                    # with different ecdf codes
                    # so we hard-code it here:
                    # this is the only exception to the general algorithm
                    # TODO why not have 2 kpi's which return the same result
                    #      so the algorithm remains generic?
                    if report['kpi_name'][:5] == '106 -':
                        if balance <= 0.0:
                            ecdf_codes = ['0118', '2260']
                        else:
                            ecdf_codes = ['0117', '2259']

                        self._append_num_field(
                            form_data, ecdf_codes[0], balance,
                            comment=" %s - %s " % (comment,
                                                   report['kpi_name'])
                        )
                        self._append_num_field(
                            form_data, ecdf_codes[1], balance,
                            comment=" %s - %s " % (comment,
                                                   report['kpi_name'])
                        )

                    self._append_num_field(
                        form_data, ecdf_code, balance,
                        comment=" %s - %s " % (comment, report['kpi_name'])
                    )

        declaration.append(year)
        declaration.append(period)
        declaration.append(form_data)

        return declaration

    @api.multi
    def compute(self, mis_template, date_from, date_to):
        self.ensure_one()
        # Prepare AccountingExpressionProcessor
        aep = mis_template._prepare_aep(self.company_id)

        # Prepare KPI Matrix
        kpi_matrix = mis_template.prepare_kpi_matrix()

        # Populate the kpi_matrix
        mis_template.declare_and_compute_period(
            kpi_matrix,
            'col_key',
            'col_label',
            'col_description',
            aep,
            date_from, date_to,
            self.target_move,
            self.company_id)

        # Get the columns of the kpi_matrix
        matrix_cols = kpi_matrix.iter_cols()

        # Dictionary of values by code
        kpi_values = {}

        # Iterate the matrix to fetch data
        for col in matrix_cols:
            for cell in col.iter_cell_tuples():
                for c in cell:
                    kpi_values[c.row.kpi.name] = {'val': c.val}

        content = []
        for kpi in mis_template.kpi_ids:
            content.append({
                'kpi_name': kpi.description,
                'kpi_technical_name': kpi.name,
                'val': kpi_values[kpi.name]['val'],
            })

        return content

    def _get_xml_declarations(self, declarer):
        self.ensure_one()
        declarations = etree.Element('Declarations')
        reports = []

        # Report
        if self.with_ac:  # Chart of Accounts
            reports.append({'type': 'CA_PLANCOMPTA',
                            'model': '1',
                            'templ': templ['CA_PLANCOMPTA']})
        if self.with_bs:  # Balance Sheet
            if self.reports_type == 'full':
                reports.append({'type': 'CA_BILAN',
                                'model': '1',
                                'templ': templ['CA_BILAN']})
            else:  # Balance Sheet abreviated
                reports.append({'type': 'CA_BILANABR',
                                'model': '1',
                                'templ': templ['CA_BILANABR']})
        if self.with_pl:  # Profit and Loss
            if self.reports_type == 'full':
                reports.append({'type': 'CA_COMPP',
                                'model': '2',
                                'templ': templ['CA_COMPP']})
            else:  # Profit and Loss abreviated
                reports.append({'type': 'CA_COMPPABR',
                                'model': '1',
                                'templ': templ['CA_COMPPABR']})

        if not reports:
            raise UserError(_('No report type selected'),
                            _('Please, select a report type'))

        error_not_found = ""
        for report in reports:
            mis_report = self.env.ref(report['templ'])

            if not mis_report:
                error_not_found += '\n\t - ' + report['templ']

            data_current = self.compute(mis_report, self.date_from, self.date_to)

            if report['type'] != 'CA_PLANCOMPTA':
                date_from = fields.Date.from_string(self.date_from)
                previous_date_from = date(date_from.year + 1,
                        date_from.month, date_from.day).strftime(DATE_FORMAT)
                date_to = fields.Date.from_string(self.date_to)
                previous_date_to = date(date_to.year + 1,
                        date_to.month, date_to.day).strftime(DATE_FORMAT)
                data_previous = self.compute(mis_report,
                        previous_date_from, previous_date_to)
                financial_report = self._get_finan_report(data_current,
                                                          report['type'],
                                                          report['model'],
                                                          data_previous)
                if financial_report is not None:
                    declarer.append(financial_report)
            else:  # Chart of accounts
                chart_of_account = self._get_chart_ac(data_current,
                                                      report['type'],
                                                      report['model'])
                if chart_of_account is not None:
                    declarer.append(chart_of_account)

        if error_not_found:
            raise UserError(
                _('MIS Template(s) not found :'),
                error_not_found)

        declarations.append(declarer)
        return declarations

    @api.multi
    def get_report_instance(self, report_type):
        instance = self.env['mis.report.instance'].create({
            'name': self.name,
            'report_id': self.env.ref(templ.get(report_type)).id,
            'date_from': fields.Date.from_string(self.date_from),
            'date_to': fields.Date.from_string(self.date_to),
            'period_ids': [(0, 0, {
                'name': _('From %s To %s') % (self.date_from, self.date_to),
            })],
            'temporary': True,
        })
        return instance

    @api.multi
    def preview(self):
        self.ensure_one()
        view_id = self.env.ref('mis_builder.'
                               'mis_report_instance_result_view_form')
        preview_type = self.env.context.get('preview_type')
        if not preview_type:
            return
        report_type = 'CA_PLANCOMPTA'
        if preview_type == 'bs':
            report_type = 'CA_BILAN' if self.reports_type == 'full' else 'CA_BILANABR'
        elif preview_type == 'pl':
            report_type = 'CA_COMPP' if self.reports_type == 'full' else 'CA_COMPPABR'
        instance = self.get_report_instance(report_type)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mis.report.instance',
            'res_id': instance.id,
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': view_id.id,
            'target': 'current',
        }
