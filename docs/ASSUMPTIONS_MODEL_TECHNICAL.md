# Technical Assumptions - analyse_compteurs_eau.py

This document lists all modeling assumptions encoded in `analyse_compteurs_eau.py` (version 3.11.0). Each item is marked for Analyst verification.

Status legend:
- PENDING: not yet verified by Analyst
- VERIFIED: verified by Analyst with reputable sources
- CHALLENGED: Analyst found conflicting evidence or needs a change

Note: "Code reference" points to the class/constant/function where the assumption is defined.

## 0) Scope and accounting assumptions

| ID | Assumption | Default / Value | Units | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| SC-1 | Model scope is residential water meters and municipal CBA. | Residential, municipal context. | n/a | Module header + docstrings | PENDING | |
| SC-2 | No volumetric pricing module; benefits come from water savings (behavior + leaks). | Tariff effects excluded. | n/a | ModeCompte + comments | PENDING | |
| SC-3 | Economic mode uses social/full cost of water and counts all costs; financial mode uses variable cost avoided and counts city-paid costs only. | ECONOMIQUE vs FINANCIER logic. | n/a | ModeCompte + actualiser_series | PENDING | |
| SC-4 | Household monetary benefits from tariffs are set to zero in Quebec (no volumetric pricing). | VAN menages = 0 by default. | n/a | decomposer_par_payeur | PENDING | |
| SC-5 | Infrastructure deferral benefits are optional and default to zero. | 0 | $/yr or $/m3 | ParametresModele | PENDING | |
| SC-6 | Discounted cash flow with VAN and RBC is the core evaluation method. | NPV/RBC formulas. | n/a | actualiser_series | PENDING | |
| SC-7 | Default horizon and discount rate are long-term infrastructure values. | 20 years, 3% real | years, percent | ParametresModele | PENDING | |
| SC-8 | MCF applies only to public spending and only in economic mode when enabled. | Applied to public share only | n/a | ParametresValeurEau + actualiser_series | PENDING | |
| SC-9 | `executer_analyse_complete` defaults avoid optimistic bias. | PERSISTANCE_REALISTE + FUITES_SANS_COUT | n/a | executer_analyse_complete | PENDING | |

## 1) Core model defaults (ParametresModele)

| ID | Parameter | Default | Units | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PM-1 | nb_menages | 10000 | households | Base population size for default runs. | ParametresModele | PENDING | |
| PM-2 | nb_compteurs | None -> nb_menages | meters | 1 meter per household unless overridden. | ParametresModele | PENDING | |
| PM-3 | taille_menage | 2.1 | persons/household | Default household size. | ParametresModele | PENDING | |
| PM-4 | lpcd | 250.0 | L/person/day | Default residential use aligned with Quebec 2023 residential LPCD (245). | ParametresModele | VERIFIED | [S6] |
| PM-5 | part_menages_fuite_pct | 20.0 | percent | Default leak prevalence exceeds EPA estimate (~10% homes), needs regional justification. | ParametresModele | CHALLENGED | [S2] |
| PM-6 | debit_fuite_m3_an | 35.0 | m3/yr | Consistent with EPA ~9,400-10,000 gallons/year (~35.6-37.9 m3). | ParametresModele | VERIFIED | [S2][S3] |
| PM-7 | taux_correction_fuite_pct | 85.0 | percent | Default leak correction rate. | ParametresModele | PENDING | |
| PM-8 | reduction_comportement_pct | 8.0 | percent | Default behavioral reduction from meters. | ParametresModele | PENDING | |
| PM-9 | valeur_eau_m3 | 4.69 | $/m3 | Default social value (Quebec unit cost) pending accessible source. | ParametresModele | PENDING | |
| PM-10 | benefice_report_infra_annuel | 0.0 | $/yr | No deferral benefit unless set. | ParametresModele | PENDING | |
| PM-11 | benefice_report_infra_par_m3 | 0.0 | $/m3 | No deferral per m3 unless set. | ParametresModele | PENDING | |
| PM-12 | taux_actualisation_pct | 3.0 | percent | Default social discount rate aligned with Canadian federal CBA practice. | ParametresModele | VERIFIED | [S4][S5] |
| PM-13 | horizon_analyse | 20 | years | Default analysis horizon. | ParametresModele | PENDING | |
| PM-14 | part_ville_capex_pct | 100.0 | percent | City pays all CAPEX in financial mode by default. | ParametresModele | PENDING | |
| PM-15 | part_ville_opex_pct | 100.0 | percent | City pays all OPEX in financial mode by default. | ParametresModele | PENDING | |

## 2) Water value and MCF (ParametresValeurEau)

| ID | Parameter | Default | Units | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| VE-1 | cout_variable_m3 | 0.50 | $/m3 | Variable OPEX per m3 (chemicals, energy). | ParametresValeurEau | PENDING | |
| VE-2 | cout_opex_fixe_m3 | 1.24 | $/m3 | Fixed OPEX per m3 (labor, admin). | ParametresValeurEau | PENDING | |
| VE-3 | cout_capex_m3 | 2.95 | $/m3 | CAPEX portion per m3 (amortization/debt). | ParametresValeurEau | PENDING | |
| VE-4 | valeur_sociale_m3 | 4.69 | $/m3 | Unit cost of water services (Quebec) pending accessible source. | ParametresValeurEau | PENDING | |
| VE-5 | prix_vente_m3 | 2.50 | $/m3 | Indicative tariff value (not used without tariff module). | ParametresValeurEau | PENDING | |
| VE-6 | mcf | 0.20 | ratio | Marginal social cost of public funds (MSCPF) set to 20%. | ParametresValeurEau | VERIFIED | [S4] |
| VE-7 | appliquer_mcf | False | bool | MCF disabled by default. | ParametresValeurEau | PENDING | |
| VE-8 | Full cost definition | Total cost = operating costs + average investment needs (investment share pending source). | n/a | Cost accounting definition. | ParametresValeurEau docstring | PENDING | |
| VE-9 | Externalities exclusion | 4.69 does not include explicit environmental externalities; externalities only in \"rarete\" preset. | n/a | Scope assumption. | ParametresValeurEau docstring | PENDING | |

### Presets for water value

| ID | Preset | Values | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| VE-P1 | VALEUR_EAU_QUEBEC | Total cost 4.69 $/m3 (component split pending); mcf=0.20; appliquer_mcf=False | Quebec full cost baseline; total cost pending source. | VALEUR_EAU_QUEBEC | PENDING | |
| VE-P2 | VALEUR_EAU_CONSERVATEUR | 0.25 + 0.75 + 1.50 = 2.50 | Low cost sensitivity case. | VALEUR_EAU_CONSERVATEUR | PENDING | |
| VE-P3 | VALEUR_EAU_RARETE | 1.50 + 1.50 + 3.00 = 8.00 | Scarcity premium case. | VALEUR_EAU_RARETE | PENDING | |
| VE-P4 | VALEUR_EAU_SANS_MCF | Same as Quebec, mcf=0 | MCF off (backward compat). | VALEUR_EAU_SANS_MCF | PENDING | |
| VE-P5 | VALEUR_EAU_QUEBEC_AVEC_MCF | Quebec values, mcf=0.20, appliquer_mcf=True | Sensitivity with MCF. | VALEUR_EAU_QUEBEC_AVEC_MCF | PENDING | |

## 3) Economies of scale (ConfigEconomiesEchelle)

| ID | Parameter | Default | Units | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ES-1 | activer | False | bool | No economies of scale unless enabled. | ConfigEconomiesEchelle | PENDING | |
| ES-2 | poids_compteur | 1.0 | ratio | Full scale effect applies to meter hardware. | ConfigEconomiesEchelle | PENDING | |
| ES-3 | poids_reseau | 0.5 | ratio | Partial scale effect on network costs. | ConfigEconomiesEchelle | PENDING | |
| ES-4 | poids_installation | 0.0 | ratio | Labor has no scale effect by default. | ConfigEconomiesEchelle | PENDING | |
| ES-5 | paliers | {0:1.00, 10k:0.95, 50k:0.90, 100k:0.85, 200k:0.80} | factor | Stepwise scale discounts. | ConfigEconomiesEchelle | PENDING | |
| ES-6 | utiliser_modele_continu | False | bool | Stepwise model used unless enabled. | ConfigEconomiesEchelle | PENDING | |
| ES-7 | elasticite_echelle | 0.05 | ratio | 5% reduction per doubling (log model). | ConfigEconomiesEchelle | PENDING | |
| ES-8 | nb_reference | 10000 | meters | Reference point for log model. | ConfigEconomiesEchelle | PENDING | |
| ES-9 | facteur_echelle bounds | 0.70 to 1.0 | ratio | Scale factor capped between 0.70 and 1.0. | calculer_facteur_echelle | PENDING | |

## 4) OPEX ventilation (VentilationOPEX)

| ID | Parameter | Default | Units | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OPEX-1 | cybersecurite_pct | 0.15 | ratio | 15% of OPEX for cybersecurity. | VentilationOPEX | PENDING | |
| OPEX-2 | licences_logiciels_pct | 0.20 | ratio | 20% of OPEX for software licenses. | VentilationOPEX | PENDING | |
| OPEX-3 | stockage_donnees_pct | 0.10 | ratio | 10% of OPEX for data storage. | VentilationOPEX | PENDING | |
| OPEX-4 | service_client_pct | 0.25 | ratio | 25% of OPEX for customer service. | VentilationOPEX | PENDING | |
| OPEX-5 | integration_si_pct | 0.30 | ratio | 30% of OPEX for IT integration. | VentilationOPEX | PENDING | |

### OPEX ventilation presets

| ID | Preset | Values | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| OPEX-P1 | VENTILATION_OPEX_STANDARD | 15/20/10/25/30 percent | Standard industry split. | VENTILATION_OPEX_STANDARD | PENDING | |
| OPEX-P2 | VENTILATION_OPEX_SECURITE_ELEVEE | 25/20/10/20/25 percent | Higher cybersecurity share. | VENTILATION_OPEX_SECURITE_ELEVEE | PENDING | |
| OPEX-P3 | VENTILATION_OPEX_CLOUD | 12/25/18/20/25 percent | Cloud heavy cost split. | VENTILATION_OPEX_CLOUD | PENDING | |

## 5) Meter parameters (ParametresCompteur)

| ID | Parameter | Default | Units | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MC-1 | type_compteur | AMI | enum | Default tech is AMI. | ParametresCompteur | PENDING | |
| MC-2 | cout_compteur | 250.0 | $ | Default meter hardware cost. | ParametresCompteur | PENDING | |
| MC-3 | heures_installation | 1.5 | hours | Default install time per meter. | ParametresCompteur | PENDING | |
| MC-4 | taux_horaire_installation | 125.0 | $/hour | Default labor rate. | ParametresCompteur | PENDING | |
| MC-5 | cout_infra_fixe | 0.0 | $ | Fixed AMI infrastructure cost (default 0). | ParametresCompteur | PENDING | |
| MC-6 | cout_reseau_par_compteur | 50.0 | $ | AMI network cost per meter. | ParametresCompteur | PENDING | |
| MC-7 | duree_vie_compteur | 20 | years | Meter life. | ParametresCompteur | PENDING | |
| MC-8 | duree_vie_batterie | 15 | years | Battery life (AMI/AMR). | ParametresCompteur | PENDING | |
| MC-9 | cout_remplacement_batterie | 30.0 | $ | Battery replacement cost. | ParametresCompteur | PENDING | |
| MC-10 | cout_lecture_manuel | 25.0 | $/meter/year | Manual read cost. | ParametresCompteur | PENDING | |
| MC-11 | cout_maintenance_ami | 5.0 | $/meter/year | AMI maintenance cost. | ParametresCompteur | PENDING | |
| MC-12 | cout_maintenance_amr | 8.0 | $/meter/year | AMR maintenance cost. | ParametresCompteur | PENDING | |
| MC-13 | cout_maintenance_manuel | 3.0 | $/meter/year | Manual maintenance cost. | ParametresCompteur | PENDING | |
| MC-14 | cout_opex_non_tech_ami | 15.0 | $/meter/year | Non-technical AMI OPEX. | ParametresCompteur | PENDING | |
| MC-15 | cout_lecture_amr | 8.0 | $/meter/year | AMR reading cost. | ParametresCompteur | PENDING | |
| MC-16 | facteur_efficacite_comportement | 1.0 | ratio | AMI reference value. | ParametresCompteur | PENDING | |
| MC-17 | facteur_efficacite_fuites | 1.0 | ratio | AMI reference value. | ParametresCompteur | PENDING | |
| MC-18 | Default factors for MANUEL | 0.40 (behavior), 0.30 (leaks) | ratio | Manual reading has weaker effects. | ParametresCompteur.__post_init__ | PENDING | |
| MC-19 | Default factors for AMR | 0.60 (behavior), 0.50 (leaks) | ratio | AMR has reduced effects vs AMI. | ParametresCompteur.__post_init__ | PENDING | |
| MC-20 | Non-technical AMI OPEX breakdown (example) | Telecom 5, cyber 3, licenses 4, storage 2, support 1 | $/yr | Assumed composition for 15 $/yr. | ParametresCompteur comments | PENDING | |

## 6) Persistence of behavioral effects (ParametresPersistance)

| ID | Parameter | Default | Units | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PR-1 | mode | CONSTANT | enum | No decay unless scenario says otherwise. | ParametresPersistance | PENDING | |
| PR-2 | alpha_initial | 0.08 | ratio | 8% initial reduction. | ParametresPersistance | PENDING | |
| PR-3 | alpha_plateau | 0.025 | ratio | 2.5% long-run plateau. | ParametresPersistance | PENDING | |
| PR-4 | lambda_decay | 0.15 | 1/yr | Decay speed (half-life ~4.6y); consistent with ~10-20%/yr decay. | ParametresPersistance | PENDING | |
| PR-5 | annees_fadeout | 10 | years | Linear fadeout duration. | ParametresPersistance | PENDING | |
| PR-6 | Formula by mode | Constant / exp plateau / linear fade / exp fade | n/a | Chosen functional forms for persistence. | calculer_alpha_comportement | PENDING | |

### Persistence presets

| ID | Preset | Values | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| PR-P1 | PERSISTANCE_OPTIMISTE | constant alpha=0.08 | Permanent effect. | PERSISTANCE_OPTIMISTE | PENDING | |
| PR-P2 | PERSISTANCE_REALISTE | alpha0=0.08, plateau=0.025, lambda=0.15 | Partial decay to plateau. | PERSISTANCE_REALISTE | PENDING | |
| PR-P3 | PERSISTANCE_PESSIMISTE | alpha0=0.08, fadeout=10y | Linear fade to zero. | PERSISTANCE_PESSIMISTE | PENDING | |
| PR-P4 | PERSISTANCE_ULTRA_PESSIMISTE | alpha0=0.0 | No behavior effect. | PERSISTANCE_ULTRA_PESSIMISTE | PENDING | |

## 7) Private leak module (ParametresFuites)

| ID | Parameter | Default | Units | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LF-1 | part_menages_fuite_pct | 20.0 | percent | Aggregate leak prevalence; EPA reports ~10% of homes with leaks, so 20% requires regional justification. | ParametresFuites | CHALLENGED | [S2] |
| LF-2 | debit_fuite_m3_an | 35.0 | m3/yr | Aggregate leak volume; EPA cites ~9,400-10,000 gallons/year (~35.6-37.9 m3). | ParametresFuites | VERIFIED | [S2][S3] |
| LF-3 | utiliser_prevalence_differenciee | False | bool | Two-stock mode off by default. | ParametresFuites | PENDING | |
| LF-4 | part_menages_fuite_any_pct | 20.0 | percent | Any leak prevalence (two-stock). | ParametresFuites | PENDING | |
| LF-5 | debit_fuite_any_m3_an | 10.0 | m3/yr | Small leak volume. | ParametresFuites | PENDING | |
| LF-6 | part_menages_fuite_significative_pct | 5.0 | percent | Significant leak prevalence. | ParametresFuites | PENDING | |
| LF-7 | debit_fuite_significative_m3_an | 50.0 | m3/yr | Significant leak volume. | ParametresFuites | PENDING | |
| LF-8 | part_fuites_persistantes_pct | 5.0 | percent | Fraction never repaired. | ParametresFuites | PENDING | |
| LF-9 | facteur_duree_longue_traine | 5.0 | ratio | Repair duration multiplier (long tail). | ParametresFuites | PENDING | |
| LF-10 | facteur_detection_sig | 1.2 | ratio | Significant leaks easier to detect. | ParametresFuites | PENDING | |
| LF-11 | facteur_reparation_sig | 1.4 | ratio | Significant leaks more likely repaired. | ParametresFuites | PENDING | |
| LF-12 | cout_reparation_any | 100.0 | $ | Small leak repair cost. | ParametresFuites | PENDING | |
| LF-13 | cout_reparation_sig | 400.0 | $ | Large leak repair cost. | ParametresFuites | PENDING | |
| LF-14 | taux_detection_pct | 90.0 | percent | AMI leak detection rate. | ParametresFuites | PENDING | |
| LF-15 | taux_reparation_pct | 85.0 | percent | Repair rate after detection. | ParametresFuites | PENDING | |
| LF-16 | cout_reparation_moyen | 200.0 | $ | Average repair cost (aggregated). | ParametresFuites | PENDING | |
| LF-17 | mode_repartition | MENAGE_SEUL | enum | Costs borne by households by default. | ParametresFuites | PENDING | |
| LF-18 | part_ville_pct | 0.0 | percent | City share of repair costs. | ParametresFuites | PENDING | |
| LF-19 | taux_nouvelles_fuites_pct | 5.0 | percent/yr | New leaks per year. | ParametresFuites | PENDING | |
| LF-20 | duree_moyenne_fuite_sans_compteur | None | years | Derived if None; else specified. | ParametresFuites | PENDING | |
| LF-21 | inclure_cout_reparation | True | bool | Repair costs included by default. | ParametresFuites | PENDING | |
| LF-22 | Two-stock assumption | p_sig is subset of p_any; p_any_excl = p_any - p_sig | n/a | Stock definition for two-stock mode. | volume_fuite_moyen_pondere | PENDING | |
| LF-23 | Leak dynamics | Stock model with new leaks and repair rates; mu derived as q/p0 if not provided, else 0.25 fallback | n/a | Stock-flow assumption. | calculer_dynamique_fuites | PENDING | |
| LF-24 | Significant-leak detection/repair multipliers | d_sig = min(1, d_eff * facteur_detection_sig); r_sig = r_base * facteur_reparation_sig | n/a | Larger leaks are easier to detect/repair. | calculer_dynamique_fuites | PENDING | |
| LF-25 | Long-tail handling | Persistent fraction reduces correction rate; long tail slows mu and k by factor_duree_longue_traine. | n/a | Repairs take longer for long tail. | calculer_dynamique_fuites | PENDING | |
| LF-26 | If inclure_cout_reparation is False, part_ville forced to 0. | 0 | percent | Repair costs ignored in cost allocation. | calculer_dynamique_fuites | PENDING | |

### Leak scenario presets (with tariff or strong incentives)

| ID | Preset | Key values | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| LF-P1 | FUITES_SANS_COUT | prevalence 20%, debit 35, detect 90%, repair 85%, persist 5%, duration 4y, no repair costs | Baseline without repair costs. | FUITES_SANS_COUT | PENDING | |
| LF-P2 | FUITES_MENAGE_SEUL | prevalence 20%, debit 35, detect 90%, repair 85%, persist 5%, duration 4y, cost 200, city 0% | Household pays all. | FUITES_MENAGE_SEUL | PENDING | |
| LF-P3 | FUITES_SUBVENTION_50 | same as MENAGE_SEUL but city 50% | 50/50 cost share. | FUITES_SUBVENTION_50 | PENDING | |
| LF-P4 | FUITES_VILLE_SEULE | same as MENAGE_SEUL but city 100% | City pays all. | FUITES_VILLE_SEULE | PENDING | |
| LF-P5 | FUITES_CONTEXTE_QUEBEC | prevalence 35%, duration 7y, detect 90%, repair 85%, persist 5% | Higher prevalence for no-meter context. | FUITES_CONTEXTE_QUEBEC | PENDING | |
| LF-P6 | FUITES_QUEBEC_DEUX_STOCKS | any 30%, sig 6%, debit 10/50, costs 150/600, persist 5%, duration 6y | Two-stock Quebec case. | FUITES_QUEBEC_DEUX_STOCKS | PENDING | |

### Leak scenario presets (no volumetric pricing)

| ID | Preset | Key values | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| LF-NT1 | FUITES_MENAGE_SANS_TARIF | repair 55%, persist 10%, prevalence 20%, duration 4y | No-price incentive reduces repairs. | FUITES_MENAGE_SANS_TARIF | PENDING | |
| LF-NT2 | FUITES_QUEBEC_SANS_TARIF | prevalence 35%, repair 55%, persist 10%, duration 7y | Quebec no-tariff context. | FUITES_QUEBEC_SANS_TARIF | PENDING | |
| LF-NT3 | FUITES_QUEBEC_DEUX_STOCKS_SANS_TARIF | repair 55%, persist 10%, factor_reparation_sig 1.4 | Two-stock, no tariff. | FUITES_QUEBEC_DEUX_STOCKS_SANS_TARIF | PENDING | |

## 8) Network leak module (ParametresFuitesReseau)

| ID | Parameter | Default | Units | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NR-1 | volume_pertes_m3_an | 0.0 | m3/yr | No network losses by default. | ParametresFuitesReseau | PENDING | |
| NR-2 | reduction_max_pct | 0.0 | percent | No reduction by default. | ParametresFuitesReseau | PENDING | |
| NR-3 | mode_reduction | LINEAIRE | enum | Linear ramp by default. | ParametresFuitesReseau | PENDING | |
| NR-4 | annees_atteinte | 5 | years | Target reached in 5 years (linear). | ParametresFuitesReseau | PENDING | |
| NR-5 | lambda_reduction | 0.5 | 1/yr | Exponential speed if enabled. | ParametresFuitesReseau | PENDING | |
| NR-6 | annee_demarrage | 1 | year | Start year. | ParametresFuitesReseau | PENDING | |
| NR-7 | cout_programme_annuel | 0.0 | $/yr | No program OPEX by default. | ParametresFuitesReseau | PENDING | |
| NR-8 | cout_reparation_m3 | 0.0 | $/m3 | No variable repair cost by default. | ParametresFuitesReseau | PENDING | |
| NR-9 | cout_capex_initial | 0.0 | $ | No initial CAPEX by default. | ParametresFuitesReseau | PENDING | |
| NR-10 | annee_capex | 1 | year | CAPEX year if used. | ParametresFuitesReseau | PENDING | |
| NR-11 | pondere_par_adoption | True | bool | Network savings/costs scale with adoption. | ParametresFuitesReseau | PENDING | |
| NR-12 | activer | True | bool | Module active but zeroed by default. | ParametresFuitesReseau | PENDING | |

## 9) Adoption module (ParametresAdoption)

| ID | Parameter | Default | Units | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AD-1 | mode | OBLIGATOIRE | enum | Default is immediate deployment. | ParametresAdoption | PENDING | |
| AD-2 | k_vitesse | 0.5 | ratio | Logistic adoption speed. | ParametresAdoption | PENDING | |
| AD-3 | t0_point_median | 5.0 | years | Logistic midpoint year. | ParametresAdoption | PENDING | |
| AD-4 | adoption_max_pct | 90.0 | percent | Default adoption ceiling. | ParametresAdoption | PENDING | |
| AD-5 | taux_nouveaux_pct | 2.0 | percent/yr | New-build adoption rate. | ParametresAdoption | PENDING | |
| AD-6 | nb_secteurs | 5 | count | Sectors for phased rollout. | ParametresAdoption | PENDING | |
| AD-7 | annees_par_secteur | 2.0 | years | Years per sector. | ParametresAdoption | PENDING | |
| AD-8 | etaler_capex | False | bool | CAPEX not spread by default. | ParametresAdoption | PENDING | |
| AD-9 | cout_incitatif_par_menage | 0.0 | $ total | Default incentives zero. | ParametresAdoption | PENDING | |
| AD-10 | duree_incitatif_ans | 1 | years | Incentive duration. | ParametresAdoption | PENDING | |
| AD-11 | fraction_premiere_annee | 1.0 | ratio | Full-year effect for first year. | ParametresAdoption | PENDING | |
| AD-12 | annee_demarrage | 1 | year | Start year. | ParametresAdoption | PENDING | |
| AD-13 | Adoption formula | Logistic (voluntary), linear (new builds), stepwise (by sector), immediate (mandatory) | n/a | Functional forms used. | calculer_adoption | PENDING | |
| AD-14 | OBLIGATOIRE special-case | If adoption_max_pct == 90 (default) or >= 100, treat as 100% | ratio | Mandatory deployment defaults to full coverage. | calculer_adoption | PENDING | |

### Adoption strategy presets

| ID | Preset | Key values | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| AD-P1 | ADOPTION_OBLIGATOIRE | Amax 100%, capex upfront | Mandatory immediate deployment. | ADOPTION_OBLIGATOIRE | PENDING | |
| AD-P2 | ADOPTION_RAPIDE | k=1.5, t0=2, Amax 95%, incentives 540 over 3y, fraction 0.5 | Fast voluntary adoption. | ADOPTION_RAPIDE | PENDING | |
| AD-P3 | ADOPTION_PROGRESSIVE | k=0.6, t0=5, Amax 85%, incentives 180 over 3y, fraction 0.5 | Moderate voluntary adoption. | ADOPTION_PROGRESSIVE | PENDING | |
| AD-P4 | ADOPTION_NOUVEAUX | taux_nouveaux 3%, Amax 60%, fraction 0.5 | New builds only. | ADOPTION_NOUVEAUX | PENDING | |
| AD-P5 | ADOPTION_PAR_SECTEUR | 5 sectors, 2y per sector, Amax 100%, fraction 0.5 | Phased rollout. | ADOPTION_PAR_SECTEUR | PENDING | |
| AD-P6 | ADOPTION_LENTE | k=0.3, t0=10, Amax 70%, incentives 90 over 3y, fraction 0.5 | Slow voluntary adoption. | ADOPTION_LENTE | PENDING | |
| AD-P7 | ADOPTION_ICI_SEULEMENT | Amax 10% (default) | ICI-only placeholder. | ADOPTION_ICI_SEULEMENT | PENDING | |
| AD-P8 | ADOPTION_ECHANTILLONNAGE_380 | Amax 0.327% for Longueuil | SQEEP sample of 380 meters. | ADOPTION_ECHANTILLONNAGE_380 | PENDING | |

## 10) Segmentation module (ParametresSegment)

| ID | Parameter | Default | Units | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SG-1 | type_logement | UNIFAMILIAL | enum | Default segment type. | ParametresSegment | PENDING | |
| SG-2 | nb_menages | 10000 | households | Default segment size. | ParametresSegment | PENDING | |
| SG-3 | nb_compteurs | None -> nb_menages | meters | One meter per household by default. | ParametresSegment | PENDING | |
| SG-4 | personnes_par_menage | 2.3 | persons/household | Default for segment. | ParametresSegment | PENDING | |
| SG-5 | lpcd | 250.0 | L/person/day | Default segment consumption. | ParametresSegment | PENDING | |
| SG-6 | cout_compteur_ajustement | 1.0 | ratio | No cost adjustment by default. | ParametresSegment | PENDING | |
| SG-7 | cout_installation_ajustement | 1.0 | ratio | No install adjustment by default. | ParametresSegment | PENDING | |
| SG-8 | prevalence_fuites_pct | 20.0 | percent | Segment leak prevalence. | ParametresSegment | PENDING | |
| SG-9 | potentiel_reduction_pct | 8.0 | percent | Segment behavioral potential. | ParametresSegment | PENDING | |
| SG-10 | Multilogement exclusion | Excluded by default due to data gaps. | n/a | Methodological limitation. | SEGMENT_MULTILOGEMENT comments | PENDING | |

### Quebec segmentation presets

| ID | Preset | Key values | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| SG-P1 | SEGMENT_UNIFAMILIAL | 70k households, 2.5 persons, 250 lpcd, leak 22%, reduction 10% | Unifamilial segment baseline. | SEGMENT_UNIFAMILIAL | PENDING | |
| SG-P2 | SEGMENT_MULTIPLEX | 25k households, 10k meters, 2.0 persons, 210 lpcd, leak 20%, reduction 7% | Multiplex baseline. | SEGMENT_MULTIPLEX | PENDING | |
| SG-P3 | SEGMENT_MULTILOGEMENT | 21k households, 4.2k meters, 1.7 persons, 180 lpcd, leak 18%, reduction 5% | Excluded by default; placeholder. | SEGMENT_MULTILOGEMENT | PENDING | |
| SG-P4 | SEGMENTS_QUEBEC_DEFAUT | Unifamilial + Multiplex only (~82% coverage) | Default analysis excludes multilogement. | SEGMENTS_QUEBEC_DEFAUT | PENDING | |

## 11) Regional defaults and scenario presets

| ID | Preset | Key values | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| RD-1 | DEFAUTS_LONGUEUIL | 116,258 households, 2.18 persons, 236 lpcd | Longueuil baseline aligns with 2023 dataset. | DEFAUTS_LONGUEUIL | VERIFIED | [S6] |
| RD-2 | ORDRES_GRANDEUR_QUEBEC | res 245 lpcd, total 467, target 458, Longueuil total 567, target 184 | Quebec reference ranges; residential 245 and total 467 verified; Longueuil total 567 conflicts with dataset (552). | ORDRES_GRANDEUR_QUEBEC | CHALLENGED | [S6] |
| RD-3 | LPCD_MONTREAL_HAUT | 332 lpcd | High-consumption scenario. | LPCD_MONTREAL_HAUT | PENDING | |
| RD-4 | COMPTEUR_LONGUEUIL_AMI | 250 meter, 3h install, 125 $/h, 50 network | Longueuil AMI preset. | COMPTEUR_LONGUEUIL_AMI | PENDING | |
| RD-5 | DEFAUTS_WINNIPEG | 221,000 households, 2.3 persons | Winnipeg baseline. | DEFAUTS_WINNIPEG | PENDING | |
| RD-6 | COMPTEUR_WINNIPEG | 350 meter, 1h install, 100 $/h, 161 network | Winnipeg AMI preset. | COMPTEUR_WINNIPEG | PENDING | |
| RD-7 | COMPTEUR_AMI_OPEX_BAS | opex_non_tech 10 (total 15) | Low OPEX sensitivity. | COMPTEUR_AMI_OPEX_BAS | PENDING | |
| RD-8 | COMPTEUR_AMI_OPEX_HAUT | opex_non_tech 35 (total 40) | High OPEX sensitivity. | COMPTEUR_AMI_OPEX_HAUT | PENDING | |

## 12) Monte Carlo settings and distributions

| ID | Parameter | Default | Units | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MCAR-1 | n_simulations | 10000 | runs | Default simulation count. | ParametresMonteCarlo | PENDING | |
| MCAR-2 | seed | None | n/a | Randomized unless set. | ParametresMonteCarlo | PENDING | |
| MCAR-3 | Minimum simulations | >= 100 | runs | Lower bound for reliability. | ParametresMonteCarlo.__post_init__ | PENDING | |
| MCAR-4 | Default distributions | Triangular for most parameters | n/a | Uncertainty modeled via triangular ranges. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-5 | alpha0 range | 0.04 / 0.08 / 0.15 | ratio | Behavioral reduction range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-6 | lpcd range | 180 / 250 / 350 | L/person/day | Consumption range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-7 | cout_compteur range | 150 / 250 / 400 | $ | Meter cost range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-8 | cout_installation range | 80 / 120 / 200 | $ | Install cost range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-9 | heures_installation range | 1.0 / 1.5 / 3.0 | hours | Install time range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-10 | taux_horaire_installation range | 100 / 125 / 150 | $/hour | Labor rate range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-11 | opex_annuel range | 15 / 20 / 40 | $/meter/yr | AMI OPEX range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-12 | valeur_eau range | 2.50 / 4.69 / 8.00 | $/m3 | Water value range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-13 | prevalence_fuites range | 0.10 / 0.20 / 0.35 | ratio | Leak prevalence range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-14 | debit_fuite_m3_an range | 20 / 35 / 60 | m3/yr | Leak volume range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-15 | taux_detection range | 0.70 / 0.90 / 0.98 | ratio | Detection rate range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-16 | taux_reparation range | 0.60 / 0.85 / 0.95 | ratio | Repair rate range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-17 | adoption_max range | 0.70 / 0.85 / 1.00 | ratio | Adoption max range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-18 | adoption_k range | 0.3 / 0.6 / 1.5 | ratio | Adoption speed range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-19 | adoption_t0 range | 2 / 5 / 10 | years | Adoption midpoint range. | DISTRIBUTIONS_DEFAUT | PENDING | |
| MCAR-20 | taux_actualisation range | 0.02 / 0.03 / 0.05 | ratio | Discount rate range. | DISTRIBUTIONS_DEFAUT | PENDING | |

## 13) Calibration ranges (ParametreCalibre)

This section documents the calibrated default values and recommended ranges used to validate parameters.

| ID | Parameter | Default | Recommended range | Units | Assumption | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CAL-1 | alpha_initial | 0.08 | 0.05 - 0.15 | ratio | Behavioral reduction year 1. | CALIBRATION["persistance"]["alpha0"] | PENDING | |
| CAL-2 | alpha_plateau | 0.025 | 0.00 - 0.05 | ratio | Long-run plateau. | CALIBRATION["persistance"]["alpha_inf"] | PENDING | |
| CAL-3 | lambda_decay | 0.15 | 0.10 - 0.35 | 1/yr | Decay speed. | CALIBRATION["persistance"]["lambda_decay"] | PENDING | |
| CAL-4 | part_menages_fuite_pct | 20.0 | 12.0 - 25.0 | percent | Leak prevalence. | CALIBRATION["fuites"]["prevalence"] | PENDING | |
| CAL-5 | debit_fuite_m3_an | 35.0 | 20.0 - 75.0 | m3/yr | Leak volume. | CALIBRATION["fuites"]["debit_fuite"] | PENDING | |
| CAL-6 | taux_reparation_pct | 85.0 | 60.0 - 95.0 | percent | Repair rate. | CALIBRATION["fuites"]["taux_reparation"] | PENDING | |
| CAL-7 | cout_reparation_moyen | 200.0 | 100.0 - 500.0 | $ | Repair cost. | CALIBRATION["fuites"]["cout_reparation"] | PENDING | |
| CAL-8 | facteur_echelle | 0.85 | 0.80 - 0.92 | ratio | Scale factor for >100k. | CALIBRATION["economies_echelle"]["facteur_100k"] | PENDING | |
| CAL-9 | valeur_sociale_m3 | 4.69 | 2.50 - 8.00 | $/m3 | Social value of water. | CALIBRATION["valeur_eau"]["valeur_sociale"] | PENDING | |
| CAL-10 | cout_variable_m3 | 0.50 | 0.10 - 1.50 | $/m3 | Variable cost avoided. | CALIBRATION["valeur_eau"]["cout_variable"] | PENDING | |
| CAL-11 | taux_actualisation_pct | 3.0 | 2.0 - 5.0 | percent | Discount rate. | CALIBRATION["financier"]["taux_actualisation"] | PENDING | |

## 14) Structural calculation assumptions

| ID | Assumption | Default / Value | Units | Code reference | Verification | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| ST-1 | Annual base use per household = lpcd * household_size * 365 / 1000. | Formula | m3/yr | calculer_economies_eau | PENDING | |
| ST-2 | Behavioral reduction applies to usage net of leaks to avoid double counting. | usage_reductible = usage_base - leaks | m3/yr | calculer_economies_eau | PENDING | |
| ST-3 | Leak savings = prevalence * leak volume * correction rate * detection efficiency. | Formula | m3/yr | calculer_economies_eau | PENDING | |
| ST-4 | Default adoption is immediate (mandatory) unless a strategy is provided. | ADOPTION_OBLIGATOIRE | n/a | generer_trajectoires | PENDING | |
| ST-5 | Economies of scale use effective meter count = H * A_max. | Formula | meters | generer_trajectoires | PENDING | |
| ST-6 | Benefits and OPEX scale with adoption A(t). | Proportional scaling | n/a | generer_trajectoires | PENDING | |
| ST-7 | CAPEX either upfront (I0) or spread by new adopters. | etaler_capex flag | n/a | calculer_capex_etale | PENDING | |
| ST-8 | Battery replacement repeats every `duree_vie_batterie` years for AMI/AMR. | Periodic | years | generer_trajectoires | PENDING | |
| ST-9 | Repair costs follow cohort convolution like benefits. | Cohort convolution | n/a | generer_trajectoires | PENDING | |
| ST-10 | Incentives are transfers in economic mode (excluded), costs in financial mode. | Exclude/Include | n/a | actualiser_series | PENDING | |
| ST-11 | MCF multiplies public CAPEX/OPEX only in economic mode. | Partial MCF | n/a | actualiser_series + calculer_van_cumulative | PENDING | |
| ST-12 | Network leak reductions follow linear or exponential ramp; costs can scale with adoption. | Formula | n/a | calculer_dynamique_fuites_reseau | PENDING | |
| ST-13 | Default value_eau uses ParametresValeurEau(valeur_sociale=params.valeur_eau_m3, cout_variable=Quebec default). | Fallback logic | n/a | generer_trajectoires | PENDING | |
| ST-14 | Repair costs in economic mode include household costs without MCF; public share gets MCF. | Partial MCF | n/a | actualiser_series | PENDING | |
| ST-15 | If config_echelle is None, economies of scale are disabled. | Disabled | n/a | executer_modele | PENDING | |
| ST-16 | If persistance is None, behavior is constant using reduction_comportement_pct. | Constant alpha | n/a | generer_trajectoires | PENDING | |
| ST-17 | If params_fuites is None, leak savings use ParametresModele fields and repair costs are excluded. | No repair costs | n/a | executer_modele + calculer_economies_eau | PENDING | |
| ST-18 | If params_fuites uses two-stock mode, leak volume and correction rate are adjusted (weighted volume + persistence). | Adjusted | n/a | calculer_economies_eau | PENDING | |
| ST-19 | If params_adoption is None, adoption is mandatory and immediate. | ADOPTION_OBLIGATOIRE | n/a | generer_trajectoires | PENDING | |
| ST-20 | Total CAPEX = adjusted cost per meter * H_compteurs + cout_infra_fixe (AMI only). | Formula | $ | generer_trajectoires | PENDING | |
| ST-21 | OPEX = cout_exploitation_annuel * H_compteurs, scaled by adoption A(t). | Formula | $/yr | generer_trajectoires | PENDING | |
| ST-22 | Infrastructure deferral benefit is constant annual amount scaled by adoption; optional per-m3 benefit adds to it. | Formula | $/yr | generer_trajectoires | PENDING | |
| ST-23 | VAN = PV(benefits) - PV(costs). | Formula | $ | actualiser_series | VERIFIED | [S4] |
| ST-24 | RBC = PV(benefits) / PV(costs). | Formula | ratio | actualiser_series | VERIFIED | [S4] |
