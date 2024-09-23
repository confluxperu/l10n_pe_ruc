#######################################################################################
#
#    Copyright (C) 2019-TODAY Obox.
#    Author      :  Obox del Peru S.A.C. (<https://obox.pe>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
#######################################################################################
import contextlib
import logging
import json
import requests
import threading
import uuid
from odoo import _, api, fields, models, exceptions
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_pe_commercial_name = fields.Char(string="Name Commercial")
    l10n_pe_state = fields.Selection(
        [("habido", "Habido"), ("nhabido", "No Habido")], string="Contributor Condition"
    )
    l10n_pe_remote_id = fields.Char(string="Remote ID")
    l10n_pe_alert_warning_vat = fields.Boolean(string="Alert warning vat", default=False)
    l10n_pe_alert_contributor_state = fields.Char(string="Alert State", readonly=True)
    l10n_pe_contributor_state = fields.Boolean()

    @api.onchange("vat", "l10n_latam_identification_type_id")
    def onchange_vat(self):
        res = {}
        if self.vat:
            if self.l10n_latam_identification_type_id.l10n_pe_vat_code == "6":
                if len(self.vat) != 11:
                    res["warning"] = {
                        "title": _("Warning"),
                        "message": _("The Ruc must be 11 characters long."),
                    }
                else:
                    company = self.env["res.company"].browse(self.env.company.id)
                    if company.l10n_pe_ruc_validation:
                        return self.get_data_ruc()
            elif self.l10n_latam_identification_type_id.l10n_pe_vat_code == "1":
                if len(self.vat) != 8:
                    res["warning"] = {
                        "title": _("Warning"),
                        "message": _("The Dni must be 8 characters long."),
                    }
                else:
                    company = self.env["res.company"].browse(self.env.company.id)
                    if company.l10n_pe_dni_validation:
                        return self.get_data_dni()
        if res:
            return res

    def get_data_ruc(self):
        result = self.l10n_pe_ruc_connection(self.vat)
        _logger.info(result)
        if result and not result.get('warning'):
            self.l10n_pe_remote_id = result["l10n_pe_remote_id"]
            self.l10n_pe_alert_contributor_state = result["estado"]
            self.l10n_pe_alert_warning_vat = False
            self.company_type = "company"
            self.name = str(result["business_name"]).strip()
            self.l10n_pe_commercial_name = str(
                result["l10n_pe_commercial_name"] or result["business_name"]
            ).strip()
            self.street = str(result["residence"]).strip()
            if result["estado"] == "ACTIVO":
                self.l10n_pe_contributor_state = True
            else:
                self.l10n_pe_contributor_state = False
            if result["contributing_condition"] == "HABIDO":
                self.l10n_pe_state = "habido"
            else:
                self.l10n_pe_state = "nhabido"
            if result["value"]:
                self.l10n_pe_district = result["value"]["district_id"]
                self.city_id = result["value"]["city_id"]
                self.state_id = result["value"]["state_id"]
        return result

    def get_data_dni(self):
        result = self.l10n_pe_dni_connection(self.vat)
        _logger.info(result)
        if result and not result.get('warning'):
            self.l10n_pe_remote_id = result.get("l10n_pe_remote_id", "")
            self.l10n_pe_alert_warning_vat = False
            self.name = str(result.get("nombre", "")).strip()
            self.company_type = "person"
            self.l10n_pe_alert_contributor_state = ""
            self.l10n_pe_commercial_name = ""
            self.street = ""
            self.l10n_pe_contributor_state = ""
            self.l10n_pe_state = ""
            self.l10n_pe_district = ""
            self.city_id = ""
            self.state_id = ""
        return result


    def fetch_ruc_data(self, vat_number):
        user_token = self.env["iap.account"].get("l10n_pe_data")
        company = self.env.company
        dbuuid = self.env["ir.config_parameter"].sudo().get_param("database.uuid")
        data = {}
        params = {
            "client_service_token": company.l10n_pe_partner_token,
            "l10n_pe_remote_id": self.l10n_pe_remote_id,
            "account_token": user_token.account_token,
            "doc_number": vat_number,
            "type_consult": "ruc_consult" if len(vat_number) != 8 else "dni_consult",
            "currency": "",
            "company_name": company.name,
            "phone": company.phone,
            "email": company.email,
            "service": "partner",
            # "company_image": company.logo.decode("utf-8"),
            "number": company.vat,
            "dbuuid": dbuuid,
        }
        try:
            if len(vat_number) != 8:
                result = self.api_json('https://ruc.conflux.pe/ruc/'+vat_number, params=params, token=company.l10n_pe_partner_token)
            else:
                result = self.api_json('https://ruc.conflux.pe/dni/'+vat_number, params=params, token=company.l10n_pe_partner_token)
            if result.get("status") == "not found":
                return {'warning': {'title': _("Warning"), 'message': _("No se encontraron datos para el número de RUC/DNI proporcionado.")}}
            else:
                if len(vat_number) != 8:
                    data = self.ruc_connection(result)
                elif len(vat_number) != 11:
                    data = self.dni_connection(result)
        except Exception as e:
            data["warning"] = {
                    "title": _("Warning"),
                    "message": _(f"Error al conectar con el servicio. {str(e)}"),
                }
        finally:
            return data

    @api.model
    def ruc_connection(self, result):
        data = {}
        try:
            data["l10n_pe_remote_id"] = result.get("l10n_pe_remote_id", False)
            data["ruc"] = result.get("_id")
            data["business_name"] = result.get("nombre")
            data["estado"] = result.get("estado")
            data["contributing_condition"] = result.get("condicion")
            data["l10n_pe_commercial_name"] = result.get("nombre")
            provincia = result.get("provincia","").title()
            distrito = result.get("distrito","").title()
            prov_ids = self.env["res.city"].search(
                [("name", "=", provincia), ("state_id", "!=", False)]
            )
            dist_id = self.env["l10n_pe.res.city.district"].search(
                [("name", "=", distrito), ("city_id", "in", [x.id for x in prov_ids])],
                limit=1,
            )
            dist_short_id = self.env["l10n_pe.res.city.district"].search(
                [("name", "=", result.get("distrito"))], limit=1
            )
            if dist_id:
                l10n_pe_district = dist_id
            else:
                l10n_pe_district = dist_short_id
            vals = {}
            if l10n_pe_district:
                vals["district_id"] = l10n_pe_district.id
                vals["district_name"] = l10n_pe_district.name
                vals["city_id"] = l10n_pe_district.city_id.id
                vals["city_name"] = l10n_pe_district.city_id.name
                vals["state_id"] = l10n_pe_district.city_id.state_id.id
                vals["state_name"] = l10n_pe_district.city_id.state_id.name
                vals["country_id"] = l10n_pe_district.city_id.state_id.country_id.id
                vals["country_name"] = l10n_pe_district.city_id.state_id.country_id.name
            data["value"] = vals
            data["residence"] = result.get("direccion")
        except Exception:
            self.l10n_pe_alert_warning_vat = True
            data = False
        return data

    @api.model
    def l10n_pe_ruc_connection(self, vat_number):
        data = self.fetch_ruc_data(vat_number)
        if data.get("warning") or data.get("l10n_pe_remote_id"):
            return data
        return data

    @api.model
    def dni_connection(self, result):
        data = {}
        try:
            data["l10n_pe_remote_id"] = result.get("l10n_pe_remote_id", False)
            name = result.get("nombre")
            if result.get("name", False):
                name = result.get("name")
            data["nombre"] = name
        except Exception:
            self.l10n_pe_alert_warning_vat = True
            data = False
        return data

    @api.model
    def l10n_pe_dni_connection(self, vat_number):
        data = {}
        data = self.fetch_ruc_data(vat_number)
        if data.get("warning") or data.get("l10n_pe_remote_id"):
            return data
        return data

    @api.onchange("l10n_pe_district")
    def _onchange_l10n_pe_district(self):
        if self.l10n_pe_district and self.l10n_pe_district.city_id:
            self.city_id = self.l10n_pe_district.city_id

    @api.onchange("city_id")
    def _onchange_city_id(self):
        if self.city_id and self.city_id.state_id:
            self.state_id = self.city_id.state_id
        res = {}
        res["domain"] = {}
        res["domain"]["l10n_pe_district"] = []
        if self.city_id:
            res["domain"]["l10n_pe_district"] += [("city_id", "=", self.city_id.id)]
        return res

    @api.onchange("state_id")
    def _onchange_state_id(self):
        if self.state_id and self.state_id.country_id:
            self.country_id = self.state_id.country_id
        res = {}
        res["domain"] = {}
        res["domain"]["city_id"] = []
        if self.state_id:
            res["domain"]["city_id"] += [("state_id", "=", self.state_id.id)]
        return res

    def api_json(self, url, params=None, token=None, timeout=15):
        """
        Calls the provided JSON-RPC endpoint, unwraps the result and
        returns JSON-RPC errors as exceptions.
        """
        if hasattr(threading.current_thread(), 'testing') and threading.current_thread().testing:
            raise exceptions.AccessError("Unavailable during tests.")

        #payload = params
        payload = {}

        _logger.info('iap jsonrpc %s', url)
        try:
            req = requests.get(url, json=payload, timeout=timeout, headers = {
                'Content-Type': 'application/json',
                'Authorization': token
            })
            req.raise_for_status()
            response = req.json()
            #_logger.info(response)
            _logger.info("api json %s answered in %s seconds", url, req.elapsed.total_seconds())
            if 'error' in response:
                name = response['error']['data'].get('name').rpartition('.')[-1]
                message = response['error']['data'].get('message')
                e_class = exceptions.UserError
                e = e_class(message)
                e.data = response['error']['data']
                raise e
            return response
        except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema, requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
            raise exceptions.AccessError(
                _('The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was %s', url)
            )
