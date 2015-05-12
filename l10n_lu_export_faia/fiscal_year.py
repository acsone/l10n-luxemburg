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
        writer.characters(str(string) or "N/A")


def write_optional(element, string, writer):
    if string:
        with writer.element(element):
            writer.characters(str(string))


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


def write_account_faia(account, writer):
    write_mandatory("AccountID", account.code, writer)
    write_mandatory("AccountDescription", account.name, writer)
    # The type need to be improve
    # Should be either Asset/Liability/Sale/Expense
    write_mandatory("AccountType", account.user_type.name, writer)

    write_mandatory("OpeningDebitBalance", "0.0", writer)
    write_mandatory("ClosingDebitBalance", "0.0", writer)


def write_journal_faia(journal, account_period_ids, writer):
    write_mandatory("JournalID", journal.code, writer)
    write_mandatory("Description", journal.name, writer)
    # Type is 9 char max
    write_mandatory("Type", journal.type[:9], writer)
    account_moves = journal.env['account.move'].search(
        [('journal_id', '=', journal.id),
         ('period_id', 'in', account_period_ids)])
    for account_move in account_moves:
        with writer.element("Transaction"):
            write_account_move_faia(account_move, writer)


def write_account_move_faia(move, writer):
    write_mandatory("TransactionID", move.id, writer)
    write_mandatory("Period", move.period_id.id, writer)
    period_year = fields.Date.from_string(move.period_id.date_start).year
    write_mandatory("PeriodYear", period_year, writer)
    date = fields.Date.from_string(move.date).isoformat()
    write_mandatory("TransactionDate", date, writer)
    write_mandatory("Description", move.name, writer)
    create_date = fields.Date.from_string(move.create_date).isoformat()
    write_mandatory("SystemEntryDate", date, writer)
    # No posting date in odoo, so use the create_date instead
    write_mandatory("GLPostingDate", create_date, writer)
    for move_line in move.line_id:
        with writer.element("Line"):
            write_account_move_line_faia(move_line, writer)


def write_account_move_line_faia(move_line, writer):
    write_mandatory("RecordID", move_line.id, writer)
    write_mandatory("AccountID", move_line.account_id.code, writer)
    write_mandatory("Description", move_line.name, writer)
    if move_line.debit:
        with writer.element("DebitAmount"):
            write_amount_faia(move_line.debit, writer)
    else:
        with writer.element("CreditAmount"):
            write_amount_faia(move_line.credit, writer)


def write_amount_faia(amount, writer):
    write_mandatory("Amount", amount, writer)


class account_fiscalyear(models.Model):
    _inherit = "account.fiscalyear"

    @api.one
    def get_faia_data(self):
        s = StringIO()
        date_now = date.today().isoformat()
        current_company = self.env.user.company_id
        accounts = self.env['account.account'].search(
            [('company_id', '=', current_company.id)])
        journals = self.env['account.journal'].search(
            [('company_id', '=', current_company.id)])

        account_period_ids = [p.id for p in self.period_ids]

        account_moves_count = self.env['account.move'].search_count([
            ('period_id', 'in', account_period_ids)])

        self.env.cr.execute("""
            SELECT 
                SUM(credit),
                SUM(debit)
            FROM account_move_line
            WHERE
                period_id in %s
        """, (tuple(account_period_ids),))

        total_credit, total_debit = self.env.cr.fetchall()[0]

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
                with writer.element("MasterFiles"):
                    with writer.element("GeneralLedgerAccounts"):
                        for account in accounts:
                            with writer.element("Account"):
                                write_account_faia(account, writer)
                with writer.element("GeneralLedgerEntries"):
                    write_mandatory("NumberOfEntries", account_moves_count, writer)
                    write_mandatory("TotalDebit", total_debit, writer)
                    write_mandatory("TotalCredit", total_credit, writer)
                    for journal in journals:
                        with writer.element("Journal"):
                            write_journal_faia(journal, account_period_ids, writer)

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
