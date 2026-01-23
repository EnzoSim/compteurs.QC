/**
 * QuebecMap - Professional Water Consumption Map
 * Interactive map of Quebec municipalities with LPCD data
 */

class QuebecMap {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.options = {
            center: [46.8, -73.0],
            zoom: 6,
            minZoom: 5,
            maxZoom: 13,
            dataPath: 'data/current/quebec-municipalities.geojson',
            statsPath: 'data/current/municipalities-stats.json',
            metadataPath: 'data/current/metadata.json',
            mamhPath: 'data/current/mamh-data.json',
            onSelect: null, // Callback when municipality is selected
            ...options
        };

        this.map = null;
        this.geojsonLayer = null;
        this.geojsonLayers = [];
        this.geojsonData = null;
        this.stats = {};
        this.metadata = {};
        this.mamh = {};
        this.statsIndex = null;
        this.mamhIndex = null;
        this.currentMetric = 'lpcd';
        this.selectedFeature = null;
        this.searchIndex = [];
        this.globalStats = null;

        // Quebec-calibrated LPCD scale (residential consumption)
        // Target: 220 L/pers/jour (Strategie quebecoise d'economie d'eau potable)
        // Sources: Gouvernement du Quebec, MAMH SQEEP 2019-2025
        this.targetLpcd = 220; // Cible provinciale
        this.colorScales = {
            lpcd: {
                ranges: [200, 250, 300, 350],
                colors: ['#059669', '#0891b2', '#ca8a04', '#ea580c', '#dc2626'],
                labels: ['Excellent', 'Bon', 'Moyen', 'Élevé', 'Critique'],
                descriptions: ['< 200', '200-250', '250-300', '300-350', '> 350'],
                unit: 'L/pers/jour'
            },
            population: {
                ranges: [1000, 5000, 25000, 100000],
                colors: ['#dbeafe', '#93c5fd', '#3b82f6', '#1d4ed8', '#1e3a8a'],
                labels: ['< 1k', '1k-5k', '5k-25k', '25k-100k', '> 100k'],
                descriptions: ['< 1 000', '1 000 - 5 000', '5 000 - 25 000', '25 000 - 100 000', '> 100 000'],
                unit: 'habitants'
            }
        };

        this.init();
    }

    async init() {
        this.showLoader('Initialisation...', 0);
        this.createMap();
        await this.loadData();
        this.calculateGlobalStats();
        this.buildSearchIndex();
        this.addLegend();
        this.addControls();
        this.setupSearch();
        this.setupMethodologyPanel();
        this.updateHeaderStats();
        this.showDataStatus();
        this.hideLoader();
    }

    createMap() {
        this.map = L.map(this.containerId, {
            center: this.options.center,
            zoom: this.options.zoom,
            minZoom: this.options.minZoom,
            maxZoom: this.options.maxZoom,
            zoomControl: false
        });

        // Create custom panes for layered rendering (small municipalities on top)
        this.map.createPane('municipalitiesLarge');
        this.map.createPane('municipalitiesMedium');
        this.map.createPane('municipalitiesSmall');
        this.map.createPane('municipalitiesTiny');

        this.map.getPane('municipalitiesLarge').style.zIndex = 400;
        this.map.getPane('municipalitiesMedium').style.zIndex = 410;
        this.map.getPane('municipalitiesSmall').style.zIndex = 420;
        this.map.getPane('municipalitiesTiny').style.zIndex = 430;

        // Clean map tiles (CartoDB Positron)
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
            maxZoom: 19,
            subdomains: 'abcd'
        }).addTo(this.map);

        // Add labels on top
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png', {
            maxZoom: 19,
            subdomains: 'abcd',
            pane: 'shadowPane'
        }).addTo(this.map);

        // Add zoom control to bottom right
        L.control.zoom({ position: 'bottomleft' }).addTo(this.map);

        // Update styles on zoom
        this.map.on('zoomend', () => {
            if (this.geojsonLayers) {
                this.geojsonLayers.forEach(layer => {
                    layer.setStyle((feature) => this.getFeatureStyle(feature));
                });
            }
        });

        // Close info panel on map click
        this.map.on('click', (e) => {
            if (e.originalEvent.target === this.map.getContainer()) {
                this.closeInfoPanel();
            }
        });
    }

    async loadData() {
        this.showLoader('Chargement des données...', 20);

        try {
            // Load GeoJSON
            const geojsonResponse = await fetch(this.options.dataPath);
            if (!geojsonResponse.ok) throw new Error('Données géographiques non disponibles');

            this.showLoader('Traitement des géométries...', 40);
            const geojson = await geojsonResponse.json();
            this.normalizeGeoJSON(geojson);

            this.showLoader('Chargement des statistiques...', 60);
            await this.loadAuxiliaryData();

            this.showLoader('Enrichissement des données...', 80);
            this.enrichGeoJSON(geojson);
            this.geojsonData = geojson;

            this.showLoader('Rendu de la carte...', 90);
            this.addGeoJSONLayer(geojson);

        } catch (error) {
            console.error('Error loading data:', error);
            this.showError(error.message);
        }
    }

    async loadAuxiliaryData() {
        const fetchJson = async (path) => {
            if (!path) return null;
            try {
                const res = await fetch(path);
                return res.ok ? await res.json() : null;
            } catch {
                return null;
            }
        };

        const [stats, metadata, mamh] = await Promise.all([
            fetchJson(this.options.statsPath),
            fetchJson(this.options.metadataPath),
            fetchJson(this.options.mamhPath)
        ]);

        if (stats) {
            this.stats = stats;
            this.buildStatsIndex(stats);
        }

        if (metadata) {
            this.metadata = metadata;
        }

        if (mamh) {
            this.mamh = mamh;
            this.buildMamhIndex(mamh);
        }
    }

    buildStatsIndex(stats) {
        const byId = new Map();
        const byName = new Map();

        for (const entry of Object.values(stats)) {
            if (!entry) continue;
            const id = entry.csd_uid ?? entry.osm_id;
            if (id != null) byId.set(String(id), entry);
            if (entry.name) byName.set(this.normalizeName(entry.name), entry);
        }

        this.statsIndex = { byId, byName };
    }

    buildMamhIndex(mamh) {
        const byName = new Map();
        for (const entry of Object.values(mamh)) {
            if (!entry?.nom_mun) continue;
            const key = this.normalizeName(entry.nom_mun);
            if (!byName.has(key)) byName.set(key, entry);
        }
        this.mamhIndex = { byName };
    }

    normalizeName(name) {
        if (!name) return '';
        return name.toString().trim().toLowerCase()
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
            .replace(/[-\u2013\u2014''./(),]/g, ' ')
            .replace(/\s+/g, ' ').trim();
    }

    enrichGeoJSON(geojson) {
        if (!geojson?.features) return;

        for (const feature of geojson.features) {
            const props = feature.properties || {};
            const nameKey = this.normalizeName(props.name || props.name_fr || '');

            // Stats join
            let statsMatch = null;
            if (this.statsIndex) {
                const id = props.csd_uid ?? props.ref_statcan ?? props.osm_id;
                if (id != null) statsMatch = this.statsIndex.byId.get(String(id));
                if (!statsMatch && nameKey) statsMatch = this.statsIndex.byName.get(nameKey);
            }

            if (statsMatch) {
                props.population = props.population ?? statsMatch.population;
                props.households = props.households ?? statsMatch.households;
                props.household_size = props.household_size ?? statsMatch.household_size;
                props.lpcd = props.lpcd ?? statsMatch.lpcd;
                props.lpcd_status = props.lpcd_status ?? statsMatch.lpcd_status;
                props.lpcd_total = props.lpcd_total ?? statsMatch.lpcd_total;
                props.consommation = props.consommation ?? statsMatch.consommation;
                props.population_desservie = props.population_desservie ?? statsMatch.population_desservie;
                props.nb_logements = props.nb_logements ?? statsMatch.nb_logements;
                props.pers_par_residence = props.pers_par_residence ?? statsMatch.pers_par_residence;
                props.nb_reseaux = props.nb_reseaux ?? statsMatch.nb_reseaux;
                props.indice_fuites = props.indice_fuites ?? statsMatch.indice_fuites;
                props.lpcd_data_year = props.lpcd_data_year ?? statsMatch.lpcd_data_year;
            }

            // MAMH fallback
            if (this.mamhIndex && nameKey) {
                const mamhMatch = this.mamhIndex.byName.get(nameKey);
                if (mamhMatch) {
                    props.lpcd = props.lpcd ?? mamhMatch.lpcd;
                    props.lpcd_status = props.lpcd_status ?? mamhMatch.lpcd_status;
                    props.lpcd_total = props.lpcd_total ?? mamhMatch.lpcd_total;
                    props.consommation = props.consommation ?? mamhMatch.consommation;
                    props.population_desservie = props.population_desservie ?? mamhMatch.population_desservie;
                    props.nb_logements = props.nb_logements ?? mamhMatch.nb_logements;
                    props.pers_par_residence = props.pers_par_residence ?? mamhMatch.pers_par_residence;
                    props.nb_reseaux = props.nb_reseaux ?? mamhMatch.nb_reseaux;
                    props.indice_fuites = props.indice_fuites ?? mamhMatch.indice_fuites;
                    props.lpcd_data_year = props.lpcd_data_year ?? mamhMatch.data_year;
                }
            }

            // Flag missing data
            if (props.lpcd == null && !props.lpcd_status) {
                props.lpcd_status = 'missing';
            }

            feature.properties = props;
        }
    }

    normalizeGeoJSON(geojson) {
        if (!geojson?.features) return;

        for (const feature of geojson.features) {
            const geom = feature?.geometry;
            if (!geom?.coordinates) continue;

            if (geom.type === 'Polygon') {
                geom.coordinates = this.normalizePolygonCoords(geom.coordinates);
                this.stripInnerRings(geom);
            } else if (geom.type === 'MultiPolygon') {
                geom.coordinates = this.normalizeMultiPolygonCoords(geom.coordinates);
                this.stripInnerRings(geom);
            }
        }
    }

    stripInnerRings(geom) {
        if (!geom?.coordinates) return;
        if (geom.type === 'Polygon' && geom.coordinates.length > 1) {
            geom.coordinates = [geom.coordinates[0]];
        } else if (geom.type === 'MultiPolygon') {
            geom.coordinates = geom.coordinates.map(poly =>
                Array.isArray(poly) && poly.length > 1 ? [poly[0]] : poly
            );
        }
    }

    normalizePolygonCoords(coords) {
        if (!Array.isArray(coords)) return coords;
        if (coords.length === 1 && this.isRingList(coords[0])) return coords[0];
        return coords;
    }

    normalizeMultiPolygonCoords(coords) {
        if (!Array.isArray(coords)) return coords;
        return coords.map(poly =>
            Array.isArray(poly) && poly.length === 1 && this.isRingList(poly[0]) ? poly[0] : poly
        );
    }

    isRingList(v) { return Array.isArray(v) && v.length > 0 && this.isRing(v[0]); }
    isRing(v) { return Array.isArray(v) && v.length > 0 && this.isPoint(v[0]); }
    isPoint(v) { return Array.isArray(v) && typeof v[0] === 'number' && typeof v[1] === 'number'; }

    calculateGlobalStats() {
        if (!this.geojsonData?.features) return;

        const lpcdValues = [];
        let withData = 0;
        let withoutData = 0;

        for (const feature of this.geojsonData.features) {
            const lpcd = feature.properties?.lpcd;
            if (lpcd != null && feature.properties?.lpcd_status !== 'missing') {
                lpcdValues.push(lpcd);
                withData++;
            } else {
                withoutData++;
            }
        }

        lpcdValues.sort((a, b) => a - b);
        const sum = lpcdValues.reduce((a, b) => a + b, 0);

        this.globalStats = {
            total: this.geojsonData.features.length,
            withData,
            withoutData,
            coverage: Math.round((withData / (withData + withoutData)) * 100),
            average: lpcdValues.length ? Math.round(sum / lpcdValues.length) : null,
            median: lpcdValues.length ? lpcdValues[Math.floor(lpcdValues.length / 2)] : null,
            min: lpcdValues.length ? lpcdValues[0] : null,
            max: lpcdValues.length ? lpcdValues[lpcdValues.length - 1] : null
        };
    }

    buildSearchIndex() {
        if (!this.geojsonData?.features) return;

        this.searchIndex = this.geojsonData.features
            .filter(f => f.properties?.name)
            .map(f => ({
                name: f.properties.name,
                normalized: this.normalizeName(f.properties.name),
                lpcd: f.properties.lpcd,
                feature: f
            }))
            .sort((a, b) => a.name.localeCompare(b.name, 'fr'));
    }

    addGeoJSONLayer(geojson) {
        if (this.geojsonLayers) {
            this.geojsonLayers.forEach(layer => this.map.removeLayer(layer));
        }
        this.geojsonLayers = [];

        // Calculate areas and assign panes
        const featuresWithArea = geojson.features
            .filter(f => this.isRenderableFeature(f))
            .map(f => ({
                feature: f,
                area: this.getFeatureArea(f)
            }));

        // Sort by area (largest first for consistent processing)
        featuresWithArea.sort((a, b) => b.area - a.area);

        // Define area thresholds for panes (in degrees²)
        // Tiny: < 0.01 (enclaved cities like Ville Mont-Royal, Westmount)
        // Small: 0.01 - 0.1
        // Medium: 0.1 - 1
        // Large: > 1
        const thresholds = {
            tiny: 0.01,
            small: 0.1,
            medium: 1
        };

        // Group features by size category
        const groups = {
            large: [],
            medium: [],
            small: [],
            tiny: []
        };

        for (const { feature, area } of featuresWithArea) {
            if (area < thresholds.tiny) {
                groups.tiny.push(feature);
            } else if (area < thresholds.small) {
                groups.small.push(feature);
            } else if (area < thresholds.medium) {
                groups.medium.push(feature);
            } else {
                groups.large.push(feature);
            }
        }

        // Create layer for each group with appropriate pane
        const paneNames = ['municipalitiesLarge', 'municipalitiesMedium', 'municipalitiesSmall', 'municipalitiesTiny'];
        const groupNames = ['large', 'medium', 'small', 'tiny'];

        for (let i = 0; i < groupNames.length; i++) {
            const features = groups[groupNames[i]];
            if (features.length === 0) continue;

            const layer = L.geoJSON({ type: 'FeatureCollection', features }, {
                pane: paneNames[i],
                style: (feature) => this.getFeatureStyle(feature),
                onEachFeature: (feature, layer) => this.onEachFeature(feature, layer)
            }).addTo(this.map);

            this.geojsonLayers.push(layer);
        }

        // Keep reference to first layer for bounds
        this.geojsonLayer = this.geojsonLayers[0];

        if (geojson.features?.length > 0 && this.geojsonLayers.length > 0) {
            // Get bounds from all layers
            let bounds = null;
            for (const layer of this.geojsonLayers) {
                const layerBounds = layer.getBounds();
                if (layerBounds.isValid()) {
                    bounds = bounds ? bounds.extend(layerBounds) : layerBounds;
                }
            }
            if (bounds) {
                this.map.fitBounds(bounds, { padding: [20, 20] });
            }
        }
    }

    getFeatureArea(feature) {
        // Estimation rapide de l'aire via bounding box
        if (!feature?.geometry?.coordinates) return 0;
        try {
            const bounds = L.geoJSON(feature).getBounds();
            const width = bounds.getEast() - bounds.getWest();
            const height = bounds.getNorth() - bounds.getSouth();
            return width * height;
        } catch {
            return 0;
        }
    }

    isRenderableFeature(feature) {
        if (!feature?.geometry) return false;
        const ratio = feature.properties?.shape_ratio;
        return !(ratio != null && ratio > 0 && ratio < 0.001);
    }

    getFeatureStyle(feature) {
        const props = feature.properties || {};
        const value = props[this.currentMetric];
        const status = props.lpcd_status;
        const zoom = this.map?.getZoom() ?? this.options.zoom;

        // Metric-aware data availability check
        const hasData = this.currentMetric === 'lpcd'
            ? (value != null && status !== 'missing')
            : (value != null);

        // Opacity based on zoom
        const fillOpacity = hasData
            ? (zoom < 7 ? 0.5 : 0.75)
            : (zoom < 7 ? 0.1 : 0.2);

        // Missing data style (only for current metric)
        if (!hasData) {
            return {
                fillColor: '#e2e8f0',
                fillOpacity,
                color: '#94a3b8',
                weight: zoom < 8 ? 0.3 : 0.5,
                opacity: zoom < 7 ? 0.3 : 0.5
            };
        }

        const color = this.getColor(value, this.currentMetric);
        return {
            fillColor: color,
            fillOpacity,
            color: '#64748b',
            weight: zoom < 8 ? 0.3 : 0.6,
            opacity: zoom < 7 ? 0.4 : 0.7
        };
    }

    getColor(value, metric) {
        if (value == null) return '#e2e8f0';

        const scale = this.colorScales[metric];
        if (!scale) return '#64748b';

        for (let i = 0; i < scale.ranges.length; i++) {
            if (value < scale.ranges[i]) return scale.colors[i];
        }
        return scale.colors[scale.colors.length - 1];
    }

    getLpcdCategory(value) {
        if (value == null) return 'missing';
        const scale = this.colorScales.lpcd;
        for (let i = 0; i < scale.ranges.length; i++) {
            if (value < scale.ranges[i]) return scale.labels[i].toLowerCase();
        }
        return 'critique';
    }

    onEachFeature(feature, layer) {
        const props = feature.properties || {};

        layer.bindPopup(() => this.createPopupContent(props), {
            maxWidth: 280,
            className: 'municipality-popup',
            closeButton: false
        });

        layer.on({
            mouseover: (e) => this.highlightFeature(e),
            mouseout: (e) => this.resetHighlight(e),
            click: (e) => this.selectFeature(e, feature)
        });
    }

    createPopupContent(props) {
        const name = props.name || 'Municipalité inconnue';
        const lpcd = props.lpcd;
        const hasLpcd = lpcd != null && props.lpcd_status !== 'missing';
        const category = this.getLpcdCategory(lpcd);
        const color = hasLpcd ? this.getColor(lpcd, 'lpcd') : '#94a3b8';

        return `
            <div class="popup-content">
                <div class="popup-title">${name}</div>
                <div class="popup-lpcd">
                    <span class="popup-lpcd-value" style="color: ${color}">
                        ${hasLpcd ? lpcd : '—'}
                    </span>
                    <span class="popup-lpcd-unit">L/pers/jour</span>
                </div>
                <div class="popup-stats">
                    <div class="popup-stat-row">
                        <span class="popup-stat-label">Statut</span>
                        <span class="popup-stat-value">${hasLpcd ? this.capitalizeFirst(category) : 'Non disponible'}</span>
                    </div>
                    ${props.population ? `
                    <div class="popup-stat-row">
                        <span class="popup-stat-label">Population</span>
                        <span class="popup-stat-value">${this.formatNumber(props.population)}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    highlightFeature(e) {
        const layer = e.target;
        layer.setStyle({
            weight: 2,
            color: '#1e293b',
            fillOpacity: 0.9
        });
        layer.bringToFront();
    }

    resetHighlight(e) {
        // Find which layer contains this feature and reset its style
        if (this.geojsonLayers) {
            for (const geoLayer of this.geojsonLayers) {
                if (geoLayer.hasLayer(e.target)) {
                    geoLayer.resetStyle(e.target);
                    break;
                }
            }
        }
    }

    selectFeature(e, feature) {
        L.DomEvent.stopPropagation(e);
        this.selectedFeature = feature;
        this.updateInfoPanel(feature.properties);

        // API: Dispatch custom event for external integrations (e.g., calculator)
        const event = new CustomEvent('municipalitySelected', {
            detail: { ...feature.properties },
            bubbles: true
        });
        document.dispatchEvent(event);

        // API: Call onSelect callback if provided
        if (typeof this.options.onSelect === 'function') {
            this.options.onSelect(feature.properties);
        }

        // API: PostMessage for iframe integration (calculator modal)
        // Security: Only send to same origin or explicitly allowed origins
        if (window.parent !== window) {
            // Get the parent origin - default to same origin for security
            const allowedOrigins = [
                window.location.origin,  // Same origin (most common case)
                'https://water-cba.onrender.com',  // Production domain
                'http://localhost:8000',  // Local development
                'http://127.0.0.1:8000',  // Local development alt
            ];

            // Use same origin by default, which is the most secure option
            const targetOrigin = window.location.origin;

            try {
                window.parent.postMessage({
                    type: 'municipalitySelected',
                    data: { ...feature.properties }
                }, targetOrigin);
            } catch (e) {
                // Fallback: if same-origin fails (cross-origin iframe), log warning
                console.warn('PostMessage failed - cross-origin iframe detected. Municipality selection event not sent to parent.');
            }
        }
    }

    updateInfoPanel(props) {
        const panel = document.getElementById('info-panel');
        if (!panel) return;

        const name = props.name || 'Municipalité inconnue';
        const lpcd = props.lpcd;
        const hasLpcd = lpcd != null && props.lpcd_status !== 'missing';
        const category = this.getLpcdCategory(lpcd);
        const color = hasLpcd ? this.getColor(lpcd, 'lpcd') : '#94a3b8';

        // Calculate comparison percentage (position in Quebec range)
        let comparisonPercent = 50;
        if (hasLpcd && this.globalStats) {
            const min = this.globalStats.min || 100;
            const max = this.globalStats.max || 600;
            comparisonPercent = Math.min(100, Math.max(0, ((lpcd - min) / (max - min)) * 100));
        }

        panel.innerHTML = `
            <div class="info-panel-header">
                <div>
                    <div class="info-panel-title">${name}</div>
                    <div class="info-panel-subtitle">Données ${props.lpcd_data_year || 'MAMH'}</div>
                </div>
                <button class="info-panel-close" onclick="window.quebecMap.closeInfoPanel()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
            <div class="info-panel-body">
                <div class="lpcd-gauge">
                    <div class="lpcd-value ${category}" style="color: ${color}">
                        ${hasLpcd ? lpcd : '—'}
                    </div>
                    <div class="lpcd-unit">litres par personne par jour</div>
                    ${hasLpcd ? `<div class="lpcd-status ${category}">${this.capitalizeFirst(category)}</div>` : ''}
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-card-label">Pop. desservie</div>
                        <div class="stat-card-value ${props.population_desservie ? '' : 'na'}">
                            ${props.population_desservie ? this.formatNumber(Math.round(props.population_desservie)) : 'N/D'}
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-card-label">Logements</div>
                        <div class="stat-card-value ${props.nb_logements ? '' : 'na'}">
                            ${props.nb_logements ? this.formatNumber(props.nb_logements) : 'N/D'}
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-card-label">Volume distribué</div>
                        <div class="stat-card-value ${props.consommation ? '' : 'na'}">
                            ${props.consommation ? this.formatNumber(Math.round(props.consommation * 1000 / 365)) + ' m³/j' : 'N/D'}
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-card-label">Pers./logement</div>
                        <div class="stat-card-value ${props.pers_par_residence ? '' : 'na'}">
                            ${props.pers_par_residence ? props.pers_par_residence.toFixed(2) : 'N/D'}
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-card-label">Réseaux</div>
                        <div class="stat-card-value ${props.nb_reseaux ? '' : 'na'}">
                            ${props.nb_reseaux ? props.nb_reseaux : 'N/D'}
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-card-label">Indice fuites</div>
                        <div class="stat-card-value ${props.indice_fuites ? '' : 'na'}">
                            ${props.indice_fuites ? props.indice_fuites.toFixed(1) : 'N/D'}
                        </div>
                    </div>
                </div>

                ${hasLpcd ? `
                <div class="comparison-section">
                    <div class="comparison-title">Comparaison avec la cible QC (${this.targetLpcd} L/j)</div>
                    <div class="comparison-bar">
                        <div class="comparison-bar-fill" style="width: ${comparisonPercent}%; background: ${color}"></div>
                        <div class="comparison-bar-marker comparison-bar-target" style="left: ${Math.min(100, Math.max(0, ((this.targetLpcd - (this.globalStats?.min || 100)) / ((this.globalStats?.max || 400) - (this.globalStats?.min || 100))) * 100))}%" title="Cible QC: ${this.targetLpcd}"></div>
                    </div>
                    <div class="comparison-labels">
                        <span>${this.globalStats?.min || '—'}</span>
                        <span>Cible: ${this.targetLpcd}</span>
                        <span>${this.globalStats?.max || '—'}</span>
                    </div>
                    <div class="target-comparison ${lpcd <= 250 ? 'good' : 'bad'}">
                        ${lpcd <= 250
                            ? '&#10003; Sous ou proche de la cible'
                            : '&#10007; ' + Math.round(((lpcd - this.targetLpcd) / this.targetLpcd) * 100) + '% au-dessus de la cible'}
                    </div>
                </div>
                ` : ''}
            </div>
        `;

        panel.classList.add('active');
    }

    closeInfoPanel() {
        const panel = document.getElementById('info-panel');
        if (panel) panel.classList.remove('active');
        this.selectedFeature = null;
    }

    addLegend() {
        const legend = L.control({ position: 'bottomright' });

        legend.onAdd = () => {
            const div = L.DomUtil.create('div', 'legend');
            const scale = this.colorScales[this.currentMetric];

            // Count municipalities per category
            const counts = this.countByCategory();

            let html = `
                <div class="legend-header">
                    <span class="legend-title">Consommation d'eau</span>
                    <span class="legend-unit">${scale.unit}</span>
                </div>
                <div class="legend-scale">
            `;

            for (let i = 0; i < scale.colors.length; i++) {
                const count = counts[i] || 0;
                html += `
                    <div class="legend-item">
                        <span class="legend-color" style="background: ${scale.colors[i]}"></span>
                        <span class="legend-label">${scale.labels[i]} (${scale.descriptions[i]})</span>
                        <span class="legend-count">${count}</span>
                    </div>
                `;
            }

            html += `
                </div>
                <div class="legend-divider"></div>
                <div class="legend-target">
                    <span class="legend-target-label">Cible Quebec</span>
                    <span class="legend-target-value">${this.targetLpcd} L/pers/j</span>
                </div>
                <div class="legend-divider"></div>
                <div class="legend-item legend-missing">
                    <span class="legend-color"></span>
                    <span class="legend-label">Données non disponibles</span>
                    <span class="legend-count">${counts.missing || 0}</span>
                </div>
            `;

            div.innerHTML = html;
            return div;
        };

        legend.addTo(this.map);
        this.legend = legend;
    }

    countByCategory() {
        const counts = { missing: 0 };
        const scale = this.colorScales[this.currentMetric];

        if (!this.geojsonData?.features) return counts;

        for (const feature of this.geojsonData.features) {
            const value = feature.properties?.[this.currentMetric];
            const status = feature.properties?.lpcd_status;

            if (value == null || status === 'missing') {
                counts.missing++;
                continue;
            }

            let category = scale.ranges.length;
            for (let i = 0; i < scale.ranges.length; i++) {
                if (value < scale.ranges[i]) {
                    category = i;
                    break;
                }
            }
            counts[category] = (counts[category] || 0) + 1;
        }

        return counts;
    }

    addControls() {
        const metricControl = L.control({ position: 'topright' });

        metricControl.onAdd = () => {
            const div = L.DomUtil.create('div', 'metric-control');
            div.innerHTML = `
                <select id="metric-selector">
                    <option value="lpcd" selected>Consommation (LPCD)</option>
                    <option value="population">Population</option>
                </select>
            `;

            L.DomEvent.disableClickPropagation(div);
            div.querySelector('#metric-selector').addEventListener('change', (e) => {
                this.setMetric(e.target.value);
            });

            return div;
        };

        metricControl.addTo(this.map);
    }

    setupSearch() {
        const searchInput = document.getElementById('search-input');
        const searchResults = document.getElementById('search-results');

        if (!searchInput || !searchResults) return;

        let debounceTimer;

        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const query = this.normalizeName(e.target.value);
                if (query.length < 2) {
                    searchResults.classList.remove('active');
                    return;
                }

                const results = this.searchIndex
                    .filter(item => item.normalized.includes(query))
                    .slice(0, 8);

                if (results.length === 0) {
                    searchResults.classList.remove('active');
                    return;
                }

                searchResults.innerHTML = results.map(item => `
                    <div class="search-result-item" data-name="${item.name}">
                        <div class="search-result-name">${item.name}</div>
                        <div class="search-result-region">
                            ${item.lpcd ? `${item.lpcd} L/pers/jour` : 'Données non disponibles'}
                        </div>
                    </div>
                `).join('');

                searchResults.classList.add('active');
            }, 150);
        });

        searchResults.addEventListener('click', (e) => {
            const item = e.target.closest('.search-result-item');
            if (!item) return;

            const name = item.dataset.name;
            const result = this.searchIndex.find(r => r.name === name);

            if (result?.feature) {
                this.zoomToFeature(result.feature);
                this.updateInfoPanel(result.feature.properties);
            }

            searchInput.value = name;
            searchResults.classList.remove('active');
        });

        searchInput.addEventListener('blur', () => {
            setTimeout(() => searchResults.classList.remove('active'), 200);
        });

        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                searchResults.classList.remove('active');
                searchInput.blur();
            }
        });
    }

    zoomToFeature(feature) {
        if (!feature?.geometry) return;

        const layer = this.findLayerByFeature(feature);
        if (layer) {
            this.map.fitBounds(layer.getBounds(), { maxZoom: 11, padding: [50, 50] });
            layer.openPopup();
        }
    }

    findLayerByFeature(feature) {
        let found = null;
        if (this.geojsonLayers) {
            for (const geoLayer of this.geojsonLayers) {
                geoLayer.eachLayer(layer => {
                    if (layer.feature === feature) found = layer;
                });
                if (found) break;
            }
        }
        return found;
    }

    setMetric(metric) {
        this.currentMetric = metric;
        if (this.geojsonLayers) {
            this.geojsonLayers.forEach(layer => {
                layer.setStyle((feature) => this.getFeatureStyle(feature));
            });
        }
        if (this.legend) {
            this.map.removeControl(this.legend);
            this.addLegend();
        }
        // Update header stats for the new metric
        this.updateHeaderStats();
    }

    updateHeaderStats() {
        const avgEl = document.getElementById('stat-average');
        const countEl = document.getElementById('stat-count');
        const coverageEl = document.getElementById('stat-coverage');

        if (!this.globalStats || !this.geojsonData?.features) return;

        // Metric-aware stats calculation
        if (this.currentMetric === 'lpcd') {
            if (avgEl) {
                avgEl.textContent = this.globalStats.average || '—';
                avgEl.className = 'stat-value ' + this.getLpcdCategory(this.globalStats.average);
            }
            if (coverageEl) coverageEl.textContent = this.globalStats.coverage + '%';
        } else if (this.currentMetric === 'population') {
            // Calculate population stats
            const popValues = this.geojsonData.features
                .map(f => f.properties?.population)
                .filter(p => p != null);

            const totalPop = popValues.reduce((a, b) => a + b, 0);
            const avgPop = popValues.length ? Math.round(totalPop / popValues.length) : null;
            const popCoverage = Math.round((popValues.length / this.geojsonData.features.length) * 100);

            if (avgEl) {
                avgEl.textContent = avgPop ? this.formatNumber(avgPop) : '—';
                avgEl.className = 'stat-value';
            }
            if (coverageEl) coverageEl.textContent = popCoverage + '%';
        }

        if (countEl) countEl.textContent = this.formatNumber(this.globalStats.total);
    }

    showDataStatus() {
        const statusEl = document.getElementById('data-status');
        if (!statusEl || !this.metadata) return;

        const date = this.metadata.last_update
            ? new Date(this.metadata.last_update).toLocaleDateString('fr-CA')
            : 'N/D';

        const hasWarnings = this.metadata.warnings?.length > 0;

        statusEl.innerHTML = `
            <span class="data-status-dot"></span>
            <span>MAJ: ${date}</span>
        `;

        if (hasWarnings) {
            statusEl.classList.add('warning');
            statusEl.title = this.metadata.warnings.join(', ');
        }
    }

    // Loader methods
    showLoader(message, progress) {
        let loader = document.getElementById('map-loader');
        if (!loader) {
            loader = document.createElement('div');
            loader.id = 'map-loader';
            loader.className = 'map-loader';
            loader.innerHTML = `
                <div class="loader-content">
                    <div class="loader-spinner"></div>
                    <div class="loader-title">Chargement de la carte</div>
                    <div class="loader-message">${message}</div>
                    <div class="loader-progress">
                        <div class="loader-progress-bar"></div>
                    </div>
                </div>
            `;
            document.querySelector('.map-container')?.appendChild(loader);
        }

        const msgEl = loader.querySelector('.loader-message');
        const barEl = loader.querySelector('.loader-progress-bar');

        if (msgEl) msgEl.textContent = message;
        if (barEl) barEl.style.width = progress + '%';

        loader.classList.remove('hidden');
    }

    hideLoader() {
        const loader = document.getElementById('map-loader');
        if (loader) {
            loader.classList.add('hidden');
            setTimeout(() => loader.remove(), 300);
        }
    }

    showError(message) {
        const container = document.getElementById(this.containerId);
        if (container) {
            container.innerHTML = `
                <div class="error-container">
                    <div class="error-icon">!</div>
                    <div class="error-title">Erreur de chargement</div>
                    <div class="error-message">${message}</div>
                </div>
            `;
        }
    }

    // Utility methods
    formatNumber(num) {
        if (num == null) return 'N/D';
        return Number(num).toLocaleString('fr-CA');
    }

    capitalizeFirst(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    // Methodology Panel
    setupMethodologyPanel() {
        const btn = document.getElementById('btn-methodology');
        if (btn) {
            btn.addEventListener('click', () => this.openMethodologyPanel());
        }

        // Setup overlay click handler
        const overlay = document.getElementById('methodology-overlay');
        if (overlay) {
            overlay.addEventListener('click', () => this.closeMethodologyPanel());
        }
    }

    openMethodologyPanel() {
        const panel = document.getElementById('methodology-panel');
        const overlay = document.getElementById('methodology-overlay');

        if (panel) {
            panel.classList.add('active');

            // Update dynamic content
            const coverageEl = document.getElementById('methodology-coverage');
            if (coverageEl && this.globalStats) {
                coverageEl.textContent = `Couverture actuelle : ${this.globalStats.coverage}% des municipalités ont des données LPCD disponibles.`;
            }

            const updateEl = document.getElementById('methodology-update-date');
            if (updateEl && this.metadata?.last_update) {
                const date = new Date(this.metadata.last_update).toLocaleDateString('fr-CA', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                });
                updateEl.textContent = `Dernière mise à jour : ${date}`;
            }
        }

        if (overlay) {
            overlay.classList.add('active');
        }
    }

    closeMethodologyPanel() {
        const panel = document.getElementById('methodology-panel');
        const overlay = document.getElementById('methodology-overlay');

        if (panel) panel.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
    }

    // Public API
    async refresh() {
        await this.loadData();
        this.calculateGlobalStats();
        this.updateHeaderStats();
        this.showDataStatus();
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = QuebecMap;
}

// Listen for invalidateSize message from parent (modal open)
window.addEventListener('message', function(event) {
    if (event.data?.type === 'invalidateSize' && window.quebecMap?.map) {
        window.quebecMap.map.invalidateSize();
        // Re-fit bounds after invalidating size
        if (window.quebecMap.geojsonLayers?.length > 0) {
            let bounds = null;
            for (const layer of window.quebecMap.geojsonLayers) {
                const layerBounds = layer.getBounds();
                if (layerBounds.isValid()) {
                    bounds = bounds ? bounds.extend(layerBounds) : layerBounds;
                }
            }
            if (bounds) {
                window.quebecMap.map.fitBounds(bounds, { padding: [20, 20] });
            }
        }
    }
});
