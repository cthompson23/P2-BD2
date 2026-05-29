const express = require("express");
const router = express.Router();
const controller = require("../controllers/search_controllers.js");

router.get("/ping", controller.ping);
router.get("/products", controller.searchDish);
router.get("/products/category/:category", controller.searchByCategory);
router.get("/reindex", controller.reindex);
module.exports = router;