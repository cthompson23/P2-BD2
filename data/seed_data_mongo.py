"""
Genera datos sintéticos para el proyecto de restaurantes.
Pobla MongoDB con datos coherentes.

Instalación de dependencias:
    pip install faker pymongo

Uso:
    python seed_data.py
"""

import random
import uuid
from datetime import datetime, date, timedelta, time
from faker import Faker
from pymongo import MongoClient

# ──────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────
MONGO_URI = "mongodb://localhost:27017"
MONGO_DB  = "restaurantes_db"

# ──────────────────────────────────────────────
# VOLUMEN DE DATOS
# ──────────────────────────────────────────────
NUM_RESTAURANTES  = 40
NUM_USUARIOS      = 2
NUM_RESERVACIONES = 200
NUM_PEDIDOS       = 300

fake = Faker("es_MX")
random.seed(42)

# ══════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════

def random_time():
    hour   = random.randint(11, 21)
    minute = random.choice([0, 30])
    return time(hour, minute)

def random_date(start_days_ago=365, end_days_ago=0):
    delta = random.randint(end_days_ago, start_days_ago)
    return date.today() - timedelta(days=delta)

# ══════════════════════════════════════════════
# DATOS DE REFERENCIA
# ══════════════════════════════════════════════

CATEGORIAS_MENU = ["Desayunos", "Almuerzos", "Cenas", "Postres", "Bebidas", "Entradas"]

PLATOS_POR_CATEGORIA = {
    "Desayunos": [
        ("Gallo pinto con huevo", 4500),
        ("Casado de desayuno",    5500),
        ("Pancakes con miel",     3800),
        ("Frutas con granola",    3200),
    ],
    "Almuerzos": [
        ("Casado de pollo",       6500),
        ("Casado de res",         7000),
        ("Casado vegetariano",    5800),
        ("Arroz con camarones",   8500),
    ],
    "Cenas": [
        ("Filete de tilapia",     9000),
        ("Lomo saltado",          9500),
        ("Pasta alfredo",         7500),
        ("Pollo a la plancha",    7000),
    ],
    "Postres": [
        ("Tres leches",           2500),
        ("Flan de coco",          2200),
        ("Brownie con helado",    3000),
        ("Arroz con leche",       1800),
    ],
    "Bebidas": [
        ("Refresco natural",      1500),
        ("Agua mineral",           800),
        ("Café chorreado",        1200),
        ("Jugo de naranja",       1800),
    ],
    "Entradas": [
        ("Ceviche de camarón",    5500),
        ("Patacones con guacamole", 3500),
        ("Ensalada César",        4000),
        ("Sopa del día",          3000),
    ],
}

TIPOS_PEDIDO        = ["en sitio", "para llevar", "delivery"]
ESTADOS_PEDIDO      = ["pendiente", "confirmado", "en_preparacion", "listo", "entregado", "cancelado"]
ESTADOS_RESERVACION = ["activa", "completada", "cancelada"]

UBICACIONES_CR = [
    "San José Centro", "Escazú", "Santa Ana", "Heredia", "Alajuela",
    "Cartago", "Liberia", "Pérez Zeledón", "Limón", "Jacó",
]

# ══════════════════════════════════════════════
# SEEDER MONGODB
# ══════════════════════════════════════════════

def seed_mongo(mongo_db):
    now = datetime.utcnow()

    # ── Limpiar colecciones ───────────────────
    print("→ Limpiando colecciones MongoDB...")
    for col in ["restaurantes", "menus", "mesas", "platos", "pedidos", "reservaciones"]:
        mongo_db[col].drop()

    # ── Restaurantes ──────────────────────────
    print("→ Insertando restaurantes...")
    restaurantes_docs = []
    for ubicacion in UBICACIONES_CR[:NUM_RESTAURANTES]:
        restaurantes_docs.append({
            "nombre_rest":  f"Restaurante {fake.last_name()}",
            "ubicacion":    ubicacion,
            "correo_rest":  fake.unique.email(),
            "telefono_rest": fake.numerify("2###-####"),
            "createdAt":    now,
            "updatedAt":    now,
        })

    rest_result = mongo_db["restaurantes"].insert_many(restaurantes_docs)
    rest_ids    = rest_result.inserted_ids
    print(f"  ✓ {len(rest_ids)} restaurantes")

    # ── Menús ─────────────────────────────────
    print("→ Insertando menús...")
    menus_docs = []
    for rest_id in rest_ids:
        for categoria in random.sample(CATEGORIAS_MENU, k=random.randint(3, 5)):
            menus_docs.append({
                "nombre_menu": categoria,
                "rest_id":     str(rest_id),
                "createdAt":   now,
                "updatedAt":   now,
            })

    menu_result = mongo_db["menus"].insert_many(menus_docs)
    menu_ids    = menu_result.inserted_ids
    menu_docs   = list(mongo_db["menus"].find({"_id": {"$in": menu_ids}}))
    print(f"  ✓ {len(menu_ids)} menús")

    # ── Platos ────────────────────────────────
    print("→ Insertando platos...")
    platos_docs = []
    for menu_doc in menu_docs:
        opciones = PLATOS_POR_CATEGORIA.get(menu_doc["nombre_menu"], [])
        for nombre_plato, precio_base in opciones:
            precio = precio_base + random.randint(-200, 500)
            platos_docs.append({
                "nombre_plato": nombre_plato,
                "precio":       precio,
                "menu_id":      str(menu_doc["_id"]),
                "descripcion":  fake.sentence(nb_words=8),
                "createdAt":    now,
                "updatedAt":    now,
            })

    plato_result = mongo_db["platos"].insert_many(platos_docs)
    plato_ids    = plato_result.inserted_ids
    print(f"  ✓ {len(plato_ids)} platos")

    # ── Mesas ─────────────────────────────────
    print("→ Insertando mesas...")
    mesas_docs = []
    for rest_id in rest_ids:
        for num in range(1, random.randint(6, 12) + 1):
            mesas_docs.append({
                "rest_id":     str(rest_id),
                "numero_mesa": num,
                "capacidad":   random.choice([2, 4, 4, 6, 8]),
                "disponible":  True,
                "createdAt":   now,
                "updatedAt":   now,
            })

    mesa_result = mongo_db["mesas"].insert_many(mesas_docs)
    mesa_ids    = mesa_result.inserted_ids
    print(f"  ✓ {len(mesa_ids)} mesas")

    # ── Usuarios (solo IDs, viven en Keycloak) ─
    user_ids = [str(uuid.uuid4()) for _ in range(NUM_USUARIOS)]
    print(f"  ✓ {NUM_USUARIOS} IDs de usuarios generados")

    # ── Reservaciones ─────────────────────────
    print("→ Insertando reservaciones...")
    reservaciones_docs = []
    for _ in range(NUM_RESERVACIONES):
        estado = random.choices(ESTADOS_RESERVACION, weights=[20, 60, 20])[0]
        reservaciones_docs.append({
            "usuario_id":      random.choice(user_ids),
            "mesa_id":         str(random.choice(mesa_ids)),
            "dia_reservacion": random_date().isoformat(),
            "hora_reservacion": random_time().strftime("%H:%M"),
            "estado":          estado,
            "createdAt":       now,
            "updatedAt":       now,
        })

    res_result = mongo_db["reservaciones"].insert_many(reservaciones_docs)
    res_docs   = list(mongo_db["reservaciones"].find({
        "_id":    {"$in": res_result.inserted_ids},
        "estado": "completada"
    }))
    res_ids_completadas = [str(d["_id"]) for d in res_docs]
    print(f"  ✓ {NUM_RESERVACIONES} reservaciones ({len(res_ids_completadas)} completadas)")

    # ── Pedidos ───────────────────────────────
    print("→ Insertando pedidos...")
    pedidos_docs = []
    for _ in range(NUM_PEDIDOS):
        tiene_reservacion = random.random() < 0.45 and res_ids_completadas
        reservacion_id    = random.choice(res_ids_completadas) if tiene_reservacion else None
        estado            = random.choices(ESTADOS_PEDIDO, weights=[10, 15, 20, 15, 25, 15])[0]

        platos_sel = random.sample(list(plato_ids), k=random.randint(1, 4))
        items = [
            {"plato_id": str(p), "cantidad": random.randint(1, 3)}
            for p in platos_sel
        ]

        pedidos_docs.append({
            "usuario_id":     random.choice(user_ids),
            "reservacion_id": reservacion_id,
            "tipo_pedido":    random.choice(TIPOS_PEDIDO),
            "fecha_orden":    random_date().isoformat(),
            "estado":         estado,
            "items":          items,
            "createdAt":      now,
            "updatedAt":      now,
        })

    mongo_db["pedidos"].insert_many(pedidos_docs)
    print(f"  ✓ {NUM_PEDIDOS} pedidos")

# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("  Seeder — Sistema de Restaurantes (MongoDB)")
    print("=" * 50)

    try:
        print(f"\nConectando a {MONGO_URI} → DB: {MONGO_DB}")
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        mongo_client.server_info()
        print("Conexión exitosa.\n")

        mongo_db = mongo_client[MONGO_DB]
        seed_mongo(mongo_db)
        mongo_client.close()

        print("\n✓ Seeding completado.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("Verificá que tu contenedor de MongoDB esté corriendo en el puerto 27017.")