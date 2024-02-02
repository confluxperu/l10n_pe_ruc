def post_init_hook(env):

    company_ids = (
        env["res.company"].search([]).filtered(lambda r: r.country_id.code == "PE")
    )
    company_ids.write({"l10n_pe_ruc_validation": True, "l10n_pe_dni_validation": True})