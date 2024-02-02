#######################################################################################
#
#    Copyright (C) 2019-TODAY Obox.
#    Author      :  Obox del Peru S.A.C. (<https://obox.pe>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
#######################################################################################

{
    "name": "Validador de identificación - Peru",
    "version": "17.0.1.0.0",
    "author": "Obox",
    "category": "Generic Modules/Base",
    "summary": "RUC validator - PERU",
    "license": "LGPL-3",
    "contributors": [
        "Soporte Obox <soporte@obox.pe>",
    ],
    "website": "https://obox.pe",
    "depends": ["web", "l10n_latam_base", "l10n_pe"],
    "data": [
        "views/res_partner_view.xml",
        "views/res_config_settings_views.xml",
        "views/res_company_views.xml",
        "views/validation_info_templates.xml",
    ],
    "qweb": [],
    "demo": [],
    "test": [],
    "images": [
        "static/description/banner.png",
    ],
    "support": "soporte@obox.pe",
    "installable": True,
    "auto_install": False,
    "sequence": 1,
    "post_init_hook": "post_init_hook",
}
