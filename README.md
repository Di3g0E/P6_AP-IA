# P6_AP-IA — Sistema unificado multiagente de gestión financiera personal

Integra las funcionalidades de las prácticas P1-P5 bajo un único sistema controlado por agentes con autenticación biométrica, soporte multiusuario y persistencia en Postgres.


## Descripción del sistema

Sistema controlado por un grafo jerárquico de LangGraph:

- **Agente Orquestador** (LLM): único interlocutor con el usuario. Decide a qué sub-agente delegar y narra los resultados.
- **Agente Security** (determinista, P5): biometría facial, cifrado de embeddings, control de intentos, validación anti-anomalías.
- **Agente Registrar** (determinista, P2 + P3): alta de transacciones manuales o vía OCR, categorización automática.
- **Agente Analyst** (determinista + LLM opcional, P1 + P4): analytics, tendencias, predicción temporal, evaluación de objetivos.

Cada usuario accede mediante login (email + passphrase) y verificación biométrica (foto). Los datos financieros se guardan en Postgres con TDE del proveedor; los embeddings biométricos se cifran a nivel aplicación con Fernet (AES-128) + PBKDF2-HMAC-SHA256.

## Reutilización de las prácticas anteriores

| De | Qué se reutiliza | A dónde en P6 |
|---|---|---|
| **P1** | Predictores temporales (RF, HistGradBoosting, ARIMA) | `src/agents/analyst/forecasters.py` |
| **P2** | `FinancialClassifier` (SGDClassifier + char n-grams) | `src/agents/registrar/classifier.py` |
| **P3** | Motor OCR (PaddleOCR + GB scoring) | `src/agents/registrar/ocr_engine.py` |
| **P4** | Esqueleto LangGraph + analytics | `src/agents/orchestrator/graph.py`, `src/agents/analyst/analytics.py` |
| **P5** | Cifrado, biometría, lockout, notificaciones, anomalías | `src/utils/security.py`, `src/utils/notifications.py`, `src/agents/security/` |

El código se ha **copiado físicamente** dentro de `P6_AP-IA/`; no se importa de otros directorios de prácticas.

## Stack técnico

```
Frontend:    Next.js (Vercel free) — pendiente
Backend:     FastAPI + LangGraph + uvicorn
LLM:         Groq por defecto + plug-in OpenAI / Anthropic / Google AI Studio por usuario
Base datos:  Postgres 15 (Supabase free o local Docker)
Memoria:     LangGraph PostgresSaver (thread_id = user:session)
Logs:        JSON estructurado → tabla events + fichero rotado
Túnel:       Cloudflare Tunnel (opcional, gratis)
Despliegue:  Docker Compose (imagen única, NumPy 1.26)
```

## Estructura del proyecto

```text
P6_AP-IA/
├── src/
│   ├── agents/
│   │   ├── orchestrator/    # Grafo LangGraph + LLM router + narración
│   │   ├── security/        # Biometría, cifrado, lockout, anomalías
│   │   ├── registrar/       # OCR (P3) + clasificador (P2)
│   │   ├── analyst/         # Analytics (P4) + predicción (P1)
│   │   └── contracts.py     # Dataclasses Pydantic compartidas
│   ├── api/
│   │   ├── main.py          # FastAPI app
│   │   └── routers/         # auth, chat, transactions, settings, me (RGPD)
│   ├── data/
│   │   ├── schema.py        # Modelos SQLAlchemy
│   │   └── database.py      # Engine + factory de sesiones
│   └── utils/
│       ├── security.py      # Fernet + PBKDF2 + lockout (de P5)
│       ├── notifications.py # Telegram + WhatsApp multiusuario
│       ├── logging_config.py
│       └── config.py
├── models/                  # Binarios entrenados (P1/P2/P3 joblib)
├── data/                    # Datasets (raw, processed, external)
├── doc/
│   └── agent_contracts.md   # Contrato de cada sub-agente
├── logs/                    # Logs JSON rotados
├── tests/
├── playground/              # Notebooks de exploración
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── main.py
```

## Configuración del entorno

> **Resumen rápido**: hay tres formas de levantarlo según tu entorno.
>
> | Opción | DB | Cuándo usarla | Tiempo de setup |
> |---|---|---|---|
> | **1. Local + SQLite** | `data/p6.db` | Desarrollo y demo en tu máquina. Cero infra. | ~5-10 min (instalar deps) |
> | **2A. Mixto** (uvicorn local + Postgres en Docker) | Postgres en contenedor `db` | Quieres Postgres real pero sin meter el backend (con torch/paddle) en Docker. | ~5 min |
> | **2B. Todo en Docker** | Postgres en contenedor `db` | Demo reproducible / despliegue. **Requiere ≥ 8 GB RAM y ≥ 60 GB de disco asignados a Docker Desktop**, ver Troubleshooting. | ~20-25 min (build pesado) |
> | **3. Cloud** | Supabase | Demo pública vía Cloudflare Tunnel + Vercel. | variable |

### Opción 1 — Local con `uv` + SQLite (recomendada para desarrollo)

Cero infra: el backend corre en tu Python local y los datos van a `data/p6.db`.

```bash
# 1. Crear entorno virtual
uv venv .venv --python 3.12

# 2. Instalar dependencias (~2 GB en total: torch, paddle, paddleocr, ...)
uv pip install --python .venv/Scripts/python.exe --link-mode=copy -r requirements.txt

# 3. Copiar variables de entorno
cp .env.example .env
```

Edita `.env` y rellena al menos:
- **`DATABASE_URL=`** — déjalo **vacío** para que caiga automáticamente a SQLite (`data/p6.db`). Si pegaste accidentalmente una URL Postgres aquí, fallará con `connection refused`.
- **`MASTER_FERNET_KEY`** — generar con el comando indicado en `.env.example`.
- **`GROQ_API_KEY`** — https://console.groq.com (tier free).
- `TELEGRAM_BOT_TOKEN` — opcional.

```bash
# 4. Inicializar la base de datos (crea tablas + usuario demo + migra el CSV)
.venv/Scripts/python.exe scripts/init_db.py

# 5. Lanzar la API
.venv/Scripts/python.exe -m uvicorn src.api.main:app --reload --port 8000
# → http://localhost:8000/docs

# (alternativa: demo CLI sin servidor HTTP)
.venv/Scripts/python.exe main.py
```

> **Nota**: `scripts/init_db.py` es idempotente — vuelve a lanzarlo cuantas veces
> quieras. Para empezar de cero usa `python scripts/init_db.py --reset`.

### Opción 2A — Mixto: uvicorn local + Postgres en Docker

Útil si quieres Postgres real (en lugar de SQLite) pero **sin** construir la imagen pesada del backend. Solo levantas el contenedor `db`.

```bash
# 1. Solo el servicio de Postgres
docker compose up -d db

# 2. En .env pon:
#    DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/p6
#    (host = localhost porque uvicorn corre fuera de docker)

# 3. Inicializar BD desde tu máquina
.venv/Scripts/python.exe scripts/init_db.py

# 4. Arrancar uvicorn local como en la Opción 1
.venv/Scripts/python.exe -m uvicorn src.api.main:app --reload --port 8000
```

### Opción 2B — Todo en Docker Compose

Levanta `db` + `api` en la misma red Docker. La API queda en `http://localhost:8000`.

> ⚠️ **Antes de lanzar el build** — en Docker Desktop → Settings → Resources, asegúrate de tener **al menos 8 GB de RAM y 60 GB de disco** asignados. La imagen del backend pesa varios GB (torch + paddle + paddleocr) y por defecto Docker Desktop puede no tener suficiente para exportar la capa final. Ver [Troubleshooting](#troubleshooting).

```bash
cp .env.example .env  # editar con tus claves (DATABASE_URL puede dejarse vacío)
docker compose up --build

# (En otra terminal, una vez la BD está arriba)
docker compose exec api python scripts/init_db.py
```

> No necesitas tocar `DATABASE_URL` en `.env`: `docker-compose.yml` la sobreescribe con `postgresql+psycopg://app:app@db:5432/p6` (host = `db`, el nombre del servicio en la red interna de Docker). Lo que pongas en `.env` para esa variable se ignora.

### Opción 3 — Cloud gratuito (recomendado para demo pública)

Combinación: **Supabase** (Postgres gestionado) + **Cloudflare Tunnel** (URL pública HTTPS para el backend que sigue corriendo en tu máquina) + **Vercel** (frontend Next.js).

#### 3.1 — Postgres en Supabase

1. Crea cuenta gratuita en https://supabase.com → **New project**. Anota la **database password** que te pide al crear.
2. En el proyecto: **Project Settings → Database → Connection string** → pestaña **URI**.
   - Copia la URL del **Connection pooling** (puerto `6543`, modo *transaction*). Es más estable para apps serverless / con reconexiones que la directa del 5432.
3. Pega esa URL en tu `.env` añadiéndole el driver `+psycopg`:
   ```
   DATABASE_URL=postgresql+psycopg://postgres.<ref>:<PASSWORD>@aws-0-<region>.pooler.supabase.com:6543/postgres
   ```
4. Crea tablas y usuario demo contra Supabase:
   ```bash
   .venv/Scripts/python.exe scripts/init_db.py
   ```

#### 3.2 — Backend público con Cloudflare Tunnel

Tu uvicorn sigue corriendo en local (`localhost:8000`); Cloudflare expone una URL HTTPS pública que apunta a él.

**Variante rápida (URL aleatoria, sin cuenta)** — ideal para una demo de un rato:

```bash
# Instalar cloudflared (Windows: winget install --id Cloudflare.cloudflared, o descarga desde cloudflare.com)
cloudflared tunnel --url http://localhost:8000
```
Imprime una URL del estilo `https://random-words-1234.trycloudflare.com`. Cambia cada vez que lo arrancas.

**Variante persistente (URL fija, requiere cuenta gratis Cloudflare)**:

1. https://dash.cloudflare.com → **Zero Trust → Networks → Tunnels → Create a tunnel**.
2. Asigna nombre, copia el **token**.
3. En tu `.env` añade `CLOUDFLARED_TOKEN=<tu_token>`.
4. Descomenta el bloque `cloudflared` en [`docker-compose.yml`](docker-compose.yml#L60-L66) y lánzalo:
   ```bash
   docker compose up -d cloudflared
   ```
5. En el panel del túnel, configura un *public hostname* (subdominio Cloudflare gratis o tu dominio) que apunte a `http://host.docker.internal:8000` (o `http://api:8000` si tu uvicorn corre en `docker compose`).

Arranca uvicorn como en la Opción 1: `python -m uvicorn src.api.main:app --port 8000`.

#### 3.3 — Frontend en Vercel

1. Sube tu repo a GitHub si aún no lo está.
2. https://vercel.com → **Add New Project** → importa el repo.
3. **Root directory**: `P6_AP-IA/frontend`. Vercel detecta Next.js automáticamente.
4. **Environment Variables** (en la página del proyecto en Vercel):
   ```
   NEXT_PUBLIC_API_BASE_URL = https://<tu-tunel>.trycloudflare.com
   ```
   (la URL pública que te dio Cloudflare en el paso 3.2)
5. Deploy. Vercel te asigna un dominio `https://<proyecto>.vercel.app`.

#### 3.4 — Permitir el dominio Vercel en CORS

De vuelta en tu `.env` del backend:
```
CORS_ORIGINS=http://localhost:3000,https://<proyecto>.vercel.app
```
**Reinicia uvicorn** para que recargue. Sin este paso, el frontend desplegado no podrá llamar al backend (el navegador bloquea por CORS).

> **Nota privacidad**: con esta arquitectura los datos viajan de Vercel → Cloudflare Tunnel → tu máquina → Supabase. Todo sobre HTTPS. La biometría se sigue cifrando con Fernet en aplicación antes de tocar Postgres.


## Modos de ejecución

### Demo CLI

```bash
.venv/Scripts/python.exe main.py
```

Inicia un chat interactivo con el orquestador usando el usuario demo (UUID
fijo). Ideal para probar rápido sin levantar el servidor HTTP.

### API REST (FastAPI)

```bash
.venv/Scripts/python.exe -m uvicorn src.api.main:app --reload --port 8000
```

Documentación interactiva: <http://localhost:8000/docs> (Swagger UI).

#### Endpoints v1

| Método | Path | Auth | Función |
|---|---|---|---|
| GET | `/` | — | Healthcheck |
| POST | `/auth/register` | — | Multipart con foto + email + passphrase + consent → JWT |
| POST | `/auth/login` | — | Multipart con foto + credenciales → JWT |
| POST | `/chat` | Bearer | Mensaje al orquestador |
| POST | `/transactions` | Bearer | Alta manual |
| GET | `/transactions/pending` | Bearer | Transacciones marcadas para revisión |
| POST | `/transactions/pending/{id}/confirm` | Bearer | Aprobar |
| DELETE | `/transactions/pending/{id}` | Bearer | Rechazar |

#### Ejemplo curl

```bash
# 1. Registro (devuelve un JWT)
TOKEN=$(curl -s -X POST http://localhost:8000/auth/register \
  -F "email=alice@p6.local" -F "passphrase=hunter22" \
  -F "biometric_consent=true" -F "face=@mi_foto.jpg" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. Chat
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "resume mis gastos del último mes"}'

# 3. Listar transacciones pendientes de revisar
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/transactions/pending
```

### Tests

```bash
.venv/Scripts/python.exe -m pytest tests/ -v
```

Suite completa: 72 tests (analyst, registrar, security, orquestador,
revisión de pendientes, integración BD y endpoints API).

### Frontend Next.js

Cliente web con webcam + chat + revisión de pendientes en
[`frontend/`](frontend/). Stack: Next.js 14 (App Router) + TypeScript +
Tailwind. Detalles en [frontend/README.md](frontend/README.md).

```bash
# en otra terminal, con el backend ya arrancado en :8000:
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
# → http://localhost:3000
```

Páginas:
- `/login`, `/register` — captura por webcam + JWT al backend.
- `/chat` — conversación con el orquestador (session_id mantenido entre turnos).
- `/pending` — listar / aprobar / rechazar transacciones marcadas por Security.

## Configuración de notificaciones (multiusuario)

El sistema **no usa datos de un único usuario**: cada usuario indica sus propios destinatarios desde su panel de configuración:

- **Telegram (canal primario)**: el usuario crea un chat con el bot del servidor (`@TuBotName`) escribiéndole `/start`, copia su `chat_id` y lo guarda en su perfil. El `TELEGRAM_BOT_TOKEN` del bot vive en el `.env` del servidor (compartido entre todos los usuarios).
- **WhatsApp (canal secundario opcional)**: el usuario añade su número internacional. Limitación: pywhatkit requiere que la máquina del backend tenga sesión activa de WhatsApp Web (no funciona en Docker headless).

### Guía de configuración rápida (Telegram)

1.  **Crea tu Bot**: Habla con [@BotFather](https://t.me/botfather) en Telegram y genera un bot. Copia el `API TOKEN`.
2.  **Obtén tu Chat ID**: Escribe `/start` a tu bot y luego consulta tu ID numérico (puedes usar [@userinfobot](https://t.me/userinfobot)).
3.  **Configura el Servidor**:
    *   En el archivo `.env`, añade: `TELEGRAM_BOT_TOKEN='tu_token_aqui'`.
    *   **Reinicia el proceso de uvicorn** para que cargue el token.
4.  **Activa las notificaciones en la BD**: Ejecuta este comando SQL (sustituyendo tus datos):
    ```bash
    docker compose exec db psql -U app -d p6 -c "INSERT INTO user_settings (user_id, notifications_enabled, telegram_chat_id, notification_level) VALUES ('TU-UUID', true, 'TU-CHAT-ID', 'info');"
    ```

### Triggers de notificación (RGPD opt-in)


| Evento | Origen |
|---|---|
| Alta de usuario | Agente Security |
| Login (éxito o fallo) | Agente Security |
| Anomalía financiera detectada | Agente Security (validador del Registrar) |
| Objetivo de gasto > 80 % | Agente Analyst |

Cada usuario decide su `notification_level`:
- `redacted` (defecto): solo evento + categoría, sin importes ni descripciones.
- `full`: incluye importes y descripciones (opt-in explícito por privacidad).

## Cumplimiento RGPD

- Consentimiento biométrico explícito al registro (campo `users.biometric_consent`).
- Endpoint `DELETE /me` con cascade que purga embedding + transacciones + objetivos + eventos del usuario.
- Endpoint `GET /me/export` que genera un ZIP con todos los datos del usuario.
- Logs sin PII en claro: la tabla `events` solo guarda IDs/hashes y metadatos.
- TLS obligatorio en producción (provisto por Cloudflare Tunnel o Vercel).

## Troubleshooting

### Docker: `failed to compute cache key: EOF` o error 500 al final del build

Síntoma: el `docker compose up --build` instala las dependencias correctamente (`Successfully installed ...152 paquetes`), pero al llegar al paso `exporting layers` Docker Desktop se reinicia o devuelve un error EOF / 500.

Causa: torch + paddlepaddle + paddleocr + facenet-pytorch generan una imagen de varios GB; al consolidar la capa final Docker Desktop se queda sin memoria o sin disco.

Soluciones (en orden):
1. **Subir recursos**: Docker Desktop → Settings → Resources → Memory ≥ 8 GB, Disk image size ≥ 60 GB. Aplicar y reiniciar.
2. **Liberar espacio**: `docker system prune -a --volumes` (¡borra todas las imágenes y volúmenes locales — confirma primero!).
3. **Construir solo `api`** para aislar el problema: `docker compose build api`.
4. **Salir de Docker para el backend**: usa la **Opción 2A** (uvicorn local + Postgres en Docker). Solo el contenedor `db` es ligero (~80 MB).

### `connection refused` a Postgres en Opción 1

Has dejado `DATABASE_URL=postgresql+psycopg://...` en `.env` pero estás en modo SQLite. Vacía la variable (`DATABASE_URL=`) o ponla a `sqlite:///./data/p6.db` y reinicia uvicorn.

### `paddle` / `torch` no se importan tras la instalación

Verifica que estás usando el Python del venv correcto:
```bash
.venv/Scripts/python.exe -c "import torch, paddleocr, langgraph, fastapi; print('OK')"
```
Si falta algo, reinstala: `uv pip install --python .venv/Scripts/python.exe --link-mode=copy -r requirements.txt`.

## Documentación adicional

- [doc/agent_contracts.md](doc/agent_contracts.md) — Contrato de los agentes y dataclasses.
- `.env.example` — Variables de entorno con documentación inline.

## Autores

- Diego Esclarín
- Sofía Contreras

*Curso 2025-26 — Grado en Ingeniería en Inteligencia Artificial — URJC*
