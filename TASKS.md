# TASKS - Calculateur CBA Compteurs d'Eau

## Contexte

Ce fichier liste les tâches restantes pour compléter l'intégration du calculateur.
Les tâches P0/P1 critiques ont été complétées. Reste les améliorations P1/P2.

**Fichiers principaux:**
- `api.py` - API FastAPI
- `index.html` - Frontend (HTML + JS inline)
- `analyse_compteurs_eau.py` - Modèle de calcul Python
- `test_api.py` - Tests de non-régression

---

## P1 - Importantes

### TASK-01: Segmentation par typologies de logements

**Description:** Permettre d'analyser différents types de logements (maisons, condos, appartements) avec des paramètres différents et une agrégation pondérée.

**À implémenter:**
1. API: Ajouter endpoint `/api/segmented_analysis` qui accepte un tableau de segments
2. Chaque segment: `{ type: "maison"|"condo"|"appartement", nb_menages, lpcd, taille_menage, poids }`
3. UI: Ajouter section "Segmentation" avec possibilité d'ajouter/supprimer des segments
4. Calcul: Exécuter le modèle pour chaque segment et agréger les résultats pondérés

**Fichiers à modifier:** `api.py`, `index.html`

**Notes:** Le modèle `analyse_compteurs_eau.py` a déjà des bases pour la segmentation (v3.11 changelog). Vérifier `creer_params_segment()`.

---

### TASK-02: Export JSON complet inputs + outputs

**Description:** L'export JSON actuel n'exporte que les inputs. Ajouter les outputs (résultats) pour traçabilité complète.

**À implémenter:**
1. Modifier `exportJSON()` dans `index.html`
2. Inclure: params + result (VAN, RBC, séries temporelles)
3. Ajouter timestamp et version du modèle

**Fichiers à modifier:** `index.html`

**Complexité:** Faible

---

## P2 - Nice to have

### TASK-03: Mode expert complet

**Description:** Exposer tous les paramètres du modèle pour les utilisateurs avancés.

**À implémenter:**
1. UI: Ajouter toggle "Mode expert" qui affiche tous les paramètres cachés
2. Paramètres à exposer:
   - MCF (coût marginal des fonds publics)
   - Externalités environnementales
   - Paramètres fins persistance (lambda_decay, alpha_plateau)
   - Ventilation OPEX détaillée (cyber, licences, stockage séparément)
3. Presets: "Standard", "Conservateur", "Agressif"

**Fichiers à modifier:** `api.py` (si nouveaux champs), `index.html`

**Complexité:** Moyenne

---

### TASK-04: Monte Carlo avancé

**Description:** Permettre de configurer les distributions pour chaque paramètre.

**À implémenter:**
1. UI: Section "Configuration Monte Carlo" avec:
   - Choix de distribution par paramètre (normal, triangulaire, uniforme)
   - Min/max/mode pour chaque paramètre
   - Option corrélations entre paramètres
2. API: Étendre `/api/monte_carlo` pour accepter `distributions_custom`
3. Export: Permettre d'exporter/importer les configurations de distribution

**Fichiers à modifier:** `api.py`, `index.html`

**Notes:** Le modèle a déjà `DISTRIBUTIONS_DEFAUT` et `ParametresMonteCarlo`. Étendre pour custom.

**Complexité:** Moyenne

---

### TASK-05: Assistant calibrage automatique

**Description:** L'utilisateur importe 12 mois de consommation (CSV) et l'outil propose des valeurs plausibles.

**À implémenter:**
1. UI: Bouton "Importer données de consommation"
2. Parser CSV: colonnes `mois, consommation_m3` ou `date, valeur`
3. Calculs automatiques:
   - LPCD moyen
   - Variance saisonnière
   - Détection anomalies (fuites probables)
   - Estimation prévalence fuites
4. API: Nouvel endpoint `/api/calibrate_from_data`
5. Afficher les valeurs suggérées avec intervalles de confiance

**Fichiers à modifier:** `api.py`, `index.html`

**Complexité:** Élevée

---

### TASK-06: Déploiement optimisé sous contraintes

**Description:** Trouver la trajectoire d'adoption qui maximise la VAN sous contraintes.

**À implémenter:**
1. UI: Section "Optimisation" avec contraintes:
   - Budget annuel max ($/an)
   - Capacité installation max (compteurs/an)
   - Objectif: maximiser VAN ou minimiser payback
2. API: Nouvel endpoint `/api/optimize_deployment`
3. Algorithme: Recherche par grille ou optimisation scipy

**Fichiers à modifier:** `api.py`, `index.html`

**Complexité:** Élevée

---

### TASK-07: Architecture CI/CD et versioning API

**Description:** Mettre en place une infrastructure de déploiement professionnelle.

**À implémenter:**
1. Fichier `Dockerfile` pour containerisation
2. GitHub Actions workflow (`.github/workflows/ci.yml`):
   - Lancer tests sur PR
   - Build et push Docker image
3. Versioning API: header `X-API-Version` dans les réponses
4. Fichier `CHANGELOG.md` structuré

**Fichiers à créer:** `Dockerfile`, `.github/workflows/ci.yml`, `CHANGELOG.md`

**Complexité:** Moyenne

---

### TASK-08: Observabilité production

**Description:** Ajouter logs structurés et métriques pour monitoring.

**À implémenter:**
1. Logging structuré (JSON) avec `structlog` ou `python-json-logger`
2. Métriques:
   - Temps de réponse par endpoint
   - Nombre de requêtes
   - Erreurs par type
3. Endpoint `/api/metrics` (format Prometheus)
4. Health check enrichi `/api/health` avec:
   - Version modèle
   - Uptime
   - Dernière erreur

**Fichiers à modifier:** `api.py`
**Dépendances à ajouter:** `structlog` ou équivalent

**Complexité:** Faible

---

### TASK-09: Accessibilité et responsive

**Description:** Améliorer l'accessibilité (a11y) et l'affichage mobile.

**À implémenter:**
1. Attributs ARIA sur les éléments interactifs
2. Labels explicites pour tous les inputs
3. Contraste couleurs suffisant (WCAG AA)
4. Media queries pour mobile:
   - Sidebar collapsible sur mobile
   - Graphiques responsive
   - Touch-friendly sliders
5. Skip links pour navigation clavier

**Fichiers à modifier:** `index.html` (CSS + HTML)

**Complexité:** Moyenne

---

### TASK-10: Bilingue (FR/EN)

**Description:** Ajouter support anglais.

**À implémenter:**
1. Fichier de traductions `translations.js` ou JSON
2. Toggle langue (FR/EN) dans le header
3. Traduire:
   - Labels UI
   - Messages d'erreur
   - Tooltips et help texts
   - Noms de scénarios
4. API: Paramètre `lang` optionnel pour les messages d'erreur

**Fichiers à modifier:** `index.html`, `api.py`

**Complexité:** Moyenne (beaucoup de texte à traduire)

---

### TASK-11: Comptes utilisateurs et sauvegarde cloud

**Description:** Permettre aux utilisateurs de sauvegarder leurs scénarios en ligne.

**À implémenter:**
1. Backend auth: JWT ou OAuth (Google/GitHub)
2. Base de données: PostgreSQL ou SQLite pour stocker scénarios
3. Endpoints:
   - `POST /api/auth/login`
   - `GET /api/scenarios` (liste)
   - `POST /api/scenarios` (sauvegarder)
   - `DELETE /api/scenarios/:id`
4. UI: Bouton connexion, liste scénarios cloud

**Fichiers à modifier:** `api.py`, `index.html`
**Dépendances:** `sqlalchemy`, `python-jose` (JWT)

**Complexité:** Élevée

---

## Ordre suggéré

1. **TASK-08** (Observabilité) - Quick win, utile pour debug
2. **TASK-02** (Export JSON complet) - Quick win
3. **TASK-07** (CI/CD) - Fondation pour la suite
4. **TASK-03** (Mode expert) - Demandé par utilisateurs avancés
5. **TASK-09** (Accessibilité) - Bonne pratique
6. **TASK-04** (Monte Carlo avancé) - Valeur analytique
7. **TASK-01** (Segmentation) - Réalisme municipal
8. **TASK-10** (Bilingue) - Si audience anglophone
9. **TASK-05** (Calibrage auto) - Feature différenciante
10. **TASK-06** (Optimisation) - Feature avancée
11. **TASK-11** (Comptes cloud) - Si besoin collaboration

---

## Notes pour les agents

- Toujours lancer les tests après modification: `python3 -m pytest test_api.py -v`
- Le modèle core (`analyse_compteurs_eau.py`) est stable, éviter de le modifier sauf si nécessaire
- Préférer ajouter des endpoints API plutôt que modifier les existants
- L'UI est dans un seul fichier `index.html` (HTML + CSS + JS inline)
- CORS est configurable via variable d'environnement `CORS_ORIGINS`
