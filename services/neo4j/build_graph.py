"""
Construcción del grafo de Neo4j a partir de los datos de MongoDB.

Modela:
    Usuario     -[:HIZO]->                  Pedido
    Pedido      -[:CONTIENE {cantidad}]->   Plato
    Plato       -[:PERTENECE_A]->           Restaurante   (vía menú)
    Usuario     -[:RECOMIENDA]->            Usuario       (simulado)
    Restaurante -[:CERCA_DE {distancia_km}]-> Restaurante (Haversine)
    Repartidor  -[:ENTREGA]->                Pedido       (asignado por vecino más cercano)

Requisitos:
    pip install pymongo neo4j --break-system-packages

Uso:
    python build_graph.py
"""

import random
import math
from pymongo import MongoClient
from neo4j import GraphDatabase

# ── Configuración ──────────────────────────────────────────────────────────────
MONGO_URI = "mongodb://localhost:27017"
MONGO_DB  = "restaurantes_db"

NEO4J_URI  = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "restaurantes123"

# Bounding box aproximado de Costa Rica (para coordenadas simuladas)
CR_LAT_MIN, CR_LAT_MAX = 8.0, 11.2
CR_LON_MIN, CR_LON_MAX = -85.9, -82.6

N_REPARTIDORES = 8

random.seed(42)  # reproducibilidad


def haversine(lat1, lon1, lat2, lon2):
    """Distancia en km entre dos coordenadas geográficas."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def main():
    print("Conectando a MongoDB...")
    mongo = MongoClient(MONGO_URI)
    db = mongo[MONGO_DB]

    usuarios_doc      = list(db["usuarios"].find())
    restaurantes_doc  = list(db["restaurantes"].find())
    menus_doc         = list(db["menus"].find())
    platos_doc        = list(db["platos"].find())
    pedidos_doc       = list(db["pedidos"].find())

    print(f"  usuarios: {len(usuarios_doc)} | restaurantes: {len(restaurantes_doc)} | "
          f"menus: {len(menus_doc)} | platos: {len(platos_doc)} | pedidos: {len(pedidos_doc)}")

    # Mapear menu_id -> rest_id para poder vincular plato -> restaurante
    menu_to_rest = {str(m["_id"]): str(m["rest_id"]) for m in menus_doc}

    print("\nConectando a Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    with driver.session() as session:
        print("Limpiando grafo anterior...")
        session.run("MATCH (n) DETACH DELETE n")

        print("Creando constraints...")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:Usuario) REQUIRE u.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Plato) REQUIRE p.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:Restaurante) REQUIRE r.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (pe:Pedido) REQUIRE pe.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (re:Repartidor) REQUIRE re.id IS UNIQUE")

        # ── Restaurantes (con coordenadas simuladas dentro de Costa Rica) ──────────
        print(f"Creando {len(restaurantes_doc)} restaurantes...")
        for r in restaurantes_doc:
            lat = random.uniform(CR_LAT_MIN, CR_LAT_MAX)
            lon = random.uniform(CR_LON_MIN, CR_LON_MAX)
            session.run("""
                CREATE (r:Restaurante {
                    id: $id, nombre: $nombre, ubicacion: $ubicacion,
                    lat: $lat, lon: $lon
                })
            """, id=str(r["_id"]), nombre=r.get("nombre_rest"),
                 ubicacion=r.get("ubicacion"), lat=lat, lon=lon)

        # ── Usuarios (creados a partir de los IDs reales usados en pedidos) ─────────
        usuarios_reales = {u.get("id"): u for u in usuarios_doc if u.get("id")}
        usuario_ids_en_pedidos = sorted({p.get("usuario_id") for p in pedidos_doc if p.get("usuario_id")})

        print(f"Creando {len(usuario_ids_en_pedidos)} usuarios (a partir de pedidos; "
              f"{len(usuarios_reales)} con datos reales, resto simulados)...")
        for uid in usuario_ids_en_pedidos:
            lat = random.uniform(CR_LAT_MIN, CR_LAT_MAX)
            lon = random.uniform(CR_LON_MIN, CR_LON_MAX)
            datos_reales = usuarios_reales.get(uid)
            nombre = datos_reales.get("nombre") if datos_reales else f"Usuario {uid[:8]}"
            email  = datos_reales.get("email") if datos_reales else None
            session.run("""
                CREATE (u:Usuario {id: $id, nombre: $nombre, email: $email, lat: $lat, lon: $lon})
            """, id=uid, nombre=nombre, email=email, lat=lat, lon=lon)

        # ── Platos (vinculados a su restaurante) ────────────────────────────────────
        print(f"Creando {len(platos_doc)} platos...")
        for p in platos_doc:
            rest_id = menu_to_rest.get(str(p.get("menu_id")))
            session.run("""
                MATCH (r:Restaurante {id: $rest_id})
                CREATE (pl:Plato {id: $id, nombre: $nombre, precio: $precio})
                CREATE (pl)-[:PERTENECE_A]->(r)
            """, id=str(p["_id"]), nombre=p.get("nombre_plato"),
                 precio=p.get("precio"), rest_id=rest_id)

        # ── Pedidos + relaciones HIZO y CONTIENE ────────────────────────────────────
        print(f"Creando {len(pedidos_doc)} pedidos y sus relaciones...")
        for ped in pedidos_doc:
            usuario_id = ped.get("usuario_id")
            session.run("""
                MATCH (u:Usuario {id: $usuario_id})
                CREATE (pe:Pedido {id: $id, fecha: $fecha, estado: $estado})
                CREATE (u)-[:HIZO]->(pe)
            """, id=str(ped["_id"]), usuario_id=usuario_id,
                 fecha=ped.get("fecha_orden"), estado=ped.get("estado"))

            for item in ped.get("items", []):
                session.run("""
                    MATCH (pe:Pedido {id: $pedido_id})
                    MATCH (pl:Plato {id: $plato_id})
                    CREATE (pe)-[:CONTIENE {cantidad: $cantidad}]->(pl)
                """, pedido_id=str(ped["_id"]), plato_id=item.get("plato_id"),
                     cantidad=item.get("cantidad", 1))

        # ── RECOMIENDA (simulado) ────────────────────────────────────────────────────
        # Regla: si dos usuarios pidieron al menos 2 platos en común, uno recomienda al otro
        print("Simulando relaciones RECOMIENDA entre usuarios...")
        usuario_ids = usuario_ids_en_pedidos
        n_usuarios = len(usuario_ids)

        if n_usuarios >= 2:
            # Con pocos usuarios de seed, generamos relaciones aleatorias plausibles
            n_recomendaciones = max(1, n_usuarios // 2)
            pares = set()
            intentos = 0
            while len(pares) < n_recomendaciones and intentos < n_usuarios * 5:
                a, b = random.sample(usuario_ids, 2)
                pares.add((a, b))
                intentos += 1

            for a, b in pares:
                peso = round(random.uniform(0.5, 1.0), 2)
                session.run("""
                    MATCH (u1:Usuario {id: $a}), (u2:Usuario {id: $b})
                    CREATE (u1)-[:RECOMIENDA {afinidad: $peso}]->(u2)
                """, a=a, b=b, peso=peso)
            print(f"  ✓ {len(pares)} relaciones RECOMIENDA creadas")

        # ── CERCA_DE entre restaurantes (distancia real via Haversine) ─────────────
        print("Calculando distancias entre restaurantes...")
        rest_coords = []
        result = session.run("MATCH (r:Restaurante) RETURN r.id AS id, r.lat AS lat, r.lon AS lon")
        for record in result:
            rest_coords.append((record["id"], record["lat"], record["lon"]))

        count_links = 0
        for i in range(len(rest_coords)):
            for j in range(i + 1, len(rest_coords)):
                id1, lat1, lon1 = rest_coords[i]
                id2, lat2, lon2 = rest_coords[j]
                dist = haversine(lat1, lon1, lat2, lon2)
                if dist <= 50:  # solo conectar restaurantes a menos de 50km (rutas razonables)
                    session.run("""
                        MATCH (r1:Restaurante {id: $id1}), (r2:Restaurante {id: $id2})
                        CREATE (r1)-[:CERCA_DE {distancia_km: $dist}]->(r2)
                        CREATE (r2)-[:CERCA_DE {distancia_km: $dist}]->(r1)
                    """, id1=id1, id2=id2, dist=round(dist, 2))
                    count_links += 2
        print(f"  ✓ {count_links} relaciones CERCA_DE creadas")

        # ── Repartidores (simulados con ubicación inicial) ──────────────────────────
        print(f"Creando {N_REPARTIDORES} repartidores...")
        repartidores = []
        for i in range(1, N_REPARTIDORES + 1):
            lat = random.uniform(CR_LAT_MIN, CR_LAT_MAX)
            lon = random.uniform(CR_LON_MIN, CR_LON_MAX)
            rid = f"REP-{i:03d}"
            session.run("""
                CREATE (r:Repartidor {id: $id, nombre: $nombre, lat: $lat, lon: $lon})
            """, id=rid, nombre=f"Repartidor {i}", lat=lat, lon=lon)
            repartidores.append((rid, lat, lon))
        print(f"  ✓ {len(repartidores)} repartidores creados")

        # ── Asignación de pedidos a repartidores (vecino más cercano) ──────────────
        # Heurística: cada pedido se asigna al repartidor cuya ubicación actual
        # está más cerca del usuario que hizo el pedido. La ubicación del
        # repartidor se actualiza después de cada entrega (simulación greedy).
        print("Asignando pedidos a repartidores (vecino más cercano)...")

        pedidos_con_usuario = []
        result = session.run("""
            MATCH (u:Usuario)-[:HIZO]->(pe:Pedido)
            RETURN pe.id AS pedido_id, u.lat AS lat, u.lon AS lon, pe.fecha AS fecha
            ORDER BY pe.fecha
        """)
        for record in result:
            pedidos_con_usuario.append({
                "pedido_id": record["pedido_id"],
                "lat": record["lat"],
                "lon": record["lon"],
                "fecha": record["fecha"]
            })

        # Estado mutable de posición actual de cada repartidor
        estado_repartidores = {rid: (lat, lon) for rid, lat, lon in repartidores}

        asignaciones = 0
        for pedido in pedidos_con_usuario:
            mejor_rep = None
            mejor_dist = float("inf")
            for rid, (rlat, rlon) in estado_repartidores.items():
                dist = haversine(rlat, rlon, pedido["lat"], pedido["lon"])
                if dist < mejor_dist:
                    mejor_dist = dist
                    mejor_rep = rid

            session.run("""
                MATCH (r:Repartidor {id: $rid}), (pe:Pedido {id: $pedido_id})
                CREATE (r)-[:ENTREGA {distancia_km: $dist, orden: $orden}]->(pe)
            """, rid=mejor_rep, pedido_id=pedido["pedido_id"],
                 dist=round(mejor_dist, 2), orden=asignaciones + 1)

            estado_repartidores[mejor_rep] = (pedido["lat"], pedido["lon"])
            asignaciones += 1

        print(f"  ✓ {asignaciones} pedidos asignados a repartidores")

    driver.close()
    mongo.close()
    print("\n✓ Grafo construido exitosamente.")


if __name__ == "__main__":
    main()