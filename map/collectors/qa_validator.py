"""
Contrôle qualité (QA) automatique pour les données AquaMap QC.

Ce module valide:
- Couverture des données LPCD
- Détection d'outliers
- Doublons d'identifiants
- Cohérence des unités
- Intégrité des données
"""

import logging
from typing import Dict, Any, List, Optional
from collections import Counter

logger = logging.getLogger(__name__)


class QAValidator:
    """Validateur de qualité des données."""

    # Seuils de validation
    LPCD_MIN = 50  # L/pers/jour - En dessous: probablement une erreur
    LPCD_MAX = 1000  # L/pers/jour - Au-dessus: probablement une erreur
    LPCD_WARNING_LOW = 100  # L/pers/jour - Inhabituellement bas
    LPCD_WARNING_HIGH = 600  # L/pers/jour - Inhabituellement élevé

    POPULATION_MIN = 1
    POPULATION_MAX = 5_000_000  # Montréal ~1.7M

    CONSOMMATION_MIN = 0.001  # ML/an
    CONSOMMATION_MAX = 1_000_000  # ML/an

    def __init__(self):
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.info: List[Dict[str, Any]] = []

    def validate(
        self,
        geojson: dict,
        mamh_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Exécute tous les contrôles qualité.

        Args:
            geojson: Données GeoJSON fusionnées
            mamh_data: Données MAMH brutes

        Returns:
            Résultats de validation avec erreurs, warnings et summary
        """
        self.errors = []
        self.warnings = []
        self.info = []

        features = geojson.get("features", [])

        logger.info(f"Running QA on {len(features)} features...")

        # Run all checks
        self._check_lpcd_coverage(features)
        self._check_lpcd_outliers(features)
        self._check_duplicate_ids(features)
        self._check_duplicate_names(features)
        self._check_population_consistency(features)
        self._check_consommation_values(features)
        self._check_missing_names(features)
        self._check_mamh_data_quality(mamh_data)

        # Generate summary
        summary = self._generate_summary(features)

        return {
            "errors": self.errors,
            "warnings": [w["message"] for w in self.warnings],
            "info": self.info,
            "summary": summary,
        }

    def _check_lpcd_coverage(self, features: List[dict]):
        """Vérifie le pourcentage de municipalités avec LPCD disponible."""
        total = len(features)
        if total == 0:
            self.errors.append({
                "check": "lpcd_coverage",
                "message": "Aucune feature dans le GeoJSON",
            })
            return

        with_lpcd = sum(
            1 for f in features
            if f.get("properties", {}).get("lpcd") is not None
            and f.get("properties", {}).get("lpcd_status") != "missing"
        )

        coverage = round(with_lpcd / total * 100, 1)

        if coverage < 50:
            self.errors.append({
                "check": "lpcd_coverage",
                "message": f"Couverture LPCD critique: {coverage}% ({with_lpcd}/{total})",
            })
        elif coverage < 70:
            self.warnings.append({
                "check": "lpcd_coverage",
                "message": f"Couverture LPCD faible: {coverage}% ({with_lpcd}/{total})",
            })
        else:
            self.info.append({
                "check": "lpcd_coverage",
                "message": f"Couverture LPCD: {coverage}% ({with_lpcd}/{total})",
            })

    def _check_lpcd_outliers(self, features: List[dict]):
        """Détecte les valeurs LPCD aberrantes."""
        outliers_critical = []
        outliers_warning = []

        for f in features:
            props = f.get("properties", {})
            lpcd = props.get("lpcd")
            name = props.get("name", "Unknown")

            if lpcd is None:
                continue

            if lpcd < self.LPCD_MIN:
                outliers_critical.append({
                    "name": name,
                    "lpcd": lpcd,
                    "reason": f"LPCD < {self.LPCD_MIN}",
                })
            elif lpcd > self.LPCD_MAX:
                outliers_critical.append({
                    "name": name,
                    "lpcd": lpcd,
                    "reason": f"LPCD > {self.LPCD_MAX}",
                })
            elif lpcd < self.LPCD_WARNING_LOW:
                outliers_warning.append({
                    "name": name,
                    "lpcd": lpcd,
                    "reason": f"LPCD inhabituellement bas (< {self.LPCD_WARNING_LOW})",
                })
            elif lpcd > self.LPCD_WARNING_HIGH:
                outliers_warning.append({
                    "name": name,
                    "lpcd": lpcd,
                    "reason": f"LPCD inhabituellement élevé (> {self.LPCD_WARNING_HIGH})",
                })

        if outliers_critical:
            self.errors.append({
                "check": "lpcd_outliers",
                "message": f"{len(outliers_critical)} valeurs LPCD aberrantes détectées",
                "details": outliers_critical[:10],  # Limit to 10
            })

        if outliers_warning:
            self.warnings.append({
                "check": "lpcd_outliers",
                "message": f"{len(outliers_warning)} valeurs LPCD inhabituelles",
                "details": outliers_warning[:10],
            })

    def _check_duplicate_ids(self, features: List[dict]):
        """Vérifie les doublons d'identifiants CSD."""
        ids = []
        for f in features:
            props = f.get("properties", {})
            csd_uid = props.get("csd_uid") or props.get("CSDUID")
            if csd_uid:
                ids.append(str(csd_uid))

        duplicates = [id for id, count in Counter(ids).items() if count > 1]

        if duplicates:
            self.errors.append({
                "check": "duplicate_ids",
                "message": f"{len(duplicates)} identifiants CSD en double",
                "details": duplicates[:20],
            })

    def _check_duplicate_names(self, features: List[dict]):
        """Vérifie les collisions de noms de municipalités."""
        names = []
        for f in features:
            props = f.get("properties", {})
            name = props.get("name") or props.get("CSDNAME")
            if name:
                names.append(name.strip().lower())

        duplicates = [name for name, count in Counter(names).items() if count > 1]

        if duplicates:
            self.warnings.append({
                "check": "duplicate_names",
                "message": f"{len(duplicates)} noms de municipalités en double (homonymes possibles)",
                "details": duplicates[:20],
            })

    def _check_population_consistency(self, features: List[dict]):
        """Vérifie la cohérence des valeurs de population."""
        issues = []

        for f in features:
            props = f.get("properties", {})
            name = props.get("name", "Unknown")
            pop = props.get("population")
            pop_desservie = props.get("population_desservie")

            if pop is not None:
                if pop < self.POPULATION_MIN or pop > self.POPULATION_MAX:
                    issues.append({
                        "name": name,
                        "population": pop,
                        "reason": "Population hors limites raisonnables",
                    })

            # Check if served population > total population
            if pop is not None and pop_desservie is not None:
                if pop_desservie > pop * 1.1:  # Allow 10% margin
                    issues.append({
                        "name": name,
                        "population": pop,
                        "population_desservie": pop_desservie,
                        "reason": "Population desservie > population totale",
                    })

        if issues:
            self.warnings.append({
                "check": "population_consistency",
                "message": f"{len(issues)} incohérences de population détectées",
                "details": issues[:10],
            })

    def _check_consommation_values(self, features: List[dict]):
        """Vérifie les valeurs de consommation (vol_eau_dist en ML/an)."""
        issues = []

        for f in features:
            props = f.get("properties", {})
            name = props.get("name", "Unknown")
            consommation = props.get("consommation")

            if consommation is not None:
                if consommation < self.CONSOMMATION_MIN:
                    issues.append({
                        "name": name,
                        "consommation": consommation,
                        "reason": "Consommation anormalement basse",
                    })
                elif consommation > self.CONSOMMATION_MAX:
                    issues.append({
                        "name": name,
                        "consommation": consommation,
                        "reason": "Consommation anormalement élevée",
                    })

        if issues:
            self.warnings.append({
                "check": "consommation_values",
                "message": f"{len(issues)} valeurs de consommation inhabituelles",
                "details": issues[:10],
            })

    def _check_missing_names(self, features: List[dict]):
        """Vérifie les features sans nom."""
        missing_names = sum(
            1 for f in features
            if not (f.get("properties", {}).get("name") or f.get("properties", {}).get("CSDNAME"))
        )

        if missing_names > 0:
            self.warnings.append({
                "check": "missing_names",
                "message": f"{missing_names} municipalités sans nom",
            })

    def _check_mamh_data_quality(self, mamh_data: Dict[str, Any]):
        """Vérifie la qualité des données MAMH brutes."""
        if not mamh_data:
            self.warnings.append({
                "check": "mamh_data",
                "message": "Aucune donnée MAMH disponible",
            })
            return

        # Check for missing LPCD in MAMH data
        missing_lpcd = sum(
            1 for entry in mamh_data.values()
            if entry.get("lpcd") is None or entry.get("lpcd_status") == "missing"
        )

        total = len(mamh_data)
        if missing_lpcd > 0:
            pct = round(missing_lpcd / total * 100, 1)
            self.info.append({
                "check": "mamh_data",
                "message": f"{missing_lpcd}/{total} ({pct}%) entrées MAMH sans LPCD",
            })

    def _generate_summary(self, features: List[dict]) -> Dict[str, Any]:
        """Génère un résumé des statistiques QA."""
        total = len(features)

        lpcd_values = [
            f.get("properties", {}).get("lpcd")
            for f in features
            if f.get("properties", {}).get("lpcd") is not None
        ]

        pop_values = [
            f.get("properties", {}).get("population")
            for f in features
            if f.get("properties", {}).get("population") is not None
        ]

        summary = {
            "total_features": total,
            "with_lpcd": len(lpcd_values),
            "with_population": len(pop_values),
            "lpcd_coverage_pct": round(len(lpcd_values) / total * 100, 1) if total > 0 else 0,
            "population_coverage_pct": round(len(pop_values) / total * 100, 1) if total > 0 else 0,
            "errors_count": len(self.errors),
            "warnings_count": len(self.warnings),
        }

        if lpcd_values:
            sorted_lpcd = sorted(lpcd_values)
            summary["lpcd_stats"] = {
                "min": sorted_lpcd[0],
                "max": sorted_lpcd[-1],
                "median": sorted_lpcd[len(sorted_lpcd) // 2],
                "mean": round(sum(sorted_lpcd) / len(sorted_lpcd), 1),
            }

        return summary


def validate_data(
    geojson: dict,
    mamh_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Fonction utilitaire pour valider les données.

    Args:
        geojson: Données GeoJSON
        mamh_data: Données MAMH

    Returns:
        Résultats de validation
    """
    validator = QAValidator()
    return validator.validate(geojson, mamh_data)


if __name__ == "__main__":
    import json
    import logging

    logging.basicConfig(level=logging.INFO)

    # Load test data
    from .config import config

    geojson_path = config.CURRENT_DIR / config.GEOJSON_FILE
    mamh_path = config.CURRENT_DIR / "mamh-data.json"

    with open(geojson_path) as f:
        geojson = json.load(f)

    with open(mamh_path) as f:
        mamh_data = json.load(f)

    results = validate_data(geojson, mamh_data)

    print("\n=== QA RESULTS ===")
    print(f"Errors: {len(results['errors'])}")
    print(f"Warnings: {len(results['warnings'])}")
    print(f"\nSummary: {json.dumps(results['summary'], indent=2)}")
