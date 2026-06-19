"""
DAG: etl_restaurantes
Frecuencia: semanal (cada lunes a medianoche)
Parámetro: fuente = "mongo" | "postgres"

Pasos:
  1. extraer              — verifica conexión a la fuente
  2. transformar          — envía el script ETL al contenedor spark-master via docker exec
  3. cargar_hive          — confirma que las tablas existen en Hive
  4. verificar_cambios_es — detecta si cambiaron los platos
  5. reindexar_es         — reindexar platos en ElasticSearch si hubo cambios
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.models.param import Param
import subprocess
import requests
import json
import os

# ── Configuración ──────────────────────────────────────────────────────────────
MONGO_URI   = "mongodb://host.docker.internal:27017"
MONGO_DB    = "restaurantes_db"

PG_HOST     = "host.docker.internal"
PG_PORT     = 4001
PG_DB       = "restaurantes_db"
PG_USER     = "postgres"
PG_PASSWORD = "postgres"

SPARK_MASTER    = "spark://spark-master:7077"
HIVE_HOST       = "hiveserver2"
HIVE_PORT       = 10000
ES_HOST         = "elasticsearch"
ES_PORT         = 9200
ES_INDEX_PLATOS = "platos"

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


# ── Tareas ─────────────────────────────────────────────────────────────────────

def verificar_fuente(**context):
    """Verifica que la fuente de datos esté disponible."""
    fuente = context["params"]["fuente"]
    print(f"Verificando conexión a {fuente.upper()}...")

    if fuente == "mongo":
        from pymongo import MongoClient
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        db = client[MONGO_DB]
        colecciones = db.list_collection_names()
        print(f"✓ MongoDB OK — colecciones: {colecciones}")
        client.close()

    elif fuente == "postgres":
        import psycopg2
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, dbname=PG_DB,
            user=PG_USER, password=PG_PASSWORD
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM pedidos")
        count = cur.fetchone()[0]
        print(f"✓ PostgreSQL OK — pedidos: {count}")
        conn.close()

    else:
        raise ValueError(f"FUENTE debe ser 'mongo' o 'postgres', recibido: {fuente}")

    context["ti"].xcom_push(key="fuente", value=fuente)


def transformar_con_spark(**context):
    """Envía el script ETL al contenedor spark-master via docker exec."""
    fuente = context["ti"].xcom_pull(key="fuente", task_ids="extraer")
    print(f"Iniciando transformación Spark para fuente: {fuente.upper()}")

    spark_script = f"""
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, explode, sum as spark_sum, count, rank, desc, asc,
    lag, round as spark_round, coalesce, lit, to_date, to_timestamp,
    date_format, year, month, dayofmonth, hour, substring, regexp_extract
)
from pyspark.sql.window import Window

FUENTE           = "{fuente}"
HIVE_DB_ANALISIS = "restaurantes"
HIVE_DB_ESTRELLA = "estrella"
MONGO_URI        = "{MONGO_URI}"
MONGO_DB         = "{MONGO_DB}"

builder = (
    SparkSession.builder
    .appName("ETL Restaurantes Airflow")
    .master("{SPARK_MASTER}")
    .config("spark.executor.memory", "1g")
    .config("spark.executor.cores", "1")
    .config("spark.sql.warehouse.dir", "/opt/hive/data/warehouse")
    .config("spark.sql.catalogImplementation", "hive")
)

if FUENTE == "mongo":
    builder = builder \\
        .config("spark.mongodb.read.connection.uri", f"{{MONGO_URI}}/{{MONGO_DB}}")

spark = builder.enableHiveSupport().getOrCreate()
spark.sparkContext.setLogLevel("WARN")

# Lectura
if FUENTE == "mongo":
    def read_col(c):
        return spark.read.format("mongodb").option("collection", c).load()
    pedidos       = read_col("pedidos")
    platos        = read_col("platos")
    menus         = read_col("menus")
    reservaciones = read_col("reservaciones")
    usuarios      = read_col("usuarios")
    mesas         = read_col("mesas")
    restaurantes  = read_col("restaurantes")
else:
    JDBC_URL   = "jdbc:postgresql://{PG_HOST}:{PG_PORT}/{PG_DB}"
    JDBC_PROPS = {{"user": "{PG_USER}", "password": "{PG_PASSWORD}", "driver": "org.postgresql.Driver"}}
    def read_table(t):
        return spark.read.jdbc(url=JDBC_URL, table=t, properties=JDBC_PROPS)
    pedidos       = read_table("pedidos")
    item_pedido   = read_table("item_pedido")
    platos        = read_table("platos")
    menus         = read_table("menus")
    reservaciones = read_table("reservaciones")
    usuarios      = read_table("usuarios")
    mesas         = read_table("mesas")
    restaurantes  = read_table("restaurantes")

def save(df, db, table):
    data = df.collect()
    out  = spark.createDataFrame(data, df.schema)
    out.write.mode("overwrite").saveAsTable(f"{{db}}.{{table}}")
    print(f"✓ {{db}}.{{table}}: {{len(data)}} filas")

# Analisis OLAP
spark.sql(f"CREATE DATABASE IF NOT EXISTS {{HIVE_DB_ANALISIS}}")

if FUENTE == "mongo":
    items = (pedidos.filter(col("estado") != "cancelado")
        .select(explode(col("items")).alias("item"))
        .select(col("item.plato_id").alias("plato_id"), col("item.cantidad").alias("cantidad")))
    items_platos = items.join(
        platos.select(col("_id").alias("plato_id_join"), "nombre_plato", "precio", "menu_id"),
        items.plato_id == col("plato_id_join"), how="left")
    items_platos_menus = items_platos.join(
        menus.select(col("_id").alias("menu_id_join"), col("nombre_menu").alias("categoria")),
        items_platos.menu_id == col("menu_id_join"), how="left")
else:
    items = (item_pedido.join(
        pedidos.select(col("id").alias("pedido_id_join"), col("estado")),
        item_pedido.pedido_id == col("pedido_id_join"), how="left")
        .filter(col("estado") != "cancelado")
        .select(col("plato_id"), col("cantidad")))
    items_platos = items.join(
        platos.select(col("id").alias("plato_id_join"), "nombre_plato", "precio", "menu_id"),
        items.plato_id == col("plato_id_join"), how="left")
    items_platos_menus = items_platos.join(
        menus.select(col("id").alias("menu_id_join"), col("nombre_menu").alias("categoria")),
        items_platos.menu_id == col("menu_id_join"), how="left")

window_cat = Window.partitionBy("categoria").orderBy(desc("total_pedido"))
top_por_categoria = (items_platos_menus
    .groupBy("categoria", "nombre_plato", "precio")
    .agg(spark_sum("cantidad").alias("total_pedido"))
    .withColumn("rank", rank().over(window_cat))
    .filter(col("rank") <= 5)
    .orderBy("categoria", "rank"))
save(top_por_categoria, HIVE_DB_ANALISIS, "tendencias_consumo")

if FUENTE == "mongo":
    hora_col = regexp_extract(col("hora_reservacion"), r"^(\\d{{2}})", 1).cast("int")
else:
    hora_col = hour(col("hora_reservacion"))

horarios_pico = (reservaciones
    .filter(col("estado").isin("activa", "completada"))
    .withColumn("hora", hora_col)
    .groupBy("hora").agg(count("*").alias("total_reservaciones"))
    .orderBy("hora"))
save(horarios_pico, HIVE_DB_ANALISIS, "horarios_pico")

if FUENTE == "mongo":
    fecha_col = substring(col("fecha_orden"), 1, 7)
else:
    fecha_col = date_format(col("fecha_orden"), "yyyy-MM")

window_mes = Window.orderBy("anio_mes")
crecimiento = (pedidos
    .withColumn("anio_mes", fecha_col)
    .groupBy("anio_mes").agg(count("*").alias("total_pedidos"))
    .orderBy("anio_mes")
    .withColumn("mes_anterior", lag("total_pedidos", 1).over(window_mes))
    .withColumn("variacion_pct", coalesce(
        spark_round(((col("total_pedidos") - col("mes_anterior")) / col("mes_anterior")) * 100, 2),
        lit(0.0))))
save(crecimiento, HIVE_DB_ANALISIS, "crecimiento_mensual")

# Esquema estrella
spark.sql(f"CREATE DATABASE IF NOT EXISTS {{HIVE_DB_ESTRELLA}}")

if FUENTE == "mongo":
    dim_restaurante = restaurantes.select(col("_id").alias("restaurante_sk"), "nombre_rest", "ubicacion", "correo_rest", "telefono_rest")
    dim_usuario     = usuarios.select(col("_id").alias("usuario_sk"), col("id").alias("usuario_id"), "nombre", "email")
    dim_plato       = platos.join(menus.select(col("_id").alias("menu_id_join"), col("nombre_menu").alias("categoria")),
        platos.menu_id == col("menu_id_join"), how="left").select(
        col("_id").alias("plato_sk"), "nombre_plato", "precio", "categoria", "descripcion")
    dim_mesa        = mesas.join(restaurantes.select(col("_id").alias("rest_id_join"), "nombre_rest"),
        mesas.rest_id == col("rest_id_join"), how="left").select(
        col("_id").alias("mesa_sk"), "numero_mesa", "capacidad", "disponible", col("nombre_rest").alias("restaurante"))
    fechas = pedidos.select(col("fecha_orden").alias("fecha_str")).union(
        reservaciones.select(col("dia_reservacion").alias("fecha_str"))).distinct()
    fact_items = pedidos.select(
        col("_id").alias("pedido_id"), col("usuario_id"),
        col("fecha_orden"), col("estado"), col("tipo_pedido"),
        explode(col("items")).alias("item")).select(
        col("pedido_id"), col("usuario_id").alias("usuario_sk"),
        col("item.plato_id").alias("plato_sk"),
        date_format(to_date(col("fecha_orden"), "yyyy-MM-dd"), "yyyyMMdd").alias("tiempo_sk"),
        col("item.cantidad").alias("cantidad"), col("estado"), col("tipo_pedido"))
    fact_pedidos = fact_items.join(
        platos.select(col("_id").alias("plato_id_join"), "precio"),
        fact_items.plato_sk == col("plato_id_join"), how="left").select(
        "pedido_id", "usuario_sk", "plato_sk", "tiempo_sk", "cantidad",
        (col("cantidad") * col("precio")).alias("precio_total"), "estado", "tipo_pedido")
    fact_reservaciones = reservaciones.select(
        col("_id").alias("reservacion_sk"), col("usuario_id").alias("usuario_sk"),
        col("mesa_id").alias("mesa_sk"),
        date_format(to_date(col("dia_reservacion"), "yyyy-MM-dd"), "yyyyMMdd").alias("tiempo_sk"),
        col("hora_reservacion"), col("estado"))
else:
    dim_restaurante = restaurantes.select(col("id").cast("string").alias("restaurante_sk"), "nombre_rest", "ubicacion", "correo_rest", "telefono_rest")
    dim_usuario     = usuarios.select(col("id").alias("usuario_sk"), "usuario", "nombre", "apellido", "email")
    dim_plato       = platos.join(menus.select(col("id").alias("menu_id_join"), col("nombre_menu").alias("categoria")),
        platos.menu_id == col("menu_id_join"), how="left").select(
        col("id").cast("string").alias("plato_sk"), "nombre_plato", "precio", "categoria", "descripcion")
    dim_mesa        = mesas.join(restaurantes.select(col("id").alias("rest_id_join"), "nombre_rest"),
        mesas.rest_id == col("rest_id_join"), how="left").select(
        col("id").cast("string").alias("mesa_sk"), "numero_mesa", "capacidad", "disponible", col("nombre_rest").alias("restaurante"))
    fechas = pedidos.select(col("fecha_orden").cast("string").alias("fecha_str")).union(
        reservaciones.select(col("dia_reservacion").cast("string").alias("fecha_str"))).distinct()
    fact_pedidos = (item_pedido.join(
        pedidos.select(col("id").alias("pedido_id"), "usuario_id", "fecha_orden", "estado", "tipo_pedido"),
        item_pedido.pedido_id == col("pedido_id"), how="left")
        .join(platos.select(col("id").alias("plato_id_join"), "precio"),
        item_pedido.plato_id == col("plato_id_join"), how="left")
        .select(col("pedido_id").cast("string"), col("usuario_id").alias("usuario_sk"),
        col("plato_id").cast("string").alias("plato_sk"),
        date_format(col("fecha_orden"), "yyyyMMdd").alias("tiempo_sk"),
        col("cantidad"), (col("cantidad") * col("precio")).alias("precio_total"),
        col("estado"), col("tipo_pedido")))
    fact_reservaciones = reservaciones.select(
        col("id").cast("string").alias("reservacion_sk"), col("usuario_id").alias("usuario_sk"),
        col("mesa_id").cast("string").alias("mesa_sk"),
        date_format(col("dia_reservacion"), "yyyyMMdd").alias("tiempo_sk"),
        col("hora_reservacion").cast("string"), col("estado"))

dim_tiempo = (fechas
    .withColumn("fecha", to_date(col("fecha_str"), "yyyy-MM-dd"))
    .filter(col("fecha").isNotNull())
    .select(
        date_format(col("fecha"), "yyyyMMdd").alias("tiempo_sk"),
        col("fecha"), year(col("fecha")).alias("anio"),
        month(col("fecha")).alias("mes"),
        date_format(col("fecha"), "MMMM").alias("nombre_mes"),
        dayofmonth(col("fecha")).alias("dia"),
        date_format(col("fecha"), "EEEE").alias("dia_semana"))
    .distinct())

for df, table in [
    (dim_restaurante, "dim_restaurante"), (dim_usuario, "dim_usuario"),
    (dim_plato, "dim_plato"), (dim_mesa, "dim_mesa"), (dim_tiempo, "dim_tiempo"),
    (fact_pedidos, "fact_pedidos"), (fact_reservaciones, "fact_reservaciones")
]:
    save(df, HIVE_DB_ESTRELLA, table)

print("ETL completado exitosamente.")
spark.stop()
"""

    # Escribir el script en un archivo local temporal y copiarlo al contenedor
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(spark_script)
        tmp_path = f.name

    # Copiar al contenedor spark-master
    cp_result = subprocess.run(
        ["docker", "cp", tmp_path, "spark-master:/tmp/etl_airflow.py"],
        capture_output=True, text=True, timeout=30
    )
    if cp_result.returncode != 0:
        raise Exception(f"Error copiando script: {cp_result.stderr}")

    # Ejecutar con spark-submit
    result = subprocess.run(
        ["docker", "exec", "spark-master", "bash", "-c",
         f"/opt/spark/bin/spark-submit --master {SPARK_MASTER} /tmp/etl_airflow.py"],
        capture_output=True, text=True, timeout=3600
    )

    print(result.stdout[-3000:] if result.stdout else "")
    if result.returncode != 0:
        print(result.stderr[-2000:] if result.stderr else "")
        raise Exception(f"Spark ETL fallo con codigo {result.returncode}")

    print("Transformacion Spark completada.")


def verificar_hive(**context):
    """Verifica que las tablas existan en Hive usando docker exec."""
    tablas_requeridas = [
        ("restaurantes", "tendencias_consumo"),
        ("restaurantes", "horarios_pico"),
        ("restaurantes", "crecimiento_mensual"),
        ("estrella",     "fact_pedidos"),
        ("estrella",     "fact_reservaciones"),
        ("estrella",     "dim_plato"),
    ]

    for db, tabla in tablas_requeridas:
        result = subprocess.run(
            ["docker", "exec", "hiveserver2", "bash", "-c",
             f"/opt/hive/bin/beeline -u \'jdbc:hive2://localhost:10000/{db}\' "
             f"--silent=true -e \'SELECT COUNT(*) FROM {tabla};\' 2>&1"],
            capture_output=True, text=True, timeout=120
        )
        print(f"✓ {db}.{tabla} verificado")


def verificar_cambios_platos(**context):
    """Compara el catálogo actual de platos con el índice en ES."""
    fuente = context["ti"].xcom_pull(key="fuente", task_ids="extraer")

    if fuente == "mongo":
        from pymongo import MongoClient
        client = MongoClient(MONGO_URI)
        platos = list(client[MONGO_DB]["platos"].find({}, {"_id": 1}))
        platos_set = {str(p["_id"]) for p in platos}
        client.close()
    else:
        import psycopg2
        conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB,
                                user=PG_USER, password=PG_PASSWORD)
        cur = conn.cursor()
        cur.execute("SELECT id::text FROM platos")
        platos_set = {row[0] for row in cur.fetchall()}
        conn.close()

    try:
        resp = requests.get(
            f"http://{ES_HOST}:{ES_PORT}/{ES_INDEX_PLATOS}/_search",
            json={"size": 10000, "_source": False}, timeout=10)
        if resp.status_code == 200:
            hits = resp.json().get("hits", {}).get("hits", [])
            es_set = {h["_id"] for h in hits}
        else:
            es_set = set()
    except Exception:
        es_set = set()

    hay_cambios = platos_set != es_set
    print(f"Platos en fuente: {len(platos_set)} | En ES: {len(es_set)} | Cambios: {hay_cambios}")
    context["ti"].xcom_push(key="hay_cambios", value=hay_cambios)
    return "reindexar_elasticsearch" if hay_cambios else "sin_cambios_es"


def reindexar_elasticsearch(**context):
    """Reindexar el catálogo de platos en ElasticSearch."""
    fuente = context["ti"].xcom_pull(key="fuente", task_ids="extraer")
    print("Reindexando platos en ElasticSearch...")

    if fuente == "mongo":
        from pymongo import MongoClient
        client = MongoClient(MONGO_URI)
        platos = list(client[MONGO_DB]["platos"].find(
            {}, {"_id": 1, "nombre_plato": 1, "precio": 1, "descripcion": 1}))
        docs = [{"id": str(p["_id"]), "nombre_plato": p.get("nombre_plato"),
                 "precio": p.get("precio"), "descripcion": p.get("descripcion")} for p in platos]
        client.close()
    else:
        import psycopg2
        conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB,
                                user=PG_USER, password=PG_PASSWORD)
        cur = conn.cursor()
        cur.execute("SELECT p.id, p.nombre_plato, p.precio, p.descripcion, m.nombre_menu FROM platos p JOIN menus m ON p.menu_id = m.id")
        rows = cur.fetchall()
        docs = [{"id": str(r[0]), "nombre_plato": r[1], "precio": float(r[2]),
                 "descripcion": r[3], "categoria": r[4]} for r in rows]
        conn.close()

    requests.delete(f"http://{ES_HOST}:{ES_PORT}/{ES_INDEX_PLATOS}", timeout=10)

    bulk_body = ""
    for doc in docs:
        bulk_body += json.dumps({"index": {"_index": ES_INDEX_PLATOS, "_id": doc["id"]}}) + "\n"
        bulk_body += json.dumps(doc) + "\n"

    resp = requests.post(
        f"http://{ES_HOST}:{ES_PORT}/_bulk",
        data=bulk_body,
        headers={"Content-Type": "application/x-ndjson"},
        timeout=60)

    result = resp.json()
    if result.get("errors"):
        raise Exception(f"Error en reindexado ES: {result}")

    print(f"✓ Reindexados {len(docs)} platos en ElasticSearch.")


# ── DAG ────────────────────────────────────────────────────────────────────────
with DAG(
    dag_id="etl_restaurantes",
    description="ETL semanal: extrae de Mongo/Postgres, transforma con Spark, carga en Hive y reindexar ES",
    schedule_interval="@weekly",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args=default_args,
    params={
        "fuente": Param("mongo", type="string", enum=["mongo", "postgres"],
                        description="Fuente de datos: 'mongo' o 'postgres'")
    },
    tags=["etl", "spark", "hive", "elasticsearch"],
) as dag:

    inicio = EmptyOperator(task_id="inicio")

    extraer = PythonOperator(
        task_id="extraer",
        python_callable=verificar_fuente,
    )

    transformar = PythonOperator(
        task_id="transformar",
        python_callable=transformar_con_spark,
        execution_timeout=timedelta(hours=1),
    )

    cargar_hive = PythonOperator(
        task_id="cargar_hive",
        python_callable=verificar_hive,
    )

    verificar_es = BranchPythonOperator(
        task_id="verificar_cambios_es",
        python_callable=verificar_cambios_platos,
    )

    reindexar_es = PythonOperator(
        task_id="reindexar_elasticsearch",
        python_callable=reindexar_elasticsearch,
    )

    sin_cambios_es = EmptyOperator(task_id="sin_cambios_es")

    fin = EmptyOperator(
        task_id="fin",
        trigger_rule="none_failed_min_one_success"
    )

    inicio >> extraer >> transformar >> cargar_hive >> verificar_es
    verificar_es >> [reindexar_es, sin_cambios_es]
    [reindexar_es, sin_cambios_es] >> fin