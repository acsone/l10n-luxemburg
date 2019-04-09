# -*- coding: utf-8 -*-
# Copyright 2016-2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re as re

from lxml import etree
from openerp.addons.mis_builder.models.accounting_none import AccountingNone
from openerp.exceptions import ValidationError, Warning as UserError
from openerp.tests import SavepointCase


class TestEcdfVatReport(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestEcdfVatReport, cls).setUpClass()

        # ENVIRONMENTS
        cls.vat_report = cls.env['vat.report']
        cls.vat_report_line = cls.env['vat.report.line']
        cls.res_company = cls.env['res.company']

        # INSTANCES
        # Instance: company
        cls.company = cls.env.ref('base.main_company')

        # Instance: VAT agent
        cls.agent = cls.env.ref('ecdf_vat_report.demo_vat_agent')

        # VAT report instance
        cls.report = cls.env.ref('ecdf_vat_report.demo_vat_report')

        # VAT report line instance (manual) | Not a valid eCDF VAT code
        cls.line1 = cls.vat_report_line.create({
            'description': 'Vat report line 1',
            'code': '101',
            'value': 11.1,
            'report_id': cls.report.id})

        # VAT report line instance (automatic) | Not a valid eCDF VAT code
        cls.line2 = cls.vat_report_line.create({
            'description': 'Vat report line 2',
            'code': '102',
            'value': 22.2,
            'isAutomatic': True,
            'report_id': cls.report.id})

        # VAT report line instance (manual) | Valid eCDF VAT code
        cls.line3 = cls.vat_report_line.create({
            'description': 'Vat report line 3',
            'code': '454',
            'value': 33.3,
            'report_id': cls.report.id})

        # VAT report line instance (automatic) | Valid eCDF VAT code
        cls.line4 = cls.vat_report_line.create({
            'description': 'Vat report line 4',
            'code': '457',
            'value': 44.4,
            'isAutomatic': True,
            'report_id': cls.report.id})

    def test_check_matr(self):
        '''
        Matricule must be 11 or 13 characters long
        '''
        # Matricule too short (10)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.agent.matr = '1111111111'

        # Matricule's length not 11 nor 13 characters (12)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.agent.matr = '111111111112'

        # Matricule OK
        try:
            self.agent.matr = '11111111111'
        except ValidationError:
            self.fail()

    def test_check_rcs(self):
        '''
        RCS number must begin with an uppercase letter\
        followed by 2 to 6 digits. The first digit must not be 0
        '''
        # RCS doesn't begin with an upercase letter (lowercase letter instead)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.agent.rcs = 'l123456'

        # First digit is a zero
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.agent.rcs = 'L0234567'

        # RCS too short
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.agent.rcs = 'L1'

        # RCS dont begin with a letter
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.agent.rcs = '1123456'

        # RCS OK
        try:
            self.agent.rcs = 'L123456'
        except ValidationError:
            self.fail()

    def test_check_vat(self):
        '''
        VAT number must begin with two uppercase letters followed by 8 digits.
        '''
        # VAT doesn't begin with two upercase letters (lowercase instead)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.agent.vat = 'lu12345678'

        # VAT doesn't begin with two letters
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.agent.vat = '0912345678'

        # VAT too short (missing digits)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.agent.vat = 'LU1234567'

        # VAT OK
        try:
            self.agent.vat = 'LU12345678'
        except ValidationError:
            self.fail()

    # VAT REPORT

    def test_compute_file_name(self):
        '''
        File name must match the following pattern : 000000XyyyymmddThhmmssNN
        '''
        # Regular expression of the expected file name
        exp = r"""^\d{6}X\d{8}T\d{8}$"""
        rexp = re.compile(exp, re.X)

        self.report._compute_file_name()

        self.assertIsNotNone(rexp.match(self.report.file_name))

    def test_onchange_type(self):
        '''
        onchange_type set the report.period to 1
        '''
        self.report._onchange_type()
        self.assertEqual(self.report.period, 1)

    def test_get_ecdf_file_version(self):
        report_file_version = self.report.get_ecdf_file_version()
        file_version = '1.1'

        self.assertEqual(report_file_version, file_version)

    def test_get_interface(self):
        report_interface = self.report.get_interface()
        interface = 'CODL7'

        self.assertEqual(report_interface, interface)

    def test_get_language(self):
        language = self.report.get_language()
        expected = 'FR'

        self.assertEqual(language, expected)

    # GETTERS DECLARER

    def test_get_matr_declarer(self):
        '''
        Test of bordeline cases of get_matr_declarer
        '''
        # With a matricule set to the company
        declarer_matr = self.report.get_matr_declarer()
        expected = '0000000000000'
        self.assertEqual(declarer_matr, expected)

        # With no matricule set to the company
        self.company.l10n_lu_matricule = False
        with self.assertRaises(UserError), self.cr.savepoint():
            declarer_matr = self.report.get_matr_declarer()

    def test_get_rcs_declarer(self):
        '''
        Test of bordeline cases of get_rcs_declarer
        '''
        # With a rcs number set to the company
        declarer_rcs = self.report.get_rcs_declarer()
        expected = 'L654321'
        self.assertEqual(declarer_rcs, expected)

        # With no rcs number set to the company
        self.company.company_registry = False
        declarer_rcs = self.report.get_rcs_declarer()
        expected = 'NE'
        self.assertEqual(declarer_rcs, expected)

    def test_get_vat_declarer(self):
        '''
        Test of bordeline cases of get_vat_declarer
        '''
        # With a vat number set to the company
        declarer_vat = self.report.get_vat_declarer()
        expected = '12345613'
        self.assertEqual(declarer_vat, expected)

        # With no vat number set to the company
        self.company.vat = False
        declarer_vat = self.report.get_vat_declarer()
        expected = 'NE'
        self.assertEqual(declarer_vat, expected)

    # GETTERS AGENT

    def test_get_matr_agent(self):
        '''
        Test of bordeline cases of get_matr_agent
        '''
        # Report has an agent set
        report_matr = self.report.get_matr_agent()
        expected = '1111111111111'
        self.assertEqual(report_matr, expected)

        # Report has no agent set
        self.report.agent_id = False
        report_matr = self.report.get_matr_agent()
        # The expected matricule is the company one
        expected = '0000000000000'
        self.assertEqual(report_matr, expected)

    def test_get_rcs_agent(self):
        '''
        Test of bordeline cases of get_rcs_agent
        '''
        # Report has an agent set
        report_rcs = self.report.get_rcs_agent()
        expected = 'L123456'
        self.assertEqual(report_rcs, expected)

        # Report has no agent set
        self.report.agent_id = False
        report_rcs = self.report.get_rcs_agent()
        # The expected rcs is the company one
        expected = 'L654321'
        self.assertEqual(report_rcs, expected)

    def test_get_vat_agent(self):
        '''
        Test of bordeline cases of get_vat_agent
        '''
        # Report has an agent set
        report_vat = self.report.get_vat_agent()
        expected = '12345678'
        self.assertEqual(report_vat, expected)

        # Report has no agent set
        self.report.agent_id = False
        report_vat = self.report.get_vat_agent()
        # The expected VAT is the company one
        expected = '12345613'
        self.assertEqual(report_vat, expected)

    def test_append_num_field(self):
        '''
        Test of bordeline cases of the method append_num_field
        '''
        # Initial data : code not in NO_REQUIRED
        ecdf = '123'
        comment = "A comment"

        # Test with valid float value
        element = etree.Element('FormData')
        val = 5.5
        self.report._append_num_field(element, ecdf, val, comment)
        expected = '<FormData><!--A comment--><NumericField id="123">\
5,50</NumericField></FormData>'
        self.assertEqual(etree.tostring(element), expected)

        # Test with None value, code not in NO_REQUIRED
        element = etree.Element('FormData')
        val = None
        self.report._append_num_field(element, ecdf, val, comment)
        expected = '<FormData><!--A comment--><NumericField id="123">0,00\
</NumericField></FormData>'
        self.assertEqual(etree.tostring(element), expected)

        # Test with AccountingNone value, code not in NO_REQUIRED
        element = etree.Element('FormData')
        val = AccountingNone
        self.report._append_num_field(element, ecdf, val, comment)
        expected = '<FormData><!--A comment--><NumericField id="123">0,00\
</NumericField></FormData>'
        self.assertEqual(etree.tostring(element), expected)

        # Data : code in NO_REQUIRED
        ecdf = '015'

        # Test with None value, code in NO_REQUIRED
        element = etree.Element('FormData')
        val = None
        self.report._append_num_field(element, ecdf, val, comment)
        expected = '<FormData/>'
        self.assertEqual(etree.tostring(element), expected)

        # Test with AccountingNone value, code in NO_REQUIRED
        element = etree.Element('FormData')
        val = AccountingNone
        self.report._append_num_field(element, ecdf, val, comment)
        expected = '<FormData/>'
        self.assertEqual(etree.tostring(element), expected)

        # Test without comment
        element = etree.Element('FormData')
        val = 5.5
        self.report._append_num_field(element, ecdf, val)
        expected = '<FormData><NumericField id="015">5,50</NumericField>\
</FormData>'
        self.assertEqual(etree.tostring(element), expected)

    def test_fetch_manual_lines(self):
        '''
        Test _fetch_manual_lines : check the returned dictionary
        '''
        mis_template = self.report.get_mis_report_month()
        manual_lines = self.report._fetch_manual_lines(mis_template.kpi_ids)

        try:
            manual_value = manual_lines['ecdf_101']
            self.assertEqual(manual_value, 11.1)
        except KeyError:
            self.fail()

    def test_clear_lines(self):
        '''
        Delete report's lines
        '''
        self.report.clear_lines()
        if len(self.report.line_ids) > 0:
            self.fail()

    def test_generate_lines(self):
        '''
        Lines generation is not available for annual declaration
        '''
        self.report.generate_lines()
        self.assertEqual(len(self.report.line_ids), 157)

        self.report.type = 'year'
        with self.assertRaises(UserError), self.cr.savepoint():
            self.report.generate_lines()

    def test_refresh_lines(self):
        '''
        Lines refresh is not available for annual declaration
        '''
        self.report.generate_lines()
        self.report.refresh_lines()
        self.assertEqual(len(self.report.line_ids), 157)

        self.report.type = 'year'
        with self.assertRaises(UserError), self.cr.savepoint():
            self.report.generate_lines()

    def test_print_report(self):
        '''
        Main test : print report
        '''
        self.report.generate_lines()
        self.report._print_report({'form': {}})

        # Report with no line
        self.report.clear_lines()
        with self.assertRaises(UserError), self.cr.savepoint():
            self.report._print_report({'form': {}})

    # VAT REPORT LINE

    def test_check_code(self):
        '''
        A line's code must be unique in the VAT report
        '''
        # Try to insert a line with a already existing code in the VAT report
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.vat_report_line.create({
                'description': 'Vat report line 1',
                'code': '101',
                'value': 11.1,
                'report_id': self.report.id})

        # Try to insert a line with a new code in the VAT report
        self.vat_report_line.create({
            'description': 'Vat report line 1',
            'code': '109',
            'value': 11.1,
            'report_id': self.report.id})

    def test_unlink(self):
        '''
        Automatic lines cannot be deleted
        '''
        # Try to delete an automatic line
        with self.assertRaises(UserError), self.cr.savepoint():
            self.line2.unlink()

        # Try to delete a manual line
        self.line1.unlink()
