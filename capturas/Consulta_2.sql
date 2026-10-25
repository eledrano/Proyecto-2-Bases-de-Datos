-- Top de Funciones Mas Demandadas

-- Creacion del indice, necesario solo 1 vez
CREATE INDEX idx_boleto_fecha_emision
    ON boleto (fecha_emision) INCLUDE (id_funcion)
    WHERE estado <> 'anulado';

-- Analisis sin el indice de la consulta
BEGIN;

DROP INDEX idx_boleto_fecha_emision;

EXPLAIN (ANALYZE, BUFFERS)

SELECT p.titulo,
       COUNT(*) AS boletos_vendidos
FROM boleto b
JOIN funcion  f ON f.id_funcion  = b.id_funcion
JOIN pelicula p ON p.id_pelicula = f.id_pelicula
WHERE b.fecha_emision >= LOCALTIMESTAMP - INTERVAL '7 days'
  AND b.estado <> 'anulado'
GROUP BY p.id_pelicula, p.titulo
ORDER BY boletos_vendidos DESC
LIMIT 5;

ROLLBACK;

-- Analisis con el indice
EXPLAIN (ANALYZE, BUFFERS)

SELECT p.titulo,
       COUNT(*) AS boletos_vendidos
FROM boleto b
JOIN funcion  f ON f.id_funcion  = b.id_funcion
JOIN pelicula p ON p.id_pelicula = f.id_pelicula
WHERE b.fecha_emision >= LOCALTIMESTAMP - INTERVAL '7 days'
  AND b.estado <> 'anulado'
GROUP BY p.id_pelicula, p.titulo
ORDER BY boletos_vendidos DESC
LIMIT 5;