import dash
from dash import dcc, html
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json
import os

# Inicializar app
app = dash.Dash(__name__)
server = app.server  # Importante para Render
app.title = "Dashboard GNCV"

# Función para convertir datos a GeoJSON
def convert_to_geojson(df, lat_col, lon_col, properties_cols):
    """
    Convierte un DataFrame con coordenadas a formato GeoJSON.
    
    Args:
        df: DataFrame con datos
        lat_col: Nombre de la columna con latitudes
        lon_col: Nombre de la columna con longitudes
        properties_cols: Lista de columnas a incluir como propiedades
        
    Returns:
        Diccionario con estructura GeoJSON
    """
    features = []
    
    # Filtrar filas sin coordenadas
    valid_df = df.dropna(subset=[lat_col, lon_col])
    
    for _, row in valid_df.iterrows():
        # Crear propiedades del feature
        properties = {}
        for col in properties_cols:
            # Convertir valores no serializables a string
            if isinstance(row[col], (pd.Timestamp, np.integer, np.floating, np.bool_)):
                properties[col] = str(row[col])
            else:
                properties[col] = row[col]
        
        # Crear feature
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row[lon_col]), float(row[lat_col])]
            },
            "properties": properties
        }
        
        features.append(feature)
    
    # Crear estructura GeoJSON
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return geojson

# Cargar datos
try:
    # Ruta del archivo CSV
    csv_path = "Consulta_Precios_Promedio_de_Gas_Natural_Comprimido_Vehicular__AUTOMATIZADO__20250314.csv"
    df = pd.read_csv(csv_path, encoding="latin1")
    
    # Convertir fecha a datetime
    fecha_col = 'FECHA_PRECIO'
    precio_col = 'PRECIO_PROMEDIO_PUBLICADO'
    departamento_col = 'DEPARTAMENTO_EDS'
    
    df[fecha_col] = pd.to_datetime(df[fecha_col])
    
    # Crear columnas ANIO y MES
    df['ANIO'] = df[fecha_col].dt.year
    df['MES'] = df[fecha_col].dt.month
    
    # -------------------------
    # GRÁFICOS ESTADÍSTICOS
    # -------------------------
    fig_hist = px.histogram(df, x=precio_col, nbins=30, title="Distribución de Precios Promedio")
    fig_box = px.box(df, x=departamento_col, y=precio_col, title="Boxplot por Departamento")
    
    df_line = df.groupby([fecha_col, departamento_col])[precio_col].mean().reset_index()
    fig_line = px.line(df_line, x=fecha_col, y=precio_col, color=departamento_col, title="Evolución por Departamento")
    
    df_trend = df.groupby(fecha_col)[precio_col].mean().reset_index()
    fig_trend = px.line(df_trend, x=fecha_col, y=precio_col, title="Tendencia Global de Precios")
    
    df_anual_mes = df.groupby(['ANIO', 'MES'])[precio_col].mean().reset_index()
    fig_anual_mes = px.line(df_anual_mes, x='MES', y=precio_col, color='ANIO', title="Tendencia por Año y Mes")
    
    precio_por_departamento = df.groupby(departamento_col)[precio_col].mean().sort_values()
    fig_bar = px.bar(x=precio_por_departamento.values, y=precio_por_departamento.index, orientation='h', title="Precio Promedio por Departamento")
    
    top_municipios = df.groupby('MUNICIPIO_EDS')[precio_col].mean().nlargest(10)
    fig_top_municipios = px.bar(x=top_municipios.values, y=top_municipios.index, orientation='h', title="Top 10 Municipios con Precios Más Altos")
    
    corr_matrix = df.select_dtypes(include=np.number).corr().round(2)
    fig_corr = px.imshow(corr_matrix, text_auto=True, color_continuous_scale='RdBu_r', title="Matriz de Correlación")
    
    # -------------------------
    # MAPA CON GEOJSON
    # -------------------------
    ultimo_mes = df[fecha_col].max()
    df_ultimo_mes = df[df[fecha_col] == ultimo_mes]
    
    # Convertir datos a GeoJSON y guardar en archivo
    propiedades = ['MUNICIPIO_EDS', 'DEPARTAMENTO_EDS', precio_col]
    geojson_data = convert_to_geojson(df_ultimo_mes, 'LATITUD_MUNICIPIO', 'LONGITUD_MUNICIPIO', propiedades)
    
    # Guardar GeoJSON en archivo (opcional)
    geojson_path = 'municipios_precios.geojson'
    with open(geojson_path, 'w') as f:
        json.dump(geojson_data, f)
    
    # Crear mapa Choropleth con GeoJSON generado
    fig_mapa = px.choropleth_mapbox(
        df_ultimo_mes,
        geojson=geojson_data,
        locations=df_ultimo_mes.index,  # Usar índice como identificador
        color=precio_col,
        color_continuous_scale="sunsetdark",
        mapbox_style="carto-positron",
        zoom=4.5,
        center={"lat": 4.57, "lon": -74.3},
        opacity=0.7,
        hover_name="MUNICIPIO_EDS",
        hover_data=[departamento_col, precio_col],
        title=f"📍 Precios de GNCV por Municipio - {ultimo_mes.strftime('%B %Y')}"
    )
    
    # Si el mapa choropleth no funciona bien, crear mapa de dispersión como respaldo
    fig_mapa_scatter = px.scatter_mapbox(
        df_ultimo_mes.dropna(subset=['LATITUD_MUNICIPIO', 'LONGITUD_MUNICIPIO']),
        lat="LATITUD_MUNICIPIO",
        lon="LONGITUD_MUNICIPIO",
        color=precio_col,
        size=[10] * len(df_ultimo_mes),  # Tamaño fijo para todos los puntos
        color_continuous_scale="sunsetdark",
        zoom=4.5,
        mapbox_style="carto-positron",
        hover_name="MUNICIPIO_EDS",
        hover_data=[departamento_col, precio_col],
        title=f"📍 Precios de GNCV por Municipio - {ultimo_mes.strftime('%B %Y')}"
    )
    
    # Seleccionar el mapa que se usará (descomentar la línea según el mapa preferido)
    # fig_mapa_final = fig_mapa  # Usar mapa choropleth
    fig_mapa_final = fig_mapa_scatter  # Usar mapa de dispersión
    
    graficos_disponibles = True
    
except Exception as e:
    print(f"Error al cargar datos o crear gráficos: {e}")
    graficos_disponibles = False

# Construir pestañas
tabs = []

# Añadir pestaña de mapa
if graficos_disponibles:
    tabs.append(
        dcc.Tab(label="📍 Mapa de Precios", children=[
            dcc.Graph(figure=fig_mapa_final)
        ])
    )

# Añadir pestañas de gráficos estadísticos
if graficos_disponibles:
    tabs.extend([
        dcc.Tab(label='Histograma', children=[dcc.Graph(figure=fig_hist)]),
        dcc.Tab(label='Boxplot por Departamento', children=[dcc.Graph(figure=fig_box)]),
        dcc.Tab(label='Evolución por Departamento', children=[dcc.Graph(figure=fig_line)]),
        dcc.Tab(label='Tendencia Global', children=[dcc.Graph(figure=fig_trend)]),
        dcc.Tab(label='Tendencia Año/Mes', children=[dcc.Graph(figure=fig_anual_mes)]),
        dcc.Tab(label='Barras por Departamento', children=[dcc.Graph(figure=fig_bar)]),
        dcc.Tab(label='Top 10 Municipios', children=[dcc.Graph(figure=fig_top_municipios)]),
        dcc.Tab(label='Matriz de Correlación', children=[dcc.Graph(figure=fig_corr)])
    ])

# Layout final
if len(tabs) > 0:
    app.layout = html.Div([
        html.H1("📈 Análisis de Precios de GNCV en Colombia", style={"textAlign": "center"}),
        html.Div([
            html.P("Análisis estadístico y geoespacial de precios de GNCV", 
                  style={"textAlign": "center", "fontStyle": "italic"})
        ]),
        dcc.Tabs(tabs)
    ])
else:
    # Mostrar mensaje de error si no hay datos disponibles
    app.layout = html.Div([
        html.H1("Error al cargar el Dashboard", style={"textAlign": "center", "color": "red"}),
        html.P("No se pudieron cargar los datos necesarios. Verifica que el archivo CSV está en la ruta correcta.", 
               style={"textAlign": "center"})
    ])

# Ejecutar el servidor
if __name__ == '__main__':
    app.run(debug=True, port=8051)