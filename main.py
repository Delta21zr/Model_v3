from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware # <-- NUEVO
from fastapi.responses import FileResponse, JSONResponse # <-- NUEVO
from pydantic import BaseModel, Field
import pandas as pd
import xgboost as xgb
import json
import difflib
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

app = FastAPI(
    title="API Oráculo de Conciertos V3", 
    version="1.4", # Subimos la versión por las mejoras de seguridad
    description="Microservicio de ML con validaciones, manejo de Typos y protección Anti-DDoS."
)

# ==========================================
# 1. PROTECCIÓN ANTI-DDOS (RATE LIMITING)
# ==========================================
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ==========================================
# 2. MIDDLEWARES DE SEGURIDAD
# ==========================================
# A. Defensa Anti-Colapso de RAM (Límite de 1MB)
class LimitarTamanoPayload(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tamano_maximo = 1024 * 1024  # 1 MB
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > tamano_maximo:
            return JSONResponse(
                status_code=413, 
                content={"detail": "Petición rechazada: El tamaño de los datos es excesivo."}
            )
        return await call_next(request)

app.add_middleware(LimitarTamanoPayload)

# B. Defensa CORS (Solo tu URL de Render y local)
origenes_permitidos = [
    "https://model-v3-vcc7.onrender.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes_permitidos, 
    allow_credentials=True,
    allow_methods=["GET", "POST"], # Solo lo necesario
    allow_headers=["*"],
)

# ==========================================
# 3. VARIABLES GLOBALES Y ESQUEMAS
# ==========================================
modelo_xgb = None
historial = None
features_names = None

class EventoRequest(BaseModel):
    artista: str = Field(..., min_length=1)
    lugar: str = Field(..., min_length=1)
    genero_principal: str = Field(..., min_length=1)
    capacidad_maxima: int = Field(..., ge=1, le=500000)
    precio_promedio: float = Field(..., ge=0.0, le=1000000.0)
    popularidad_spotify: int = Field(..., ge=0, le=100)
    seguidores_spotify: int = Field(..., ge=0, le=3000000000)
    seguidores_ig: int = Field(..., ge=0, le=3000000000)

@app.on_event("startup")
def cargar_modelo():
    global modelo_xgb, historial, features_names
    try:
        modelo_xgb = xgb.XGBRegressor()
        modelo_xgb.load_model('modelo_3.json')
        
        with open('historial_3.json', 'r', encoding='utf-8') as f:
            historial = json.load(f)
            
        with open('features_3.json', 'r', encoding='utf-8') as f:
            features_names = json.load(f)
            
    except Exception as e:
        print(f"Error al cargar archivos: {e}")

# ==========================================
# 4. RUTAS (ENDPOINTS)
# ==========================================
@app.post("/api/v1/predict")
@limiter.limit("15/minute") 
async def predecir_asistencia(request: Request, evento: EventoRequest):
    if modelo_xgb is None or historial is None:
        raise HTTPException(status_code=500, detail="El modelo no está disponible.")

    artista_upper = evento.artista.strip().upper()
    lugar_upper = evento.lugar.strip().upper()

    # Validación y corrección ortográfica para el artista
    if artista_upper in historial['artistas_ocup']:
        hist_ocup_art = historial['artistas_ocup'][artista_upper]
    else:
        artistas_conocidos = list(historial['artistas_ocup'].keys())
        posibles_matches = difflib.get_close_matches(artista_upper, artistas_conocidos, n=1, cutoff=0.8)
        
        if posibles_matches:
            raise HTTPException(
                status_code=400, 
                detail=f"¿Quisiste decir '{posibles_matches[0]}'? Revisa la ortografía del artista."
            )
        hist_ocup_art = 0.5 

    # Validación y corrección ortográfica para el recinto
    if lugar_upper in historial['lugares_ocup']:
        hist_ocup_lug = historial['lugares_ocup'][lugar_upper]
    else:
        recintos_conocidos = list(historial['lugares_ocup'].keys())
        posibles_matches = difflib.get_close_matches(lugar_upper, recintos_conocidos, n=1, cutoff=0.8)
        
        if posibles_matches:
            raise HTTPException(
                status_code=400, 
                detail=f"¿Quisiste decir el recinto '{posibles_matches[0]}'? Revisa la ortografía."
            )
        hist_ocup_lug = 0.5

    # Preparación de variables para el modelo XGBoost
    row = {col: 0.0 for col in features_names}
    
    if 'precio_promedio' in row: row['precio_promedio'] = evento.precio_promedio
    if 'hist_ocup_artista' in row: row['hist_ocup_artista'] = hist_ocup_art
    if 'hist_ocup_lugar' in row: row['hist_ocup_lugar'] = hist_ocup_lug
    if 'popularidad' in row: row['popularidad'] = evento.popularidad_spotify
    if 'seguidores' in row: row['seguidores'] = evento.seguidores_spotify
    if 'Seguidores Instagram' in row: row['Seguidores Instagram'] = evento.seguidores_ig
    
    if evento.genero_principal in row:
        row[evento.genero_principal] = 1.0

    # Predicción y reglas de negocio
    df_input = pd.DataFrame([row], columns=features_names)
    ocup_pred = float(modelo_xgb.predict(df_input)[0])
    
    personas_estimadas = int(max(0, min(ocup_pred * evento.capacidad_maxima, evento.capacidad_maxima)))
    porcentaje_final = personas_estimadas / evento.capacidad_maxima if evento.capacidad_maxima > 0 else 0

    veredicto = "Riesgo Alto"
    if porcentaje_final > 0.95: veredicto = "SOLD OUT TOTAL"
    elif porcentaje_final > 0.75: veredicto = "Muy Buena Entrada"
    elif porcentaje_final > 0.50: veredicto = "Entrada Media"

    return {
        "status": "success",
        "prediccion": {
            "asistencia_estimada": personas_estimadas,
            "porcentaje_ocupacion": round(porcentaje_final, 2), # <-- PRECISIÓN A 2 DECIMALES PARA SEGURIDAD
            "veredicto_comercial": veredicto
        }
    }

@app.get("/api/v1/opciones")
async def obtener_opciones():
    if historial is None:
        raise HTTPException(status_code=500, detail="Datos no disponibles")
    return {
        "artistas": list(historial['artistas_ocup'].keys()),
        "lugares": list(historial['lugares_ocup'].keys())
    }

# ==========================================
# RUTAS DE INTERFAZ Y PING DE RENDER
# ==========================================
@app.get("/app", response_class=FileResponse)
def mostrar_interfaz():
    return FileResponse("index.html")

@app.get("/")
def read_root():
    return {"mensaje": "API Segura Activa. Visita /app para la interfaz visual."}