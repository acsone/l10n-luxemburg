# -*- coding: utf-8 -*-

from openerp.tests import common
# from lxml import etree
# from datetime import datetime
import re as re
from openerp.exceptions import ValidationError


class TestEcdfVatReport(common.TransactionCase):
    def setUp(self):
        super(TestEcdfVatReport, self).setUp()

        # Environements
        self.vat_agent = self.env['vat.agent']
        self.vat_report = self.env['vat.report']
        self.vat_report_line = self.env['vat.report.line']
        self.res_company = self.env['res.company']

        # Company instance
        self.company = self.env.ref('base.main_company')
        self.company.l10n_lu_matricule = '0000000000000'
        self.company.company_registry = 'L654321'
        self.company.vat = 'LU12345613'

        # VAT agent instance
        self.agent = self.vat_agent.create({
            'name': 'Test Agent',
            'matr': '1111111111111',
            'rcs': 'L123456',
            'vat': 'LU12345678'})

        # VAT report instance
        self.report = self.vat_report.create({
            'name': 'Test Vat Report',
            'description': 'A VAT report for unit tests',
            'language': 'FR',
            'type': 'month',
            'year': 2016,
            'period': 3,
            'agent_id': self.agent.id,
            'regime': 'sales'})

        # VAT report line instance
        self.line1 = self.vat_report_line.create({
            'description': 'Vat report line 1',
            'code': '101',
            'value': 11.1,
            'report_id': self.report.id})

    # VAT AGENT

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

    def test_get_matr_agent(self):
        report_matr = self.report.get_matr_agent()
        expected = '1111111111111'

        self.assertEqual(report_matr, expected)

    def test_get_rcs_agent(self):
        report_rcs = self.report.get_rcs_agent()
        expected = 'L123456'

        self.assertEqual(report_rcs, expected)

    def test_get_vat_agent(self):
        report_vat = self.report.get_vat_agent()
        expected = '12345678'

        self.assertEqual(report_vat, expected)
    
    # VAT REPORT LINE
