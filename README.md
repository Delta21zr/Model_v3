# API Oráculo de Conciertos V3

Un microservicio basado en Machine Learning (XGBoost) y FastAPI diseñado para predecir la asistencia y ocupación de conciertos musicales. La API evalúa factores clave como el artista, el recinto, el género musical, los precios de los boletos y las métricas sociales (Spotify, Instagram) para entregar un pronóstico comercial del evento.

## Características Principales

- **Predicción Inteligente:** Modelo XGBoost entrenado para estimar la asistencia y calcular el riesgo comercial (ej. "Riesgo Alto", "Entrada Media", "Muy Buena Entrada", "SOLD OUT TOTAL").
- **Manejo de Errores Ortográficos:** Integración con `difflib` para corregir de forma inteligente los errores tipográficos comunes en los nombres de artistas y recintos.
- **Validación Estricta:** Uso de Pydantic para garantizar que los datos entrantes (precios, capacidades, seguidores) estén dentro de rangos estadísticamente válidos y lógicos.
- **Microservicio Eficiente:** Construido sobre FastAPI, garantizando alta velocidad de respuesta y documentación automática nativa (Swagger/OpenAPI).

## Seguridad y Resiliencia (Hardening)

El proyecto cuenta con múltiples capas defensivas producto de rigurosas auditorías de seguridad:
- **Protección Anti-Inyección ML:** Filtrado estricto de categorías y `Literal` typing para evitar contaminación de diccionarios de inferencia.
- **Defensa Anti-DDoS:** Limitador de peticiones (Rate Limit de 15/minuto) por IP.
- **Protección de Memoria (RAM):** Middleware de lectura de flujos (Stream) que bloquea subidas mayores a 1 MB independientemente del encabezado `Content-Length`.
- **Mitigación de Agotamiento de CPU:** Limitadores de longitud máxima (256 caracteres) antes del procesamiento de distancias de strings (`difflib`).
- **Higiene de Infraestructura:** Contenedores Docker ejecutados sin privilegios de superusuario (`appuser`), montajes de lectura estricta y fijación absoluta de dependencias.

## Pila Tecnológica (Tech Stack)

- **Backend:** Python 3.12, FastAPI, Uvicorn, SlowAPI
- **Machine Learning:** XGBoost, Pandas, Scikit-Learn
- **Contenedores:** Docker, Docker Compose

## Instalación y Despliegue Local

### Opción 1: Uso con Docker (Recomendado)

1. Construir la imagen y levantar el contenedor:
   ```bash
   docker-compose -f docker-compose.sandbox.yml up --build
   ```
2. La API estará disponible en `http://localhost:8000`.

### Opción 2: Entorno Virtual Local

1. Crear y activar un entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```
2. Instalar las dependencias exactas:
   ```bash
   pip install -r requirements.txt
   ```
3. Iniciar el servidor:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Uso de la API

### 1. Interfaz Gráfica Integrada
Puedes acceder a la interfaz de usuario visitando el endpoint raíz en tu navegador:
`GET /app`

### 2. Predicción de Asistencia
**Endpoint:** `POST /api/v1/predict`

**Ejemplo de Petición (Payload):**
```json
{
  "artista": "Dua Lipa",
  "lugar": "Foro Sol",
  "genero_principal": "cat_pop",
  "capacidad_maxima": 65000,
  "precio_promedio": 1500.50,
  "popularidad_spotify": 95,
  "seguidores_spotify": 40000000,
  "seguidores_ig": 85000000
}
```

**Ejemplo de Respuesta:**
```json
{
  "status": "success",
  "prediccion": {
    "asistencia_estimada": 63000,
    "porcentaje_ocupacion": 0.97,
    "veredicto_comercial": "SOLD OUT TOTAL"
  }
}
```

### 3. Opciones Disponibles
**Endpoint:** `GET /api/v1/opciones`
Retorna las listas de artistas y lugares conocidos por el historial del modelo.
