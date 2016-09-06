# -*- coding: utf-8 -*-
# Copyright 2016 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'eCDF VAT Report',
    'description': """
        This modules allows to make VAT reports in XML format, ready for eCDF.
    """,
    'version': '9.0.1.0.0',
    'licence': 'AGPL-3',
    'author': 'ACSONE SA/NV, Odoo Community Association (OCA)',
    'website': 'http://acsone.eu',
    'website': 'www.acsone.eu',
    'depends': [
        'l10n_lu_ext',
        'mis_builder'
    ],
    'data': [
        'views/ecdf_vat_report.xml',
        'views/res_company.xml',
        'data/mis_report_vat.xml',
        'security/vat_agent.xml',
        'security/vat_report_line.xml',
        'security/vat_report.xml',
    ],
    'demo': [
        'demo/demo_ecdf_vat_report.xml',
    ]
}
