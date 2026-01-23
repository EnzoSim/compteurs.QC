# TASKS - Calculateur CBA Compteurs d'Eau

## Contexte

Ce fichier liste les tâches pour compléter l'intégration du calculateur.

**Fichiers principaux:**
- `api.py` - API FastAPI
- `index.html` - Frontend (HTML + JS inline)
- `analyse_compteurs_eau.py` - Modèle de calcul Python
- `test_api.py` - Tests de non-régression

---

## Tâches complétées

### ✅ TASK-02: Export JSON complet inputs + outputs
**Statut:** COMPLÉTÉ

Export JSON incluant inputs + outputs (VAN, RBC, séries) + timestamp + version modèle.

---

### ✅ TASK-03: Mode expert complet
**Statut:** COMPLÉTÉ

Toggle "Mode expert" avec paramètres avancés:
- MCF optionnel (coût marginal des fonds publics, Treasury Board: 0.20)
- Paramètres persistance personnalisables (lambda_decay, alpha_plateau)
- OPEX détaillé (cyber, licences, stockage, télécom)
- Presets: Standard, Conservateur, Agressif

**Implémentation API:**
- Paramètres `expert_lambda_decay`, `expert_alpha_plateau`, `appliquer_mcf`, `mcf` dans `CalculRequest`
- `get_persistance()` accepte les valeurs custom pour le mode "réaliste"
- MCF ajuste la VAN et le RBC quand activé

---

### ✅ TASK-04: Monte Carlo avancé
**Statut:** COMPLÉTÉ

Configuration des distributions personnalisées:
- Min/max/mode par paramètre
- Endpoint `/api/monte_carlo_advanced`
- Endpoint `/api/monte_carlo/distributions`
- Export/import configurations

---

### ✅ TASK-05: Assistant calibrage automatique
**Statut:** COMPLÉTÉ

Import CSV de consommation mensuelle:
- Calcul LPCD, variance saisonnière, anomalies
- Estimation prévalence fuites
- Endpoint `/api/calibrate_from_data`
- Modal avec suggestions et intervalles de confiance

---

### ✅ TASK-06: Déploiement optimisé sous contraintes
**Statut:** COMPLÉTÉ

Optimisation du déploiement:
- Contraintes budget annuel et capacité installation
- Objectif: maximiser VAN ou minimiser payback
- Endpoint `/api/optimize_deployment`
- Comparaison de scénarios

---

### ✅ TASK-07: Architecture CI/CD et versioning API
**Statut:** COMPLÉTÉ

Infrastructure de déploiement:
- `Dockerfile` pour containerisation
- `.github/workflows/ci.yml` pour GitHub Actions
- `CHANGELOG.md` structuré
- Header `X-API-Version` dans les réponses

---

### ✅ TASK-08: Observabilité production
**Statut:** COMPLÉTÉ

Monitoring et logs:
- Logging structuré JSON
- Métriques: temps réponse, requêtes, erreurs
- Endpoint `/api/metrics` (format Prometheus)
- Health check enrichi `/api/health` (uptime, version, erreurs)

---

### ✅ TASK-09: Accessibilité et responsive
**Statut:** COMPLÉTÉ

Améliorations a11y et mobile:
- Skip link pour navigation clavier
- Focus visible amélioré
- Media queries responsive (mobile, tablette)
- Sidebar collapsible sur mobile
- Support prefers-reduced-motion

---

### ✅ TASK-10: Bilingue (FR/EN)
**Statut:** COMPLÉTÉ

Support multilingue:
- Fichier `translations.js` avec ~400 clés de traduction FR/EN
- Toggle langue dans le header
- 201 éléments HTML avec attribut `data-i18n`
- Support des éléments `<option>` et `<optgroup>` dans `updateUILanguage()`

---

## Tâches facultatives (P3)

### 🔵 TASK-01: Segmentation par typologies de logements
**Statut:** FACULTATIF

Permettre d'analyser différents types de logements (maisons, condos, appartements) avec des paramètres différents et une agrégation pondérée.

**À implémenter si besoin:**
1. API: Endpoint `/api/segmented_analysis` avec tableau de segments
2. UI: Section "Segmentation" avec ajout/suppression de segments
3. Calcul: Agrégation pondérée des résultats

**Notes:** Le modèle a déjà des bases pour la segmentation (v3.11).

---

### 🔵 TASK-11: Comptes utilisateurs et sauvegarde cloud
**Statut:** FACULTATIF

Permettre aux utilisateurs de sauvegarder leurs scénarios en ligne.

**À implémenter si besoin:**
1. Backend auth: JWT ou OAuth (Google/GitHub)
2. Base de données: PostgreSQL ou SQLite
3. Endpoints: login, CRUD scénarios
4. UI: Connexion, liste scénarios cloud

**Dépendances requises:** `sqlalchemy`, `python-jose` (JWT)

**Note:** Complexité élevée, nécessite infrastructure supplémentaire.

---

## Résumé

| Tâche | Description | Statut |
|-------|-------------|--------|
| TASK-02 | Export JSON complet | ✅ Complété |
| TASK-03 | Mode expert | ✅ Complété |
| TASK-04 | Monte Carlo avancé | ✅ Complété |
| TASK-05 | Calibrage automatique | ✅ Complété |
| TASK-06 | Optimisation déploiement | ✅ Complété |
| TASK-07 | CI/CD | ✅ Complété |
| TASK-08 | Observabilité | ✅ Complété |
| TASK-09 | Accessibilité | ✅ Complété |
| TASK-10 | Bilingue | ✅ Complété |
| TASK-01 | Segmentation | 🔵 Facultatif |
| TASK-11 | Comptes cloud | 🔵 Facultatif |

---

## Notes pour les agents

- Toujours lancer les tests après modification: `python3 -m pytest test_api.py -v`
- Le modèle core (`analyse_compteurs_eau.py`) est stable, éviter de le modifier
- CORS configurable via variable d'environnement `CORS_ORIGINS`
