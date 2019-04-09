# -*- coding: utf-8 -*-
# Copyright 2016-2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class res_company(models.Model):
    _inherit = "res.company"
    ecdf_prefixe = fields.Char("eCDF Prefix", size=6)
