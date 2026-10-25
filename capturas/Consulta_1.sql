-- Ocupacion y Recaudacion por Funcion

-- Creacion del indice, necesario solo 1 vez
CREATE INDEX idx_boleto_funcion_cubriente
    ON boleto (id_funcion) INCLUDE (precio)
    WHERE estado <> 'anulado';

-- Analisis sin el indice de la consulta y el de unicidad
BEGIN;

DROP INDEX uq_boleto_funcion_asiento;
DROP INDEX idx_boleto_funcion_cubriente;

EXPLAIN (ANALYZE, BUFFERS)

SELECT ROUND(COUNT(b.id_boleto) * 100.0 / s.capacidad, 2) AS pct_ocupacion,
       COALESCE(SUM(b.precio), 0) AS ingresos
FROM funcion f
JOIN sala s ON s.id_sala = f.id_sala
LEFT JOIN boleto b ON b.id_funcion = f.id_funcion AND b.estado <> 'anulado'
WHERE f.id_funcion = 19
GROUP BY f.id_funcion, s.capacidad;

ROLLBACK;

-- Analisis con el indice
EXPLAIN (ANALYZE, BUFFERS)

SELECT ROUND(COUNT(b.id_boleto) * 100.0 / s.capacidad, 2) AS pct_ocupacion,
       COALESCE(SUM(b.precio), 0) AS ingresos
FROM funcion f
JOIN sala s ON s.id_sala = f.id_sala
LEFT JOIN boleto b ON b.id_funcion = f.id_funcion AND b.estado <> 'anulado'
WHERE f.id_funcion = 19
GROUP BY f.id_funcion, s.capacidad;