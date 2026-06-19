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
NUM_PEDIDOS       = 500
NUM_RESTAURANTES = 50

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
# NOMBRES DE RESTAURANTES
# ══════════════════════════════════════════════

PREFIJOS_RESTAURANTE = [
    "La", "El", "Los", "Las", "Casa", "Rincón", "Fogón", "Sabores de",
    "Cocina", "Rancho", "Patio", "Mar y", "Tierra y", "Don", "Doña",
]

SUFIJOS_RESTAURANTE = [
    "la Abuela", "los Andes", "la Costa", "Tradición", "del Pacífico",
    "Tico", "del Campo", "Herencia", "del Volcán", "Caribe",
    "la Montaña", "del Mar", "Sabroso", "Tropical", "del Valle",
    "Bendición", "los Sueños", "la Familia", "Auténtico", "Buenaventura",
]

NOMBRES_PROPIOS = [
    "Marisol", "Don Chico", "Lupita", "El Viejo Roble", "Tres Marías",
    "La Choza", "Rancho Alegre", "El Bohío", "Sabor Nuestro", "La Candela",
    "Donde Marta", "El Quincho", "La Tinaja", "Mar Adentro", "Tierra Viva",
    "El Copal", "La Iguana", "Punto y Coma", "El Zaguán", "La Fogata",
]

def generar_nombre_restaurante():
    estilo = random.choice(["prefijo_sufijo", "propio", "propio"])
    if estilo == "prefijo_sufijo":
        return f"{random.choice(PREFIJOS_RESTAURANTE)} {random.choice(SUFIJOS_RESTAURANTE)}"
    else:
        return random.choice(NOMBRES_PROPIOS)

# ══════════════════════════════════════════════
# DATOS DE REFERENCIA
# ══════════════════════════════════════════════

CATEGORIAS_MENU = [
    "Desayunos", "Almuerzos", "Cenas", "Postres", "Bebidas",
    "Entradas", "Ensaladas", "Sopas", "Mariscos", "Carnes", "Vegetariano",
]

PLATOS_POR_CATEGORIA = {
    "Desayunos": [
        ("Gallo pinto con huevo",           4500),
        ("Casado de desayuno",              5500),
        ("Pancakes con miel",               3800),
        ("Frutas con granola",              3200),
        ("Huevos benedictinos",             6200),
        ("Omelette de vegetales",           5000),
        ("Tostadas francesas",              4200),
        ("Burrito de desayuno",             5800),
        ("Avena con frutas tropicales",     3500),
        ("Waffles con fresas",              4800),
        ("Bagel con salmón ahumado",        7500),
        ("Wrap de huevo y tocino",          5200),
    ],
    "Almuerzos": [
        ("Casado de pollo",                 6500),
        ("Casado de res",                   7000),
        ("Casado vegetariano",              5800),
        ("Arroz con camarones",             8500),
        ("Casado de pescado frito",         7200),
        ("Pollo al curry con arroz",        7800),
        ("Chifrijo",                        5500),
        ("Tamal de pollo",                  4500),
        ("Arroz con pollo",                 6800),
        ("Sopa de mondongo",                6000),
        ("Casado de cerdo",                 6700),
        ("Burrito de frijoles y arroz",     5200),
        ("Plato de gallos mixtos",          5500),
        ("Caldo de res",                    6200),
    ],
    "Cenas": [
        ("Filete de tilapia",               9000),
        ("Lomo saltado",                    9500),
        ("Pasta alfredo",                   7500),
        ("Pollo a la plancha",              7000),
        ("Costillas BBQ",                  10500),
        ("Salmón en salsa de limón",       12000),
        ("Risotto de hongos",               8800),
        ("Pollo en salsa de mostaza",       8200),
        ("Filete de res en salsa de vino",  11000),
        ("Camarones al ajillo",             9800),
        ("Pechuga rellena de espinacas",    8500),
        ("Trucha al vapor",                 9200),
        ("Cordero con hierbas",            13000),
        ("Pulpo a la gallega",             11500),
    ],
    "Postres": [
        ("Tres leches",                     2500),
        ("Flan de coco",                    2200),
        ("Brownie con helado",              3000),
        ("Arroz con leche",                 1800),
        ("Cheesecake de maracuyá",          3500),
        ("Churros con chocolate",           2800),
        ("Tiramisu",                        3200),
        ("Crepes de nutella",               2900),
        ("Helado artesanal 3 bolas",        2600),
        ("Pastel de chocolate",             3400),
        ("Natilla con tamal",               2100),
        ("Panna cotta de vainilla",         3100),
        ("Gelatina de frutas tropicales",   1900),
        ("Waffles con dulce de leche",      3600),
    ],
    "Bebidas": [
        ("Refresco natural",                1500),
        ("Agua mineral",                     800),
        ("Café chorreado",                  1200),
        ("Jugo de naranja",                 1800),
        ("Horchata",                        1600),
        ("Agua de jamaica",                 1400),
        ("Limonada con hierbabuena",        1700),
        ("Batido de fresa",                 2200),
        ("Batido de mango",                 2200),
        ("Té frío de durazno",              1500),
        ("Agua de pipa",                    2000),
        ("Jugo verde detox",                2500),
        ("Chocolate caliente",              1900),
        ("Smoothie tropical",               2800),
        ("Cerveza artesanal",               3500),
        ("Kombucha de jengibre",            2600),
    ],
    "Entradas": [
        ("Ceviche de camarón",              5500),
        ("Patacones con guacamole",         3500),
        ("Ensalada César",                  4000),
        ("Sopa del día",                    3000),
        ("Tabla de quesos y embutidos",     6500),
        ("Alitas de pollo BBQ",             5200),
        ("Yuca frita con chimichurri",      3200),
        ("Bruschetta de tomate",            3800),
        ("Calamares fritos",                5800),
        ("Nachos con queso fundido",        4500),
        ("Rollitos de primavera",           4200),
        ("Tostones con frijoles",           3000),
        ("Carpaccio de res",                6000),
        ("Dip de espinaca con chips",       3700),
    ],
    "Ensaladas": [
        ("Ensalada griega",                 4500),
        ("Ensalada caprese",                4800),
        ("Ensalada de pollo y aguacate",    5500),
        ("Ensalada de atún",                4200),
        ("Ensalada de rúcula y pera",       5000),
        ("Ensalada waldorf",                4600),
        ("Ensalada tropical de palmito",    4900),
        ("Ensalada de quinoa",              5200),
        ("Ensalada niçoise",                5500),
        ("Ensalada de espinaca y fresas",   4700),
    ],
    "Sopas": [
        ("Sopa de tomate",                  3200),
        ("Crema de elote",                  3500),
        ("Consomé de pollo",                3000),
        ("Sopa de mariscos",                6500),
        ("Crema de zapallo",                3300),
        ("Sopa minestrone",                 3800),
        ("Caldo tlalpeño",                  4000),
        ("Sopa de lentejas",                3200),
        ("Bisque de langosta",              7500),
        ("Sopa de fideos",                  2800),
        ("Crema de champiñones",            3600),
    ],
    "Mariscos": [
        ("Ceviche mixto",                   8500),
        ("Langosta al ajillo",             15000),
        ("Camarones en salsa criolla",      9500),
        ("Pulpo en aceite de oliva",       11000),
        ("Tilapia entera frita",            8000),
        ("Corvina al vapor",                9800),
        ("Cangrejo en salsa de coco",      12000),
        ("Calamar en su tinta",             9200),
        ("Salmón a la mantequilla",        11500),
        ("Coctel de mariscos",              7500),
        ("Mariscos al grill",              13000),
        ("Paella de mariscos",             14000),
    ],
    "Carnes": [
        ("Churrasco 300g",                 12000),
        ("Lomo fino en salsa bordelesa",   14000),
        ("Punta de lomo al carbón",        11500),
        ("Costilla de cerdo ahumada",      10000),
        ("Picaña brasileña",               13000),
        ("Entrecot de res",                13500),
        ("Rack de cordero",                15000),
        ("Medallón de cerdo con manzana",   9500),
        ("Pollo entero a la brasa",        10500),
        ("Anticuchos de res",               6500),
        ("Hamburguesa gourmet 200g",        8500),
        ("Tacos de carnitas x3",            6000),
    ],
    "Vegetariano": [
        ("Curry de garbanzos",              6500),
        ("Hamburguesa de lentejas",         6000),
        ("Bowl de quinoa y vegetales",      6800),
        ("Tofu a la plancha con salsa de soya", 5500),
        ("Lasaña de vegetales",             7000),
        ("Falafel con hummus",              5800),
        ("Wrap de aguacate y frijoles",     5200),
        ("Pizza margarita vegetariana",     7500),
        ("Stir fry de vegetales y tofu",    6200),
        ("Tacos de champiñones y rajas",    5500),
        ("Enchiladas verdes vegetarianas",  6300),
        ("Buddha bowl",                     6900),
    ],
}

TIPOS_PEDIDO        = ["en sitio", "para llevar", "delivery"]
ESTADOS_PEDIDO      = ["pendiente", "confirmado", "en_preparacion", "listo", "entregado", "cancelado"]
ESTADOS_RESERVACION = ["activa", "completada", "cancelada"]

UBICACIONES_CR = [
    "San José Centro", "Escazú", "Santa Ana", "Heredia", "Alajuela",
    "Cartago", "Liberia", "Pérez Zeledón", "Limón", "Jacó",
    "Guanacaste", "Puntarenas", "Quepos", "Grecia", "Palmares",
    "Nicoya", "Tilaran", "Ciudad Quesada", "Turrialba", "Atenas",
    "Naranjo", "Orotina", "Sarchí", "Zarcero", "Paraíso",
    "Tres Ríos", "Curridabat", "Desamparados", "Aserrí", "Moravia",
    "Guadalupe", "San Pedro", "Los Yoses", "La Uruca", "Tibás",
    "Coronado", "San Pablo", "Barva", "Belén", "Flores",
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
            generar_nombre_restaurante(),
            random.choice(UBICACIONES_CR),
            fake.unique.email(),
            fake.numerify("2###-####"),
        )
        for _ in range(NUM_RESTAURANTES)
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
        for categoria in random.sample(CATEGORIAS_MENU, k=random.randint(5, 10)):
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