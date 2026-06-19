--Ingresoss por mes y categoria
SELECT
    anio,
    nombre_mes,
    mes,
    ingresos_total,
    total_pedidos
FROM estrella.cubo_ventas_por_tiempo
ORDER BY anio, mes

--Actividad de clientes por zona geográfica
SELECT
    restaurante,
    ubicacion,
    total_pedidos,
    ingresos_total,
    ticket_promedio
FROM estrella.cubo_ventas_por_ubicacion
ORDER BY ingresos_total DESC

--Pedidos completados y cancelados
SELECT
    anio,
    nombre_mes,
    mes,
    SUM(completadas) AS completadas,
    SUM(canceladas) AS canceladas,
    SUM(total_reservaciones) AS total_reservaciones,
    ROUND(SUM(completadas) * 100.0 / SUM(total_reservaciones), 2) AS tasa_completadas_pct
FROM estrella.cubo_reservaciones_por_tiempo
GROUP BY anio, nombre_mes, mes
ORDER BY anio, mes