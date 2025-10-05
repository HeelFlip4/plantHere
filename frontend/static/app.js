// GreenPulse - Frontend JavaScript
const API_BASE = window.location.origin;

let map;
let heatmapLayer;
let pointsLayer;
let currentCity = null;

// Inicializa o mapa
function initMap() {
    map = L.map('map').setView([-15.78, -47.93], 4);
    
    // Camada base do OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);
    
    // Grupo de camadas para pontos
    pointsLayer = L.layerGroup().addTo(map);
}

// Carrega lista de cidades
async function loadCities() {
    try {
        const response = await fetch(`${API_BASE}/api/cities`);
        const cities = await response.json();
        
        const select = document.getElementById('citySelect');
        select.innerHTML = '<option value="">Selecione uma cidade...</option>';
        
        cities.forEach(city => {
            const option = document.createElement('option');
            option.value = city.id;
            option.textContent = city.name;
            select.appendChild(option);
        });
        
        // Event listener para mudança de cidade
        select.addEventListener('change', (e) => {
            if (e.target.value) {
                loadHeatmap(e.target.value);
            }
        });
        
    } catch (error) {
        console.error('Erro ao carregar cidades:', error);
        alert('Erro ao carregar lista de cidades');
    }
}

// Carrega mapa de calor para uma cidade
async function loadHeatmap(cityId) {
    const loading = document.getElementById('loading');
    const statsCard = document.getElementById('statsCard');
    
    loading.style.display = 'block';
    statsCard.style.display = 'none';
    
    // Limpa pontos anteriores
    clearPoints();
    
    try {
        const response = await fetch(`${API_BASE}/api/heatmap/${cityId}?days=30`);
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        currentCity = cityId;
        
        // Centraliza o mapa na cidade
        map.setView(data.center, data.zoom);
        
        // Remove camada de heatmap anterior
        if (heatmapLayer) {
            map.removeLayer(heatmapLayer);
        }
        
        // Adiciona camada de tiles do Earth Engine
        heatmapLayer = L.tileLayer(data.tile_url, {
            maxZoom: 18,
            opacity: 0.7
        }).addTo(map);
        
        // Atualiza estatísticas
        document.getElementById('tempMin').textContent = `${data.statistics.min.toFixed(1)}°C`;
        document.getElementById('tempMax').textContent = `${data.statistics.max.toFixed(1)}°C`;
        document.getElementById('tempMean').textContent = `${data.statistics.mean.toFixed(1)}°C`;
        
        statsCard.style.display = 'block';
        loading.style.display = 'none';
        
    } catch (error) {
        console.error('Erro ao carregar mapa de calor:', error);
        loading.style.display = 'none';
        alert('Erro ao carregar mapa de calor. Verifique se o Earth Engine está autenticado.');
    }
}

// Identifica pontos para plantio
async function findPlantingPoints() {
    if (!currentCity) {
        alert('Selecione uma cidade primeiro!');
        return;
    }
    
    const loading = document.getElementById('loading');
    loading.style.display = 'block';
    
    try {
        const response = await fetch(
            `${API_BASE}/api/planting-points/${currentCity}?threshold=35&max_points=30&days=30`
        );
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Limpa pontos anteriores
        clearPoints();
        
        // Adiciona marcadores no mapa
        const pointsContainer = document.getElementById('pointsContainer');
        pointsContainer.innerHTML = '';
        
        data.points.forEach((point, index) => {
            // Cria marcador
            const marker = L.circleMarker([point.lat, point.lon], {
                radius: 8,
                fillColor: getColorForTemp(point.temperature),
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8
            }).addTo(pointsLayer);
            
            // Popup do marcador
            const popupContent = `
                <div class="popup-content">
                    <h4>🌳 Ponto Prioritário #${index + 1}</h4>
                    <p><strong>Temperatura:</strong> <span class="temp-badge ${getTempClass(point.temperature)}">${point.temperature.toFixed(1)}°C</span></p>
                    <p><strong>Coordenadas:</strong> ${point.lat.toFixed(5)}, ${point.lon.toFixed(5)}</p>
                    <p style="margin-top: 10px; color: #666;">Esta área apresenta alta temperatura e é prioritária para plantio de árvores.</p>
                </div>
            `;
            marker.bindPopup(popupContent);
            
            // Adiciona item na lista
            const pointItem = document.createElement('div');
            pointItem.className = 'point-item';
            pointItem.innerHTML = `
                <div><strong>Ponto #${index + 1}</strong></div>
                <div class="point-temp">${point.temperature.toFixed(1)}°C</div>
            `;
            pointItem.addEventListener('click', () => {
                map.setView([point.lat, point.lon], 15);
                marker.openPopup();
            });
            pointsContainer.appendChild(pointItem);
        });
        
        // Mostra lista de pontos
        document.getElementById('pointsList').style.display = 'block';
        document.getElementById('clearPointsBtn').style.display = 'block';
        
        // Ajusta zoom para mostrar todos os pontos
        if (data.points.length > 0) {
            const bounds = L.latLngBounds(data.points.map(p => [p.lat, p.lon]));
            map.fitBounds(bounds, { padding: [50, 50] });
        }
        
        loading.style.display = 'none';
        
    } catch (error) {
        console.error('Erro ao identificar pontos:', error);
        loading.style.display = 'none';
        alert('Erro ao identificar pontos para plantio');
    }
}

// Limpa pontos do mapa
function clearPoints() {
    pointsLayer.clearLayers();
    document.getElementById('pointsList').style.display = 'none';
    document.getElementById('clearPointsBtn').style.display = 'none';
    document.getElementById('pointsContainer').innerHTML = '';
}

// Retorna cor baseada na temperatura
function getColorForTemp(temp) {
    if (temp >= 40) return '#a50026';
    if (temp >= 38) return '#d73027';
    if (temp >= 36) return '#f46d43';
    if (temp >= 34) return '#fdae61';
    if (temp >= 32) return '#fee090';
    if (temp >= 30) return '#ffffbf';
    if (temp >= 28) return '#e0f3f8';
    if (temp >= 26) return '#abd9e9';
    if (temp >= 24) return '#74add1';
    if (temp >= 22) return '#4575b4';
    return '#313695';
}

// Retorna classe CSS para temperatura
function getTempClass(temp) {
    return temp >= 37 ? 'temp-hot' : 'temp-warm';
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    loadCities();
    
    document.getElementById('findPointsBtn').addEventListener('click', findPlantingPoints);
    document.getElementById('clearPointsBtn').addEventListener('click', clearPoints);
});
