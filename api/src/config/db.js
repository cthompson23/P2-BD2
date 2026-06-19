let pool = null; // PostgreSQL
let mongoClient = null; // MongoDB
let mongoDb = null;

if (process.env.DB_TYPE === "postgres") {
    const { Pool } = require("pg");
    
    pool = new Pool({
        user: process.env.BD_USER,
        password: process.env.BD_PASSWORD,
        database: process.env.BD_DATABASE,
        host: process.env.BD_HOST,
        port: process.env.BD_PORT
    });
    
    console.log("Conectado a PostgreSQL");
    module.exports = pool;
} 
else if (process.env.DB_TYPE === "mongo") {
    const { MongoClient } = require("mongodb");
    
    const mongoUrl = process.env.MONGO_URL || "mongodb://localhost:27017";
    const mongoDbName = process.env.MONGO_DATABASE || "restaurantes_db";
    
    const getMongoClient = async () => {
        if (!mongoClient || !mongoClient.topology?.isConnected()) {
            mongoClient = new MongoClient(mongoUrl);
            await mongoClient.connect();
            console.log("Conectado a MongoDB");
        }
        return mongoClient;
    };
    
    const getDb = async () => {
        const client = await getMongoClient();
        return client.db(mongoDbName);
    };
    
    console.log("Usando MongoDB");
    module.exports = { getDb, getMongoClient };
}
else {
    throw new Error(`DB_TYPE no reconocido: ${process.env.DB_TYPE}`);
}