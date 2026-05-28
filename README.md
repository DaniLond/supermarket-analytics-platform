# Supermercado Analytics

Plataforma de analítica de transacciones de supermercado con procesamiento distribuido
(PySpark), almacén analítico (Parquet + DuckDB), API REST (FastAPI) y dashboard interactivo (React).

## Arquitectura rápida

```
Dataset CSV → PySpark (batch) → Parquet particionado → DuckDB → FastAPI → React Dashboard
```

Ver [`docs/arquitectura.md`](docs/arquitectura.md) para el diagrama completo.

---

## Prerrequisitos

| Herramienta | Versión mínima |
|-------------|---------------|
| Python | 3.11 |
| Java (para PySpark) | 17 |
| Node.js | 20 |
| Docker + Docker Compose | 24 |

---

## Arranque rápido (Docker)

```bash
# 1. Clonar / descargar el proyecto
cd Proyecto

# 2. Levantar servicios
docker compose up --build

# Frontend → http://localhost:3000
# API      → http://localhost:8000
# Swagger  → http://localhost:8000/docs
```

---

## Arranque local (sin Docker)

### Backend

```bash
cd backend
py -m pip install -e ".[dev]"
py -m uvicorn app.main:app --reload --port 8000
```

> **Nota:** si los Parquet no existen aún, el health check reportará
> `transactions_loaded: false`. Ejecuta la ingesta primero (ver abajo).

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## Cómo cargar el dataset inicial

El dataset ya está extraído en `data/DataSet/`. Con el backend corriendo, dispara la ingesta:

```powershell
# PowerShell (con el backend corriendo en puerto 8000)
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/ingest"

# Verificar estado del job
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/ingest/status"
```

Esto genera:

```
data/processed/
├── transactions_long/      particionado por store_id / year_month
├── transactions_basket/    particionado por store_id / year_month
└── catalog/                productos y categorías
```

---

## Cómo agregar transacciones nuevas vía API

```bash
curl -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [
      {"date": "2013-07-01", "store_id": 102, "customer_id": 999, "categories": [1, 5, 10]}
    ]
  }'
```

---

## Cómo reentrenar los modelos ML

```bash
# Segmentación K-Means
python spark_jobs/train_segmentation.py

# Reglas de asociación FP-Growth
python spark_jobs/train_recommender.py

# O vía API (dispara ambos en subproceso):
curl -X POST http://localhost:8000/api/v1/models/retrain
```

---

## Estructura del proyecto

```
Proyecto/
├── backend/          FastAPI + DuckDB (Python 3.11)
├── spark_jobs/       Batch PySpark (ingesta + ML)
├── frontend/         React 18 + Vite + TypeScript + Tailwind
├── data/
│   ├── DataSet/      Dataset crudo
│   ├── processed/    Parquet generado por Spark
│   └── models/       Modelos ML serializados
├── docs/             Arquitectura e informe técnico
└── docker-compose.yml
```

