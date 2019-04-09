# -*- coding: utf-8 -*-
# Copyright 2016-2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Luxembourg - Accounting - Extension",
    "version": "10.0.0.0.1",
    "author": "ACSONE SA/NV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Accounting & Finance",
    "website": "http://acsone.eu",
    "depends": ["l10n_lu"],
    "description": """
    Improvements to the official l10n_lu.

    * New menus: Balance Sheet and Profit and Loss in
      Accounting > Reporting > Legal reports > Luxembourg
""",
    "data": [
        "account_financial_report_view.xml",
        "views/res_company.xml",
    ],
    "active": False,
    'installable': True
}
