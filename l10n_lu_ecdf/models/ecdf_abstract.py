# -*- coding: utf-8 -*-
# Copyright 2016-2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from datetime import datetime
from lxml import etree
import base64
from StringIO import StringIO

from odoo import models, fields, api, _, tools
from odoo.exceptions import Warning as UserError
from odoo.addons.mis_builder.models.accounting_none import AccountingNone


class EcdfAbstractReport(models.AbstractModel):
    '''
    Abstract eCDF report
    '''
    _name = 'ecdf.abstract'
    _description = 'eCDF Abstract Report'

    name = fields.Char(string='Name')
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 readonly=True,
                                 default=lambda self: self.env.user.company_id)
    language = fields.Selection(
        (('FR', 'FR'), ('DE', 'DE'), ('EN', 'EN')),
        string='Language',
        required=True,
        default='EN',
        help='Specify the language in the eCDF XML report.\
         This will not change the display Language.')
    agent_id = fields.Many2one(
        string='Agent',
        comodel_name='ecdf.agent',
        help='You can use the Matricule, VAT and Company\
         Registry from the company itself or create an Agent to\
         specify new ones.')
    matr = fields.Char(string='Matricule',
                       related="agent_id.matr",
                       readonly=True)
    rcs = fields.Char(string='Company Registry',
                      related="agent_id.rcs",
                      readonly=True)
    vat = fields.Char(string='Tax ID',
                      related="agent_id.vat",
                      readonly=True)
    file_name = fields.Char(sring='File name',
                            size=24,
                            compute='_compute_file_name')
    xml_file = fields.Binary('XML File', readonly=True)

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
                                    datetime.now().strftime(dtf),
                                    nbr))
            report.file_name = res

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
        value = round(val, 2)
        if comment:
            element.append(etree.Comment(comment))
        child = etree.Element('NumericField', id=ecdf)
        child.text = ("%.2f" % value).replace('.', ',')
        element.append(child)

    def _get_xml_declarations(self, declarer):
        return etree.Element('')

    @api.multi
    def print_xml(self):
        '''
        Generates the VAT declaration in XML format
        :param data: dictionary of values for the xml file
        '''
        self.ensure_one()
        nsmap = {None: "http://www.ctie.etat.lu/2011/ecdf"}
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

        # Declarations
        declarations = self._get_xml_declarations(declarer)
        root.append(declarations)
        # Write the xml
        xml = etree.tostring(root, encoding='UTF-8', xml_declaration=True)
        # Validate the generated XML schema
        xsd = tools.file_open('l10n_lu_ecdf/xsd/eCDF_file_v1.1.xsd')
        xmlschema_doc = etree.parse(xsd)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        xml_to_validate = StringIO(xml)
        parse_result = etree.parse(xml_to_validate)
        # Validation
        if xmlschema.validate(parse_result):
            self.xml_file = base64.encodestring(xml)
            return {
                'type': 'ir.actions.report.xml',
                'report_type': 'controller',
                'report_file':
                    '/web/content/%s/%s/xml_file/%s.xml?download=true'
                    % (self._name, str(self.id), self.file_name),
            }
        else:
            error = xmlschema.error_log[0]
            raise UserError(
                _('The generated file doesn\'t fit the required schema !'),
                error.message)
