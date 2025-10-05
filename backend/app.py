
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import ee
import json
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='../frontend/static', template_folder='../frontend/templates')
CORS(app)

EARTH_ENGINE_PROJECT = 'codonautas-2025'


# Inicializa Google Earth Engine
try:
    ee.Initialize(project=EARTH_ENGINE_PROJECT)  
    print("✓ Google Earth Engine inicializado")
except:
    print("⚠ Execute ee.Authenticate() primeiro")

# Base de dados de cidades brasileiras
CITIES = {
    'sao_paulo': {
        'name': 'São Paulo',
        'bounds': [-46.82, -23.79, -46.36, -23.38],
        'center': [-23.55, -46.63],
        'zoom': 11
    },
    'rio_janeiro': {
        'name': 'Rio de Janeiro',
        'bounds': [-43.79, -23.08, -43.09, -22.74],
        'center': [-22.91, -43.17],
        'zoom': 11
    },
    'brasilia': {
        'name': 'Brasília',
        'bounds': [-48.08, -16.03, -47.38, -15.50],
        'center': [-15.78, -47.93],
        'zoom': 11
    },
    'belo_horizonte': {
        'name': 'Belo Horizonte',
        'bounds': [-44.08, -20.08, -43.85, -19.78],
        'center': [-19.92, -43.94],
        'zoom': 11
    },
    'curitiba': {
        'name': 'Curitiba',
        'bounds': [-49.38, -25.64, -49.18, -25.34],
        'center': [-25.43, -49.27],
        'zoom': 11
    },
    'fortaleza': {
        'name': 'Fortaleza',
        'bounds': [-38.63, -3.88, -38.40, -3.68],
        'center': [-3.73, -38.52],
        'zoom': 11
    },
    'recife': {
        'name': 'Recife',
        'bounds': [-35.03, -8.18, -34.85, -7.93],
        'center': [-8.05, -34.88],
        'zoom': 11
    },
    'salvador': {
        'name': 'Salvador',
        'bounds': [-38.58, -13.02, -38.30, -12.83],
        'center': [-12.97, -38.51],
        'zoom': 11
    }
}


def get_modis_lst(geometry, start_date, end_date):
    """
    Obtém dados de temperatura de superfície do MODIS.
    
    Args:
        geometry: Geometria da área de interesse
        start_date: Data inicial (YYYY-MM-DD)
        end_date: Data final (YYYY-MM-DD)
    
    Returns:
        ee.Image: Imagem de LST em Celsius
    """
    def process_modis(image):
        # Banda LST_Day_1km
        lst = image.select('LST_Day_1km')
        
        # Fator de escala: LST (K) = DN * 0.02
        lst_kelvin = lst.multiply(0.02)
        lst_celsius = lst_kelvin.subtract(273.15)
        
        # Máscara de qualidade
        qc = image.select('QC_Day')
        mask = qc.bitwiseAnd(3).eq(0)
        
        return lst_celsius.updateMask(mask)
    
    # Carrega coleção MODIS Terra
    collection = ee.ImageCollection('MODIS/061/MOD11A1') \
        .filterBounds(geometry) \
        .filterDate(start_date, end_date) \
        .map(process_modis)
    
    return collection.mean().clip(geometry)


def identify_hotspots(lst_image, threshold=35.0):
    """
    Identifica áreas críticas (ilhas de calor).
    
    Args:
        lst_image: Imagem de LST
        threshold: Temperatura limiar em °C
    
    Returns:
        ee.Image: Máscara de hotspots
    """
    return lst_image.gt(threshold)


def get_planting_points(lst_image, geometry, threshold=35.0, max_points=50):
    """
    Identifica pontos prioritários para plantio de árvores.
    
    Args:
        lst_image: Imagem de LST
        geometry: Área de interesse
        threshold: Temperatura mínima para considerar
        max_points: Número máximo de pontos
    
    Returns:
        list: Lista de pontos [lat, lon, temperatura]
    """
    # Cria máscara de hotspots
    hotspots = lst_image.gt(threshold)
    
    # Amostra pontos nas áreas quentes
    points = lst_image.updateMask(hotspots).sample(
        region=geometry,
        scale=1000,
        numPixels=max_points,
        geometries=True
    )
    
    # Converte para lista
    points_list = points.toList(max_points)
    size = points_list.size().getInfo()
    
    result = []
    for i in range(min(size, max_points)):
        point = ee.Feature(points_list.get(i))
        coords = point.geometry().coordinates().getInfo()
        temp = point.get('LST_Day_1km').getInfo()
        
        if temp and coords:
            result.append({
                'lat': coords[1],
                'lon': coords[0],
                'temperature': round(temp, 2)
            })
    
    return result


@app.route('/')
def index():
    """Página principal."""
    return send_from_directory('../frontend/templates', 'index.html')


@app.route('/api/cities', methods=['GET'])
def get_cities():
    """Retorna lista de cidades disponíveis."""
    cities_list = [
        {
            'id': city_id,
            'name': data['name'],
            'center': data['center'],
            'zoom': data['zoom']
        }
        for city_id, data in CITIES.items()
    ]
    return jsonify(cities_list)


@app.route('/api/heatmap/<city_id>', methods=['GET'])
def get_heatmap(city_id):
    """
    Gera dados de mapa de calor para uma cidade.
    
    Query params:
        - days: número de dias para análise (padrão: 30)
    """
    if city_id not in CITIES:
        return jsonify({'error': 'Cidade não encontrada'}), 404
    
    city = CITIES[city_id]
    days = int(request.args.get('days', 30))
    
    # Define período
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Cria geometria
    bounds = city['bounds']
    geometry = ee.Geometry.Rectangle(bounds)
    
    try:
        # Obtém dados MODIS
        lst_image = get_modis_lst(
            geometry,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # Calcula estatísticas
        stats = lst_image.reduceRegion(
            reducer=ee.Reducer.minMax().combine(
                ee.Reducer.mean(), '', True
            ).combine(
                ee.Reducer.stdDev(), '', True
            ),
            geometry=geometry,
            scale=1000,
            maxPixels=1e9
        ).getInfo()
        
        # Extrai valores
        temp_min = stats.get('LST_Day_1km_min', 0)
        temp_max = stats.get('LST_Day_1km_max', 0)
        temp_mean = stats.get('LST_Day_1km_mean', 0)
        temp_std = stats.get('LST_Day_1km_stdDev', 0)
        
        # Gera URL do tile para visualização
        map_id = lst_image.getMapId({
            'min': 20,
            'max': 45,
            'palette': [
                '313695', '4575b4', '74add1', 'abd9e9', 'e0f3f8',
                'ffffbf', 'fee090', 'fdae61', 'f46d43', 'd73027', 'a50026'
            ]
        })
        
        return jsonify({
            'city': city['name'],
            'bounds': bounds,
            'center': city['center'],
            'zoom': city['zoom'],
            'tile_url': map_id['tile_fetcher'].url_format,
            'statistics': {
                'min': round(temp_min, 2),
                'max': round(temp_max, 2),
                'mean': round(temp_mean, 2),
                'stdDev': round(temp_std, 2)
            },
            'period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
                'days': days
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/planting-points/<city_id>', methods=['GET'])
def get_planting_points_api(city_id):
    """
    Identifica pontos prioritários para plantio.
    
    Query params:
        - threshold: temperatura mínima (padrão: 35)
        - max_points: número máximo de pontos (padrão: 30)
        - days: número de dias para análise (padrão: 30)
    """
    if city_id not in CITIES:
        return jsonify({'error': 'Cidade não encontrada'}), 404
    
    city = CITIES[city_id]
    threshold = float(request.args.get('threshold', 35.0))
    max_points = int(request.args.get('max_points', 30))
    days = int(request.args.get('days', 30))
    
    # Define período
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Cria geometria
    bounds = city['bounds']
    geometry = ee.Geometry.Rectangle(bounds)
    
    try:
        # Obtém dados MODIS
        lst_image = get_modis_lst(
            geometry,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # Identifica pontos
        points = get_planting_points(
            lst_image,
            geometry,
            threshold=threshold,
            max_points=max_points
        )
        
        return jsonify({
            'city': city['name'],
            'threshold': threshold,
            'points_count': len(points),
            'points': points
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
