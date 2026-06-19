# ETL Automatizado con Apache Airflow

Orquesta semanalmente la extracción de datos desde MongoDB o PostgreSQL, su transformación con Spark (análisis OLAP + esquema estrella), la carga en el data warehouse de Hive, y el reindexado condicional de ElasticSearch cuando cambia el catálogo de platos.

## Estructura

```
services/airflow/
└── docker/
    ├── docker-compose_airflow.yml
    └── dags/
        └── etl_restaurantes.py
```

## Servicios

| Servicio | Imagen | Puerto |
|---|---|---|
| airflow-webserver | apache/airflow:2.9.0 | 8090 (UI) |
| airflow-scheduler | apache/airflow:2.9.0 | — |
| airflow-worker | apache/airflow:2.9.0 | — |
| airflow-db | postgres:15 | — (interno) |
| airflow-redis | redis:7 | — (interno) |

Corre en la misma red `olap-network` que el resto del stack, ya que necesita comunicarse con `spark-master`, `hiveserver2` y `elasticsearch`.

## Requisitos

- Docker Desktop instalado y corriendo
- Socket de Docker accesible desde `airflow-worker` (necesario para que el DAG pueda hacer `docker exec`/`docker cp` sobre `spark-master` y `hiveserver2`)
- Servicios del stack OLAP corriendo: `spark-master`, `spark-worker`, `hive-metastore`, `hiveserver2`
- MongoDB o PostgreSQL corriendo con los datos de origen
- ElasticSearch corriendo (para el paso de reindexado)
- Los JARs del conector de MongoDB ya descargados en `spark-master` **y** `spark-worker` (ver README del proyecto OLAP — estos JARs no persisten si los contenedores se recrean)

## Primera vez — inicializar Airflow

```bash
cd services/airflow/docker
docker compose -f docker-compose_airflow.yml run --rm airflow-init
```

Esto crea la base de datos interna de Airflow y el usuario administrador (`admin` / `admin`).

## Levantar Airflow

```bash
docker compose -f docker-compose_airflow.yml up -d
```

Esperar ~1 minuto y abrir **http://localhost:8090**.

**Login:** usuario `admin` / contraseña `admin`

## El DAG: `etl_restaurantes`

**Frecuencia:** semanal (`@weekly`)
**Parámetro:** `fuente` — `"mongo"` o `"postgres"`

### Flujo

```
inicio
  └─→ extraer                    (verifica conexión a la fuente)
        └─→ transformar          (Spark: análisis OLAP + esquema estrella)
              └─→ cargar_hive    (confirma que las tablas existen)
                    └─→ verificar_cambios_es
                          ├─→ reindexar_elasticsearch   (si el catálogo cambió)
                          └─→ sin_cambios_es             (si no cambió)
                                └─→ fin
```

### Qué hace cada tarea

| Tarea | Detalle |
|---|---|
| `extraer` | Se conecta a Mongo o Postgres (según el parámetro `fuente`) y verifica que las colecciones/tablas respondan |
| `transformar` | Genera un script PySpark completo (los 3 análisis OLAP + las 5 dimensiones y 2 hechos del esquema estrella), lo copia al contenedor `spark-master` vía `docker cp`, y lo ejecuta con `spark-submit` |
| `cargar_hive` | Verifica vía `docker exec` a `hiveserver2` (beeline) que las tablas clave existen tanto en `restaurantes` como en `estrella` |
| `verificar_cambios_es` | Compara el conjunto de IDs de platos en la fuente contra los IDs indexados actualmente en ElasticSearch. Es un `BranchPythonOperator`: decide a cuál de las dos ramas siguientes ir |
| `reindexar_elasticsearch` | Borra el índice `platos` y lo recrea completo a partir de la fuente actual |
| `sin_cambios_es` | Rama vacía — se ejecuta (y aparece como *skipped*, no como *failed*) cuando no hubo cambios en el catálogo |

### Por qué usa `docker exec` / `docker cp` en lugar de PySpark directo

El contenedor de Airflow no tiene Java ni PySpark instalados, y no es necesario instalarlos. En cambio, la tarea `transformar` escribe el script en un archivo temporal local, lo copia dentro de `spark-master` con `docker cp`, y lo ejecuta ahí con `spark-submit` — reutilizando el cluster de Spark que ya existe en lugar de duplicar el entorno de ejecución dentro de Airflow.

Mismo principio para `cargar_hive`: en vez de instalar un cliente Hive (`pyhive`) en Airflow, se usa `beeline` que ya está disponible dentro del contenedor `hiveserver2`.

## Correr el DAG manualmente

1. En la UI, ubicar `etl_restaurantes` en la lista de DAGs
2. Click en ▶ (Play) → **Trigger DAG w/ config**
3. En el campo JSON:
   ```json
   {"fuente": "mongo"}
   ```
   o
   ```json
   {"fuente": "postgres"}
   ```
4. **Trigger**
5. Ver el progreso en la vista **Graph** o **Grid** — cada tarea se pone verde al completar, roja si falla, rosa si fue saltada (*skipped*)

## Problemas conocidos y soluciones

**`ModuleNotFoundError: No module named 'pymongo'/'psycopg2'`**
Faltan las dependencias Python en los contenedores de Airflow. Se resuelve con la variable de entorno `_PIP_ADDITIONAL_REQUIREMENTS` en el compose (ya configurada): `pymongo psycopg2-binary pyhive requests`.

**`LOCATION_ALREADY_EXISTS` al correr `transformar`**
Quedaron carpetas de una corrida anterior en el warehouse de Hive. Limpiar antes de reintentar:
```bash
docker exec -u root hive-metastore bash -c "rm -rf /opt/hive/data/warehouse/restaurantes.db /opt/hive/data/warehouse/estrella.db"
```

**`DATA_SOURCE_NOT_FOUND: mongodb` o `ClassCastException` en `transformar`**
El conector de MongoDB no está instalado en `spark-master` y/o `spark-worker` (no persiste entre reinicios de esos contenedores). Verificar y reinstalar siguiendo el README del proyecto OLAP, sección de JARs de MongoDB.

**La tarea `extraer` queda en `queued` y falla sin log ("Was the task killed externally?")**
Generalmente por falta de memoria en el worker o por una dependencia faltante que crashea el proceso antes de loguear. Revisar `docker stats airflow-worker` y los logs de `airflow-scheduler`.

## Apagar Airflow

```bash
docker compose -f docker-compose_airflow.yml down
```

Para borrar también el historial de corridas y usuarios:
```bash
docker compose -f docker-compose_airflow.yml down -v
```