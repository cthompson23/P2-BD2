# Análisis de Grafos y Rutas con Neo4j

Modela la relación entre usuarios, productos, pedidos y restaurantes en un grafo, simula repartidores con geolocalización, e implementa consultas Cypher para co-compra, usuarios influyentes y caminos mínimos de reparto.

## Estructura

```
services/neo4j/
├── docker-compose_neo4j.yml
├── build_graph.py            ← construye el grafo desde MongoDB
└── consultas_cypher.cypher   ← queries de análisis y rutas
```

## Servicios

| Servicio | Imagen | Puerto |
|---|---|---|
| neo4j | neo4j:5.24 (+ plugin APOC) | 7474 (Browser), 7687 (Bolt) |

## Requisitos

- Docker Desktop instalado y corriendo
- MongoDB corriendo en `localhost:27017` con la base `restaurantes_db`
- Python en el host (no en contenedor) con:
  ```bash
  pip install pymongo neo4j --break-system-packages
  ```

## Levantar Neo4j

```bash
docker network create olap-network   # si no existe aún
docker compose -f docker-compose_neo4j.yml up -d
```

Esperar ~20 segundos y abrir **http://localhost:7474**.

**Login:** usuario `neo4j` / contraseña `restaurantes123`

## Construir el grafo

Desde la carpeta `services/neo4j/`, con MongoDB corriendo:

```bash
python build_graph.py
```

Esto limpia el grafo anterior y vuelve a construirlo desde cero. Correr cada vez que cambien los datos en MongoDB.

### Qué construye

| Nodo | Origen | Notas |
|---|---|---|
| `Usuario` | IDs reales encontrados en `pedidos.usuario_id` | La colección `usuarios` del seed está incompleta (solo 1 doc real) — los nodos se generan a partir de los IDs que aparecen efectivamente en los pedidos, enriquecidos con datos reales cuando existen |
| `Restaurante` | `restaurantes` | Coordenadas simuladas dentro de Costa Rica |
| `Plato` | `platos` | Vinculado a su restaurante vía `menus` |
| `Pedido` | `pedidos` | — |
| `Repartidor` | Simulado (8 repartidores) | Coordenadas simuladas dentro de Costa Rica |

| Relación | Significado |
|---|---|
| `(Usuario)-[:HIZO]->(Pedido)` | Quién hizo cada pedido |
| `(Pedido)-[:CONTIENE {cantidad}]->(Plato)` | Qué platos incluye cada pedido |
| `(Plato)-[:PERTENECE_A]->(Restaurante)` | A qué restaurante pertenece el plato |
| `(Usuario)-[:RECOMIENDA {afinidad}]->(Usuario)` | Simulado — relación de recomendación entre usuarios |
| `(Restaurante)-[:CERCA_DE {distancia_km}]->(Restaurante)` | Distancia real (Haversine) entre restaurantes a ≤50km |
| `(Repartidor)-[:ENTREGA {distancia_km, orden}]->(Pedido)` | Asignación por heurística de vecino más cercano |

### Heurística de asignación de repartidores

Cada pedido (ordenado por fecha) se asigna al repartidor que esté más cerca de la ubicación del cliente **en su posición actual**. Después de cada entrega, el repartidor "se mueve" a esa ubicación antes de evaluar el siguiente pedido — simula una ruta encadenada en lugar de reasignar siempre desde el punto de partida.

## Consultas Cypher

Abrir `consultas_cypher.cypher`, copiar cada bloque (separado por `;`) y pegarlo en Neo4j Browser.

| # | Consulta | Qué responde |
|---|---|---|
| 1 | Co-compra | Los 5 pares de platos más comprados juntos en el mismo pedido |
| 2a | Recomendaciones | Lista de quién recomienda a quién |
| 2b | Más recomendados | Usuarios más influyentes (mayor in-degree en `RECOMIENDA`) |
| 2c | Más recomendadores | Usuarios que más recomiendan a otros (mayor out-degree) |
| 3a | Camino mínimo directo | `shortestPath` entre dos restaurantes específicos |
| 3b | Camino mínimo (Dijkstra) | Vía APOC, pondera por `distancia_km` |
| 3c | Alcance desde un restaurante | Todos los restaurantes alcanzables y su distancia mínima |
| 4a | Ruta de un repartidor | Orden de entregas asignadas a un repartidor específico |
| 4b | Carga de trabajo | Total de entregas y distancia por repartidor |
| 4c | Vista completa | Todas las asignaciones repartidor → pedido → cliente |
| 4d | Asignación on-demand | Repartidor más cercano a una ubicación nueva (sin re-correr el script) |

### Nota sobre conectividad geográfica

Las coordenadas de restaurantes se simulan aleatoriamente dentro de todo Costa Rica, y `CERCA_DE` solo conecta pares a ≤50km. Esto puede dejar "islas" de restaurantes sin camino entre sí (normal con datos simulados dispersos). Para probar las queries de camino mínimo (3a, 3b), usar pares que ya tengan una relación `CERCA_DE` directa o indirecta:

```cypher
MATCH (a:Restaurante)-[r:CERCA_DE]->(b:Restaurante)
RETURN a.nombre, b.nombre, r.distancia_km
LIMIT 5
```

## Apagar Neo4j

```bash
docker compose -f docker-compose_neo4j.yml down
```

Para borrar también los datos del grafo:
```bash
docker compose -f docker-compose_neo4j.yml down -v
```