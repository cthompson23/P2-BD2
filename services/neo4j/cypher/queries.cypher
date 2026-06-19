// ═══════════════════════════════════════════════════════════════════════════
// ANÁLISIS DE GRAFOS Y RUTAS — CONSULTAS CYPHER
// ═══════════════════════════════════════════════════════════════════════════


// ─────────────────────────────────────────────────────────────────────────────
// 1. LOS 5 PRODUCTOS MÁS COMPRADOS JUNTOS (CO-COMPRA)
// ─────────────────────────────────────────────────────────────────────────────
// Encuentra pares de platos que aparecen juntos en el mismo pedido más frecuentemente.

MATCH (pe:Pedido)-[:CONTIENE]->(p1:Plato)
MATCH (pe)-[:CONTIENE]->(p2:Plato)
WHERE p1.id < p2.id  // evita duplicados (A,B) y (B,A)
WITH p1.nombre AS plato1, p2.nombre AS plato2, count(DISTINCT pe) AS veces_juntos
RETURN plato1, plato2, veces_juntos
ORDER BY veces_juntos DESC
LIMIT 5;


// ─────────────────────────────────────────────────────────────────────────────
// 2. USUARIOS QUE RECOMIENDAN A OTROS (INFLUENCERS)
// ─────────────────────────────────────────────────────────────────────────────
// 2a. Lista simple de quién recomienda a quién

MATCH (u1:Usuario)-[r:RECOMIENDA]->(u2:Usuario)
RETURN u1.nombre AS recomienda, u2.nombre AS recomendado, r.afinidad AS afinidad
ORDER BY r.afinidad DESC;

// 2b. Usuarios más influyentes (más recomendados por otros = mayor in-degree)

MATCH (u:Usuario)<-[:RECOMIENDA]-(otro:Usuario)
RETURN u.nombre AS usuario, count(otro) AS veces_recomendado
ORDER BY veces_recomendado DESC
LIMIT 10;

// 2c. Usuarios que más recomiendan (mayor out-degree) — "embajadores"

MATCH (u:Usuario)-[:RECOMIENDA]->(otro:Usuario)
RETURN u.nombre AS usuario, count(otro) AS veces_que_recomienda
ORDER BY veces_que_recomienda DESC
LIMIT 10;


// ─────────────────────────────────────────────────────────────────────────────
// 3. CAMINOS MÍNIMOS ENTRE UBICACIONES (PARA REPARTO EFICIENTE)
// ─────────────────────────────────────────────────────────────────────────────
// 3a. Camino más corto entre dos restaurantes específicos (usando CERCA_DE)
//     Reemplazar los nombres por los restaurantes que quieras consultar.

MATCH (origen:Restaurante {nombre: "Mar y Tropical"}),
      (destino:Restaurante {nombre: "Donde Marta"})
MATCH path = shortestPath(
    (origen)-[:CERCA_DE*]-(destino)
)
RETURN [n IN nodes(path) | n.nombre] AS ruta,
       reduce(dist = 0.0, r IN relationships(path) | dist + r.distancia_km) AS distancia_total_km;

// 3b. Todos los restaurantes alcanzables desde uno dado, con su distancia mínima

MATCH (origen:Restaurante {nombre: "Mar y Tropical"})
MATCH (destino:Restaurante)
WHERE destino <> origen
MATCH path = shortestPath((origen)-[:CERCA_DE*]-(destino))
RETURN destino.nombre AS restaurante,
       reduce(dist = 0.0, r IN relationships(path) | dist + r.distancia_km) AS distancia_km
ORDER BY distancia_km ASC;


// ─────────────────────────────────────────────────────────────────────────────
// 4. RUTAS DE ENTREGA OPTIMIZADAS POR REPARTIDOR
// ─────────────────────────────────────────────────────────────────────────────
// 4a. Ver la ruta completa de un repartidor (orden de entregas asignadas
//     por la heurística de vecino más cercano, ya guardada en el grafo)

MATCH (r:Repartidor {id: "REP-001"})-[e:ENTREGA]->(pe:Pedido)<-[:HIZO]-(u:Usuario)
RETURN r.nombre AS repartidor,
       e.orden AS orden_entrega,
       pe.id AS pedido,
       u.nombre AS cliente,
       u.lat AS lat_cliente,
       u.lon AS lon_cliente,
       e.distancia_km AS distancia_km
ORDER BY e.orden;

// 4b. Resumen de carga de trabajo por repartidor (cuántas entregas y distancia total)

MATCH (r:Repartidor)-[e:ENTREGA]->(pe:Pedido)
RETURN r.nombre AS repartidor,
       count(pe) AS total_entregas,
       round(sum(e.distancia_km), 2) AS distancia_total_km,
       round(avg(e.distancia_km), 2) AS distancia_promedio_km
ORDER BY total_entregas DESC;

// 4c. Todas las asignaciones repartidor → pedido → cliente (vista completa)

MATCH (r:Repartidor)-[e:ENTREGA]->(pe:Pedido)<-[:HIZO]-(u:Usuario)
RETURN r.nombre AS repartidor, pe.id AS pedido, u.nombre AS cliente,
       e.distancia_km AS distancia_km, e.orden AS orden
ORDER BY r.nombre, e.orden;

// 4d. Encontrar el repartidor más cercano a un pedido NUEVO (simulación on-demand)
//     Útil para asignar en tiempo real sin re-correr todo el script.
//     Reemplazar lat/lon por la ubicación real del nuevo pedido.

MATCH (r:Repartidor)
WITH r, point({latitude: r.lat, longitude: r.lon}) AS pos_repartidor,
     point({latitude: 9.93, longitude: -84.08}) AS pos_pedido   // ejemplo: San José centro
RETURN r.nombre AS repartidor,
       round(point.distance(pos_repartidor, pos_pedido) / 1000, 2) AS distancia_km
ORDER BY distancia_km ASC
LIMIT 1;
