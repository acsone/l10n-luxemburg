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
from cStringIO import StringIO
from lxml import etree
import logging
from datetime import date
import pytz

from openerp import models, fields, api, tools, release, _
from streamingxmlwriter import StreamingXMLWriter


_logger = logging.getLogger(__name__)


def write_mandatory(element, string, writer):
    with writer.element(element):
        writer.characters(string or "N/A")


def write_optional(element, string, writer):
    if string:
        with writer.element(element):
            writer.characters(string)


def write_company_faia(company, writer):
    write_mandatory("RegistrationNumber", company.company_registry, writer)
    write_mandatory("Name", company.name, writer)
    with writer.element("Address"):
        write_address_faia(company.partner_id, writer)
    write_optional("TaxID", company.vat, writer)
    with writer.element("Contact"):
        write_contact_faia(company.partner_id, writer)


def write_address_faia(partner, writer):
    write_mandatory("City", partner.city, writer)
    write_mandatory("PostalCode", partner.zip, writer)


def write_contact_faia(partner, writer):
    with writer.element("ContactPerson"):
        write_person_faia(partner, writer)
    write_mandatory("Telephone", partner.phone, writer)
    write_optional("Fax", partner.fax, writer)
    write_optional("Email", partner.email, writer)
    write_optional("Website", partner.website, writer)


def write_person_faia(partner, writer):
    write_mandatory("FirstName", False, writer)
    write_mandatory("LastName", partner.name, writer)


class account_fiscalyear(models.Model):
    _inherit = "account.fiscalyear"

    @api.one
    def get_faia_data(self):
        s = StringIO()
        date_now = date.today().isoformat()
        current_company = self.env.user.company_id
        with StreamingXMLWriter(s) as writer:
            with writer.element("AuditFile"):
                with writer.element("Header"):
                    write_mandatory("AuditFileVersion", "2.01B", writer)
                    write_mandatory("AuditFileCountry", "LU", writer)
                    write_mandatory("AuditFileDateCreated", date_now, writer)
                    # Name of the software company whose product
                    # created the FAIA.
                    write_mandatory("SoftwareCompanyName",
                                    "ACSONE SA/NV", writer)
                    write_mandatory("SoftwareID", release.product_name, writer)
                    write_mandatory("SoftwareVersion", release.version, writer)
                    with writer.element("Company"):
                        write_company_faia(current_company, writer)
                    write_mandatory("DefaultCurrencyCode",
                                    current_company.currency_id.name, writer)
                    write_mandatory("TaxAccountingBasis", "TODO", writer)

        # validate the generated XML schema
        xsd = tools.file_open('l10n_lu_export_faia/'
                              'FAIA_v_2.01_reduced_version_B.xsd')
        xmlschema_doc = etree.parse(xsd)
        xmlschema = etree.XMLSchema(xmlschema_doc)

        parse_result = etree.parse(StringIO(s.getvalue()))

        if xmlschema.validate(parse_result):
            return s.getvalue()
        else:
            _logger.error('The generated XML file does not fit '
                          'the required schema !')
            _logger.error(tools.ustr(xmlschema.error_log.last_error))
            error = xmlschema.error_log[0]
            raise models.except_orm(_('The generated XML file does not fit the'
                                      ' required schema !'), error.message)
        return s.getvalue()