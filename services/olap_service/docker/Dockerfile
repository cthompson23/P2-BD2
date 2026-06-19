FROM apache/spark:4.1.2

USER root

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# ── Driver Postgres ────────────────────────────────────────────────────────────
RUN wget -q -O /opt/spark/jars/postgresql-42.7.3.jar \
    https://jdbc.postgresql.org/download/postgresql-42.7.3.jar

# ── Drivers MongoDB ────────────────────────────────────────────────────────────
RUN wget -q -O /opt/spark/jars/mongo-spark-connector_2.12-10.3.0.jar \
    https://repo1.maven.org/maven2/org/mongodb/spark/mongo-spark-connector_2.12/10.3.0/mongo-spark-connector_2.12-10.3.0.jar \
 && wget -q -O /opt/spark/jars/mongodb-driver-sync-4.11.0.jar \
    https://repo1.maven.org/maven2/org/mongodb/mongodb-driver-sync/4.11.0/mongodb-driver-sync-4.11.0.jar \
 && wget -q -O /opt/spark/jars/bson-4.11.0.jar \
    https://repo1.maven.org/maven2/org/mongodb/bson/4.11.0/bson-4.11.0.jar \
 && wget -q -O /opt/spark/jars/mongodb-driver-core-4.11.0.jar \
    https://repo1.maven.org/maven2/org/mongodb/mongodb-driver-core/4.11.0/mongodb-driver-core-4.11.0.jar

# ── Hive Metastore client (Hive 3.1.3) ────────────────────────────────────────
RUN mkdir -p /opt/spark/hive-jars \
 && wget -q -O /opt/spark/hive-jars/hive-metastore-3.1.3.jar \
    https://repo1.maven.org/maven2/org/apache/hive/hive-metastore/3.1.3/hive-metastore-3.1.3.jar \
 && wget -q -O /opt/spark/hive-jars/hive-exec-3.1.3.jar \
    https://repo1.maven.org/maven2/org/apache/hive/hive-exec/3.1.3/hive-exec-3.1.3.jar \
 && wget -q -O /opt/spark/hive-jars/hive-common-3.1.3.jar \
    https://repo1.maven.org/maven2/org/apache/hive/hive-common/3.1.3/hive-common-3.1.3.jar \
 && wget -q -O /opt/spark/hive-jars/libfb303-0.9.3.jar \
    https://repo1.maven.org/maven2/org/apache/thrift/libfb303/0.9.3/libfb303-0.9.3.jar \
 && wget -q -O /opt/spark/hive-jars/libthrift-0.9.3.jar \
    https://repo1.maven.org/maven2/org/apache/thrift/libthrift/0.9.3/libthrift-0.9.3.jar

# ── Configuración Spark y Hive ─────────────────────────────────────────────────
RUN mkdir -p /opt/spark/conf
COPY hive-site.xml        /opt/spark/conf/hive-site.xml
COPY spark.conf  /opt/spark/conf/spark.conf

# ── Python packages ────────────────────────────────────────────────────────────
RUN pip3 install --no-cache-dir \
    jupyterlab \
    pyspark==4.0.0 \
    pandas \
    pyarrow \
    findspark

RUN mkdir -p /home/jovyan/work && chmod 777 /home/jovyan/work
WORKDIR /home/jovyan/work

EXPOSE 8888

ENTRYPOINT ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''"]