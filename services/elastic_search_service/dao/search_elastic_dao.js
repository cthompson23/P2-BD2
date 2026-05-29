const client = require("../../../api/src/config/elastic.js");
const { dishes_dao, menus_dao } = require("../../../api/src/config/database_selector.js");

exports.ping = async () => {
  const result = await client.info();
  return result.body || result;
};

// Búsqueda por nombre de plato
exports.search = async (q) => {
  const result = await client.search({
    index: "dishes",
    query: {
      match: { nombre_plato: q }
    }
  });

  return result.hits.hits.map(hit => {
    const dish = hit._source;
    return {
      ...dish,
      description: dish.description || "Producto sin descripción"
    };
  });
};

exports.reindex = async () => {
  try {
    // Borrar índice existente si hay
    try {
      await client.indices.delete({ index: "dishes" });
    } catch (error) {
      if (error.meta?.statusCode !== 404) {
        throw error;
      }
    }

    // Crear índice con mapping explícito para keyword en nombre_menu
    await client.indices.create({
      index: "dishes",
      mappings: {
        properties: {
          nombre_plato: { type: "text" },
          precio: { type: "float" },
          menu_id: { type: "keyword" },
          nombre_menu: { type: "keyword" }
        }
      }
    });

    // Obtener todos los platos y menús
    const dishes = await dishes_dao.getAll();
    const menus = await menus_dao.getAll();

    // Crear un mapa menu_id -> nombre_menu para enriquecer cada plato
    const menuMap = {};
    for (const menu of menus) {
      menuMap[menu.id.toString()] = menu.nombre_menu;
    }

    // Indexar cada plato con su nombre_menu incluido
    for (const dish of dishes) {
      const menu_id = dish.menu_id ? dish.menu_id.toString() : null;
      await client.index({
        index: "dishes",
        document: {
          id: dish.id,
          nombre_plato: dish.nombre_plato,
          precio: dish.precio,
          menu_id: menu_id,
          nombre_menu: menuMap[menu_id] || null,
          description: dish.description || "Producto sin descripción"
        }
      });
    }

    await client.indices.refresh({ index: "dishes" });

    return { message: "Reindexing completed", total: dishes.length };

  } catch (error) {
    throw error;
  }
};

// Búsqueda por categoría (nombre_menu exacto)
exports.searchByCategory = async (category) => {
  try {
    if (!category) {
      return { message: "Category parameter is required" };
    }

    const result = await client.search({
      index: "dishes",
      query: {
        term: {
          nombre_menu: category
        }
      }
    });

    const dishes = result.hits.hits.map(hit => ({ ...hit._source }));

    return { dishes };

  } catch (error) {
    throw error;
  }
};
