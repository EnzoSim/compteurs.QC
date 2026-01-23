# Dictionnaire des données - AquaMap QC

Ce document décrit les champs de données utilisés dans AquaMap QC, l'outil de visualisation de la consommation d'eau des municipalités du Québec.

## Fichiers de données

| Fichier | Description |
|---------|-------------|
| `quebec-municipalities.geojson` | Géométries des municipalités avec données enrichies |
| `municipalities-stats.json` | Statistiques par municipalité (format JSON indexé par CSD UID) |
| `mamh-data.json` | Données brutes MAMH SQEEP |
| `metadata.json` | Métadonnées sur les sources et la qualité des données |

---

## Champs principaux

### Identifiants

| Champ | Type | Description | Source |
|-------|------|-------------|--------|
| `csd_uid` | string | Identifiant unique de subdivision de recensement (7 chiffres) | Statistique Canada |
| `code_mun` | string | Code municipal MAMH | MAMH |
| `name` | string | Nom officiel de la municipalité | StatCan / MAMH |

### Données démographiques

| Champ | Type | Unité | Description | Source |
|-------|------|-------|-------------|--------|
| `population` | integer | habitants | Population totale de la municipalité | Recensement 2021 |
| `population_desservie` | integer | habitants | Population desservie par le réseau d'eau potable | MAMH SQEEP |
| `households` | integer | ménages | Nombre de ménages privés | Recensement 2021 |
| `household_size` | float | pers./ménage | Taille moyenne des ménages | Calculé |

### Données de consommation d'eau

| Champ | Type | Unité stockée | Unité affichée | Description | Source |
|-------|------|---------------|----------------|-------------|--------|
| `lpcd` | float | L/pers/jour | L/pers/jour | **Consommation résidentielle** - Litres par personne par jour. Exclut usages commerciaux/industriels et pertes. | MAMH SQEEP (consom_resid) |
| `consommation` | float | ML/an | m³/jour | **Volume total distribué** - Mégalitres par an. Converti à l'affichage: `m³/j = ML/an × 1000 ÷ 365` | MAMH SQEEP (vol_eau_dist) |
| `lpcd_status` | string | — | — | Statut de la donnée: `exact`, `estimated`, `missing` | Calculé |
| `lpcd_data_year` | integer | — | — | Année des données LPCD | MAMH SQEEP |

### Conversion des unités

**Volume distribué (consommation):**
- Stocké en: **Mégalitres par an (ML/an)**
- Affiché en: **Mètres cubes par jour (m³/j)**
- Formule: `m³/jour = ML/an × 1000 ÷ 365`
- Exemple: 16.15 ML/an = 44.3 m³/jour

**LPCD:**
- Stocké et affiché en: **Litres par personne par jour (L/pers/jour)**
- Pas de conversion nécessaire

---

## Valeurs de référence

### Échelle LPCD

| Catégorie | Plage (L/pers/jour) | Couleur | Interprétation |
|-----------|---------------------|---------|----------------|
| Excellent | < 200 | Vert (#059669) | Consommation très efficiente |
| Bon | 200-250 | Cyan (#0891b2) | Proche ou sous la cible provinciale |
| Moyen | 250-300 | Jaune (#ca8a04) | Consommation moyenne |
| Élevé | 300-350 | Orange (#ea580c) | Consommation au-dessus de la moyenne |
| Critique | > 350 | Rouge (#dc2626) | Consommation excessive |

### Cible provinciale

**220 L/pers/jour** - Objectif fixé par la [Stratégie québécoise d'économie d'eau potable](https://www.environnement.gouv.qc.ca/eau/potable/strategie/) du Gouvernement du Québec.

---

## Sources de données

### MAMH SQEEP 2019-2025
- **URL**: https://www.donneesquebec.ca/recherche/dataset/sqeep-2019-2025
- **Producteur**: Ministère des Affaires municipales et de l'Habitation (MAMH)
- **Couverture**: ~1100 municipalités avec réseau d'eau potable
- **Fréquence**: Annuelle
- **Licence**: Licence ouverte du gouvernement du Québec

### Statistique Canada - Recensement 2021
- **URL**: https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/index.cfm
- **Producteur**: Statistique Canada
- **Couverture**: Toutes les subdivisions de recensement du Québec (~1282)
- **Géométries**: Fichiers de limites numériques 2021
- **Licence**: Licence ouverte du gouvernement du Canada

---

## Statuts de données

| Statut | Description |
|--------|-------------|
| `exact` | Valeur mesurée directement depuis les données SQEEP |
| `estimated` | Valeur estimée ou interpolée |
| `missing` | Donnée non disponible (municipalité sans réseau ou données manquantes) |

---

## Limites et avertissements

1. **Couverture incomplète**: Toutes les municipalités n'ont pas de données LPCD. Les municipalités sans réseau d'eau potable municipal ou avec des données manquantes apparaissent en gris.

2. **Données résidentielles**: Le LPCD représente la consommation **résidentielle** uniquement. Il exclut les usages commerciaux, industriels et institutionnels.

3. **Pertes de réseau**: Les pertes de réseau (fuites) ne sont pas incluses dans le LPCD mais sont incluses dans le volume total distribué.

4. **Délai de données**: Les données MAMH SQEEP ont généralement un délai d'un an. Les données de population proviennent du recensement 2021.

---

## Contact

Pour toute question concernant ces données, veuillez contacter le responsable du projet AquaMap QC.

---

*Dernière mise à jour: Janvier 2026*
