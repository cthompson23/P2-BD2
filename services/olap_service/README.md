# OLAP Service

Clúster de Apache Spark corriendo en Docker con un nodo master y un worker, usando la imagen oficial `apache/spark`. Incluye Apache Hive como data warehouse para almacenar los datos transformados, y Jupyter Lab para ejecutar los notebooks de análisis y transformación. Soporta ingesta desde MongoDB y PostgreSQL.

## Estructura

```
services/olap_service/
├── docker/
│   ├── docker-compose_olap.yml
│   ├── Dockerfile
│   └── hive-libs/
│       └── postgresql-42.7.3.jar   ← descargado con el script de setup
└── spark/
    ├── hive-site.xml               ← configuración de conexión al Metastore
    └── notebooks/                  ← notebooks de Jupyter
```

## Servicios

| Servicio | Imagen | Puerto(s) |
|---|---|---|
| spark-master | apache/spark:4.1.2 | 8080 (UI), 7077 (cluster) |
| spark-worker | apache/spark:4.1.2 | 8082 (UI) |
| jupyter | custom (Dockerfile) | 8888 |
| hive-metastore | apache/hive:4.0.1 | 9083 (Thrift) |
| hiveserver2 | apache/hive:4.0.1 | 10000 (JDBC), 10002 (UI) |
| hive-metastore-db | postgres:15 | — (interno) |

El worker tiene asignados **2 cores** y **2 GB de memoria**.

## Requisitos

- Docker Desktop instalado y corriendo
- Puertos `7077`, `8080`, `8082`, `8888`, `9083`, `10000` y `10002` libres
- Uno de los siguientes como fuente de datos crudos:
  - MongoDB corriendo en `localhost:27017`
  - PostgreSQL corriendo en `localhost:4001`

## Setup inicial (solo la primera vez)

Descargar el driver JDBC de PostgreSQL que necesita Hive para su base de metadatos. Ejecutar en PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path ".\hive-libs"

Invoke-WebRequest `
  -Uri "https://jdbc.postgresql.org/download/postgresql-42.7.3.jar" `
  -OutFile ".\hive-libs\postgresql-42.7.3.jar"
```

## Levantar el clúster

Crear la red externa si no existe (solo la primera vez):
```bash
docker network create olap-network
```

Levantar todos los servicios desde la carpeta `services/olap_service/docker/`:
```bash
docker compose -f docker-compose_olap.yml up -d
```

Verificar que estén corriendo (~30 segundos para que el metastore inicialice):
```bash
docker compose -f docker-compose_olap.yml ps
```

## Interfaces web

| UI | URL |
|---|---|
| Spark Master | http://localhost:8080 |
| Spark Worker | http://localhost:8082 |
| Jupyter Lab | http://localhost:8888 |
| HiveServer2 | http://localhost:10002 |

## Usar Jupyter para transformar y guardar datos

Abrir http://localhost:8888 y crear un notebook. Inicializar la sesión de Spark con soporte a Hive:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("ETL") \
    .master("spark://spark-master:7077") \
    .config("spark.sql.catalogImplementation", "hive") \
    .enableHiveSupport() \
    .getOrCreate()
```

**Leer desde la fuente (MongoDB o PostgreSQL)**, transformar con Spark, y guardar en Hive:

```python
# Escribir datos transformados al data warehouse
df_transformado.write \
    .mode("overwrite") \
    .saveAsTable("default.nombre_tabla")

# Verificar
spark.sql("SHOW TABLES").show()
spark.sql("SELECT * FROM default.nombre_tabla LIMIT 10").show()
```

## Análisis incluidos

**1. Tendencias de consumo** — platos más pedidos globalmente y top 5 por categoría (Desayunos, Almuerzos, Cenas, etc.), excluyendo pedidos cancelados.

**2. Horarios pico** — distribución de reservaciones por hora del día para reservaciones activas y completadas. Muestra la hora con mayor demanda.

**3. Crecimiento mensual** — volumen de pedidos agrupado por mes (`YYYY-MM`) con variación porcentual mes a mes para identificar tendencias de crecimiento o caída.

## Seeds

| Base | Archivo | Comando |
|---|---|---|
| MongoDB | `data/seed_data_mongo.py` | `python data/seed_data_mongo.py` |
| PostgreSQL | `data/seed_postgres.py` | `python data/seed_postgres.py` |

Dependencias para los seeds:
```bash
pip install faker pymongo psycopg2-binary
```

## Apagar el clúster

Para eliminar también los volúmenes del data warehouse y el metastore:
```bash
docker compose -f docker-compose_olap.yml down -v
```

## Recrear el hive metastore

1. Cada que se reinicia el contenedor debemos borrar el schema completo:
```bash
docker exec hive-metastore-db psql -U hive -d metastore -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```
2. Reiniciar el contenedor:
```bash
docker compose -f docker-compose_olap.yml up -d --no-deps hive-metastore
```
3. Limpiar el warehouse:
```bash
docker exec -u root hive-metastore bash -c "rm -rf /opt/hive/data/warehouse/estrella.db /opt/hive/data/warehouse/restaurantes.db"
```

## JAR de Mongo
1. Cada que se reinicia el contenedor debemos borrar el schema completo:
```bash
docker exec spark-worker bash -c "wget -q -O /opt/spark/jars/mongo-spark-connector_2.13-10.4.0.jar https://repo1.maven.org/maven2/org/mongodb/spark/mongo-spark-connector_2.13/10.4.0/mongo-spark-connector_2.13-10.4.0.jar"
```
```bash
docker exec spark-worker bash -c "wget -q -O /opt/spark/jars/mongodb-driver-sync-4.11.0.jar https://repo1.maven.org/maven2/org/mongodb/mongodb-driver-sync/4.11.0/mongodb-driver-sync-4.11.0.jar"
```
```bash
docker exec spark-worker bash -c "wget -q -O /opt/spark/jars/bson-4.11.0.jar https://repo1.maven.org/maven2/org/mongodb/bson/4.11.0/bson-4.11.0.jar"
```
```bash
docker exec spark-worker bash -c "wget -q -O /opt/spark/jars/mongodb-driver-core-4.11.0.jar https://repo1.maven.org/maven2/org/mongodb/mongodb-driver-core/4.11.0/mongodb-driver-core-4.11.0.jar"
```

2. Verificar:
```bash
docker exec spark-worker bash -c "ls /opt/spark/jars | grep mongo"
docker exec spark-worker bash -c "ls /opt/spark/jars | grep bson"
```

2. Limpiar warehouse:
```bash
docker exec -u root hive-metastore bash -c "rm -rf /opt/hive/data/warehouse/restaurantes.db /opt/hive/data/warehouse/estrella.db"
docker exec spark-master bash -c "ls /opt/hive/data/warehouse"```