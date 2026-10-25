-- Metodos de Pago Preferidos

-- Creacion del indice, necesario solo 1 vez
CREATE INDEX idx_pago_metodo_aprobado
    ON pago (metodo_pago)
    WHERE estado = 'aprobado';

-- Analisis sin el indice de la consulta
BEGIN;

DROP INDEX idx_pago_metodo_aprobado;

EXPLAIN (ANALYZE, BUFFERS)

SELECT metodo_pago,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS porcentaje
FROM pago
WHERE estado = 'aprobado'
GROUP BY metodo_pago
ORDER BY porcentaje DESC;

ROLLBACK;

-- Analisis con el indice
EXPLAIN (ANALYZE, BUFFERS)

SELECT metodo_pago,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS porcentaje
FROM pago
WHERE estado = 'aprobado'
GROUP BY metodo_pago
ORDER BY porcentaje DESC;