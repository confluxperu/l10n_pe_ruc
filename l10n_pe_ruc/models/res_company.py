#######################################################################################
#
#    Copyright (C) 2019-TODAY Obox.
#    Author      :  Obox del Peru S.A.C. (<https://obox.pe>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
#######################################################################################
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_pe_partner_token = fields.Char("Partner token")
    l10n_pe_ruc_validation = fields.Boolean(string="RUC Validation")
    l10n_pe_dni_validation = fields.Boolean(string="DNI Validation")

    @api.onchange("country_id")
    def _onchange_country_id(self):
        res = super(ResCompany, self)._onchange_country_id()
        if self.country_id and self.country_id.code == "PE":
            self.l10n_pe_ruc_validation = True
            self.l10n_pe_dni_validation = True
        else:
            self.l10n_pe_ruc_validation = False
            self.l10n_pe_dni_validation = False
        return res
