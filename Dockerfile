# 1. Usar una imagen oficial de Python ligera
FROM python:3.12-slim

# 2. Instalar una librería del sistema que XGBoost a veces necesita
RUN apt-get update && apt-get install -y libgomp1 && rm -rf /var/lib/apt/lists/*

# 3. Crear una carpeta de trabajo dentro de la caja
WORKDIR /app

# 4. Copiar e instalar los requerimientos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar todo el código y los modelos (.json) a la caja
COPY . .

# 6. Exponer el puerto por el que hablará la API
EXPOSE 8000

# 7. El comando mágico para encender el servidor al prender la caja
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]