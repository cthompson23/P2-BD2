"""
Genera datos sintéticos para el proyecto de restaurantes.
Pobla PostgreSQL con datos coherentes.

Instalación de dependencias:
    pip install faker psycopg2-binary

Uso:
    python seed_data_postgres.py
"""

import random
import uuid
from datetime import date, timedelta, time
from faker import Faker
import psycopg2
from psycopg2.extras import execute_values

# ──────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────
PG_CONFIG = {
    "host":     "localhost",
    "port":     4001,
    "dbname":   "restaurantes_db",
    "user":     "postgres",
    "password": "postgres",
}

# ──────────────────────────────────────────────
# VOLUMEN DE DATOS
# ──────────────────────────────────────────────
NUM_USUARIOS      = 20
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
# SEEDER POSTGRESQL
# ══════════════════════════════════════════════

def seed_postgres(cur):

    # ── Limpiar tablas (orden inverso por FK) ─
    print("→ Limpiando tablas...")
    cur.execute("""
        TRUNCATE TABLE item_pedido, pedidos, reservaciones, mesas, platos, menus, usuarios, restaurantes
        RESTART IDENTITY CASCADE;
    """)

    # ── Restaurantes ──────────────────────────
    print("→ Insertando restaurantes...")
    restaurantes_data = [
        (
            f"Restaurante {fake.last_name()}",
            ubicacion,
            fake.unique.email(),
            fake.numerify("2###-####"),
        )
        for ubicacion in UBICACIONES_CR
    ]
    execute_values(cur, """
        INSERT INTO restaurantes (nombre_rest, ubicacion, correo_rest, telefono_rest)
        VALUES %s
    """, restaurantes_data)

    cur.execute("SELECT id FROM restaurantes ORDER BY id")
    rest_ids = [r[0] for r in cur.fetchall()]
    print(f"  ✓ {len(rest_ids)} restaurantes")

    # ── Menús ─────────────────────────────────
    print("→ Insertando menús...")
    menus_data = []
    for rest_id in rest_ids:
        for categoria in random.sample(CATEGORIAS_MENU, k=random.randint(3, 5)):
            menus_data.append((categoria, rest_id))

    execute_values(cur, """
        INSERT INTO menus (nombre_menu, rest_id)
        VALUES %s
    """, menus_data)

    cur.execute("SELECT id, nombre_menu FROM menus ORDER BY id")
    menus_rows = cur.fetchall()
    print(f"  ✓ {len(menus_rows)} menús")

    # ── Platos ────────────────────────────────
    print("→ Insertando platos...")
    platos_data = []
    for menu_id, nombre_menu in menus_rows:
        opciones = PLATOS_POR_CATEGORIA.get(nombre_menu, [])
        for nombre_plato, precio_base in opciones:
            precio = precio_base + random.randint(-200, 500)
            platos_data.append((
                nombre_plato,
                round(precio, 2),
                menu_id,
                fake.sentence(nb_words=8),
            ))

    execute_values(cur, """
        INSERT INTO platos (nombre_plato, precio, menu_id, descripcion)
        VALUES %s
    """, platos_data)

    cur.execute("SELECT id FROM platos ORDER BY id")
    plato_ids = [r[0] for r in cur.fetchall()]
    print(f"  ✓ {len(plato_ids)} platos")

    # ── Mesas ─────────────────────────────────
    print("→ Insertando mesas...")
    mesas_data = []
    for rest_id in rest_ids:
        for num in range(1, random.randint(6, 12) + 1):
            mesas_data.append((
                True,
                rest_id,
                num,
                random.choice([2, 4, 4, 6, 8]),
            ))

    execute_values(cur, """
        INSERT INTO mesas (disponible, rest_id, numero_mesa, capacidad)
        VALUES %s
    """, mesas_data)

    cur.execute("SELECT id FROM mesas ORDER BY id")
    mesa_ids = [r[0] for r in cur.fetchall()]
    print(f"  ✓ {len(mesa_ids)} mesas")

    # ── Usuarios ──────────────────────────────
    print("→ Insertando usuarios...")
    usuarios_data = []
    for _ in range(NUM_USUARIOS):
        usuarios_data.append((
            str(uuid.uuid4()),
            fake.user_name(),
            fake.first_name(),
            fake.last_name(),
            fake.unique.email(),
        ))

    execute_values(cur, """
        INSERT INTO usuarios (id, usuario, nombre, apellido, email)
        VALUES %s
    """, usuarios_data)

    user_ids = [u[0] for u in usuarios_data]
    print(f"  ✓ {len(user_ids)} usuarios")

    # ── Reservaciones ─────────────────────────
    print("→ Insertando reservaciones...")
    reservaciones_data = []
    for _ in range(NUM_RESERVACIONES):
        estado = random.choices(ESTADOS_RESERVACION, weights=[20, 60, 20])[0]
        reservaciones_data.append((
            random.choice(user_ids),
            random.choice(mesa_ids),
            random_date().isoformat(),
            random_time().strftime("%H:%M"),
            estado,
        ))

    execute_values(cur, """
        INSERT INTO reservaciones (usuario_id, mesa_id, dia_reservacion, hora_reservacion, estado)
        VALUES %s
    """, reservaciones_data)

    cur.execute("SELECT id FROM reservaciones WHERE estado = 'completada'")
    res_ids_completadas = [r[0] for r in cur.fetchall()]
    print(f"  ✓ {NUM_RESERVACIONES} reservaciones ({len(res_ids_completadas)} completadas)")

    # ── Pedidos + item_pedido ─────────────────
    print("→ Insertando pedidos e items...")
    pedidos_data = []
    for _ in range(NUM_PEDIDOS):
        tiene_reservacion = random.random() < 0.45 and res_ids_completadas
        reservacion_id    = random.choice(res_ids_completadas) if tiene_reservacion else None
        estado            = random.choices(ESTADOS_PEDIDO, weights=[10, 15, 20, 15, 25, 15])[0]

        pedidos_data.append((
            random.choice(user_ids),
            reservacion_id,
            random.choice(TIPOS_PEDIDO),
            random_date().isoformat(),
            estado,
        ))

    execute_values(cur, """
        INSERT INTO pedidos (usuario_id, reservacion_id, tipo_pedido, fecha_orden, estado)
        VALUES %s
    """, pedidos_data)

    cur.execute("SELECT id FROM pedidos ORDER BY id")
    pedido_ids = [r[0] for r in cur.fetchall()]

    # Items por pedido
    items_data = []
    for pedido_id in pedido_ids:
        platos_sel = random.sample(plato_ids, k=random.randint(1, 4))
        for plato_id in platos_sel:
            items_data.append((
                pedido_id,
                plato_id,
                random.randint(1, 3),
            ))

    execute_values(cur, """
        INSERT INTO item_pedido (pedido_id, plato_id, cantidad)
        VALUES %s
    """, items_data)

    print(f"  ✓ {NUM_PEDIDOS} pedidos ({len(items_data)} items)")


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("  Seeder — Sistema de Restaurantes (PostgreSQL)")
    print("=" * 50)

    try:
        print(f"\nConectando a PostgreSQL en {PG_CONFIG['host']}:{PG_CONFIG['port']}...")
        conn = psycopg2.connect(**PG_CONFIG)
        conn.autocommit = False
        cur = conn.cursor()
        print("Conexión exitosa.\n")

        seed_postgres(cur)

        conn.commit()
        cur.close()
        conn.close()

        print("\n✓ Seeding completado.")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("Verificá que tu contenedor de PostgreSQL esté corriendo y las credenciales sean correctas.")