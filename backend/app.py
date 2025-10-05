import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import ee
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ===============================================================
# ⚙️ CONFIGURAÇÃO INICIAL
# ===============================================================

# Carrega variáveis do .env
load_dotenv()

basedir = os.path.dirname(os.path.abspath(__file__))
template_folder_path = os.path.join(basedir, '../frontend/templates')
static_folder_path = os.path.join(basedir, '../frontend/static')

app = Flask(
    __name__,
    template_folder=template_folder_path,
    static_folder=static_folder_path,
    static_url_path='/static'
)
CORS(app)

EARTH_PROJETO = os.getenv('EARTH_PROJETO')

try:
    ee.Initialize(project=EARTH_PROJETO)
    print(f"✅ Earth Engine inicializado no projeto: {EARTH_PROJETO}")
except Exception as e:
    print("⚠ Falha ao inicializar o Earth Engine:", e)
    print("Execute 'earthengine authenticate' no terminal.")

# ===============================================================
# 🗺️ CIDADES DISPONÍVEIS
# ===============================================================
CITIES = {
    'sao_paulo': {'name': 'São Paulo', 'center': [-23.55, -46.63], 'zoom': 11},
    'rio_janeiro': {'name': 'Rio de Janeiro', 'center': [-22.91, -43.17], 'zoom': 11},
    'brasilia': {'name': 'Brasília', 'center': [-15.78, -47.93], 'zoom': 11},
    'belo_horizonte': {'name': 'Belo Horizonte', 'center': [-19.92, -43.94], 'zoom': 11},
    'curitiba': {'name': 'Curitiba', 'center': [-25.43, -49.27], 'zoom': 11},
    'fortaleza': {'name': 'Fortaleza', 'center': [-3.73, -38.52], 'zoom': 11},
    'recife': {'name': 'Recife', 'center': [-8.05, -34.88], 'zoom': 11},
    'salvador': {'name': 'Salvador', 'center': [-12.97, -38.51], 'zoom': 11}
}

# ===============================================================
# 🔥 1. FUNÇÕES DE PROCESSAMENTO DE IMAGENS
# ===============================================================

def process_modis(image):
    lst = image.select('LST_Day_1km').multiply(0.02).subtract(273.15)
    qc = image.select('QC_Day')
    mask = qc.bitwiseAnd(3).eq(0)
    return lst.updateMask(mask).resample('bilinear')

def get_modis_lst(geometry, start_date, end_date):
    return ee.ImageCollection('MODIS/061/MOD11A1') \
        .filterBounds(geometry) \
        .filterDate(start_date, end_date) \
        .map(process_modis) \
        .mean() \
        .clip(geometry)

def get_landsat_lst(geometry, start_date, end_date):
    def process_landsat(image):
        lst = image.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15)
        qa = image.select('QA_PIXEL')
        mask = qa.bitwiseAnd(1 << 3).eq(0)
        return lst.updateMask(mask).resample('bilinear')

    return ee.ImageCollection('LANDSAT/LC09/C02/T1_L2') \
        .filterBounds(geometry) \
        .filterDate(start_date, end_date) \
        .filter(ee.Filter.lt('CLOUD_COVER', 20)) \
        .map(process_landsat) \
        .median() \
        .clip(geometry)

def get_heatmap_points_from_image(lst_image, geometry, scale=1000, num_pixels=2000):
    """
    Extrai pontos normalizados (0–1) para uso no Leaflet HeatLayer.
    Garante contraste adequado e gradiente realista.
    """
    band_name = 'temperature'
    lst_image = lst_image.select([0], [band_name])
    
    # Amostragem de pixels
    sampled = lst_image.sample(
        region=geometry,
        scale=scale,
        numPixels=num_pixels,
        geometries=True
    ).getInfo()
    
    features = sampled.get('features', [])
    if not features:
        print("⚠ Nenhum dado de temperatura coletado do GEE.")
        return []
    
    # Coleta dados crus
    raw_points = []
    for f in features:
        coords = f.get('geometry', {}).get('coordinates')
        temp = f.get('properties', {}).get(band_name)
        if coords and temp is not None:
            lat, lon = coords[1], coords[0]
            raw_points.append((lat, lon, temp))
    
    # Determina intervalo real de temperatura
    temps = [t for _, _, t in raw_points]
    t_min, t_max = min(temps), max(temps)
    t_range = max(t_max - t_min, 0.001)

    # Normaliza temperatura entre 0–1 (com leve compressão para evitar saturação)
    points_normalized = [
        [lat, lon, min(max((temp - t_min) / t_range, 0.05), 0.95)]
        for lat, lon, temp in raw_points
    ]
    
    print(f"🌡️ Heatmap normalizado: {len(points_normalized)} pontos ({round(t_min,1)}°C–{round(t_max,1)}°C)")
    return points_normalized



# ===============================================================
# 🌡️ 2. ENDPOINT - MAPA DE CALOR
# ===============================================================
@app.route('/')
def index():
    return send_from_directory(app.template_folder, 'index.html')

@app.route('/api/cities', methods=['GET'])
def get_cities():
    return jsonify([{'id': cid, 'name': data['name']} for cid, data in CITIES.items()])

@app.route('/api/heatmap/<city_id>', methods=['GET'])
def get_heatmap(city_id):
    if city_id not in CITIES:
        return jsonify({'error': 'Cidade não encontrada'}), 404

    city = CITIES[city_id]
    source = request.args.get('source', 'modis')
    radius_km = float(request.args.get('radius', 25))  # 🔹 Área circular ampliada (25 km)

    lst_image, days_used = None, 0
    for days in [30, 90, 180]:
        print(f"Tentando obter dados de {days} dias...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        geometry = ee.Geometry.Point(city['center'][1], city['center'][0]).buffer(radius_km * 1000)
        try:
            if source == 'landsat':
                image = get_landsat_lst(geometry, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            else:
                image = get_modis_lst(geometry, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

            stats = image.reduceRegion(
                reducer=ee.Reducer.minMax(),
                geometry=geometry,
                scale=1000,
                maxPixels=1e9
            ).getInfo()
            if stats and any(stats.values()):
                lst_image, days_used = image, days
                break
        except Exception as e:
            print(f"Falha ao buscar dados ({days} dias): {e}")

    if lst_image is None:
        return jsonify({'error': 'Sem dados de satélite para esta região (alta cobertura de nuvens).'}), 404

    stats_final = lst_image.reduceRegion(
        reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), '', True),
        geometry=geometry, scale=500, maxPixels=1e9
    ).getInfo()
    heatmap_points = get_heatmap_points_from_image(lst_image, geometry)

    return jsonify({
        'city': city['name'],
        'center': city['center'],
        'zoom': city['zoom'],
        'heatmap_points': heatmap_points,
        'statistics': {
            'min': round(next((v for k, v in stats_final.items() if 'min' in k), 0), 2),
            'max': round(next((v for k, v in stats_final.items() if 'max' in k), 0), 2),
            'mean': round(next((v for k, v in stats_final.items() if 'mean' in k), 0), 2)
        },
        'source': source,
        'days_used': days_used
    })

# ===============================================================
# 🌱 3. ENDPOINT - PONTOS DE PLANTIO
# ===============================================================
def get_planting_points(lst_image, geometry, threshold=35.0, max_points=50):
    band_name = lst_image.bandNames().get(0)
    lst_image = lst_image.select([band_name], ['temperature'])
    hotspots = lst_image.gt(threshold)
    samples = lst_image.updateMask(hotspots).sample(region=geometry, scale=500, numPixels=max_points, geometries=True)
    features = samples.toList(max_points)
    result = []
    for i in range(min(features.size().getInfo(), max_points)):
        f = ee.Feature(features.get(i))
        coords = f.geometry().coordinates().getInfo()
        temp = f.get('temperature').getInfo()
        if coords and temp:
            result.append({'lat': coords[1], 'lon': coords[0], 'temperature': round(temp, 2)})
    return result

@app.route('/api/planting-points/<city_id>', methods=['GET'])
def get_planting_points_api(city_id):
    if city_id not in CITIES:
        return jsonify({'error': 'Cidade não encontrada'}), 404

    city = CITIES[city_id]
    threshold = float(request.args.get('threshold', 35))
    max_points = int(request.args.get('max_points', 30))
    source = request.args.get('source', 'modis')
    radius_km = float(request.args.get('radius', 25))
    days = int(request.args.get('days', 30))

    geometry = ee.Geometry.Point(city['center'][1], city['center'][0]).buffer(radius_km * 1000)
    start_date = datetime.now() - timedelta(days=days)
    end_date = datetime.now()

    if source == 'landsat':
        lst_image = get_landsat_lst(geometry, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    else:
        lst_image = get_modis_lst(geometry, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

    points = get_planting_points(lst_image, geometry, threshold, max_points)
    return jsonify({'city': city['name'], 'points': points, 'count': len(points)})

# ===============================================================
# 🚀 EXECUÇÃO
# ===============================================================
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
