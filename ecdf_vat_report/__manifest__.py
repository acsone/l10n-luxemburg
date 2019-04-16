# -*- coding: utf-8 -*-
# Copyright 2016-2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'eCDF VAT Report',
    'description': """
        This modules allows to make VAT reports in XML format, ready for eCDF.
    """,
    'version': '10.0.0.0.1',
    'licence': 'AGPL-3',
    'author': 'ACSONE SA/NV, Odoo Community Association (OCA)',
    'website': 'www.acsone.eu',
    'depends': [
        'l10n_lu_ext',
        'mis_builder'
    ],
    'data': [
        'views/ecdf_vat_report.xml',
        'views/res_company.xml',

        'data/mis_report.xml',
        'data/mis_style.xml',
        'data/mis_sub_kpi.xml',
        'data/ecdf.manual.data.csv',
        'data/mis.report.kpi.csv',
        'data/mis.report.kpi.expression.csv',

        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/demo_ecdf_vat_report.xml',
    ]
}
