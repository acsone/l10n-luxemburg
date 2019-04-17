# -*- coding: utf-8 -*-
# Copyright 2016-2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

'''
This module provides a generated monthly VAT declaration ready for eCDF
Values are computed with MIS Builder
Some lines of the declaration are editable
The VAT report can be downloaded in XML format
'''

import calendar
import datetime

from lxml import etree
from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError, Warning as UserError


class EcdfManualInput(models.Model):
    _name = 'ecdf.manual.input'

    report_id = fields.Many2one('ecdf.vat.report', string="Report")
    name = fields.Char('Name', required=True)
    description = fields.Char('Description')
    value = fields.Float('Value')


class EcdfManualData(models.Model):
    _name = 'ecdf.manual.data'

    name = fields.Char('Name', required=True)
    description = fields.Char('Description')


class EcdfVatReport(models.Model):
    '''
    Editable VAT report instance, able to create a eCDF XML file
    '''
    _inherit = "ecdf.abstract"
    _description = 'eCDF VAT Report'
    _name = 'ecdf.vat.report'

    name = fields.Char(required=True)
    description = fields.Char(string='Description')
    manual_ids = fields.One2many('ecdf.manual.input', 'report_id',
        string="Manual Input(s)",
        default=lambda self: self._default_manual())
    period_type = fields.Selection(string='Declaration Type',
        selection=[('month', 'Monthly'),
                   ('quarter', 'Quarterly'),
                   ('year', 'Annually')],
        default='month',
        required=True)
    this_year = datetime.date.today().year
    year = fields.Selection(string='Year',
        selection=[(n, str(n)) for n in range(2019, this_year+1)],
        required=True,
        default=this_year)
    period_month = fields.Selection(string="Period",
        selection=[(1, 'January'),
                   (2, 'February'),
                   (3, 'March'),
                   (4, 'April'),
                   (5, 'May'),
                   (6, 'June'),
                   (7, 'July'),
                   (8, 'August'),
                   (9, 'September'),
                   (10, 'October'),
                   (11, 'November'),
                   (12, 'December')],
        required=True,
        default=1)
    regime = fields.Selection(string='VAT accounting scheme',
        selection=[('sales', 'On sales [204]'),
                   ('revenues', 'On payments received [205]')],
        required=True,
        default='sales')
    mis_instance_id = fields.Many2one('mis.report.instance', string="Mis report instance")

    @api.multi
    def unlink(self):
        self.mapped('mis_instance_id').unlink()
        return super(EcdfVatReport, self).unlink()

    @api.multi
    @api.constrains('period_month', 'year')
    def update_instance(self):
        self.ensure_one()
        if not self.mis_instance_id:
            return
        report = self.get_mis_report(self.year, self.period_type)
        if not report:
            raise UserError(_('Cannot find the "%s" MIS report for the year "%s".') % (self.period_type, self.year))
        nb_days = calendar.monthrange(self.year, self.period_month)[1]
        date_start = datetime.date(self.year, self.period_month, 1)
        date_stop = datetime.date(self.year, self.period_month, nb_days)
        self.mis_instance_id.write({
            'report_id': report.id,
            'date_from': date_start,
            'date_to': date_stop,
            'period_ids': [(1, self.mis_instance_id.period_ids.ids[0], {
                'name': _('VAT %s-%02d') % (self.year, self.period_month),
            })],
            'temporary': True,
        })

    def _default_manual(self):
        result = []
        for manual_input in self.env['ecdf.manual.data'].search([]):
            result.append((0, 0, {'name': manual_input.name, 'description': manual_input.description}))
        return result

    @api.onchange('period_type')
    def _onchange_period_type(self):
        '''
        On Change : 'period_type'
        Field period_month is reset to its default value
        '''
        self.period_month = 1

    @api.multi
    def get_mis_report(self, year, period_type):
        '''
        :returns: the mis report template for monthly vat declaration
        '''
        xml_id = "l10n_lu_ecdf.mis_report_%s_vat_%s" % (period_type, year)
        return self.env.ref(xml_id)

    @api.multi
    def _append_vd_lines(self, form_data, regime):
        '''
        Generates data fields of the XML file
        :param form_data: Data node of the XML file
        :param regime: Tax regime (set by user)
        '''
        self.ensure_one()
        # Choice : Tax regime
        choice_regime_sales = etree.Element('Choice', id='204')
        choice_regime_revenues = etree.Element('Choice', id='205')
        # 1 : True, 0: False
        choice_regime_sales.text = '1' if regime == 'sales' else '0'
        choice_regime_revenues.text = '0' if regime == 'sales' else '1'

        # Append Tax regime fields
        form_data.append(choice_regime_sales)
        form_data.append(choice_regime_revenues)

        instance = self.get_report_instance()
        report_data = instance.compute()['body']
        for data in report_data:
            if data['row_id'][:5] == 'ecdf_':
                names = data['row_id'][5:].split('_')
                base = names[0]
                tax = names[1] if len(names) > 1 else base
                # BASE Has an expression
                if data['cells'][0]['val_c'][-1] != '=':
                    self._append_num_field(
                        form_data, base,
                        data['cells'][0]['val'],
                        comment=data['label'])
                # TAX has an expression
                if data['cells'][1]['val_c'][-1] != '=':
                    self._append_num_field(
                        form_data, tax,
                        data['cells'][1]['val'],
                        comment=data['label'])

    @api.multi
    def _get_vat_declaration(self, decl_type):
        '''
        Generates the declaration node of the xml file
        :param decl_type: Type of the declaration (monthly or annual)
        '''
        self.ensure_one()
        # Declaration node
        declaration = etree.Element('Declaration',
                                    type=decl_type,
                                    model='1',
                                    language=self.get_language())
        # Year field
        year = etree.Element('Year')
        year.text = str(self.year)
        # Period
        period = etree.Element('Period')
        period.text = str(self.period_month)
        # Form Data
        form_data = etree.Element('FormData')

        # Generates data fields
        self._append_vd_lines(form_data, self.regime)

        # Append fields
        declaration.append(year)
        declaration.append(period)
        declaration.append(form_data)

        return declaration

    @api.multi
    def get_report_instance(self):
        self.ensure_one()
        if not self.mis_instance_id:
            nb_days = calendar.monthrange(self.year, self.period_month)[1]
            date_start = datetime.date(self.year, self.period_month, 1)
            date_stop = datetime.date(self.year, self.period_month, nb_days)
            instance = self.env['mis.report.instance'].create({
                'name': self.name,
                'report_id': self.get_mis_report(self.year, self.period_type).id,
                'date_from': date_start,
                'date_to': date_stop,
                'period_ids': [(0, 0, {
                    'name': _('VAT %s-%02d') % (self.year, self.period_month),
                })],
                'temporary': True,
            })
            self.mis_instance_id = instance
        return self.mis_instance_id

    @api.multi
    def preview(self):
        self.ensure_one()
        view_id = self.env.ref('mis_builder.'
                               'mis_report_instance_result_view_form')
        instance = self.get_report_instance()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mis.report.instance',
            'res_id': instance.id,
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': view_id.id,
            'target': 'current',
        }

    def _get_xml_declarations(self, declarer):
        self.ensure_one()
        # Declarations
        declarations = etree.Element('Declarations')
        # Declaration lines
        decl_type = 'TVA_DECM' if self.period_type == 'month' else 'TVA_DECA'
        declarer.append(self._get_vat_declaration(decl_type))
        # Declarer
        declarations.append(declarer)
        return declarations
