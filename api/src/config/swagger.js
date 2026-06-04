const swaggerJsdoc = require("swagger-jsdoc");

const options = {
  definition: {
    openapi: "3.0.0",
    info: {
      title: "Restaurant API",
      version: "1.0.0",
      description: "API para gestión de restaurantes, menús y reservaciones"
    },
    servers: [
      {
        url: "http://localhost:5001/api"
      }
    ],
    components: {
      securitySchemes: {
        bearerAuth: {
          type: "http",
          scheme: "bearer",
          bearerFormat: "JWT"
        }
      }
    },
    security: [
      {
        bearerAuth: []
      }
    ]
  },
  apis: ["./api/src/routes/*.js"] 
};

const swaggerSpec = swaggerJsdoc(options);

module.exports = swaggerSpec;