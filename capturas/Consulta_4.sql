-- Auditoria de Operaciones Criticas

-- Creacion del indice, necesario solo 1 vez
CREATE INDEX idx_audit_fecha
    ON admin_operacion_audit (fecha_hora)
    INCLUDE (id_usuario, accion, rol);

-- Analisis sin el indice de la consulta
BEGIN;

DROP INDEX idx_audit_fecha;

EXPLAIN (ANALYZE, BUFFERS)

SELECT id_usuario,
       COUNT(*) FILTER (WHERE accion = 'modificacion_manual') AS modificaciones_manuales,
       COUNT(*) FILTER (WHERE accion = 'cortesia_otorgada')   AS cortesias_otorgadas,
       COUNT(*) FILTER (WHERE accion = 'reembolso_forzado')   AS reembolsos_forzados
FROM admin_operacion_audit
WHERE rol = 'administrador'
  AND accion IN ('modificacion_manual', 'cortesia_otorgada', 'reembolso_forzado')
  AND fecha_hora >= LOCALTIMESTAMP - INTERVAL '1 month'
GROUP BY id_usuario
ORDER BY id_usuario ASC;

ROLLBACK;

-- Analisis con el indice
EXPLAIN (ANALYZE, BUFFERS)

SELECT id_usuario,
       COUNT(*) FILTER (WHERE accion = 'modificacion_manual') AS modificaciones_manuales,
       COUNT(*) FILTER (WHERE accion = 'cortesia_otorgada')   AS cortesias_otorgadas,
       COUNT(*) FILTER (WHERE accion = 'reembolso_forzado')   AS reembolsos_forzados
FROM admin_operacion_audit
WHERE rol = 'administrador'
  AND accion IN ('modificacion_manual', 'cortesia_otorgada', 'reembolso_forzado')
  AND fecha_hora >= LOCALTIMESTAMP - INTERVAL '1 month'
GROUP BY id_usuario
ORDER BY id_usuario ASC;