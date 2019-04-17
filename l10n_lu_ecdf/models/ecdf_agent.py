# -*- coding: utf-8 -*-
# Copyright 2016-2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError


class VatAgent(models.Model):
    '''
    Declarer agent
    '''
    _name = 'ecdf.agent'

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
