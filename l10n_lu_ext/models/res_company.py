# -*- coding: utf-8 -*-
# Copyright 2016-2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields


class ResCompany(models.Model):

    _inherit = "res.company"

    l10n_lu_matricule = fields.Char(
        string='Luxembourg Matricule', size=13,
        help='Identification Number delivered by the Luxembourg authorities '
             'as soon as the company is registered')
