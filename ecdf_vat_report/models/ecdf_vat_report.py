# -*- coding: utf-8 -*-
# Copyright 2016 ACSONE SA/NV
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
from openerp import api, fields, models, _, tools
from openerp.addons.mis_builder.models.accounting_none import AccountingNone
from openerp.exceptions import ValidationError, Warning as UserError
from openerp.report import report_sxw


class VatAgent(models.Model):
    '''
    Declarer agent
    '''
    _name = 'vat.agent'

    name = fields.Char(
        string='Name',
        required=True)
    matr = fields.Char(
        'Matricule',
        size=13,
        required=True)
    rcs = fields.Char(
        'Company Registry',
        size=7,
        required=True)
    vat = fields.Char(
        'Tax ID',
        size=10,
        required=True)

    @api.multi
    @api.constrains('matr')
    def check_matr(self):
        '''
        Constraint : lenght of Matricule must be 11 or 13
        '''
        for rec in self:
            if len(rec.matr) not in [11, 13]:
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
        for rec in self:
            if not rexp.match(rec.rcs):
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
        for rec in self:
            if not rexp.match(rec.vat):
                raise ValidationError(_(
                    'VAT number must begin with two uppercase letters '
                    'followed by 8 digits.'))


class VatReport(models.Model):
    '''
    Editable VAT report instance, abble to create a eCDF XML file
    '''
    _name = 'vat.report'
    _description = 'eCDF VAT Report'
    _inherit = "account.common.report"

    name = fields.Char(
        string='Name',
        required=True)
    description = fields.Char(
        string='Description')
    language = fields.Selection(
        string='Language',
        selection=[('FR', 'French'),
                   ('DE', 'German'),
                   ('EN', 'English')],
        required=True,
        default='FR'
    )
    type = fields.Selection(
        string='Declaration Type',
        selection=[('month', 'Monthly'),
                   ('year', 'Annual')],
        default='month',
        required=True)
    # Fiscal Year
    # (not before 2015, cfr. eCDF_file_v1.1-XML_documentation-02-FR.pdf)
    this_year = (datetime.date.today().year) + 1
    year = fields.Selection([(n, str(n)) for n in range(2015, this_year)],
                            string='Year',
                            required=True,
                            default=this_year - 1)
    # Month (monthly repports)
    period = fields.Selection(
        string="Period",
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
    agent_id = fields.Many2one(
        string='Agent',
        comodel_name='vat.agent',
        ondelete='restrict')
    regime = fields.Selection(
        string='Tax regime',
        selection=[('sales', 'Sales'),
                   ('revenues', 'Revenues')],
        required=True,
        default='sales')
    line_ids = fields.One2many(
        string='Lines',
        comodel_name='vat.report.line',
        inverse_name='report_id')

    # File name (computed)
    file_name = fields.Char(
        sring='File name',
        size=24,
        compute='_compute_file_name')

    @api.depends('company_id.ecdf_prefixe')
    @api.multi
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
        for rec in self:
            res = ""
            nbr = 1
            dtf = "X%Y%m%dT%H%M%S"
            prefixe = rec.company_id.ecdf_prefixe
            if not prefixe:
                prefixe = '000000'
            res = str("%s%s%02d" % (prefixe,
                                    datetime.datetime.now().strftime(dtf),
                                    nbr))
            rec.file_name = res

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
        for rec in self:
            matr = rec.company_id.l10n_lu_matricule
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
        for rec in self:
            rcs = rec.company_id.company_registry
            return rcs if rcs else 'NE'

    @api.multi
    def get_vat_declarer(self):
        '''
        :returns: VAT number of the company, 8 characters
        If no VAT number, default value 'NE' is returned
        '''
        for rec in self:
            vat = rec.company_id.vat
            if vat:
                if vat.startswith('LU'):
                    vat = vat[2:]
                return vat
            return 'NE'

    @api.multi
    def get_matr_agent(self):
        '''
        :returns: Agent matricule provided in the form
        If no agent matricule provided, the company one is returned
        '''
        for rec in self:
            if rec.agent_id:
                return rec.agent_id.matr
            else:
                return rec.get_matr_declarer()

    @api.multi
    def get_rcs_agent(self):
        '''
        :returns: RCS number (Numéro de registre de Commerce et des Sociétés)\
        provided in the form.
        If no RCS number has been provided, the company one is returned
        If no RCS number of the company, default value 'NE' is returned
        '''
        for rec in self:
            if rec.agent_id:
                if rec.agent_id.rcs:
                    return rec.agent_id.rcs
                else:
                    return 'NE'
            return rec.get_rcs_declarer()

    @api.multi
    def get_vat_agent(self):
        '''
        :returns: VAT number provided in the form. If no VAT number has been\
        provided, the VAT number of the company is returned.
        If no VAT number of the company, default value 'NE' is returned
        '''
        for rec in self:
            if rec.agent_id:
                vat = rec.agent_id.vat
                if vat:
                    if vat.startswith('LU'):
                        vat = vat[2:]
                    return vat
                else:
                    return 'NE'
            return rec.get_vat_declarer()

    @api.multi
    def get_language(self):
        '''
        :returns: the selected language in the form. Values can be :
                    - "FR" for french
                    - "DE" for german
                    - "EN" for english
        '''
        for rec in self:
            return rec.language

    @api.multi
    def get_mis_report_month(self):
        '''
        :returns: the mis report template for monthly vat declaration
        '''
        for rec in self:
            mis_env = rec.env['mis.report']
            mis_report_id = rec.env.ref("ecdf_vat_report.mis_report_vat").id
            mis_report = mis_env.search([('id', '=', mis_report_id)])
            return mis_report

    # Codes of lines that can be hidden if no move
    NO_REQUIRED = (
        "015", "016", "017", "019", "090", "092", "094", "095", "194", "195",
        "196", "226", "227", "228", "424", "435", "445", "454", "455", "456",
        "458", "459", "460", "461",)

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
        if (val is None or val is AccountingNone) and ecdf in self.NO_REQUIRED:
            return

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
        for rec in self:
            # Choice : Tax regime
            choice_regime_sales = etree.Element('Choice', id='204')
            choice_regime_revenues = etree.Element('Choice', id='205')
            # 1 : True, 0: False
            choice_regime_sales.text = '1' if regime == 'sales' else '0'
            choice_regime_revenues.text = '0' if regime == 'sales' else '1'

            # Append Tax regime fields
            form_data.append(choice_regime_sales)
            form_data.append(choice_regime_revenues)

            # Append numeric fields
            for line in rec.line_ids:
                rec._append_num_field(
                    form_data, str(line.code),
                    AccountingNone if line.isAccountingNone and
                    line.value == 0.0 else line.value,
                    comment=line.description)

    @api.multi
    def _get_vat_declaration(self, decl_type):
        '''
        Generates the declaration node of the xml file
        :param decl_type: Type of the declaration (monthly or annual)
        '''
        for rec in self:
            # Declaration node
            declaration = etree.Element('Declaration',
                                        type=decl_type,
                                        model='1',
                                        language=rec.get_language())
            # Year field
            year = etree.Element('Year')
            year.text = str(rec.year)
            # Period
            period = etree.Element('Period')
            period.text = str(rec.period)
            # Form Data
            form_data = etree.Element('FormData')

            # Generates data fields
            rec._append_vd_lines(form_data, rec.regime)

            # Append fields
            declaration.append(year)
            declaration.append(period)
            declaration.append(form_data)

            return declaration

    def _fetch_manual_lines(self, kpi_ids):
        '''
        Set a value to each manual lines
        :returns: Dictionary ecdf_code: value
        '''
        res = {}
        # first, set all manual codes to zero
        for kpi in kpi_ids:
            if kpi.name.startswith('ext_'):
                res[str('ecdf_%s' % kpi.name.split('_')[1])] = 0
        # then, set maual codes with user-added values
        for rec in self:
            for line in rec.line_ids:
                if not line.isAutomatic:
                    res[str('ecdf_%s' % line.code)] = line.value
        return res

    @api.multi
    def compute(self, mis_report, date_start, date_stop):
        '''
        Builds the "content" dictionary, with name, technical name and values\
        for each KPI expression
        :param mis_report: template MIS Builder of the report
        :param fiscal_year: fiscal year to compute
        :returns: computed content dictionary
        '''
        for rec in self:
            # Prepare AccountingExpressionProcessor
            aep = mis_report.prepare_aep(rec.company_id)

            # Prepare KPI Matrix
            kpi_matrix = mis_report.prepare_kpi_matrix()

            # Prepare the locals_dict
            locals_dict = {}
            locals_dict.update(mis_report.prepare_locals_dict())
            locals_dict.update(rec._fetch_manual_lines(mis_report.kpi_ids))

            # Populate the kpi_matrix
            mis_report.declare_and_compute_period(
                kpi_matrix,
                'col_key',
                'col_label',
                'col_description',
                aep,
                date_start, date_stop,
                rec.target_move,
                rec.company_id,
                locals_dict=locals_dict)

            # Get the columns of the kpi_matrix
            matrix_cols = kpi_matrix.iter_cols()

            # Dictionary of values by code
            kpi_values = {}

            # Iterate the matrix to fetch data
            for col in matrix_cols:
                for cell in col.iter_cell_tuples():
                    for c in cell:
                        kpi_values[c.row.kpi.name] = {'val': c.val}

            # prepare content
            content = []
            rows_by_kpi_name = {}
            for kpi in mis_report.kpi_ids:
                rows_by_kpi_name[kpi.name] = {
                    'kpi_name': kpi.description,
                    'kpi_technical_name': kpi.name,
                    'cols': [],
                }
                content.append(rows_by_kpi_name[kpi.name])

            # add kpi values
            for kpi_name in kpi_values:
                rows_by_kpi_name[kpi_name]['cols'].append(kpi_values[kpi_name])

        return {'content': content}

    @api.multi
    def _print_report(self, data):
        '''
        Generates the VAT declaration in XML format
        :param data: dictionary of values for the xml file
        '''
        for rec in self:
            # If no line has been generated, stop
            if not rec.line_ids:
                raise UserError(_('No line'))

            # Build XML
            # the default namespace(no prefix)
            nsmap = {None: "http://www.ctie.etat.lu/2011/ecdf"}
            # Root
            root = etree.Element("eCDFDeclarations", nsmap=nsmap)
            # File Reference
            file_reference = etree.Element('FileReference')
            file_reference.text = rec.file_name
            root.append(file_reference)
            # File Version
            file_version = etree.Element('eCDFFileVersion')
            file_version.text = rec.get_ecdf_file_version()
            root.append(file_version)
            # Interface
            interface = etree.Element('Interface')
            interface.text = rec.get_interface()
            root.append(interface)
            # Agent
            agent = etree.Element('Agent')
            matr_agent = etree.Element('MatrNbr')
            matr_agent.text = rec.get_matr_agent()
            rcs_agent = etree.Element('RCSNbr')
            rcs_agent.text = rec.get_rcs_agent()
            vat_agent = etree.Element('VATNbr')
            vat_agent.text = rec.get_vat_agent()
            agent.append(matr_agent)
            agent.append(rcs_agent)
            agent.append(vat_agent)
            root.append(agent)
            # Declarations
            declarations = etree.Element('Declarations')
            declarer = etree.Element('Declarer')
            matr_declarer = etree.Element('MatrNbr')
            matr_declarer.text = rec.get_matr_declarer()
            rcs_declarer = etree.Element('RCSNbr')
            rcs_declarer.text = rec.get_rcs_declarer()
            vat_declarer = etree.Element('VATNbr')
            vat_declarer.text = rec.get_vat_declarer()
            declarer.append(matr_declarer)
            declarer.append(rcs_declarer)
            declarer.append(vat_declarer)
            # Declaration lines
            decl_type = 'TVA_DECM' if rec.type == 'month' else 'TVA_DECA'
            declarer.append(rec._get_vat_declaration(decl_type))
            # Declarer
            declarations.append(declarer)
            root.append(declarations)

            # Write the xml
            xml = etree.tostring(root, encoding='UTF-8', xml_declaration=True)
            # Update the dictionary
            data['form'].update({'xml': xml})

            # set filename
            data['form']['filename'] = rec.file_name

            # Launch xml file download
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'create.xml',
                'name': data['form']['filename'],
                'datas': data,
            }

    @api.multi
    def clear_lines(self):
        '''
        Erase all lines of the current report
        '''
        for rec in self:
            if not rec.line_ids:
                return
            for line in rec.line_ids:
                line.isAutomatic = False
            rec.line_ids = False

    @api.multi
    def generate_lines(self):
        '''
        Generate the automatic lines of the report
        Non automatic lines are lost
        '''
        for rec in self:
            if rec.type != 'month':
                raise UserError(_(
                    'Only month declaration is not available'))

            # Clear lines
            rec.clear_lines()

            # Initialize the period to compute
            nb_days = calendar.monthrange(rec.year, rec.period)[1]
            date_start = datetime.date(rec.year, rec.period, 1)
            date_stop = datetime.date(rec.year, rec.period, nb_days)

            # Get mis_report for monthly VAT declaration
            mis_report = rec.get_mis_report_month()
            # If the MIS template has not been found
            if not mis_report or not len(mis_report):
                raise UserError(_(
                    'No MIS Template for VAT declaration found.'))

            # Compute values
            mis_data = rec.compute(mis_report, date_start, date_stop)

            # Regular expression to catch effective ecdf codes
            exp_ecdf = r"""^ecdf\_(?P<ecdf_code>\d{3})"""
            rexp_ecdf = re.compile(exp_ecdf, re.X)
            exp_ext = r"""^ext\_(?P<ecdf_code>\d{3})"""
            rexp_ext = re.compile(exp_ext, re.X)

            # Create new lines
            for line in mis_data['content']:
                lm_ecdf = rexp_ecdf.match(line['kpi_technical_name'])
                lm_ext = rexp_ext.match(line['kpi_technical_name'])
                if not lm_ecdf and not lm_ext:
                    continue
                rec.env['vat.report.line'].create({
                    'description': line['kpi_name'],
                    'code': lm_ecdf.group('ecdf_code') if lm_ecdf
                    else lm_ext.group('ecdf_code'),
                    'value': line['cols'][0]['val'],
                    'isAccountingNone': True if line['cols'][0]['val']
                    is AccountingNone else False,
                    'isAutomatic': True if lm_ecdf else False,
                    'report_id': rec.id})

    @api.multi
    def refresh_lines(self):
        '''
        Refreshes automatic lines of the current report with computed values
        User-added lines are kept
        '''
        for rec in self:
            # If no line, stop
            if not rec.line_ids:
                return

            if rec.type != 'month':
                raise UserError(_(
                    'Only month declaration is not available'))

            # Initialize the period to compute
            nb_days = calendar.monthrange(rec.year, rec.period)[1]
            date_start = datetime.date(rec.year, rec.period, 1)
            date_stop = datetime.date(rec.year, rec.period, nb_days)

            # Get mis_report for monthly VAT declaration
            mis_report = rec.get_mis_report_month()
            # If the MIS template has not been found
            if not mis_report or not len(mis_report):
                raise UserError(_(
                    'No MIS Template for VAT declaration found.'))

            # Compute values
            mis_data = rec.compute(mis_report, date_start, date_stop)

            # Regular expression to catch effective ecdf codes
            exp_ecdf = r"""^ecdf\_(?P<ecdf_code>\d{3})"""
            rexp_ecdf = re.compile(exp_ecdf, re.X)

            # Clear computed lines
            for line in rec.line_ids:
                if line.isAutomatic:
                    line.isAutomatic = False
                    line.report_id = False

            # Create new lines
            for line in mis_data['content']:
                lm_ecdf = rexp_ecdf.match(line['kpi_technical_name'])
                if lm_ecdf:  # Read only lines
                    rec.env['vat.report.line'].create({
                        'description': line['kpi_name'],
                        'code': lm_ecdf.group('ecdf_code'),
                        'value': line['cols'][0]['val'],
                        'isAccountingNone': True if line['cols'][0]['val']
                        is AccountingNone else False,
                        'isAutomatic': True,
                        'report_id': rec.id})


class VatReportLine(models.Model):
    '''
    Line of a VAT report
    Values can be computed and are editable
    '''
    _name = 'vat.report.line'
    _order = 'sequence, id'

    # Line description
    description = fields.Char(
        string='Description',
        required=True)
    # eCDF code : code of a computed line is read only (view)
    code = fields.Char(
        string='eCDF code',
        required=True)
    # (Computed) value
    value = fields.Float(
        string='Value',
        required=True)
    # Flag : true if value is from AccountingNone
    isAccountingNone = fields.Boolean(
        default=False)
    # Sequence number
    sequence = fields.Integer(
        string='Sequence')
    # Flag : true if computed value, false otherwise
    isAutomatic = fields.Boolean(
        string='Automatic value',
        default=False,
        readonly=True)
    # VAT report
    report_id = fields.Many2one(
        string='Report',
        comodel_name='vat.report',
        ondelete='cascade')

    @api.multi
    @api.constrains('code')
    def check_code(self):
        '''
        Check if the line's code is unique
        '''
        for rec in self:
            seen_codes = set()
            duplicates_codes = []
            for line in rec.report_id.line_ids:
                if line.code not in seen_codes:
                    seen_codes.add(line.code)
                else:
                    duplicates_codes.append(line.code)
            if duplicates_codes:
                raise UserError(_(
                    'Some lines are not unique ! Please check and remove '
                    'duplicates. Duplicated codes : '
                    '%s' % ', '.join(duplicates_codes)))

    @api.multi
    def unlink(self):
        '''
        Overriding of deletion method
        Automatic lines cannot be deleted
        '''
        for rec in self:
            if rec.isAutomatic:
                raise UserError(_('You cannot delete automatic lines.'))
            return models.Model.unlink(self)


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
        # reparse only to have line numbers in error messages?
        xml_to_validate = StringIO(xml)
        parse_result = etree.parse(xml_to_validate)
        if not xmlschema.validate(parse_result):
            error = xmlschema.error_log[0]
            raise UserError(
                _('The generated XML file does not fit the required schema !'),
                error.message)
        return (xml_to_validate.getvalue(), 'xml')

CreateXML('report.create.xml')
