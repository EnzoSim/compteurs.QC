# Plan Complet : Carte Québec avec Auto-Actualisation

## Objectif
- **1100+ municipalités** du Québec avec limites géographiques
- **Données EXACTES** auto-actualisées annuellement (population, ménages, LPCD)
- **Pipeline automatisé** sur Render.com
- **Historique annuel** pour comparaison année/année
- **Fallback intelligent** avec cache + avertissements

## DÉCOUVERTE MAJEURE : MAMH fournit des CSV directs !

```
https://donneesouvertes.affmunqc.net/sqeep_2019_2025/consommation_classe_2023.csv
https://donneesouvertes.affmunqc.net/sqeep_2019_2025/fuites_classe_2023.csv
```
→ **Pas besoin de scraper les PDFs** - données LPCD exactes disponibles en CSV (2018-2023)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RENDER.COM (Cron annuel)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ 1. OVERPASS  │    │ 2. STATCAN   │    │ 3. MAMH      │          │
│  │    API       │    │    API       │    │  CSV COLLECT │          │
│  │  (GeoJSON)   │    │ (Pop/Ménages)│    │   (LPCD)     │          │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘          │
│         │                   │                   │                   │
│         └───────────────────┼───────────────────┘                   │
│                             ▼                                        │
│                    ┌────────────────┐                               │
│                    │  4. MERGER     │                               │
│                    │  & VALIDATOR   │                               │
│                    └────────┬───────┘                               │
│                             │                                        │
│              ┌──────────────┼──────────────┐                        │
│              ▼              ▼              ▼                         │
│     ┌────────────┐  ┌────────────┐  ┌────────────┐                 │
│     │  CACHE     │  │  DATA      │  │  METADATA  │                 │
│     │ (fallback) │  │  (actuel)  │  │  (status)  │                 │
│     └────────────┘  └────────────┘  └────────────┘                 │
│                             │                                        │
└─────────────────────────────┼────────────────────────────────────────┘
                              ▼
                    ┌────────────────┐
                    │   FRONTEND     │
                    │   (Leaflet)    │
                    └────────────────┘
```

---

## Composants à Développer

### 1. Collecteur GeoJSON (Overpass API)
**Fichier**: `map/collectors/overpass_collector.py`

```python
# Requête Overpass pour toutes les municipalités du Québec
[out:json][timeout:300];
area["ISO3166-2"="CA-QC"]->.quebec;
(
  relation["admin_level"="8"]["boundary"="administrative"](area.quebec);
);
out geom;
```

**Données récupérées**:
- Polygones de toutes les municipalités
- Noms officiels (français)
- Codes géographiques (ref:statcan)
- Type (ville, municipalité, village, etc.)

**Estimation**: ~1,100 entités, ~15-30 MB GeoJSON

---

### 2. Collecteur Statistique Canada
**Fichier**: `map/collectors/statcan_collector.py`

**Source**: API Web Data Service de Statistique Canada
- Tableau 17-10-0142: Estimations de la population
- Tableau 98-10-0001: Profil du recensement (ménages)

**Données récupérées**:
- Population par subdivision de recensement
- Nombre de ménages
- Taille moyenne des ménages

**Fréquence**: Estimations annuelles + recensement tous les 5 ans

---

### 3. Collecteur MAMH (CSV directs)
**Fichier**: `map/collectors/mamh_collector.py`

**Source**: Données ouvertes MAMH (SQEEP)
- URL: `https://donneesouvertes.affmunqc.net/sqeep_2019_2025/`

**Fichiers CSV disponibles**:
- `consommation_classe_YYYY.csv` - Consommation d'eau par municipalité
- `fuites_classe_YYYY.csv` - Taux de fuites par municipalité
- Années disponibles: 2018-2023

**Stratégie**:
1. Télécharger les CSV de l'année la plus récente
2. Parser avec pandas
3. Mapper les codes municipaux vers codes StatCan
4. Extraire LPCD exact par municipalité

**Données récupérées**:
- Consommation totale (m³/jour)
- Population desservie
- LPCD exact (pas d'estimation!)

**Complexité**: FAIBLE (CSV structuré)

---

### 4. Merger & Validator
**Fichier**: `map/collectors/data_merger.py`

**Fonctions**:
1. Fusionner GeoJSON + Stats + LPCD par code géographique
2. Valider la cohérence des données
3. Marquer les données manquantes (`lpcd: null`, `lpcd_status: "missing"`)
4. Archiver dans history/ avant mise à jour
5. Générer les fichiers finaux

**Sortie**:
```
data/
├── current/
│   ├── quebec-municipalities.geojson    # Polygones + propriétés de base
│   └── municipalities-stats.json        # Statistiques complètes
├── history/
│   ├── 2023/
│   │   ├── quebec-municipalities.geojson
│   │   └── municipalities-stats.json
│   └── 2024/
│       └── ...
├── cache/
│   ├── geojson_backup.json         # Dernier GeoJSON valide
│   ├── stats_backup.json           # Dernières stats valides
│   └── metadata.json               # Date de mise à jour, statut sources
```

---

### 5. Système de Cache & Fallback
**Fichier**: `map/collectors/cache_manager.py`

**Logique**:
```python
def update_data():
    results = {
        'geojson': {'success': False, 'error': None},
        'statcan': {'success': False, 'error': None},
        'mamh': {'success': False, 'error': None},
    }

    # Tenter chaque source
    try:
        geojson = fetch_overpass()
        results['geojson']['success'] = True
        save_to_cache('geojson', geojson)
    except Exception as e:
        results['geojson']['error'] = str(e)
        geojson = load_from_cache('geojson')  # Fallback

    # ... idem pour autres sources

    # Sauvegarder metadata
    save_metadata({
        'last_update': datetime.now().isoformat(),
        'sources': results,
        'total_municipalities': len(geojson['features']),
    })
```

---

### 6. Cron Job Render.com
**Fichier**: `render.yaml` (mise à jour)

```yaml
services:
  - type: web
    name: compteurs-eau-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn api:app --host 0.0.0.0 --port $PORT

  - type: cron
    name: data-updater
    env: python
    schedule: "0 3 1 1 *"  # 1er janvier à 3h du matin
    buildCommand: pip install -r requirements.txt
    startCommand: python -m map.collectors.run_update
```

---

### 7. API Endpoint Status
**Fichier**: `api.py` (ajout)

```python
@app.get("/map/api/status")
async def get_data_status():
    """Retourne le statut des données et la date de dernière mise à jour."""
    metadata = load_metadata()
    return {
        "last_update": metadata.get("last_update"),
        "sources": metadata.get("sources"),
        "total_municipalities": metadata.get("total_municipalities"),
        "warnings": [
            src for src, info in metadata.get("sources", {}).items()
            if not info.get("success")
        ]
    }
```

---

### 8. Frontend - Indicateur de Fraîcheur
**Modification**: `map/index.html`

```javascript
// Afficher un badge avec la date de mise à jour
async function showDataStatus() {
    const status = await fetch('/map/api/status').then(r => r.json());

    const badge = document.getElementById('data-status');
    badge.innerHTML = `
        Données: ${new Date(status.last_update).toLocaleDateString('fr-CA')}
        ${status.warnings.length > 0 ? '⚠️' : '✓'}
    `;

    if (status.warnings.length > 0) {
        badge.title = `Sources indisponibles: ${status.warnings.join(', ')}`;
    }
}
```

---

## Structure Finale des Fichiers

```
map/
├── index.html                    # Frontend moderne
├── map.js                        # Composant Leaflet
├── map.css                       # Styles
├── map-modern.css               # Styles dark mode
│
├── collectors/                   # NOUVEAU
│   ├── __init__.py
│   ├── overpass_collector.py    # GeoJSON via OSM
│   ├── statcan_collector.py     # Population via StatCan
│   ├── mamh_collector.py        # LPCD via CSV MAMH
│   ├── data_merger.py           # Fusion des données
│   ├── cache_manager.py         # Gestion cache/fallback
│   └── run_update.py            # Point d'entrée cron
│
├── data/
│   ├── current/                     # Données actives
│   │   ├── quebec-municipalities.geojson
│   │   └── municipalities-stats.json
│   ├── history/                     # Archivage annuel
│   │   └── YYYY/
│   └── cache/
│       ├── geojson_backup.json
│       ├── stats_backup.json
│       └── metadata.json
│
└── README.md
```

---

## Dépendances Additionnelles

```txt
# requirements.txt (ajouts)
requests>=2.31.0
pandas>=2.1.0          # Manipulation données CSV
geojson>=3.1.0         # Validation GeoJSON
shapely>=2.0.0         # Géométries
retry>=0.9.2           # Retry avec backoff
```
Note: `pdfplumber` n'est plus nécessaire grâce aux CSV MAMH directs.

---

## Estimation Effort

| Composant | Complexité | Temps estimé |
|-----------|------------|--------------|
| Overpass Collector | Moyenne | 3-4h |
| StatCan Collector | Moyenne | 3-4h |
| MAMH CSV Collector | **Faible** | 2-3h |
| Merger & Validator | Moyenne | 3-4h |
| Cache Manager | Faible | 1-2h |
| Cron Setup Render | Faible | 1-2h |
| Frontend Status | Faible | 1-2h |
| **Tests & Debug** | Variable | 3-4h |
| **TOTAL** | | **18-25h** |

*Temps réduit grâce aux CSV MAMH directs (pas de scraping PDF)*

---

## Risques & Mitigations

| Risque | Probabilité | Mitigation |
|--------|-------------|------------|
| Overpass API timeout (gros volume) | Moyenne | Requêtes par région (17), retry avec backoff |
| URL CSV MAMH change | Faible | Détection automatique des nouvelles années |
| StatCan API down | Faible | Cache de 5 ans (recensement) |
| Codes géo non matchés | Moyenne | Table de correspondance manuelle |

---

## Prochaines Étapes

1. **Développer le collecteur Overpass** — Base GeoJSON (~1100 municipalités)
2. **Développer le collecteur StatCan** — Population/ménages
3. **Développer le collecteur MAMH CSV** — LPCD exact
4. **Intégrer le merger et cache** — Avec historique annuel
5. **Tester localement**
6. **Déployer sur Render avec cron**

---

## Décisions Prises

- **LPCD**: Chiffres exacts uniquement (pas d'estimation). Si manquant → `lpcd: null`
- **GeoJSON**: Version complète (~15-30 MB), pas de simplification
- **Historique**: Oui, archivage dans `data/history/YYYY/`
- **Fallback**: Cache des dernières données valides + avertissement utilisateur
