# -*- coding: utf-8 -*-

from openerp.tests import common
# from lxml import etree
# from datetime import datetime
# import re as re
from openerp.exceptions import ValidationError


class TestEcdfVatReport(common.TransactionCase):
    def setUp(self):
        super(TestEcdfVatReport, self).setUp()

        self.vat_agent = self.env['vat.agent']
        self.vat_report = self.env['vat.report']
        self.vat_report_line = self.env['vat.report.line']

        self.agent = self.vat_agent.create({
            'name': 'Test Agent',
            'matr': '0000000000000',
            'rcs': 'L123456',
            'vat': 'LU12345678'})

        self.report = self.vat_report.create({
            'name': 'Test report',
            'description': 'A report for unit tests...',
            'language': 'FR',
            'type': 'month',
            'year': 2016,
            'period': 3,
            'agent_id': self.agent.id,
            'regime': 'sales'})

        self.line1 = self.vat_report_line.create({
            'description': 'Test Line 1',
            'code': '101',
            'value': 11.1,
            'report_id': self.report.id})

        self.line2 = self.vat_report_line.create({
            'description': 'Test Line 2',
            'code': '102',
            'value': 22.2,
            'isAutomatic': True,
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

        # No matricule
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.agent.matr = None

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

        # No RCS
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.agent.rcs = None

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

        # No VAT
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.agent.vat = None

    # VAT report # VAT REPORT LINE
