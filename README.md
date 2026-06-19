# Restaurant API
API REST para la gestión de restaurantes, menús, platos, mesas y reservaciones.
El proyecto utiliza contenedores Docker, autenticación con Keycloak y una base de datos PostgreSQL o MongoDB .

## ⚙️ Tecnologías utilizadas
- **Node.js**
- **Express.js**
- **PostgreSQL**
- **Mongodb**
- **Keycloak**
- **Docker**
- **Elasticsearch**
- **Redash**
- **Airflow**
- **Spark**

## 🛠️ Instalación
Clonar repositorio:
```bash
git clone https://github.com/cthompson23/P1-BD2.git
```
Navegar al directorio `docker/`:
```bash
cd docker
```

Crear archivo ```.env.postgres```:
```
PORT=5000
BD_USER=postgres
BD_PASSWORD=postgres
BD_DATABASE=restaurantes_db
BD_HOST=db
BD_PORT=5432
DB_TYPE=postgres

POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=restaurantes_db

KC_BOOTSTRAP_ADMIN_USERNAME=admin
KC_BOOTSTRAP_ADMIN_PASSWORD=admin

POSTGRES_USER_KEYCLOAK=keycloak
POSTGRES_PASSWORD_KEYCLOAK=keycloak
POSTGRES_DB_KEYCLOAK=keycloak_db

ELASTICSEARCH_ENDPOINT= http://elasticsearch:9200
ELASTICSEARCH_API_KEY=

```

Crear archivo ```.env.mongo``` :
```
PORT=5000
DB_TYPE=mongo

MONGO_URL=mongodb://mongodb:27017
MONGO_DATABASE=restaurantes_db

KC_BOOTSTRAP_ADMIN_USERNAME=admin
KC_BOOTSTRAP_ADMIN_PASSWORD=admin
POSTGRES_USER_KEYCLOAK=keycloak
POSTGRES_PASSWORD_KEYCLOAK=keycloak
POSTGRES_DB_KEYCLOAK=keycloak_db

ELASTICSEARCH_ENDPOINT=http://elasticsearch:9200
ELASTICSEARCH_API_KEY=

```

## 🚀 Ejecución
Desde la raíz del proyecto, inicializar el servicio con el Docker Compose:

Para Postgres:

```
docker compose --env-file docker/.env.postgres -f docker/docker-compose_postgres.yml up --build 
```

Para Mongo:

```
docker compose --env-file docker/.env.mongo -f docker/docker-compose_mongo.yml up --build
```
## 📚 Documentación de la API (Swagger)
### Acceso a la documentación
Una vez que el servidor esté corriendo, puedes acceder a la interfaz en:

```bash
http://localhost:5001/api-docs
```

### Cómo probar endpoints protegidos (Admin)
Para los endpoints que requieren el rol `admin`se debe sigue:

1. **Obtener Token:** Realiza una petición de autenticación a Keycloak para obtener tu `access_token`.
2. **Autorizar:** Haz clic en el botón **"Authorize"** en la parte superior de Swagger.
3. **Insertar Token:** Pega tu token en el campo de valor.
4. **Ejecutar:** Ahora puedes usar el botón **"Try it out"** en cualquier ruta protegida.


