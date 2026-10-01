# Reporte de Remediación de Seguridad (Auditoría V1)

Este documento detalla las medidas de mitigación y remediación técnica aplicadas tras los resultados de la auditoría de seguridad del servicio "Oráculo de Conciertos V3". 

Las correcciones han sido clasificadas en 4 fases, priorizando desde vulnerabilidades críticas hasta mejoras en la higiene de la infraestructura y reducción de deuda técnica.

---

## Fase 1: Remediación Crítica (Acción Inmediata)
**Objetivo:** Parchear vulnerabilidades de alta criticidad que permitían la manipulación de las predicciones y el colapso del servicio en la nube (compartido por múltiples clientes).

* **Prevención de Inyección ML (Alta)**
  * **Problema:** El campo `genero_principal` permitía inyectar parámetros de modelo arbitrarios (como `precio_promedio`), alterando los resultados.
  * **Solución:** Se implementó una tipificación estricta utilizando `Literal` en el modelo Pydantic (`EventoRequest`) permitiendo únicamente los 8 géneros válidos del entrenamiento. Adicionalmente, se integró una doble capa de validación manual (Filtro Estricto) antes de la inyección de la variable al diccionario del modelo.
  * **Archivo(s):** `main.py`

* **Corrección del Rate Limit Compartido (Alta)**
  * **Problema:** Al estar detrás del proxy inverso de Render, Uvicorn no distinguía las IPs de los clientes, provocando que todos compartieran el mismo Rate Limit (`15/minute`).
  * **Solución:** Se agregó la bandera `--proxy-headers` y `--forwarded-allow-ips="*"` al comando de inicio (`CMD`) en el entorno de Docker para recuperar correctamente los encabezados `X-Forwarded-For`.
  * **Archivo(s):** `Dockerfile`

---

## Fase 2: Disponibilidad y Resiliencia
**Objetivo:** Mitigar vectores de ataque orientados a Denegación de Servicio (DoS) que explotan el agotamiento de recursos (CPU y Memoria RAM).

* **Mitigación de DoS por CPU en Búsquedas (Media)**
  * **Problema:** Enviar cadenas de texto excesivamente largas provocaba que la función `difflib.get_close_matches` consumiera ciclos exhaustivos de CPU, bloqueando el *Event Loop*.
  * **Solución:** Se limitaron los parámetros `artista` y `lugar` a un `max_length=256` caracteres a nivel de Pydantic. Adicionalmente, se encapsuló la llamada a `difflib` dentro de una comprobación defensiva explícita de longitud (`len() <= 256`).
  * **Archivo(s):** `main.py`

* **Prevención de Bypass en el Límite de Payload (Media)**
  * **Problema:** El middleware defensivo dependía del encabezado HTTP `Content-Length`, siendo vulnerable a envíos segmentados maliciosos (*Chunked Transfer Encoding*) que sobrepasaran el límite en RAM.
  * **Solución:** Se reescribió el middleware `LimitarTamanoPayload`. Ahora envuelve asíncronamente a `request.receive()`, contabilizando el flujo binario real procesado y cortando la conexión inmediatamente al exceder 1 MB (Lanzando código HTTP `413`).
  * **Archivo(s):** `main.py`

---

## Fase 3: Higiene de Infraestructura
**Objetivo:** Reducir la superficie de exposición y endurecer el contenedor de despliegue mediante el principio de mínimo privilegio (Defensa en Profundidad).

* **Remoción de Privilegios Administrativos (Baja)**
  * **Problema:** El contenedor ejecutaba los procesos bajo el superusuario `root`.
  * **Solución:** Se creó un usuario específico de servicio (`appuser`) mediante la directiva `adduser` en el proceso de construcción de la imagen y se delegó la ejecución a través de la instrucción `USER appuser`.
  * **Archivo(s):** `Dockerfile`

* **Fijación de Dependencias / Pinning (Baja)**
  * **Problema:** Dependencias declaradas de forma laxa, susceptibles a envenenamiento de cadena de suministro o fallos por actualizaciones no retrocompatibles.
  * **Solución:** Se reemplazaron las dependencias por versiones estrictamente ancladas (`==`).
  * **Archivo(s):** `requirements.txt`

* **Endurecimiento del Entorno Sandbox (Baja)**
  * **Problema:** El entorno local de contenedores podía ser manipulado para extraer datos o alterar código mediante persistencia en volúmenes.
  * **Solución:** Se restringió el montaje local de directorios a modo estricto de solo lectura (`:ro`) y se desactivó el stack de red (`network_mode: none`) para aislar completamente los despliegues locales analizados.
  * **Archivo(s):** `docker-compose.sandbox.yml`

---

## Fase 4: Hardening y Deuda Técnica
**Objetivo:** Configurar de forma profesional las capas base de las integraciones de red, almacenamiento de logs y secretos.

* **CORS Seguro (Media)**
  * **Problema:** Se estaban utilizando comodines de cabeceras (`*`) y aceptando peticiones desde orígenes locales (`localhost`) en el entorno productivo.
  * **Solución:** Se limitó `allow_origins` de `CORSMiddleware` exclusivamente a los dominios autorizados de despliegue y front-end. Los headers permitidos se delimitaron explícitamente (`Authorization`, `Content-Type`).
  * **Archivo(s):** `main.py`

* **Migración a Sistema de Logging (Baja)**
  * **Problema:** El manejo de excepciones críticas durante la lectura de archivos base (modelos o diccionarios) dependía de la impresión estándar `print()`, complicando su rastreo.
  * **Solución:** Se integró la librería `logging` de Python y se reemplazó su llamado por la estructura `logger.error()`.
  * **Archivo(s):** `main.py`

* **Exclusión Rigurosa de Secretos (Baja)**
  * **Problema:** Fallas de nomenclatura en el control de exclusión y posible fuga del archivo de entorno `.env`.
  * **Solución:** Se renombró el documento a `.gitignore` y se aplicó la regla explícita de exclusión para variables de ambiente locales (`.env` y `.env.*`).
  * **Archivo(s):** `.gitignore`

---
*Reporte generado de forma automática tras la ejecución de las fases de remediación de seguridad.*
