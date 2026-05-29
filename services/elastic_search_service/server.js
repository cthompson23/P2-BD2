require("dotenv").config();
const express = require("express");

const searchRoutes = require("./routes/search_routes");

const app = express();

app.use(express.json());

app.use("/", searchRoutes);

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`Search service corriendo en puerto ${PORT}`);
});