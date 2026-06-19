# Run this once before docker compose up.
# Downloads the Postgres JDBC driver that Hive needs to talk to its metastore DB.

set -e

DRIVER_VERSION="42.7.3"
DRIVER_JAR="postgresql-${DRIVER_VERSION}.jar"
DRIVER_URL="https://jdbc.postgresql.org/download/${DRIVER_JAR}"
TARGET_DIR="./hive-libs"

mkdir -p "$TARGET_DIR"

if [ -f "${TARGET_DIR}/${DRIVER_JAR}" ]; then
  echo "✓ ${DRIVER_JAR} already present in ${TARGET_DIR}, skipping download."
else
  echo "Downloading Postgres JDBC driver ${DRIVER_VERSION}..."
  curl -fL "$DRIVER_URL" -o "${TARGET_DIR}/${DRIVER_JAR}"
  echo "✓ Downloaded to ${TARGET_DIR}/${DRIVER_JAR}"
fi

echo ""
echo "All done. You can now run: docker compose up -d"