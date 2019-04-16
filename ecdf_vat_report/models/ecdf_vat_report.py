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
import re
from StringIO import StringIO

from lxml import etree
from odoo import api, fields, models, _, tools
from odoo.addons.mis_builder.models.accounting_none import AccountingNone
from odoo.exceptions import ValidationError, Warning as UserError
from odoo.report import report_sxw


class VatAgent(models.Model):
    '''
    Declarer agent
    '''
    _name = 'vat.agent'

    name = fields.Char(string='Name', required=True)
    matr = fields.Char(string='Matricule', size=13, required=True)
    rcs = fields.Char(string='Company Registry', size=7, required=True)
    vat = fields.Char(string='Tax ID', size=10, required=True)

    @api.multi
    @api.constrains('matr')
    def check_matr(self):
        '''
        Constraint : length of Matricule must be 11 or 13
        '''
        for agent in self:
            if len(agent.matr) not in [11, 13]:
                raise ValidationError(_(
                    'Matricule must be 11 or 13 characters long.'))

    @api.multi
    @api.constrains('rcs')
    def check_rcs(self):
        '''
        Constraint : regex validation on RCS Number
        '''
        exp = r"""^[A-Z][^0]\d{1,5}"""
        rexp = re.compile(exp, re.X)
        for agent in self:
            if not rexp.match(agent.rcs):
                raise ValidationError(_(
                    'RCS number must begin with an uppercase letter followed '
                    'by 2 to 6 digits. The first digit must not be 0.'))

    @api.multi
    @api.constrains('vat')
    def check_vat(self):
        '''
        Constraint : regex validation on VAT Number
        '''
        exp = r"""^[A-Z]{2}\d{8}"""
        rexp = re.compile(exp, re.X)
        for agent in self:
            if not rexp.match(agent.vat):
                raise ValidationError(_(
                    'VAT number must begin with two uppercase letters '
                    'followed by 8 digits.'))


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
        if locals_dict is None:
            locals_dict = {}
        if get_additional_query_filter:
            if get_additional_query_filter.im_self and get_additional_query_filter.im_self.report_instance_id:
                vat_report = self.env['vat.report'].search(
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


class EcdfManualInput(models.Model):
    _name = 'ecdf.manual.input'

    report_id = fields.Many2one('vat.report', string="Report")
    name = fields.Char('Name', required=True)
    description = fields.Char('Description')
    value = fields.Float('Value')


class EcdfManualData(models.Model):
    _name = 'ecdf.manual.data'

    name = fields.Char('Name', required=True)
    description = fields.Char('Description')


class VatReport(models.Model):
    '''
    Editable VAT report instance, able to create a eCDF XML file
    '''
    _inherit = "account.common.report"
    _description = 'eCDF VAT Report'
    _name = 'vat.report'
    _transient = False

    name = fields.Char(string='Name', required=True)
    description = fields.Char(string='Description')
    manual_ids = fields.One2many('ecdf.manual.input', 'report_id',
        string="Manual Input(s)",
        default=lambda self: self._default_manual())
    language = fields.Selection(string='Language',
        selection=[('FR', 'French'),
                   ('DE', 'German'),
                   ('EN', 'English')],
        required=True,
        default='FR')
    type = fields.Selection(string='Declaration Type',
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
    period = fields.Selection(string="Period",
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
    agent_id = fields.Many2one(string='Agent', comodel_name='vat.agent', ondelete='restrict')
    regime = fields.Selection(string='VAT accounting scheme',
        selection=[('sales', 'On sales [204]'),
                   ('revenues', 'On payments received [205]')],
        required=True,
        default='sales')

    # File name (computed)
    file_name = fields.Char(sring='File name', size=24, compute='_compute_file_name')
    mis_instance_id = fields.Many2one('mis.report.instance', string="Mis report instance")

    @api.multi
    def unlink(self):
        self.mapped('mis_instance_id').unlink()
        return super(VatReport, self).unlink()

    @api.multi
    @api.constrains('period', 'year')
    def update_instance(self):
        self.ensure_one()
        if not self.mis_instance_id:
            return
        report = self.get_mis_report_month(self.year)
        if not report:
            raise UserError(_('We cannot create the report for the selected year.'))
        nb_days = calendar.monthrange(self.year, self.period)[1]
        date_start = datetime.date(self.year, self.period, 1)
        date_stop = datetime.date(self.year, self.period, nb_days)
        self.mis_instance_id.write({
            'report_id': report.id,
            'date_from': date_start,
            'date_to': date_stop,
            'period_ids': [(1, self.mis_instance_id.period_ids.ids[0], {
                'name': _('VAT %s-%02d') % (self.year, self.period),
            })],
        })

    def _default_manual(self):
        result = []
        for manual_input in self.env['ecdf.manual.data'].search([]):
            result.append((0, 0, {'name': manual_input.name, 'description': manual_input.description}))
        return result

    @api.multi
    @api.depends('company_id.ecdf_prefixe')
    def _compute_file_name(self):
        '''
        000000XyyyymmddThhmmssNN
        Position 1 - 6: eCDF prefix of the user's company
        Position 7: file type (X for XML files)
        Position 8 - 15: creation date of the file, format yyyymmdd
        Position 16: the character « T » (Time)
        Position 17 - 22: creation time of the file, format hhmmss
        Position 23 - 24: sequence number (NN) in range (01 - 99)
        for the unicity of the names of the files created in the same second
        '''
        for report in self:
            nbr = 1
            dtf = "X%Y%m%dT%H%M%S"
            prefix = report.company_id.ecdf_prefixe
            if not prefix:
                prefix = '000000'
            res = str("%s%s%02d" % (prefix,
                                    datetime.datetime.now().strftime(dtf),
                                    nbr))
            report.file_name = res

    @api.onchange('type')
    def _onchange_type(self):
        '''
        On Change : 'type'
        Field period is reset to its default value
        '''
        self.period = 1

    def get_ecdf_file_version(self):
        '''
        :returns: the XML file version
        '''
        return '1.1'

    def get_interface(self):
        '''
        :returns: eCDF interface ID (provided by eCDF)
        '''
        return 'CODL7'

    @api.multi
    def get_matr_declarer(self):
        '''
        :returns: Luxemburg matricule of the company
        :raises: UserError: if no matricule
        '''
        self.ensure_one()
        matr = self.company_id.l10n_lu_matricule
        if not matr:
            raise UserError(_('The company has no matricule set.'))
        return matr

    @api.multi
    def get_rcs_declarer(self):
        '''
        :returns: RCS number of the company, 7 characters
        If no RCS number, default value 'NE' is returned
        (RCS : 'Numéro de registre de Commerce et des Sociétés')
        '''
        self.ensure_one()
        rcs = self.company_id.company_registry
        return rcs if rcs else 'NE'

    @api.multi
    def get_vat_declarer(self):
        '''
        :returns: VAT number of the company, 8 characters
        If no VAT number, default value 'NE' is returned
        '''
        self.ensure_one()
        vat = self.company_id.vat
        if vat and vat.startswith('LU'):
            return vat[2:]
        return 'NE'

    @api.multi
    def get_matr_agent(self):
        '''
        :returns: Agent matricule provided in the form
        If no agent matricule provided, the company one is returned
        '''
        self.ensure_one()
        if self.agent_id and self.agent_id.matr:
            return self.agent_id.matr
        return self.get_matr_declarer()

    @api.multi
    def get_rcs_agent(self):
        '''
        :returns: RCS number (Numéro de registre de Commerce et des Sociétés)\
        provided in the form.
        If no RCS number has been provided, the company one is returned
        If no RCS number of the company, default value 'NE' is returned
        '''
        self.ensure_one()
        if self.agent_id and self.agent_id.rcs:
            return self.agent_id.rcs
        return self.get_rcs_declarer()

    @api.multi
    def get_vat_agent(self):
        '''
        :returns: VAT number provided in the form. If no VAT number has been\
        provided, the VAT number of the company is returned.
        If no VAT number of the company, default value 'NE' is returned
        '''
        self.ensure_one()
        if self.agent_id and self.agent_id.vat:
            vat = self.agent_id.vat
            if vat.startswith('LU'):
                return vat[2:]
        return self.get_vat_declarer()

    @api.multi
    def get_language(self):
        '''
        :returns: the selected language in the form. Values can be :
                    - "FR" for french
                    - "DE" for german
                    - "EN" for english
        '''
        self.ensure_one()
        return self.language

    @api.multi
    def get_mis_report_month(self, year='2019'):
        '''
        :returns: the mis report template for monthly vat declaration
        '''
        xml_id = "ecdf_vat_report.mis_report_vat_%s" % year
        return self.env.ref(xml_id)

    def _append_num_field(self, element, ecdf, val, comment=None):
        '''
        A numeric field's value can be a integer or a float
        The only decimal separator accepted is the coma (",")
        The point (".") is not accepted as a decimal separator nor as a \
        thousands separator
        :param element: XML node
        :param ecdf: eCDF technical code
        :param val: value to add in the XML node
        :param comment: Optional comment (default None)
        '''
        if val is None or val is AccountingNone:
            val = 0.0

        # Round value, two decimal places
        value = round(val, 2)
        # Insert optional comment
        if comment:
            element.append(etree.Comment(comment))
        # Numeric field
        child = etree.Element('NumericField', id=ecdf)
        child.text = ("%.2f" % value).replace('.', ',')
        # Append to father node
        element.append(child)

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
        period.text = str(self.period)
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
            nb_days = calendar.monthrange(self.year, self.period)[1]
            date_start = datetime.date(self.year, self.period, 1)
            date_stop = datetime.date(self.year, self.period, nb_days)
            instance = self.env['mis.report.instance'].create({
                'name': self.name,
                'report_id': self.get_mis_report_month(self.year).id,
                'date_from': date_start,
                'date_to': date_stop,
                'period_ids': [(0, 0, {
                    'name': _('VAT %s-%02d') % (self.year, self.period),
                })],
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

    @api.multi
    def _print_report(self, data):
        '''
        Generates the VAT declaration in XML format
        :param data: dictionary of values for the xml file
        '''
        self.ensure_one()

        # Build XML
        # the default namespace(no prefix)
        nsmap = {None: "http://www.ctie.etat.lu/2011/ecdf"}
        # Root
        root = etree.Element("eCDFDeclarations", nsmap=nsmap)
        # File Reference
        file_reference = etree.Element('FileReference')
        file_reference.text = self.file_name
        root.append(file_reference)
        # File Version
        file_version = etree.Element('eCDFFileVersion')
        file_version.text = self.get_ecdf_file_version()
        root.append(file_version)
        # Interface
        interface = etree.Element('Interface')
        interface.text = self.get_interface()
        root.append(interface)
        # Agent
        agent = etree.Element('Agent')
        matr_agent = etree.Element('MatrNbr')
        matr_agent.text = self.get_matr_agent()
        rcs_agent = etree.Element('RCSNbr')
        rcs_agent.text = self.get_rcs_agent()
        vat_agent = etree.Element('VATNbr')
        vat_agent.text = self.get_vat_agent()
        agent.append(matr_agent)
        agent.append(rcs_agent)
        agent.append(vat_agent)
        root.append(agent)
        # Declarations
        declarations = etree.Element('Declarations')
        declarer = etree.Element('Declarer')
        matr_declarer = etree.Element('MatrNbr')
        matr_declarer.text = self.get_matr_declarer()
        rcs_declarer = etree.Element('RCSNbr')
        rcs_declarer.text = self.get_rcs_declarer()
        vat_declarer = etree.Element('VATNbr')
        vat_declarer.text = self.get_vat_declarer()
        declarer.append(matr_declarer)
        declarer.append(rcs_declarer)
        declarer.append(vat_declarer)
        # Declaration lines
        decl_type = 'TVA_DECM' if self.type == 'month' else 'TVA_DECA'
        declarer.append(self._get_vat_declaration(decl_type))
        # Declarer
        declarations.append(declarer)
        root.append(declarations)

        # Write the xml
        xml = etree.tostring(root, encoding='UTF-8', xml_declaration=True)
        # Update the dictionary
        data['form'].update({'xml': xml})

        # set filename
        data['form']['filename'] = self.file_name

        # Launch xml file download
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'create.xml',
            'name': data['form']['filename'],
            'datas': data,
        }


class CreateXML(report_sxw.report_sxw):
    '''
    XML report file
    '''

    def __init__(self, name):
        super(CreateXML, self).__init__(name, '')

    def create(self, cr, uid, ids, data, context=None):
        xml = data['form']['xml']
        xml = xml.encode('utf-8')
        # Validate the generated XML schema
        xsd = tools.file_open('ecdf_vat_report/xsd/eCDF_file_v1.1.xsd')
        xmlschema_doc = etree.parse(xsd)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        # re-parse only to have line numbers in error messages?
        xml_to_validate = StringIO(xml)
        parse_result = etree.parse(xml_to_validate)
        if not xmlschema.validate(parse_result):
            error = xmlschema.error_log[0]
            raise UserError(
                _('The generated XML file does not fit the required schema !'),
                error.message)
        return (xml_to_validate.getvalue(), 'xml')

CreateXML('report.create.xml')
