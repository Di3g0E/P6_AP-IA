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

### Opción 1 — Despliegue en Producción (Vercel + Supabase)

Esta es la configuración utilizada para el entorno de producción. Combina **Supabase** (Base de datos), **ngrok/Cloudflare** (Túnel para el backend) y **Vercel** (Frontend).

#### 1.1 — Base de datos en Supabase (Postgres)

1.  Crea una cuenta en [Supabase](https://supabase.com) → **New project**.
2.  En el dashboard, ve a **Connect** → **Connection pooling** (puerto `6543`, modo *Transaction*).
3.  Copia la URI y añádela a tu `.env` con el prefijo `+psycopg` (necesario para SQLAlchemy + Psycopg 3):
    ```env
    DATABASE_URL=postgresql+psycopg://postgres.<ref>:<PASSWORD>@aws-1-<region>.pooler.supabase.com:6543/postgres
    ```
4.  Inicializa las tablas y carga los datos de la demo:
    ```bash
    .venv/Scripts/python.exe scripts/init_db.py
    ```

#### 1.2 — Backend con Túnel (ngrok o Cloudflare)

Dado que el backend utiliza modelos pesados (Torch, PaddleOCR), se aloja en un servidor dedicado o máquina local y se expone mediante un túnel:

1.  **Lanzar el túnel**:
    ```bash
    ngrok http --url=tu-dominio-estatico.ngrok-free.app 8000
    ```
2.  **Configurar CORS**: En el `.env` del backend, añade la URL de Vercel:
    ```env
    CORS_ORIGINS=https://tu-proyecto.vercel.app
    ```
3.  **Arrancar API**:
    ```bash
    .venv/Scripts/python.exe -m uvicorn src.api.main:app --port 8000
    ```

#### 1.3 — Frontend en Vercel (Next.js)

1.  Importa el repositorio en [Vercel](https://vercel.com).
2.  Configura el **Root Directory** como `frontend/`.
3.  Añade la variable de entorno:
    *   `NEXT_PUBLIC_API_BASE_URL`: La URL de tu túnel (ej: `https://tu-dominio.ngrok-free.app`).
4.  **Deploy**. El frontend se conectará automáticamente al backend a través del túnel.

#### 1.4 — Post-despliegue y Uso

*   **Cargar datos en cuenta real**: Para que tu usuario registrado vea los datos de ejemplo del CSV:
    ```bash
    .venv/Scripts/python.exe scripts/transfer_demo_data.py <tu_email>
    ```
*   **Probar la demo**: Abre tu dominio de Vercel, regístrate y prueba el `/chat`. Las anomalías detectadas aparecerán en `/pending`.
*   **Rutina diaria**: Cada vez que quieras usar el sistema:
    1. Lanza el túnel: `ngrok http --url=tu-dominio.ngrok-free.app 8000`
    2. Lanza el backend: `.venv/Scripts/python.exe -m uvicorn src.api.main:app --port 8000`
    3. Usa la app en la URL de Vercel.

---

### Opción 2 — Desarrollo Local (uv)

Ideal para desarrollo rápido sin Docker. Usa **SQLite** por defecto.

1.  **Entorno**: `uv venv .venv --python 3.12`
2.  **Dependencias**: `uv pip install -r requirements.txt`
3.  **Variables**: `cp .env.example .env` (configura `GROQ_API_KEY` y `MASTER_FERNET_KEY`).
4.  **Init DB**: `.venv/Scripts/python.exe scripts/init_db.py`
5.  **Ejecutar CLI**: `.venv/Scripts/python.exe main.py`

---

### Opción 3 — Docker Compose

Levanta un stack completo (Postgres + API) de forma aislada.

```bash
docker compose up --build
# En otra terminal:
docker compose exec api python scripts/init_db.py
```
> **Nota**: Para que el comando `exec` funcione, asegúrate de que el directorio `scripts/` esté incluido en el Dockerfile o montado como volumen.


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

## Ejemplos de interacción (Prompts de prueba)

Puedes probar las capacidades de los agentes utilizando las siguientes frases en el chat:

### 📊 Agente Analyst (Análisis y Predicción)
*   "Resume mis gastos del último mes por categoría."
*   "¿Cuál es la predicción de mis gastos para el próximo mes?"
*   "¿Cuánto he gastado en ocio (Leisure) en los últimos 6 meses?"
*   "Analiza la tendencia de mis gastos de este año."

### 📝 Agente Registrar (Registro de Transacciones)
*   "Añade un gasto de 15€ en transporte hoy."
*   "Ayer me gasté 2500€ en una cena en el restaurante La Tagliatella."
*   "He pagado 20€ de parking esta mañana."
*   *Nota: Al introducir un importe inusualmente alto (como los 2500€ de la cena), el **Agente Security** detectará la anomalía y marcará la transacción para revisión manual en `/pending`.*

### 🤖 General / Orquestador
*   "Hola, ¿qué puedes hacer por mí?"
*   "¿Tengo alguna transacción pendiente de revisar?"
*   "Dime el estado de mis ahorros."

---

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

## Autores

- Diego Esclarín
- Sofía Contreras

*Curso 2025-26 — Grado en Ingeniería en Inteligencia Artificial — URJC*
