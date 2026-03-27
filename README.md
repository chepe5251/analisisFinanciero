# ReconcilaApp — Sistema de Conciliación Financiera de Pagos de Personal

Aplicación web para automatizar la conciliación entre una plantilla de personal y reportes bancarios de múltiples instituciones financieras.

---

## Arquitectura

```
/proyectoEveling
├── backend/                    # FastAPI + Python
│   ├── app/
│   │   ├── api/routes/         # Endpoints REST (uploads, reconciliation, reports)
│   │   ├── core/               # Config y conexión a BD
│   │   ├── models/             # Modelos SQLAlchemy
│   │   ├── schemas/            # Schemas Pydantic (validación I/O)
│   │   ├── repositories/       # Capa de acceso a datos
│   │   ├── services/           # Lógica de negocio (conciliación, reportes)
│   │   ├── utils/              # Procesamiento de archivos
│   │   └── tests/              # Tests unitarios
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                   # Next.js 14 + TypeScript + Tailwind
│   ├── src/app/                # Pages (App Router)
│   ├── src/components/         # Componentes UI, layout, dashboard
│   └── src/lib/                # API client, tipos, utilidades
├── data/                       # Archivos CSV de prueba
├── docker-compose.yml
└── .env.example
```

### Stack tecnológico

| Capa        | Tecnología                         |
|-------------|-------------------------------------|
| Frontend    | Next.js 14, TypeScript, Tailwind CSS, Recharts |
| Backend     | FastAPI, Python 3.11, Pydantic v2  |
| BD          | PostgreSQL 15                       |
| ORM         | SQLAlchemy 2.0                      |
| Archivos    | Pandas, openpyxl, xlsxwriter       |
| Contenedores| Docker, docker-compose             |

---

## Cómo correrlo localmente

### Opción A — Sin Docker (desarrollo rápido)

**Prerequisitos:** Python 3.11+, Node.js 20+, PostgreSQL corriendo localmente.

```bash
# 1. Crear base de datos
createdb reconciliation_db

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env         # ajustar DATABASE_URL si es necesario
uvicorn app.main:app --reload --port 8000

# 3. Frontend (nueva terminal)
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

La app estará disponible en:
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

---

### Opción B — Con Docker Compose

```bash
docker-compose up --build
```

Servicios levantados:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- PostgreSQL: localhost:5432

---

## Variables de entorno

### Backend (`.env`)

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql://user:password@localhost/reconciliation_db` | Conexión PostgreSQL |
| `UPLOAD_DIR` | `uploads` | Directorio local para archivos subidos |
| `MAX_FILE_SIZE_MB` | `50` | Límite de tamaño de archivo |
| `AMOUNT_TOLERANCE` | `0.01` | Tolerancia de diferencia de monto para match exacto |
| `NAME_SIMILARITY_THRESHOLD` | `0.80` | Umbral de similitud de nombre (0–1) |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Orígenes permitidos |

### Frontend (`.env.local`)

| Variable | Default | Descripción |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | URL del backend |

---

## Flujo de uso

1. **Cargar archivos** (`/uploads`)
   - Sube la plantilla de personal (CSV o Excel)
   - Sube uno o más reportes bancarios, indicando el banco

2. **Ejecutar conciliación** (`/reconciliation`)
   - Selecciona la plantilla y los reportes que quieres cruzar
   - Haz clic en "Ejecutar"

3. **Ver resultados**
   - Dashboard (`/`): KPIs y gráficas
   - Conciliación (`/reconciliation`): tabla completa con filtros
   - Inconsistencias (`/inconsistencies`): solo los registros con problemas

4. **Descargar reportes** (`/reports`)
   - Consolidado CSV / Excel completo
   - Solo inconsistencias
   - Solo faltantes
   - Solo sobrantes

---

## Archivos de prueba (carpeta `/data`)

| Archivo | Descripción |
|---|---|
| `employee_template.csv` | 12 empleados distribuidos en 3 bancos |
| `banco_a_report.csv` | Match exacto, diferencia de monto, sobrante. Falta EMP004 |
| `banco_b_report.csv` | Match exacto, diferencia, duplicado (EMP006 x2). Falta EMP008 |
| `banco_c_report.csv` | Match exacto, match por similitud de nombre, diferencia. Falta EMP011, sobrante |

Casos cubiertos: ✅ match · ⚠️ diferencia · ❌ faltante · 🔴 sobrante · 🔁 duplicado

---

## API — Endpoints principales

```
POST   /api/uploads/template          Subir plantilla de personal
POST   /api/uploads/bank-report       Subir reporte bancario
GET    /api/uploads                   Listar archivos subidos
GET    /api/uploads/{id}              Detalle de un archivo

POST   /api/reconciliation/run        Ejecutar conciliación
GET    /api/reconciliation/summary    KPIs del dashboard
GET    /api/reconciliation/bank-summary  Resumen por banco
GET    /api/reconciliation/results    Resultados con filtros y paginación
GET    /api/reconciliation/inconsistencies  Solo inconsistencias

GET    /api/reports/consolidated      CSV completo
GET    /api/reports/consolidated-excel  Excel multi-hoja
GET    /api/reports/inconsistencies   CSV inconsistencias
GET    /api/reports/missing           CSV faltantes
GET    /api/reports/extras            CSV sobrantes
```

Documentación interactiva: http://localhost:8000/docs

---

## Tests

```bash
cd backend
pytest app/tests/ -v
```

Tests cubiertos:
- Limpieza de montos (formatos americano, europeo, con símbolos)
- Parseo de fechas (múltiples formatos)
- Normalización de nombres y similitud
- Mapeo de columnas por banco
- Lógica de conciliación: match exacto, diferencia, faltante, sobrante, duplicado, match por nombre, match por employee_id en referencia, validación de banco distinto

---

## Lógica de conciliación — reglas

El algoritmo opera en **3 pasadas** en orden de confiabilidad:

| Pasada | Criterio | Resultado |
|--------|----------|-----------|
| 1 | Número de cuenta + mismo banco | matched / difference |
| 2 | employee_id encontrado en campo reference | matched / difference |
| 3 | Similitud de nombre ≥ 80% + mismo banco | matched / difference |
| Post | Sin match en plantilla | missing |
| Post | Sin match en transacciones | extra |
| Post | Misma cuenta, múltiples transacciones en mismo archivo | duplicate |

Un match se clasifica como `matched` si la diferencia de monto ≤ `AMOUNT_TOLERANCE` (0.01 por defecto). De lo contrario es `difference`.

---

## Supuestos realizados

1. **Una sola asignación por empleado**: cada empleado tiene un solo banco/cuenta por plantilla. Si hay múltiples no se manejan actualmente.

2. **Moneda no condiciona el match**: la conciliación cruza por cuenta y nombre, no por moneda. Se asume que la moneda es consistente dentro de un mismo banco.

3. **Plantilla como fuente de verdad**: todo lo que está en la plantilla y no en el banco es `missing`. Todo lo que está en el banco y no en la plantilla es `extra`.

4. **Duplicado dentro del mismo archivo**: la detección de duplicados es por cuenta + upload_id. Si el mismo empleado aparece en dos archivos distintos del mismo banco no se detecta automáticamente.

5. **Sin integración API bancaria**: toda la información proviene de archivos subidos manualmente. No hay conexión directa con sistemas bancarios.

6. **Normalización de columnas genérica**: si un banco no tiene mapeo explícito en `BANK_COLUMN_MAPPINGS`, el sistema intenta identificar columnas por aliases comunes (ver `GENERIC_ALIASES` en `file_processor.py`).

7. **Formato de montos**: se maneja formato americano (1,500.00) y europeo (1.500,00). Símbolos de moneda ($, ₡) se eliminan automáticamente.

8. **Inicialización de tablas**: las tablas se crean automáticamente al arrancar el backend (`create_all`). En producción se usaría Alembic para migraciones.

9. **Archivos en disco local**: los archivos subidos se guardan en el directorio `uploads/`. En producción esto debería moverse a un objeto de storage (S3, GCS).

---

## Mejoras futuras

### Funcionalidad
- Soporte para múltiples asignaciones por empleado (ej: pago dividido entre bancos)
- Historial de conciliaciones con comparación entre corridas
- Configuración de reglas de match desde la UI (sin tocar código)
- Alertas automáticas cuando los faltantes superan un umbral
- Módulo de aprobación/rechazo de inconsistencias con comentarios
- Match por moneda además de monto

### Técnico
- Migraciones con Alembic
- Procesamiento asíncrono de archivos grandes con Celery + Redis
- Storage de archivos en S3/GCS en lugar de disco local
- Autenticación y control de acceso por rol
- Logs estructurados con correlación de requests
- Cobertura de tests al 80%+
- CI/CD con GitHub Actions
- Rate limiting en los endpoints de carga

### UX
- Notificaciones en tiempo real del progreso de procesamiento (WebSockets)
- Edición manual de registros con trazabilidad
- Vista de comparación lado a lado (plantilla vs banco)
- Exportación con formato personalizado por cliente

---

## Riesgos y vacíos de información del negocio

| Riesgo | Descripción |
|---|---|
| Reglas de negocio específicas | No se conocen aún las reglas exactas de conciliación del cliente. La lógica actual es razonable pero puede requerir ajustes |
| Volumen de datos | No se conoce el tamaño real de las plantillas. Con >10,000 filas el procesamiento en memoria puede ser lento |
| Formatos bancarios reales | Los formatos de Banco A/B/C son supuestos. Los bancos reales pueden tener columnas adicionales o formatos distintos |
| Monedas múltiples | Si hay pagos en distintas monedas, la lógica de comparación de montos necesita conversión de tipo de cambio |
| Periodicidad | No está claro si la conciliación es mensual, quincenal, diaria. Afecta el diseño del historial |
| Reglas de duplicado | El cliente puede tener casos válidos donde el mismo empleado recibe dos pagos parciales (no duplicados) |
