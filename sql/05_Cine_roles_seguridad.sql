SET search_path TO prototipo, public;

--- Cifrado de contraseñas con la extensión pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;
UPDATE usuario
SET contrasena = crypt(contrasena, gen_salt('bf'))
WHERE contrasena NOT LIKE '$2%';

--- Inicio de sesión por usuario y contraseña
CREATE OR REPLACE FUNCTION fn_iniciar_sesion(p_correo VARCHAR, p_contrasena VARCHAR)
RETURNS TABLE (id_usuario INT, rol VARCHAR, nombre VARCHAR) AS $$
BEGIN
    RETURN QUERY
    SELECT u.id_usuario, u.rol, (u.primer_nombre || ' ' || u.primer_apellido)::VARCHAR
    FROM usuario u
    WHERE u.correo = p_correo
      AND u.activo
      AND u.contrasena = crypt(p_contrasena, u.contrasena);
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Correo o contraseña incorrectos';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Registrar usuarios
CREATE OR REPLACE FUNCTION fn_registrar_usuario(p_primer_nombre VARCHAR, p_primer_apellido VARCHAR, p_segundo_apellido VARCHAR, p_correo VARCHAR, p_contrasena VARCHAR, p_rol VARCHAR, p_id_admin INT)
RETURNS INT AS $$
DECLARE
    v_rol_admin  VARCHAR(20);
    v_id_usuario INT;
BEGIN
    IF p_rol <> 'cliente' THEN
        SELECT rol INTO v_rol_admin FROM usuario WHERE id_usuario = p_id_admin AND activo;
        IF v_rol_admin IS NULL OR v_rol_admin <> 'administrador' THEN
            RAISE EXCEPTION 'Solo un administrador puede crear usuarios de personal';
        END IF;
    END IF;
    IF length(p_contrasena) < 8 THEN
        RAISE EXCEPTION 'La contraseña debe tener al menos 8 caracteres';
    END IF;
    BEGIN
        INSERT INTO usuario (primer_nombre, primer_apellido, segundo_apellido, correo, contrasena, rol)
        VALUES (p_primer_nombre, p_primer_apellido, p_segundo_apellido, p_correo, crypt(p_contrasena, gen_salt('bf')), p_rol)
        RETURNING id_usuario INTO v_id_usuario;
    EXCEPTION
        WHEN unique_violation THEN
            RAISE EXCEPTION 'Ya existe un usuario con el correo %', p_correo;
    END;
    IF p_rol <> 'cliente' THEN
        INSERT INTO admin_operacion_audit (accion, tabla_afectada, id_registro_afectado, detalle, rol, id_usuario)
        VALUES ('crear_usuario', 'usuario', v_id_usuario, 'Crea usuario ' || p_correo || ' con rol ' || p_rol, v_rol_admin, p_id_admin);
    END IF;
    RETURN v_id_usuario;
END;
$$ LANGUAGE plpgsql;

--- Verificar las ventas y reservas en una sala
CREATE OR REPLACE FUNCTION fn_sala_tiene_ventas(p_id_sala INT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (SELECT 1
                   FROM funcion f
                   JOIN boleto b ON b.id_funcion = f.id_funcion
                   WHERE f.id_sala = p_id_sala AND f.estado = 'programada'
                    AND f.fecha_hora_inicio > NOW() AND b.estado <> 'anulado')
        OR EXISTS (SELECT 1
                   FROM funcion f
                   JOIN bloqueo_asiento bl ON bl.id_funcion = f.id_funcion
                   WHERE f.id_sala = p_id_sala AND f.estado = 'programada'
                    AND f.fecha_hora_inicio > NOW() AND bl.estado = 'activo');
END;
$$ LANGUAGE plpgsql;


--- Mapa de asientos en una saña
CREATE OR REPLACE VIEW vista_estado_asientos AS
SELECT f.id_funcion, a.id_asiento, a.fila, a.numero, a.zona,
       CASE
           WHEN EXISTS (SELECT 1 FROM boleto b
                        WHERE b.id_funcion = f.id_funcion AND b.id_asiento = a.id_asiento
                          AND b.estado <> 'anulado') THEN 'ocupado'
           WHEN EXISTS (SELECT 1 FROM bloqueo_asiento bl
                        WHERE bl.id_funcion = f.id_funcion AND bl.id_asiento = a.id_asiento
                          AND bl.estado = 'activo' AND bl.fecha_hora_expira > NOW()) THEN 'bloqueado'
           ELSE 'disponible'
       END AS estado
FROM funcion f
JOIN asiento a ON a.id_sala = f.id_sala;

--- Ejecución de las funciones según los roles asiganados
ALTER FUNCTION fn_liberar_bloqueos_expirados() SECURITY DEFINER SET search_path = prototipo, public;
ALTER FUNCTION fn_bloquear_asiento(INT, INT, INT) SECURITY DEFINER SET search_path = prototipo, public;
ALTER FUNCTION fn_liberar_asiento(INT, INT) SECURITY DEFINER SET search_path = prototipo, public;
ALTER FUNCTION fn_generar_codigo_qr(INT, INT, VARCHAR) SECURITY DEFINER SET search_path = prototipo, public;
ALTER FUNCTION fn_procesar_compra(INT, INT, VARCHAR, VARCHAR, BOOLEAN, INT[], VARCHAR[]) SECURITY DEFINER SET search_path = prototipo, public;
ALTER FUNCTION fn_validar_acceso(VARCHAR, INT, VARCHAR) SECURITY DEFINER SET search_path = prototipo, public;
ALTER FUNCTION fn_ejecutar_reembolso(INT) SECURITY DEFINER SET search_path = prototipo, public;
ALTER FUNCTION fn_anular_boleto(INT, INT) SECURITY DEFINER SET search_path = prototipo, public;
ALTER FUNCTION fn_reembolso_forzado(INT, INT, TEXT, VARCHAR) SECURITY DEFINER SET search_path = prototipo, public;
ALTER FUNCTION fn_programar_funcion(INT, INT, TIMESTAMP, INT, VARCHAR) SECURITY DEFINER SET search_path = prototipo, public;
ALTER FUNCTION fn_iniciar_sesion(VARCHAR, VARCHAR) SECURITY DEFINER SET search_path = prototipo, public;
ALTER FUNCTION fn_registrar_usuario(VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, INT) SECURITY DEFINER SET search_path = prototipo, public;
ALTER FUNCTION fn_sala_tiene_ventas(INT) SECURITY DEFINER SET search_path = prototipo, public;

--- Permisos por roles
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rol_cliente') THEN
        CREATE ROLE rol_cliente NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rol_taquillero') THEN
        CREATE ROLE rol_taquillero NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rol_operador_sala') THEN
        CREATE ROLE rol_operador_sala NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rol_contador') THEN
        CREATE ROLE rol_contador NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rol_administrador') THEN
        CREATE ROLE rol_administrador NOLOGIN;
    END IF;
    -- Usuario para conectarse con la app
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'creador') THEN
        CREATE ROLE creador LOGIN NOINHERIT PASSWORD 'ProyectoCine2026';
    END IF;
END;
$$;

GRANT rol_cliente, rol_taquillero, rol_operador_sala, rol_contador, rol_administrador TO creador;

REVOKE ALL ON ALL TABLES IN SCHEMA prototipo FROM PUBLIC;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA prototipo FROM PUBLIC;

GRANT USAGE ON SCHEMA prototipo TO creador, rol_cliente, rol_taquillero, rol_operador_sala, rol_contador, rol_administrador;

GRANT EXECUTE ON FUNCTION fn_iniciar_sesion(VARCHAR, VARCHAR) TO creador;
GRANT EXECUTE ON FUNCTION fn_registrar_usuario(VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, INT) TO creador;

--- Accesos a la cartelera
GRANT SELECT ON cine, sala, asiento, pelicula, pelicula_generos, funcion, tarifa
    TO rol_cliente, rol_taquillero, rol_operador_sala, rol_contador, rol_administrador;

--- Acceso de clientes a sus compras
GRANT SELECT ON vista_estado_asientos, compra, boleto TO rol_cliente;
GRANT EXECUTE ON FUNCTION fn_liberar_bloqueos_expirados(), fn_bloquear_asiento(INT, INT, INT),
    fn_liberar_asiento(INT, INT), fn_procesar_compra(INT, INT, VARCHAR, VARCHAR, BOOLEAN, INT[], VARCHAR[]),
    fn_anular_boleto(INT, INT)
    TO rol_cliente;

-- Accesos del taquillero a registrar clientes y verificar sus ventas
GRANT SELECT ON vista_estado_asientos, compra, boleto TO rol_taquillero;
GRANT EXECUTE ON FUNCTION fn_liberar_bloqueos_expirados(), fn_bloquear_asiento(INT, INT, INT),
    fn_liberar_asiento(INT, INT), fn_procesar_compra(INT, INT, VARCHAR, VARCHAR, BOOLEAN, INT[], VARCHAR[]),
    fn_registrar_usuario(VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, INT)
    TO rol_taquillero;

--- Accesos del operador de sala
GRANT EXECUTE ON FUNCTION fn_validar_acceso(VARCHAR, INT, VARCHAR) TO rol_operador_sala;

--- Accesos del contador a la información financiera
GRANT SELECT ON compra, compra_promociones, pago, boleto, transaccion_log TO rol_contador;

--- Accesos completos del administrador
GRANT SELECT ON ALL TABLES IN SCHEMA prototipo TO rol_administrador;
GRANT INSERT, UPDATE, DELETE ON cine, sala, asiento, pelicula, pelicula_generos, tarifa TO rol_administrador;
GRANT UPDATE (estado) ON funcion TO rol_administrador;
GRANT INSERT ON admin_operacion_audit TO rol_administrador;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA prototipo TO rol_administrador;
GRANT EXECUTE ON FUNCTION fn_programar_funcion(INT, INT, TIMESTAMP, INT, VARCHAR),
    fn_reembolso_forzado(INT, INT, TEXT, VARCHAR),
    fn_registrar_usuario(VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, INT),
    fn_liberar_bloqueos_expirados(),
    fn_sala_tiene_ventas(INT)
    TO rol_administrador;

--- Políticas para la seguridad de las compras
ALTER TABLE compra ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pol_compra_cliente ON compra;
CREATE POLICY pol_compra_cliente ON compra FOR SELECT TO rol_cliente
    USING (id_usuario_cliente = NULLIF(current_setting('app.id_usuario', true), '')::INT);

DROP POLICY IF EXISTS pol_compra_taquillero ON compra;
CREATE POLICY pol_compra_taquillero ON compra FOR SELECT TO rol_taquillero
    USING (id_usuario_vendedor = NULLIF(current_setting('app.id_usuario', true), '')::INT);

DROP POLICY IF EXISTS pol_compra_todo ON compra;
CREATE POLICY pol_compra_todo ON compra FOR SELECT TO rol_contador, rol_administrador
    USING (true);

--- Políticas para la seguridad de los boletos
ALTER TABLE boleto ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pol_boleto_cliente ON boleto;
CREATE POLICY pol_boleto_cliente ON boleto FOR SELECT TO rol_cliente
    USING (id_compra IN (SELECT id_compra FROM compra
                         WHERE id_usuario_cliente = NULLIF(current_setting('app.id_usuario', true), '')::INT));

DROP POLICY IF EXISTS pol_boleto_taquillero ON boleto;
CREATE POLICY pol_boleto_taquillero ON boleto FOR SELECT TO rol_taquillero
    USING (id_compra IN (SELECT id_compra FROM compra
                         WHERE id_usuario_vendedor = NULLIF(current_setting('app.id_usuario', true), '')::INT));

DROP POLICY IF EXISTS pol_boleto_todo ON boleto;
CREATE POLICY pol_boleto_todo ON boleto FOR SELECT TO rol_contador, rol_administrador
    USING (true);

--- Políticas para mantener la integridad de las salas
ALTER TABLE sala ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pol_sala_lectura ON sala;
CREATE POLICY pol_sala_lectura ON sala FOR SELECT USING (true);

DROP POLICY IF EXISTS pol_sala_insertar ON sala;
CREATE POLICY pol_sala_insertar ON sala FOR INSERT TO rol_administrador WITH CHECK (true);

DROP POLICY IF EXISTS pol_sala_modificar ON sala;
CREATE POLICY pol_sala_modificar ON sala FOR UPDATE TO rol_administrador
    USING (NOT fn_sala_tiene_ventas(id_sala));

DROP POLICY IF EXISTS pol_sala_eliminar ON sala;
CREATE POLICY pol_sala_eliminar ON sala FOR DELETE TO rol_administrador
    USING (NOT fn_sala_tiene_ventas(id_sala));

ALTER TABLE asiento ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pol_asiento_lectura ON asiento;
CREATE POLICY pol_asiento_lectura ON asiento FOR SELECT USING (true);

DROP POLICY IF EXISTS pol_asiento_insertar ON asiento;
CREATE POLICY pol_asiento_insertar ON asiento FOR INSERT TO rol_administrador
    WITH CHECK (NOT fn_sala_tiene_ventas(id_sala));

DROP POLICY IF EXISTS pol_asiento_modificar ON asiento;
CREATE POLICY pol_asiento_modificar ON asiento FOR UPDATE TO rol_administrador
    USING (NOT fn_sala_tiene_ventas(id_sala));

DROP POLICY IF EXISTS pol_asiento_eliminar ON asiento;
CREATE POLICY pol_asiento_eliminar ON asiento FOR DELETE TO rol_administrador
    USING (NOT fn_sala_tiene_ventas(id_sala));
