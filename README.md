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

### Opción 3 — Cloud gratuito (recomendado para demo)

- **Postgres**: [Supabase free](https://supabase.com) (500 MB, TDE en reposo).
- **Frontend**: [Vercel free](https://vercel.com) (Next.js automático desde GitHub).
- **Backend**: tu máquina local + [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) (URL pública HTTPS gratis y estable).


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

## Documentación adicional

- [doc/agent_contracts.md](doc/agent_contracts.md) — Contrato de los agentes y dataclasses.
- `.env.example` — Variables de entorno con documentación inline.

## Autores

- Diego Esclarín
- Sofía Contreras

*Curso 2025-26 — Grado en Ingeniería en Inteligencia Artificial — URJC*
