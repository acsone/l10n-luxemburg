# -*- coding: utf-8 -*-
{
    'name': 'eCDF VAT Report',
    'version': '9.0.1.0.0',
    'category': 'Reporting',
    'summary': """
        Build eCDF VAT reports
    """,
    'author': 'ACSONE SA/NV',
    'licence': 'AGPL-3',
    'website': 'http://acsone.eu',
    'depends': ["l10n_lu_ext"],
    'data': [
        'views/ecdf_vat_report.xml',
        'views/res_company.xml',
        'data/mis_report_vat.xml',
    ],
    'installable': True,
    'application': True,
}
