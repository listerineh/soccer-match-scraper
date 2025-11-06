# Análisis de Partidos de Fútbol y Altitud

Este proyecto recopila datos de partidos de torneos de fútbol sudamericanos (Copa Libertadores, Copa Sudamericana), los enriquece con información de altitud de las ciudades de los equipos y genera un archivo CSV final para análisis. El objetivo principal es estudiar el efecto de la diferencia de altitud en los resultados de los partidos.

## Nota Importante sobre el Scraper

El script `scraper.py` fue desarrollado y probado específicamente para extraer datos de los torneos de Copa Libertadores y Copa Sudamericana **entre los años 2014 y 2024**.

No se garantiza su correcto funcionamiento para años anteriores o posteriores a este rango, ya que la estructura de las páginas web de origen podría variar y requerir ajustes en las funciones de parseo (`parse_group_stage_matches`, `parse_knockout_matches`) y limpieza de datos (`clean_team_name`).

## Estructura de Carpetas y Archivos

El proyecto está organizado de la siguiente manera para separar los datos de la lógica de procesamiento.

```bash
soccer-match-scrapper/
├── README.md
├── data/
│   ├── mappings/
│   │   └── city_mappings.json
│   ├── processed/
│   │   ├── libertadores_analysis.csv
│   │   └── sudamericana_analysis.csv
│   └── raw/
│       ├── libertadores_matches.json
│       └── sudamericana_matches.json
│       ├── unique_teams_libertadores.txt
│       └── unique_teams_sudamericana.txt
├── scripts/
│   ├── generate_teams.py
│   ├── process_altitude.py
│   ├── scraper.py
├── requirements.txt
└── runner.sh
```

- **`data/mappings/`**: Contiene archivos de mapeo.
  - `city_mappings.json`: Un archivo JSON crucial que mapea ciudades a su altitud y a los equipos que juegan en ellas. **Este es el único archivo que necesita ser mantenido manualmente.**
- **`data/raw/`**: Almacena los datos brutos de los partidos en formato JSON, tal como se obtuvieron del scraping.
- **`data/processed/`**: Contiene los archivos CSV finales, enriquecidos con los datos de altitud y listos para ser analizados.
- **`scripts/`**: Contiene los scripts de Python para procesar los datos.
  - **`scraper.py`**: Realiza el web scraping de los datos de los partidos desde Wikipedia.
  - **`generate_teams.py`**: Lee los archivos JSON crudos y genera una lista de equipos únicos.
  - **`process_altitude.py`**: Procesa los datos crudos, los enriquece con la altitud y genera el CSV final.

## Uso

Para procesar los datos brutos y generar el archivo de análisis, ejecuta el script `process_altitude.py` desde la raíz del proyecto, especificando el torneo que deseas procesar.

### Prerrequisitos

- Python 3.x
- Las librerías listadas en `requirements.txt`:
  - `requests`: Para realizar peticiones HTTP (usado en `scraper.py`).
  - `pyquery`: Para parsear contenido HTML (usado en `scraper.py`).
  - `pandas`: Para manipulación y análisis de datos (usado en `process_altitude.py`).

Puedes instalar todas las dependencias necesarias ejecutando:

```bash
pip install -r requirements.txt
```

### Ejecución

Ejecuta el script desde el directorio raíz del proyecto de la siguiente manera:

```bash
# Para procesar los datos de la Copa Libertadores
python3 scripts/process_altitude.py libertadores

# Para procesar los datos de la Copa Sudamericana
python3 scripts/process_altitude.py sudamericana

# Para correr el flujo completo limpiando inicialmente los archivos anteriores
chmox -x runner.sh
./runner.sh
```

El script leerá el archivo JSON correspondiente de `data/raw/`, lo procesará usando el mapeo de `data/mappings/city_mappings.json` y guardará el resultado en un nuevo archivo CSV en la carpeta `data/processed/`.

## Lógica del Script (`scraper.py`)

Este script es el encargado de la adquisición de los datos brutos de los partidos directamente desde Wikipedia. Su funcionamiento se basa en los siguientes pasos:

1. **Manejo de Argumentos**: Recibe el nombre del torneo (`sudamericana` o `libertadores`) como argumento de línea de comandos para construir la URL de Wikipedia y determinar el nombre del archivo de salida.
2. **Rango de Años**: Itera sobre un rango predefinido de años (actualmente 2014 a 2024) para cada torneo.
3. **Descarga y Parseo HTML (`fetch_html_tree`)**:
    - Realiza una solicitud HTTP a la URL de Wikipedia correspondiente al torneo y año.
    - Utiliza `PyQuery` para parsear el contenido HTML de la página.
    - Incluye manejo de errores para problemas de red o de parseo.
4. **Extracción de Partidos de Fase de Grupos (`parse_group_stage_matches`)**:
    - Esta función es robusta y utiliza varias heurísticas para identificar las tablas de partidos de la fase de grupos.
    - Busca encabezados como "Grupo X" y luego rastrea tablas cercanas que contengan patrones de puntuación.
    - Maneja diferentes estructuras de tabla que pueden variar entre años o torneos.
5. **Extracción de Partidos de Fases Eliminatorias (`parse_knockout_matches`)**:
    - Identifica tablas de fases eliminatorias (octavos, cuartos, etc.).
    - Extrae la fecha, equipos, marcador y estadio de cada partido.
6. **Limpieza de Nombres de Equipos y Marcadores (`clean_team_name`, `clean_score`)**:
    - `clean_team_name`: Normaliza los nombres de los equipos para asegurar consistencia y facilitar el mapeo posterior con `city_mappings.json`. Esto incluye manejar variaciones como "Atlético Paranaense" vs "Paranaense".
    - `clean_score`: Extrae los goles del equipo local y visitante de la cadena de texto del marcador, eliminando información adicional como resultados de penaltis o tiempos extra.
7. **Almacenamiento de Datos**: Una vez extraídos y limpiados, los datos de todos los partidos para un torneo y año se consolidan y se guardan en un archivo JSON dentro de la carpeta `data/raw/`.

Este script es la primera etapa del pipeline de datos, generando los archivos JSON que luego serán enriquecidos por `process_altitude.py`.

## Lógica del Script (`process_altitude.py`)

El script principal orquesta todo el proceso de enriquecimiento de datos. Su lógica se puede dividir en los siguientes pasos:

1. **Manejo de Argumentos**: El bloque `if __name__ == "__main__"` se encarga de leer el argumento de la línea de comandos (`libertadores` o `sudamericana`) para determinar las rutas de los archivos de entrada y salida.

2. **Carga de Mapeos (`load_city_mappings`)**:
    - Lee el archivo `city_mappings.json`.
    - Este archivo contiene un diccionario donde cada clave es una ciudad y su valor es un objeto con la `altitude` y una lista de `teams` asociados a esa ciudad.
    - Incluye manejo de errores para `FileNotFoundError` y `json.JSONDecodeError`.

3. **Creación de un Mapa Inverso (`build_reverse_team_map`)**:
    - Para optimizar la búsqueda, esta función invierte la estructura del mapa de ciudades.
    - Crea un nuevo diccionario llamado `team_lookup` donde la clave es el **nombre del equipo** y el valor es un objeto que contiene su `city` y `altitude`.
    - Esto permite una búsqueda muy rápida (O(1)) de la información de un equipo, en lugar de tener que iterar sobre el mapa de ciudades para cada partido.
    - También valida la estructura del archivo `city_mappings.json` y advierte sobre ciudades con formato incorrecto (ej. si falta la clave `teams` o `altitude`).

4. **Procesamiento Principal (`process_data`)**:
    - Carga los datos brutos de los partidos desde el archivo JSON correspondiente.
    - Itera sobre cada partido en la lista de partidos.
    - Para cada partido, obtiene los nombres de `home_team` y `away_team`.
    - Utiliza el mapa `team_lookup` (construido a partir de `city_mappings.json`) para obtener la ciudad y la altitud de ambos equipos.
    - Si un equipo no se encuentra en el mapa, se añade a un conjunto `missing_teams` para notificar al usuario al final del proceso. Los partidos con equipos faltantes se omiten.
    - Calcula la `altitude_difference` (altitud local - altitud visitante).
    - Crea un nuevo registro de partido con los datos originales más los datos enriquecidos:
        - `home_city`, `home_altitude_meters`
        - `away_city`, `away_altitude_meters`
        - `altitude_difference`
    - Al final del bucle, si se encontraron equipos faltantes, imprime una advertencia con una lista de hasta 10 de ellos.

5. **Generación del CSV**:
    - Convierte la lista de datos procesados en un DataFrame de `pandas`.
    - Crea el directorio `data/processed/` si no existe.
    - Guarda el DataFrame en un archivo CSV con la codificación `utf-8-sig` para asegurar la compatibilidad de caracteres especiales (como tildes) en programas como Excel.
    - Finalmente, imprime un resumen del proceso, indicando cuántos partidos se procesaron y la ruta del archivo de salida.
