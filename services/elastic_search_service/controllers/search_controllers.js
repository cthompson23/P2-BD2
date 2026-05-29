const dao = require("../dao/search_elastic_dao.js");
const { dishes_dao } = require("../../../api/src/config/database_selector.js");
const client = require("../../../api/src/config/elastic.js");

exports.ping = async (req, res) => {
  try {
    const data = await dao.ping();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.searchDish = async (req, res) => {
  try {
    const result = await dao.search(req.query.q);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.reindex = async (req, res) => {
  try {
    const result = await dao.reindex();
     res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.searchByCategory = async (req, res) => {
  try {
    const result = await dao.searchByCategory(req.params.category);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};
