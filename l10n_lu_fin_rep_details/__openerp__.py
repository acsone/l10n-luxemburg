# -*- coding: utf-8 -*-
##############################################################################
#
#    Authors: Laetitia Gangloff
#    Copyright (c) 2014 Acsone SA/NV (http://www.acsone.eu)
#    All Rights Reserved
#
#    WARNING: This program as such is intended to be used by professional
#    programmers who take the whole responsibility of assessing all potential
#    consequences resulting from its eventual inadequacies and bugs.
#    End users who are looking for a ready-to-use solution with commercial
#    guarantees and support are strongly advised to contact a Free Software
#    Service Company.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "Luxembourg - Accounting - Financial Report Details",
    "version": "0.1",
    "author": "ACSONE SA/NV",
    "license": "GPL-3",
    "category": "Accounting & Finance",
    "website": "http://acsone.eu",
    "depends": ["l10n_lu_ext"],
    "module": "",
    "description": """
    Luxemburg financial report details
    
    Display account details in the following Luxemburg financial reports
    * balance sheet
    * abbreviated balance sheet
    * profit and loss
    * abbreviated profit and loss
""",
    "data": [
        "account_financial_report.xml",
        "account_financial_report_abr.xml",
    ],
    "active": False,
    "installable": True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
