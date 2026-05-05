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
Túnel:       ngrok (gratis; Cloudflare Tunnel también soportado)
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

### Opción 1 — Local con `uv` (desarrollo, sin Docker)

Por defecto usa **SQLite** en `data/p6.db`; cero setup adicional.

```bash
# 1. Crear entorno virtual
uv venv .venv --python 3.12

# 2. Instalar dependencias
uv pip install --python .venv/Scripts/python.exe --link-mode=copy -r requirements.txt

# 3. Copiar variables de entorno
cp .env.example .env
# editar .env y rellenar:
#   - MASTER_FERNET_KEY (generar con el comando indicado en el .env.example)
#   - GROQ_API_KEY (https://console.groq.com)
#   - DATABASE_URL — opcional; si vacío o '...' usa SQLite local automáticamente
#   - TELEGRAM_BOT_TOKEN (opcional)

# 4. Inicializar la base de datos (crea tablas + usuario demo + migra el CSV)
.venv/Scripts/python.exe scripts/init_db.py

# 5. Lanzar la demo CLI
.venv/Scripts/python.exe main.py
```

> **Nota**: `scripts/init_db.py` es idempotente — vuelve a lanzarlo cuantas veces
> quieras. Para empezar de cero usa `python scripts/init_db.py --reset`.

### Opción 2 — Docker Compose (despliegue local + Postgres)

```bash
cp .env.example .env  # editar con tus claves
docker compose up --build

# (En otra terminal, una vez la BD está arriba)
docker compose exec api python scripts/init_db.py
```

Esto levanta `db` (Postgres 15) + `api` (FastAPI) en la misma red Docker. La API queda accesible en `http://localhost:8000`.

> El `.env` debe tener `DATABASE_URL=postgresql+psycopg://app:app@db:5432/p6`
> (la línea ya está en `.env.example`).

### Opción 3 — Cloud gratuito (recomendado para demo pública)

Combinación validada: **Supabase** (Postgres) + **ngrok** (URL pública para tu uvicorn local) + **Vercel** (frontend Next.js). Todo gratis, sin tarjeta.

> El backend (con torch / paddleocr / facenet) **no cabe** en serverless. Vercel solo aloja el frontend; tu uvicorn sigue corriendo en tu PC y se expone vía un túnel HTTPS.

#### 3.1 — Postgres en Supabase

1. Crea cuenta en https://supabase.com → **New project**. Anota la **database password**.
2. En el dashboard del proyecto, pulsa **Connect** (arriba) → bloque **Connection pooling** (puerto `6543`, modo *Transaction*). Copia la URI.
3. En tu `.env`, prefija con `+psycopg`. **Sin comillas, sin `?pgbouncer=true`** (psycopg lo rechaza):
   ```
   DATABASE_URL=postgresql+psycopg://postgres.<ref>:<PASSWORD>@aws-1-<region>.pooler.supabase.com:6543/postgres
   ```
4. Inicializa tablas + usuario demo + migra el CSV:
   ```bash
   .venv/Scripts/python.exe scripts/init_db.py
   ```
   Espera `Migradas 887 transacciones del CSV al usuario demo.`

#### 3.2 — Backend público con ngrok

```bash
winget install --id Ngrok.Ngrok
# Authtoken (cuenta gratis en https://dashboard.ngrok.com)
ngrok config add-authtoken <tu_authtoken>
# Lanzar el tunel (deja la terminal abierta)
ngrok http 8000
```

Apunta la URL `https://xxxx-xx.ngrok-free.dev` que aparece en `Forwarding`. Es la dirección pública del backend.

> Plan free: la URL **cambia entre reinicios** y la primera visita en navegador muestra una pantalla azul (las llamadas API la saltan automáticamente con el header `ngrok-skip-browser-warning` que el frontend ya envía). Para una URL fija reclama un **dominio estático gratis** en `dashboard.ngrok.com → Domains` y lánzalo con `ngrok http --url=<tu-dominio>.ngrok-free.app 8000`.

#### 3.3 — Frontend en Vercel

1. Push del repo a GitHub si aún no está.
2. https://vercel.com → **Sign up with GitHub** → **Add New → Project** → importa el repo.
3. **Root Directory**: `frontend` (si tu repo es ya `P6_AP-IA`) o `P6_AP-IA/frontend` (en monorepo).
4. **Environment Variables** → añade UNA:
   - **Name**: `NEXT_PUBLIC_API_BASE_URL`
   - **Value**: la URL ngrok del paso 3.2 (sin barra final).
5. **Deploy**. En **Settings → Domains** verás el dominio Production estable (`<proyecto>.vercel.app`); úsalo, **no** el preview con hash que cambia con cada push.

#### 3.4 — CORS y reinicio de uvicorn

En `.env` del backend:
```
CORS_ORIGINS=http://localhost:3000,https://<proyecto>.vercel.app
```
**Reinicia uvicorn** (Ctrl+C + relanzar) para que recargue: FastAPI lee `CORS_ORIGINS` solo al arrancar. Sin esto, el navegador bloquea por CORS.

#### 3.5 — Cargar datos del CSV en una cuenta real

`init_db.py` migra el CSV al usuario demo (UUID fijo, sin biometría → no accesible vía web). Para que un usuario registrado por la web vea esos datos:

```bash
.venv/Scripts/python.exe scripts/transfer_demo_data.py <email_del_usuario>
```

Borra las transacciones existentes del destino y reasigna las del demo. Idempotente: vuelve a lanzar `init_db.py` para recargar el demo, y `transfer_demo_data.py` para preparar otra cuenta.

> **Privacidad**: los datos viajan Vercel → ngrok → tu máquina → Supabase, todo sobre HTTPS. La biometría se cifra con Fernet en aplicación antes de tocar Postgres.

#### 3.6 — Probar la demo

Con backend, ngrok y frontend arriba:

1. Abre tu dominio Vercel → `/register`. Crea un usuario con webcam + email + passphrase.
2. (Opcional) Carga el CSV en esa cuenta: `.venv/Scripts/python.exe scripts/transfer_demo_data.py <email>`.
3. Ve a `/login`, autentícate y prueba en `/chat`:
   - "Resume mis gastos del último mes."
   - "¿Cuál es la predicción de mis gastos para el mes que viene?"
   - "Analiza la tendencia de mis gastos en Leisure de los últimos 6 meses."
   - "Añade un gasto de 30€ en Food hoy."
4. Las transacciones marcadas como anómalas por el agente Security aparecen en `/pending` para aprobar o rechazar.

#### 3.7 — Rutina diaria (volver a levantar el backend en otro día)

Una vez configurado todo (Supabase + ngrok + Vercel), cada sesión de uso solo requiere dos terminales abiertas en tu PC:

**Terminal 1 — Backend**

```powershell
cd "C:\Users\diego\OneDrive - Universidad Rey Juan Carlos\Documentos\GIA_URJC\Curso 2025-26\Ap_IA\practicas\P6_AP-IA"
.venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000
```

**Terminal 2 — Túnel ngrok**

```powershell
ngrok http 8000
```

Apunta la URL de la línea `Forwarding`.

**Usar la app**: abre tu dominio Vercel (`https://<proyecto>.vercel.app`) → `/login`.

##### Si la URL ngrok ha cambiado desde la última vez

El plan free de ngrok asigna URL nueva cada arranque. Si `Forwarding` muestra una URL distinta a la que hay en Vercel:

1. **Vercel → Settings → Environment Variables** → edita `NEXT_PUBLIC_API_BASE_URL` con la URL nueva.
2. **Deployments → último → ⋯ → Redeploy** (sin caché).
3. Espera 1-2 min y recarga `/login` con `Ctrl+Shift+R`.

`CORS_ORIGINS` no hay que tocarlo (apunta a Vercel, no a ngrok).

##### Solución definitiva: dominio ngrok estático gratis

Para no perseguir URLs nunca más:

1. https://dashboard.ngrok.com/cloud-edge/domains → **+ Create domain** (free incluye uno).
2. Lanza el túnel anclado a ese dominio:
   ```powershell
   ngrok http --url=<tu-dominio>.ngrok-free.app 8000
   ```
3. Pon esa URL una vez en Vercel y se acabó la danza de redeploys.

##### Cosas a recordar

- **Cambias `.env` (CORS, claves, etc.)**: reinicia uvicorn (Ctrl+C + relanzar). FastAPI lee el `.env` solo al arrancar.
- **Cambias código backend**: reinicia uvicorn (o usa `--reload` para autoreload en dev).
- **Cambias código frontend**: push a GitHub, Vercel redeploya solo.
- **Algo no funciona**: F12 en el navegador → Console → el primer error rojo dice qué falla (CORS, ngrok caído, JWT expirado, etc.).


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
- TLS obligatorio en producción (provisto por el túnel ngrok / Cloudflare y por Vercel).

## Documentación adicional

- [doc/agent_contracts.md](doc/agent_contracts.md) — Contrato de los agentes y dataclasses.
- `.env.example` — Variables de entorno con documentación inline.

## Autores

- Diego Esclarín
- Sofía Contreras

*Curso 2025-26 — Grado en Ingeniería en Inteligencia Artificial — URJC*
