// Traductions FR/EN pour le Calculateur CBA Compteurs d'Eau
const TRANSLATIONS = {
    fr: {
        // Header
        "header.title": "Analyse Coûts-Bénéfices",
        "header.subtitle": "Compteurs d'eau intelligents — Modèle économique v3.11",
        "header.api_connecting": "Connexion API...",
        "header.api_connected": "API connectée",
        "header.api_disconnected": "API déconnectée",
        "header.api_error": "Erreur API",

        // Loading
        "loading.connecting": "Connexion au serveur...",
        "loading.init": "Initialisation du modèle",

        // Skip link
        "skip_link": "Aller au contenu principal",

        // Sections - Municipalities
        "section.municipalities": "Municipalités",
        "section.municipalities_sub": "Sélectionner un profil prédéfini",
        "section.map_picker": "Choisir sur la carte du Québec",

        // Sections - Project
        "section.project": "Paramètres du projet",
        "section.project_sub": "Configuration de base",

        // Sections - Technology
        "section.technology": "Technologie de comptage",
        "section.technology_sub": "Coûts et installation",

        // Sections - Behavior
        "section.behavior": "Comportement & Fuites",
        "section.behavior_sub": "Paramètres d'économies",

        // Sections - Deployment
        "section.deployment": "Déploiement (adoption)",
        "section.deployment_sub": "Simule un déploiement progressif",

        // Sections - Network
        "section.network": "Fuites réseau",
        "section.network_sub": "Réduction des pertes réseau (optionnel)",

        // Sections - Economic
        "section.economic": "Paramètres économiques",
        "section.economic_sub": "Valorisation de l'eau",

        // Sections - Monte Carlo
        "section.monte_carlo": "Monte Carlo",
        "section.monte_carlo_sub": "Paramètres de simulation",

        // Sections - Optimization
        "section.optimization": "Optimisation",
        "section.optimization_sub": "Déploiement sous contraintes",

        // Sections - Expert
        "section.expert": "Mode Expert",
        "section.expert_sub": "Paramètres avancés",

        // Parameters - Project
        "param.households": "Nombre de ménages",
        "param.household_size": "Taille du ménage (pers.)",
        "param.lpcd": "Consommation (L/pers/jour)",
        "param.horizon": "Horizon d'analyse (années)",
        "param.discount_rate": "Taux d'actualisation (%)",

        // Parameters - Technology
        "param.meter_type": "Type de compteur",
        "param.meter_cost": "Coût unitaire du compteur",
        "param.install_hours": "Heures d'installation",
        "param.hourly_rate": "Taux horaire installation",
        "param.network_cost": "Infrastructure réseau",
        "param.fixed_infra": "Coût infra fixe (IT, intégration)",
        "param.opex_ami": "OPEX AMI non-tech",
        "param.opex_ami_help": "Cyber, logiciels, stockage, télécom (Bas=10, Médian=15, Haut=35)",

        // Meter types
        "meter.ami": "AMI — Intelligent (temps réel)",
        "meter.amr": "AMR — Lecture automatique",
        "meter.manual": "Manuel — Relevé traditionnel",

        // Parameters - Behavior
        "param.behavior_reduction": "Réduction comportementale",
        "param.persistence": "Scénario de persistance",
        "param.leak_scenario": "Scénario de fuites",
        "param.pricing": "Signal-prix actif",
        "param.pricing_help": "<b>Signal-prix</b> = tarification au m³ (le ménage paie selon sa consommation).<br><span style='color:#059669;'>● Avec:</span> facture ↑ si fuite → forte motivation à réparer (<b>85%</b>)<br><span style='color:#dc2626;'>● Sans (Québec):</span> eau incluse dans taxes → motivation réduite (<b>55%</b>)",

        // Persistence scenarios
        "persistence.optimistic": "Optimiste — Effet constant (α = 8%)",
        "persistence.realistic": "Réaliste — Plateau à 2.5%",
        "persistence.pessimistic": "Pessimiste — Fadeout sur 10 ans",
        "persistence.ultra": "Ultra-pessimiste — Aucun effet",

        // Leak scenarios
        "leaks.group_with_price": "Avec signal-prix (réparation plus probable)",
        "leaks.group_without_price": "Sans signal-prix (sans tarification volumétrique)",
        "leaks.group_advanced": "Avancé",
        "leaks.standard": "Standard (20%)",
        "leaks.quebec": "Québec (35%)",
        "leaks.two_stocks": "Québec différencié (2 stocks)",
        "leaks.household": "Ménage (40%)",
        "leaks.subsidy_50": "Subvention 50%",
        "leaks.city": "Ville (meilleure détection)",
        "leaks.household_no_tariff": "Ménage (sans tarif)",
        "leaks.quebec_no_tariff": "Québec (sans tarif)",
        "leaks.two_stocks_no_tariff": "QC différencié (sans tarif)",
        "leaks.custom": "Personnalisé",

        // Advanced leaks
        "leaks.advanced_params": "Paramètres avancés des fuites",
        "leaks.small_leaks": "Petites fuites (toilettes, robinets)",
        "leaks.large_leaks": "Grosses fuites (conduites, chauffe-eau)",
        "leaks.small_prevalence": "Prévalence petites",
        "leaks.small_prevalence_help": "% de ménages avec petite fuite",
        "leaks.small_flow": "Débit petites fuites",
        "leaks.large_prevalence": "Prévalence grosses",
        "leaks.large_prevalence_help": "% de ménages avec grosse fuite",
        "leaks.large_flow": "Débit grosses fuites",
        "leaks.total": "Total :",
        "leaks.total_help": "% des ménages ont une fuite (petites + grosses)",
        "leaks.detection_repair": "Détection & Réparation",
        "leaks.detection_rate": "Taux de détection AMI",
        "leaks.repair_rate": "Taux de réparation (base)",
        "leaks.repair_rate_help": "Sans tarification volumétrique",
        "leaks.detection_factor": "Facteur détection grosses",
        "leaks.detection_factor_help": "Grosses fuites plus visibles",
        "leaks.repair_factor": "Facteur réparation grosses",
        "leaks.repair_factor_help": "Grosses fuites = plus d'incitatif (dommages)",
        "leaks.temporal": "Dynamique temporelle",
        "leaks.new_leaks": "Nouvelles fuites/an",
        "leaks.persistent": "Fuites persistantes",
        "leaks.persistent_help": "% jamais réparées",
        "leaks.long_tail": "Facteur longue traîne",
        "leaks.long_tail_help": "Ralentissement réparations dans le temps",
        "leaks.repair_costs": "Coûts de réparation",
        "leaks.small_cost": "Coût petite fuite",
        "leaks.large_cost": "Coût grosse fuite",
        "leaks.city_share": "Part ville (subvention)",
        "leaks.city_share_help": "0% = ménage paie tout, 100% = ville paie tout",
        "leaks.include_costs": "Inclure coûts de réparation dans la VAN",

        // Adoption scenarios
        "adoption.mandatory": "Obligatoire (100% dès l'année 1)",
        "adoption.fast": "Rapide",
        "adoption.progressive": "Progressif",
        "adoption.slow": "Lent",
        "adoption.new_households": "Nouveaux ménages",
        "adoption.by_sector": "Par secteur",
        "adoption.custom": "Personnalisé",
        "adoption.disabled": "Désactivé (test)",
        "adoption.max": "Adoption max (%)",
        "adoption.speed": "Vitesse (k)",
        "adoption.midpoint": "Point médian (t0)",
        "adoption.spread_capex": "Étaler le CAPEX",

        // Network leaks
        "network.enable": "Activer",
        "network.losses": "Pertes réseau (m³/an)",
        "network.max_reduction": "Réduction max (%)",
        "network.mode": "Mode",
        "network.linear": "Linéaire",
        "network.exponential": "Exponentiel",
        "network.years": "Années pour atteindre",
        "network.weight_adoption": "Pondérer par adoption",

        // Economic parameters
        "economic.mode_economic": "Mode Économique (valeur sociale)",
        "economic.mode_financial": "Mode Financier (coût variable)",
        "economic.water_preset": "Valeur de l'eau (preset)",
        "economic.custom": "Personnalisé",
        "economic.quebec": "Québec",
        "economic.conservative": "Conservateur",
        "economic.scarcity": "Rareté",
        "economic.quebec_mcf": "Québec + MCF",
        "economic.social_value": "Valeur sociale de l'eau",
        "economic.variable_cost": "Coût variable de production",
        "economic.economies_scale": "Économies d'échelle (>10k compteurs)",
        "economic.economies_scale_help": "Réduction 5-20% sur coûts matériel selon volume",
        "economic.infra_deferral": "Report d'infrastructure (optionnel)",
        "economic.infra_deferral_help": "Valorise les économies en eau par le report d'investissements en infrastructure (stations, réseaux).",
        "economic.annual_benefit": "Bénéfice annuel fixe",
        "economic.annual_benefit_help": "Report capacité: usine, réservoirs ($/an)",
        "economic.benefit_per_m3": "Bénéfice par m³ économisé",
        "economic.benefit_per_m3_help": "Coût marginal infrastructure évité",

        // Monte Carlo
        "mc.simulations": "Monte Carlo – Simulations",
        "mc.seed": "Monte Carlo – Seed",
        "mc.custom_distributions": "Distributions personnalisées",
        "mc.custom_distributions_help": "Configurez les distributions pour chaque paramètre clé.",
        "mc.behavior_reduction": "Réduction comportementale (%)",
        "mc.lpcd": "LPCD (L/pers/jour)",
        "mc.meter_cost": "Coût compteur ($)",
        "mc.water_value": "Valeur eau ($/m³)",
        "mc.min": "Min",
        "mc.mode": "Mode",
        "mc.max": "Max",
        "mc.use_custom": "Utiliser distributions personnalisées",
        "mc.export_config": "Exporter config",
        "mc.import_config": "Importer config",

        // Optimization
        "optim.budget_max": "Budget annuel max",
        "optim.capacity_max": "Capacité installation",
        "optim.objective": "Objectif",
        "optim.maximize_van": "Maximiser la VAN",
        "optim.minimize_payback": "Minimiser le payback",
        "optim.horizon": "Horizon déploiement",
        "optim.run": "Optimiser le déploiement",
        "optim.optimal": "Scénario optimal",

        // Expert mode
        "expert.preset": "Preset expert",
        "expert.standard": "Standard (défaut)",
        "expert.conservative": "Conservateur (prudent)",
        "expert.aggressive": "Agressif (optimiste)",
        "expert.custom": "Personnalisé",
        "expert.mcf": "Coût Marginal des Fonds publics (MCF)",
        "expert.mcf_help": "Le MCF représente le coût social de lever 1$ de taxes. Treasury Board Canada: 0.20",
        "expert.apply_mcf": "Appliquer le MCF aux dépenses publiques",
        "expert.mcf_value": "Valeur MCF",
        "expert.persistence_advanced": "Persistance comportementale (avancé)",
        "expert.persistence_help": "Paramètres fins pour le modèle de décroissance comportementale.",
        "expert.lambda_decay": "Lambda décroissance",
        "expert.lambda_decay_help": "Vitesse de déclin vers le plateau (mode réaliste)",
        "expert.alpha_plateau": "Alpha plateau (%)",
        "expert.alpha_plateau_help": "Réduction résiduelle à long terme",
        "expert.externalities": "Externalités environnementales",
        "expert.externalities_value": "Valeur externalités",
        "expert.externalities_help": "Carbone, écosystèmes (inclus dans valeur sociale)",
        "expert.opex_detailed": "OPEX détaillé (AMI)",
        "expert.opex_detailed_help": "Ventilation des coûts opérationnels non-techniques AMI.",
        "expert.cyber": "Cybersécurité",
        "expert.licenses": "Licences logicielles",
        "expert.storage": "Stockage données",
        "expert.telecom": "Télécom",
        "expert.opex_total": "Total OPEX non-tech:",

        // Metrics
        "metric.van": "Valeur Actualisée Nette",
        "metric.rbc": "Ratio Bénéfices/Coûts",
        "metric.payback": "Période de récupération",
        "metric.lcsw": "LCSW",
        "metric.invest": "Investissement total",
        "metric.savings": "Économies d'eau",
        "metric.years": "années",
        "metric.threshold": "seuil",
        "metric.initial": "initial",
        "metric.per_household": "m³/ménage/an",
        "metric.over_years": "sur {n} ans",

        // Actions
        "action.export_json": "Exporter JSON",
        "action.export_csv": "Exporter CSV",
        "action.export_pdf": "Exporter PDF",
        "action.copy_link": "Copier lien",
        "action.save": "Sauvegarder",
        "action.comparator": "Comparateur",
        "action.run_mc": "Lancer",
        "action.running": "Simulation...",

        // Comparator
        "comparator.title": "Scénarios sauvegardés",
        "comparator.clear_all": "Tout effacer",
        "comparator.no_scenarios": "Aucun scénario sauvegardé. Cliquez sur \"Sauvegarder\" pour ajouter le scénario actuel.",
        "comparator.scenarios_count": "{n} scénario(s) sauvegardé(s)",
        "comparator.scenario": "Scénario",
        "comparator.actions": "Actions",
        "comparator.load": "Charger",

        // Hypotheses
        "hypotheses.title": "Hypothèses effectives",
        "hypotheses.expand": "(cliquer pour développer)",
        "hypotheses.project": "Projet",
        "hypotheses.costs": "Coûts",
        "hypotheses.deployment": "Déploiement",
        "hypotheses.leaks": "Fuites",
        "hypotheses.behavior": "Comportement",
        "hypotheses.valuation": "Valorisation",

        // Methodology
        "methodology.title": "Méthodologie",
        "methodology.expand": "(formules et conventions)",
        "methodology.van_formula": "Valeur Actualisée Nette (VAN)",
        "methodology.sign_conventions": "Conventions de signes",
        "methodology.benefits": "Bénéfices (+)",
        "methodology.benefits_desc": "économies d'eau valorisées, report d'infrastructure",
        "methodology.costs": "Coûts (−)",
        "methodology.costs_desc": "investissement initial (CAPEX), exploitation (OPEX)",
        "methodology.perspectives": "Perspectives d'analyse",
        "methodology.economic_desc": "valorise l'eau au coût social complet (inclut externalités)",
        "methodology.financial_desc": "valorise l'eau au coût variable évité uniquement",
        "methodology.indicators": "Indicateurs clés",
        "methodology.rbc_desc": "viable si > 1",
        "methodology.lcsw_desc": "coût pour économiser 1 m³ d'eau",
        "methodology.payback_desc": "années pour récupérer l'investissement",
        "methodology.sources": "Sources: MAMH (2019-2025), méthodologie CBA standard du Conseil du Trésor.",

        // Recommendation messages
        "msg.viable": "PROJET VIABLE",
        "msg.marginal": "PROJET MARGINAL",
        "msg.not_viable": "PROJET NON RENTABLE",
        "msg.positive_van": "VAN positive de",
        "msg.negative_van": "VAN négative de",

        // Charts
        "chart.van_cumulative": "VAN Cumulative",
        "chart.van_cumulative_sub": "Évolution sur l'horizon d'analyse",
        "chart.sensitivity": "Sensibilité des Paramètres (Tornado)",
        "chart.sensitivity_sub": "Impact d'une variation de ±10%",
        "chart.waterfall": "Contribution à la VAN (Waterfall)",
        "chart.waterfall_sub": "Décomposition des bénéfices et coûts",
        "chart.technologies": "Comparaison des Technologies",
        "chart.technologies_sub": "VAN par type de compteur",
        "chart.persistence": "Scénarios de Persistance",
        "chart.persistence_sub": "Impact sur la VAN cumulative",
        "chart.alpha": "Coefficient α (comportement)",
        "chart.alpha_sub": "Évolution de l'effet comportemental",
        "chart.perspectives": "Perspectives (ville/ménages)",
        "chart.perspectives_sub": "Décomposition par payeur",
        "chart.leaks": "Dynamique des fuites",
        "chart.leaks_sub": "Évolution du stock de fuites",
        "chart.decomposition": "Décomposition des économies",
        "chart.decomposition_sub": "Comportement vs Fuites",
        "chart.monte_carlo": "Distribution Monte Carlo",
        "chart.monte_carlo_sub": "Histogramme de la VAN",
        "chart.drivers": "Drivers Monte Carlo",
        "chart.drivers_sub": "Corrélation avec la VAN",

        // MC Stats
        "mc.prob_positive": "P(VAN > 0)",
        "mc.median": "VAN Médiane",
        "mc.ci_90": "IC 90% (P5-P95)",
        "mc.std": "Écart-type",

        // Calibration modal
        "calibration.title": "Assistant de calibrage",
        "calibration.subtitle": "Importer des données de consommation pour calibrer les paramètres",
        "calibration.drop_file": "Glisser un fichier CSV ici",
        "calibration.or_click": "ou cliquer pour sélectionner",
        "calibration.format": "Format attendu (CSV):",
        "calibration.lpcd_suggested": "LPCD suggéré",
        "calibration.leak_prevalence": "Prévalence fuites",
        "calibration.confidence": "Confiance:",
        "calibration.stats": "Statistiques des données",
        "calibration.mean": "Consommation moyenne:",
        "calibration.cv": "Coefficient variation:",
        "calibration.seasonality": "Variance saisonnière:",
        "calibration.anomalies": "Anomalies détectées:",
        "calibration.apply": "Appliquer les valeurs",
        "calibration.reset": "Réinitialiser",
        "calibration.btn": "Calibrer depuis données",
        "calibration.btn_help": "Importer un CSV de consommation mensuelle",

        // Map modal
        "map.title": "Sélectionner une municipalité",
        "map.subtitle": "Cliquez sur une municipalité pour charger ses données",
        "map.data_source": "Données: BIL 2023 (MAMH) • Statistique Canada Recensement 2021",

        // Footer
        "footer.developed_by": "Modèle développé par",
        "footer.project": "Projet Mitacs / Réseau Environnement Québec",
        "footer.source": "Code source",
        "footer.docs": "Documentation",
        "footer.methodology": "Méthodologie",

        // Units
        "unit.year": "an",
        "unit.years": "ans",
        "unit.per_year": "/an",
        "unit.per_unit": "/u",
        "unit.per_unit_year": "/u/an",
        "unit.hours": "h",
        "unit.dollars": "$",
        "unit.dollars_per_hour": "$/h",
        "unit.dollars_per_m3": "$/m³",
        "unit.m3_year": "m³/an",
        "unit.percent": "%",
    },

    en: {
        // Header
        "header.title": "Cost-Benefit Analysis",
        "header.subtitle": "Smart water meters — Economic model v3.11",
        "header.api_connecting": "Connecting API...",
        "header.api_connected": "API connected",
        "header.api_disconnected": "API disconnected",
        "header.api_error": "API error",

        // Loading
        "loading.connecting": "Connecting to server...",
        "loading.init": "Initializing model",

        // Skip link
        "skip_link": "Skip to main content",

        // Sections - Municipalities
        "section.municipalities": "Municipalities",
        "section.municipalities_sub": "Select a preset profile",
        "section.map_picker": "Choose from Quebec map",

        // Sections - Project
        "section.project": "Project Parameters",
        "section.project_sub": "Basic configuration",

        // Sections - Technology
        "section.technology": "Metering Technology",
        "section.technology_sub": "Costs and installation",

        // Sections - Behavior
        "section.behavior": "Behavior & Leaks",
        "section.behavior_sub": "Savings parameters",

        // Sections - Deployment
        "section.deployment": "Deployment (adoption)",
        "section.deployment_sub": "Simulates progressive deployment",

        // Sections - Network
        "section.network": "Network Leaks",
        "section.network_sub": "Network loss reduction (optional)",

        // Sections - Economic
        "section.economic": "Economic Parameters",
        "section.economic_sub": "Water valuation",

        // Sections - Monte Carlo
        "section.monte_carlo": "Monte Carlo",
        "section.monte_carlo_sub": "Simulation parameters",

        // Sections - Optimization
        "section.optimization": "Optimization",
        "section.optimization_sub": "Deployment under constraints",

        // Sections - Expert
        "section.expert": "Expert Mode",
        "section.expert_sub": "Advanced parameters",

        // Parameters - Project
        "param.households": "Number of households",
        "param.household_size": "Household size (pers.)",
        "param.lpcd": "Consumption (L/pers/day)",
        "param.horizon": "Analysis horizon (years)",
        "param.discount_rate": "Discount rate (%)",

        // Parameters - Technology
        "param.meter_type": "Meter type",
        "param.meter_cost": "Unit meter cost",
        "param.install_hours": "Installation hours",
        "param.hourly_rate": "Hourly installation rate",
        "param.network_cost": "Network infrastructure",
        "param.fixed_infra": "Fixed infra cost (IT, integration)",
        "param.opex_ami": "AMI non-tech OPEX",
        "param.opex_ami_help": "Cyber, software, storage, telecom (Low=10, Median=15, High=35)",

        // Meter types
        "meter.ami": "AMI — Smart (real-time)",
        "meter.amr": "AMR — Automatic reading",
        "meter.manual": "Manual — Traditional reading",

        // Parameters - Behavior
        "param.behavior_reduction": "Behavioral reduction",
        "param.persistence": "Persistence scenario",
        "param.leak_scenario": "Leak scenario",
        "param.pricing": "Price signal active",
        "param.pricing_help": "<b>Price signal</b> = volumetric pricing (household pays per m³ consumed).<br><span style='color:#059669;'>● With:</span> bill ↑ if leak → strong motivation to repair (<b>85%</b>)<br><span style='color:#dc2626;'>● Without (Quebec):</span> water included in taxes → reduced motivation (<b>55%</b>)",

        // Persistence scenarios
        "persistence.optimistic": "Optimistic — Constant effect (α = 8%)",
        "persistence.realistic": "Realistic — Plateau at 2.5%",
        "persistence.pessimistic": "Pessimistic — Fadeout over 10 years",
        "persistence.ultra": "Ultra-pessimistic — No effect",

        // Leak scenarios
        "leaks.group_with_price": "With price signal (repair more likely)",
        "leaks.group_without_price": "Without price signal (no volumetric pricing)",
        "leaks.group_advanced": "Advanced",
        "leaks.standard": "Standard (20%)",
        "leaks.quebec": "Quebec (35%)",
        "leaks.two_stocks": "Quebec differentiated (2 stocks)",
        "leaks.household": "Household (40%)",
        "leaks.subsidy_50": "50% Subsidy",
        "leaks.city": "City (better detection)",
        "leaks.household_no_tariff": "Household (no tariff)",
        "leaks.quebec_no_tariff": "Quebec (no tariff)",
        "leaks.two_stocks_no_tariff": "QC differentiated (no tariff)",
        "leaks.custom": "Custom",

        // Advanced leaks
        "leaks.advanced_params": "Advanced leak parameters",
        "leaks.small_leaks": "Small leaks (toilets, faucets)",
        "leaks.large_leaks": "Large leaks (pipes, water heaters)",
        "leaks.small_prevalence": "Small prevalence",
        "leaks.small_prevalence_help": "% of households with small leak",
        "leaks.small_flow": "Small leak flow",
        "leaks.large_prevalence": "Large prevalence",
        "leaks.large_prevalence_help": "% of households with large leak",
        "leaks.large_flow": "Large leak flow",
        "leaks.total": "Total:",
        "leaks.total_help": "% of households have a leak (small + large)",
        "leaks.detection_repair": "Detection & Repair",
        "leaks.detection_rate": "AMI detection rate",
        "leaks.repair_rate": "Repair rate (base)",
        "leaks.repair_rate_help": "Without volumetric pricing",
        "leaks.detection_factor": "Large detection factor",
        "leaks.detection_factor_help": "Large leaks more visible",
        "leaks.repair_factor": "Large repair factor",
        "leaks.repair_factor_help": "Large leaks = more incentive (damages)",
        "leaks.temporal": "Temporal dynamics",
        "leaks.new_leaks": "New leaks/year",
        "leaks.persistent": "Persistent leaks",
        "leaks.persistent_help": "% never repaired",
        "leaks.long_tail": "Long tail factor",
        "leaks.long_tail_help": "Repair slowdown over time",
        "leaks.repair_costs": "Repair costs",
        "leaks.small_cost": "Small leak cost",
        "leaks.large_cost": "Large leak cost",
        "leaks.city_share": "City share (subsidy)",
        "leaks.city_share_help": "0% = household pays all, 100% = city pays all",
        "leaks.include_costs": "Include repair costs in NPV",

        // Adoption scenarios
        "adoption.mandatory": "Mandatory (100% from year 1)",
        "adoption.fast": "Fast",
        "adoption.progressive": "Progressive",
        "adoption.slow": "Slow",
        "adoption.new_households": "New households",
        "adoption.by_sector": "By sector",
        "adoption.custom": "Custom",
        "adoption.disabled": "Disabled (test)",
        "adoption.max": "Max adoption (%)",
        "adoption.speed": "Speed (k)",
        "adoption.midpoint": "Midpoint (t0)",
        "adoption.spread_capex": "Spread CAPEX",

        // Network leaks
        "network.enable": "Enable",
        "network.losses": "Network losses (m³/year)",
        "network.max_reduction": "Max reduction (%)",
        "network.mode": "Mode",
        "network.linear": "Linear",
        "network.exponential": "Exponential",
        "network.years": "Years to reach",
        "network.weight_adoption": "Weight by adoption",

        // Economic parameters
        "economic.mode_economic": "Economic Mode (social value)",
        "economic.mode_financial": "Financial Mode (variable cost)",
        "economic.water_preset": "Water value (preset)",
        "economic.custom": "Custom",
        "economic.quebec": "Quebec",
        "economic.conservative": "Conservative",
        "economic.scarcity": "Scarcity",
        "economic.quebec_mcf": "Quebec + MCF",
        "economic.social_value": "Social value of water",
        "economic.variable_cost": "Variable production cost",
        "economic.economies_scale": "Economies of scale (>10k meters)",
        "economic.economies_scale_help": "5-20% reduction on equipment costs by volume",
        "economic.infra_deferral": "Infrastructure deferral (optional)",
        "economic.infra_deferral_help": "Values water savings through deferred infrastructure investments (plants, networks).",
        "economic.annual_benefit": "Fixed annual benefit",
        "economic.annual_benefit_help": "Capacity deferral: plant, reservoirs ($/year)",
        "economic.benefit_per_m3": "Benefit per m³ saved",
        "economic.benefit_per_m3_help": "Avoided marginal infrastructure cost",

        // Monte Carlo
        "mc.simulations": "Monte Carlo – Simulations",
        "mc.seed": "Monte Carlo – Seed",
        "mc.custom_distributions": "Custom distributions",
        "mc.custom_distributions_help": "Configure distributions for each key parameter.",
        "mc.behavior_reduction": "Behavioral reduction (%)",
        "mc.lpcd": "LPCD (L/pers/day)",
        "mc.meter_cost": "Meter cost ($)",
        "mc.water_value": "Water value ($/m³)",
        "mc.min": "Min",
        "mc.mode": "Mode",
        "mc.max": "Max",
        "mc.use_custom": "Use custom distributions",
        "mc.export_config": "Export config",
        "mc.import_config": "Import config",

        // Optimization
        "optim.budget_max": "Max annual budget",
        "optim.capacity_max": "Installation capacity",
        "optim.objective": "Objective",
        "optim.maximize_van": "Maximize NPV",
        "optim.minimize_payback": "Minimize payback",
        "optim.horizon": "Deployment horizon",
        "optim.run": "Optimize deployment",
        "optim.optimal": "Optimal scenario",

        // Expert mode
        "expert.preset": "Expert preset",
        "expert.standard": "Standard (default)",
        "expert.conservative": "Conservative (cautious)",
        "expert.aggressive": "Aggressive (optimistic)",
        "expert.custom": "Custom",
        "expert.mcf": "Marginal Cost of Public Funds (MCF)",
        "expert.mcf_help": "MCF represents the social cost of raising $1 in taxes. Treasury Board Canada: 0.20",
        "expert.apply_mcf": "Apply MCF to public expenditures",
        "expert.mcf_value": "MCF value",
        "expert.persistence_advanced": "Behavioral persistence (advanced)",
        "expert.persistence_help": "Fine parameters for the behavioral decay model.",
        "expert.lambda_decay": "Lambda decay",
        "expert.lambda_decay_help": "Decline speed towards plateau (realistic mode)",
        "expert.alpha_plateau": "Alpha plateau (%)",
        "expert.alpha_plateau_help": "Long-term residual reduction",
        "expert.externalities": "Environmental externalities",
        "expert.externalities_value": "Externalities value",
        "expert.externalities_help": "Carbon, ecosystems (included in social value)",
        "expert.opex_detailed": "Detailed OPEX (AMI)",
        "expert.opex_detailed_help": "Breakdown of AMI non-technical operating costs.",
        "expert.cyber": "Cybersecurity",
        "expert.licenses": "Software licenses",
        "expert.storage": "Data storage",
        "expert.telecom": "Telecom",
        "expert.opex_total": "Total non-tech OPEX:",

        // Metrics
        "metric.van": "Net Present Value",
        "metric.rbc": "Benefit-Cost Ratio",
        "metric.payback": "Payback period",
        "metric.lcsw": "LCSW",
        "metric.invest": "Total investment",
        "metric.savings": "Water savings",
        "metric.years": "years",
        "metric.threshold": "threshold",
        "metric.initial": "initial",
        "metric.per_household": "m³/household/yr",
        "metric.over_years": "over {n} years",

        // Actions
        "action.export_json": "Export JSON",
        "action.export_csv": "Export CSV",
        "action.export_pdf": "Export PDF",
        "action.copy_link": "Copy link",
        "action.save": "Save",
        "action.comparator": "Comparator",
        "action.run_mc": "Run",
        "action.running": "Running...",

        // Comparator
        "comparator.title": "Saved scenarios",
        "comparator.clear_all": "Clear all",
        "comparator.no_scenarios": "No saved scenarios. Click \"Save\" to add the current scenario.",
        "comparator.scenarios_count": "{n} scenario(s) saved",
        "comparator.scenario": "Scenario",
        "comparator.actions": "Actions",
        "comparator.load": "Load",

        // Hypotheses
        "hypotheses.title": "Effective hypotheses",
        "hypotheses.expand": "(click to expand)",
        "hypotheses.project": "Project",
        "hypotheses.costs": "Costs",
        "hypotheses.deployment": "Deployment",
        "hypotheses.leaks": "Leaks",
        "hypotheses.behavior": "Behavior",
        "hypotheses.valuation": "Valuation",

        // Methodology
        "methodology.title": "Methodology",
        "methodology.expand": "(formulas and conventions)",
        "methodology.van_formula": "Net Present Value (NPV)",
        "methodology.sign_conventions": "Sign conventions",
        "methodology.benefits": "Benefits (+)",
        "methodology.benefits_desc": "valued water savings, infrastructure deferral",
        "methodology.costs": "Costs (−)",
        "methodology.costs_desc": "initial investment (CAPEX), operating (OPEX)",
        "methodology.perspectives": "Analysis perspectives",
        "methodology.economic_desc": "values water at full social cost (includes externalities)",
        "methodology.financial_desc": "values water at avoided variable cost only",
        "methodology.indicators": "Key indicators",
        "methodology.rbc_desc": "viable if > 1",
        "methodology.lcsw_desc": "cost to save 1 m³ of water",
        "methodology.payback_desc": "years to recover investment",
        "methodology.sources": "Sources: MAMH (2019-2025), Treasury Board standard CBA methodology.",

        // Recommendation messages
        "msg.viable": "VIABLE PROJECT",
        "msg.marginal": "MARGINAL PROJECT",
        "msg.not_viable": "NOT PROFITABLE",
        "msg.positive_van": "Positive NPV of",
        "msg.negative_van": "Negative NPV of",

        // Charts
        "chart.van_cumulative": "Cumulative NPV",
        "chart.van_cumulative_sub": "Evolution over analysis horizon",
        "chart.sensitivity": "Parameter Sensitivity (Tornado)",
        "chart.sensitivity_sub": "Impact of ±10% variation",
        "chart.waterfall": "NPV Contribution (Waterfall)",
        "chart.waterfall_sub": "Breakdown of benefits and costs",
        "chart.technologies": "Technology Comparison",
        "chart.technologies_sub": "NPV by meter type",
        "chart.persistence": "Persistence Scenarios",
        "chart.persistence_sub": "Impact on cumulative NPV",
        "chart.alpha": "α Coefficient (behavior)",
        "chart.alpha_sub": "Behavioral effect evolution",
        "chart.perspectives": "Perspectives (city/households)",
        "chart.perspectives_sub": "Breakdown by payer",
        "chart.leaks": "Leak dynamics",
        "chart.leaks_sub": "Leak stock evolution",
        "chart.decomposition": "Savings decomposition",
        "chart.decomposition_sub": "Behavior vs Leaks",
        "chart.monte_carlo": "Monte Carlo Distribution",
        "chart.monte_carlo_sub": "NPV histogram",
        "chart.drivers": "Monte Carlo Drivers",
        "chart.drivers_sub": "Correlation with NPV",

        // MC Stats
        "mc.prob_positive": "P(NPV > 0)",
        "mc.median": "NPV Median",
        "mc.ci_90": "90% CI (P5-P95)",
        "mc.std": "Std deviation",

        // Calibration modal
        "calibration.title": "Calibration assistant",
        "calibration.subtitle": "Import consumption data to calibrate parameters",
        "calibration.drop_file": "Drop a CSV file here",
        "calibration.or_click": "or click to select",
        "calibration.format": "Expected format (CSV):",
        "calibration.lpcd_suggested": "Suggested LPCD",
        "calibration.leak_prevalence": "Leak prevalence",
        "calibration.confidence": "Confidence:",
        "calibration.stats": "Data statistics",
        "calibration.mean": "Average consumption:",
        "calibration.cv": "Coefficient of variation:",
        "calibration.seasonality": "Seasonal variance:",
        "calibration.anomalies": "Anomalies detected:",
        "calibration.apply": "Apply values",
        "calibration.reset": "Reset",
        "calibration.btn": "Calibrate from data",
        "calibration.btn_help": "Import monthly consumption CSV",

        // Map modal
        "map.title": "Select a municipality",
        "map.subtitle": "Click on a municipality to load its data",
        "map.data_source": "Data: BIL 2023 (MAMH) • Statistics Canada Census 2021",

        // Footer
        "footer.developed_by": "Model developed by",
        "footer.project": "Mitacs / Réseau Environnement Québec Project",
        "footer.source": "Source code",
        "footer.docs": "Documentation",
        "footer.methodology": "Methodology",

        // Units
        "unit.year": "yr",
        "unit.years": "years",
        "unit.per_year": "/yr",
        "unit.per_unit": "/u",
        "unit.per_unit_year": "/u/yr",
        "unit.hours": "h",
        "unit.dollars": "$",
        "unit.dollars_per_hour": "$/h",
        "unit.dollars_per_m3": "$/m³",
        "unit.m3_year": "m³/yr",
        "unit.percent": "%",
    }
};

// Langue courante
let currentLang = 'fr';

// Fonction de traduction
function t(key, params = {}) {
    let text = TRANSLATIONS[currentLang][key] || TRANSLATIONS['fr'][key] || key;
    // Remplacer les paramètres {param}
    for (const [k, v] of Object.entries(params)) {
        text = text.replace(`{${k}}`, v);
    }
    return text;
}

// Changer de langue
function setLanguage(lang) {
    if (!TRANSLATIONS[lang]) return;
    currentLang = lang;
    localStorage.setItem('cba_lang', lang);
    updateUILanguage();
}

// Mettre à jour l'UI avec la nouvelle langue
function updateUILanguage() {
    // Mettre à jour tous les éléments avec data-i18n (sauf option et optgroup)
    document.querySelectorAll('[data-i18n]:not(option):not(optgroup)').forEach(el => {
        const key = el.getAttribute('data-i18n');
        const params = el.getAttribute('data-i18n-params');
        if (params) {
            try {
                el.textContent = t(key, JSON.parse(params));
            } catch (e) {
                el.textContent = t(key);
            }
        } else {
            el.textContent = t(key);
        }
    });

    // Mettre à jour les options select
    document.querySelectorAll('option[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        el.textContent = t(key);
    });

    // Mettre à jour les optgroup labels
    document.querySelectorAll('optgroup[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        el.label = t(key);
    });

    // Mettre à jour les placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        el.placeholder = t(key);
    });

    // Mettre à jour les titres (aria-label, title)
    document.querySelectorAll('[data-i18n-aria]').forEach(el => {
        const key = el.getAttribute('data-i18n-aria');
        el.setAttribute('aria-label', t(key));
    });

    // Mettre à jour le toggle de langue
    const langToggle = document.getElementById('lang-toggle');
    if (langToggle) {
        langToggle.textContent = currentLang.toUpperCase();
    }

    // Mettre à jour le HTML lang attribute
    document.documentElement.lang = currentLang;

    // Mettre à jour le mode label (cas spécial car dynamique)
    const modeLabel = document.getElementById('mode-label');
    if (modeLabel && typeof modeEconomique !== 'undefined') {
        modeLabel.textContent = t(modeEconomique ? 'economic.mode_economic' : 'economic.mode_financial');
    }
}

// Basculer entre FR et EN
function toggleLanguage() {
    const newLang = currentLang === 'fr' ? 'en' : 'fr';
    setLanguage(newLang);
}

// Initialiser la langue au chargement
function initLanguage() {
    const saved = localStorage.getItem('cba_lang');
    if (saved && TRANSLATIONS[saved]) {
        currentLang = saved;
    }
    // Mettre à jour immédiatement
    document.documentElement.lang = currentLang;
    // Attendre que le DOM soit chargé pour traduire
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updateUILanguage);
    } else {
        updateUILanguage();
    }
}

// Auto-init
initLanguage();
