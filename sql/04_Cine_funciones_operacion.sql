SET search_path TO prototipo;

--- Funciones de operación: validación en puerta, anulación y reembolsos, y programación de funciones
CREATE OR REPLACE FUNCTION fn_validar_acceso(p_codigo_qr VARCHAR, p_id_funcion INT, p_puerta VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    v_id_boleto      INT;
    v_estado         VARCHAR(10);
    v_funcion_boleto INT;
    v_inicio         TIMESTAMP;
    v_resultado      VARCHAR(20);
    v_mensaje        VARCHAR(60);
BEGIN
    SELECT id_boleto, estado, id_funcion INTO v_id_boleto, v_estado, v_funcion_boleto
    FROM boleto WHERE codigo_qr = p_codigo_qr;
    IF NOT FOUND THEN
        v_resultado := 'no_existe';
        v_mensaje   := 'Código no válido';
    ELSIF v_estado = 'anulado' THEN
        v_resultado := 'anulada';
        v_mensaje   := 'Entrada anulada';
    ELSIF v_funcion_boleto <> p_id_funcion THEN
        v_resultado := 'otra_funcion';
        v_mensaje   := 'La entrada corresponde a otra función';
    ELSIF v_estado = 'usado' THEN
        v_resultado := 'ya_utilizada';
        v_mensaje   := 'Entrada ya utilizada';

    ELSE
        SELECT fecha_hora_inicio INTO v_inicio FROM funcion WHERE id_funcion = v_funcion_boleto;
        IF NOW() < v_inicio - INTERVAL '30 minutes' OR NOW() > v_inicio + INTERVAL '15 minutes' THEN
            v_resultado := 'fuera_de_horario';
            v_mensaje   := 'Fuera del horario de ingreso';
        ELSE
            -- Con una lectura el boleto cambia a estado usado, aunque escanee 2 veces a la vez
            UPDATE boleto SET estado = 'usado' WHERE id_boleto = v_id_boleto AND estado = 'valido';
            IF FOUND THEN
                v_resultado := 'exitoso';
                v_mensaje   := 'Acceso permitido';
            ELSE
                v_resultado := 'ya_utilizada';
                v_mensaje   := 'Entrada ya utilizada';
            END IF;
        END IF;
    END IF;

    INSERT INTO acceso_puerta_log (codigo_leido, puerta, resultado, id_boleto)
    VALUES (p_codigo_qr, p_puerta, v_resultado, v_id_boleto);
    RETURN v_mensaje;
END;
$$ LANGUAGE plpgsql;

--- Realizar/ejecutar un reembolso
CREATE OR REPLACE FUNCTION fn_ejecutar_reembolso(p_id_boleto INT)
RETURNS NUMERIC AS $$
DECLARE
    v_precio    NUMERIC(10,2);
    v_id_compra INT;
    v_subtotal  NUMERIC(10,2);
    v_descuento NUMERIC(10,2);
    v_monto     NUMERIC(10,2);
    v_id_pago   INT;
BEGIN
    SELECT b.precio, b.id_compra, c.subtotal, c.descuento
    INTO v_precio, v_id_compra, v_subtotal, v_descuento
    FROM boleto b
    JOIN compra c ON c.id_compra = b.id_compra
    WHERE b.id_boleto = p_id_boleto;
    IF v_subtotal = 0 THEN
        v_monto := 0;
    ELSE
        v_monto := ROUND(v_precio * (v_subtotal - v_descuento) / v_subtotal, 2);
    END IF;
    UPDATE boleto
    SET estado = 'anulado', monto_reembolsado = v_monto, fecha_anulacion = NOW()
    WHERE id_boleto = p_id_boleto;

    SELECT id_pago INTO v_id_pago
    FROM pago WHERE id_compra = v_id_compra AND estado = 'aprobado';
    INSERT INTO transaccion_log (evento, monto, estado, id_pago)
    VALUES ('reembolso', v_monto, 'aprobado', v_id_pago);
    IF NOT EXISTS (SELECT 1 FROM boleto WHERE id_compra = v_id_compra AND estado <> 'anulado') THEN
        UPDATE compra SET estado = 'reembolsada' WHERE id_compra = v_id_compra;
    END IF;
    RETURN v_monto;
END;
$$ LANGUAGE plpgsql;

--- Cliente anula su boleto
CREATE OR REPLACE FUNCTION fn_anular_boleto(p_id_boleto INT, p_id_usuario INT)
RETURNS NUMERIC AS $$
DECLARE
    v_estado  VARCHAR(10);
    v_cliente INT;
    v_inicio  TIMESTAMP;
BEGIN
    SELECT b.estado, c.id_usuario_cliente, f.fecha_hora_inicio
    INTO v_estado, v_cliente, v_inicio
    FROM boleto b
    JOIN compra c  ON c.id_compra  = b.id_compra
    JOIN funcion f ON f.id_funcion = b.id_funcion
    WHERE b.id_boleto = p_id_boleto;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'El boleto % no existe', p_id_boleto;
    END IF;
    IF v_cliente <> p_id_usuario THEN
        RAISE EXCEPTION 'El boleto % no pertenece a este usuario', p_id_boleto;
    END IF;
    IF v_estado <> 'valido' THEN
        RAISE EXCEPTION 'Solo se pueden anular entradas sin usar (estado actual: %)', v_estado;
    END IF;
    IF NOW() > v_inicio - INTERVAL '2 hours' THEN
        RAISE EXCEPTION 'Solo se puede anular hasta 2 horas antes de la función';
    END IF;

    RETURN fn_ejecutar_reembolso(p_id_boleto);
END;
$$ LANGUAGE plpgsql;

--- El administrador hace un reembolso
CREATE OR REPLACE FUNCTION fn_reembolso_forzado(p_id_boleto INT, p_id_admin INT, p_motivo TEXT, p_direccion_ip VARCHAR)
RETURNS NUMERIC AS $$
DECLARE
    v_rol    VARCHAR(20);
    v_estado VARCHAR(10);
    v_monto  NUMERIC(10,2);
BEGIN
    SELECT rol INTO v_rol FROM usuario WHERE id_usuario = p_id_admin AND activo;
    IF v_rol IS NULL OR v_rol <> 'administrador' THEN
        RAISE EXCEPTION 'Solo un administrador puede hacer reembolsos forzados';
    END IF;
    IF p_motivo IS NULL OR p_motivo = '' THEN
        RAISE EXCEPTION 'Debe indicar el motivo del reembolso';
    END IF;

    SELECT estado INTO v_estado FROM boleto WHERE id_boleto = p_id_boleto;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'El boleto % no existe', p_id_boleto;
    END IF;
    IF v_estado = 'anulado' THEN
        RAISE EXCEPTION 'El boleto % ya fue anulado', p_id_boleto;
    END IF;
    v_monto := fn_ejecutar_reembolso(p_id_boleto);

    INSERT INTO admin_operacion_audit (accion, tabla_afectada, id_registro_afectado, detalle, rol, direccion_ip, id_usuario)
    VALUES ('reembolso_forzado', 'boleto', p_id_boleto, p_motivo || ' (monto reembolsado: ' || v_monto || ')',
            v_rol, p_direccion_ip, p_id_admin);
    RETURN v_monto;
END;
$$ LANGUAGE plpgsql;

--- Evitar choques horarios en programación de peliculas en salas
CREATE OR REPLACE FUNCTION fn_programar_funcion(p_id_pelicula INT, p_id_sala INT, p_inicio TIMESTAMP, p_id_admin INT, p_direccion_ip VARCHAR)
RETURNS INT AS $$
DECLARE
    v_rol             VARCHAR(20);
    v_duracion        INT;
    v_activa          BOOLEAN;
    v_titulo          VARCHAR(50);
    v_funcion_choque  INT;
    v_inicio_choque   TIMESTAMP;
    v_id_funcion      INT;
BEGIN
    SELECT rol INTO v_rol FROM usuario WHERE id_usuario = p_id_admin AND activo;
    IF v_rol IS NULL OR v_rol <> 'administrador' THEN
        RAISE EXCEPTION 'Solo un administrador puede programar funciones';
    END IF;
    SELECT duracion_min, activa, titulo INTO v_duracion, v_activa, v_titulo
    FROM pelicula WHERE id_pelicula = p_id_pelicula;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'La película % no existe', p_id_pelicula;
    END IF;
    IF NOT v_activa THEN
        RAISE EXCEPTION 'La película "%" no está en cartelera', v_titulo;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM sala WHERE id_sala = p_id_sala) THEN
        RAISE EXCEPTION 'La sala % no existe', p_id_sala;
    END IF;
    IF p_inicio <= NOW() THEN
        RAISE EXCEPTION 'No se puede programar una función en el pasado';
    END IF;
    -- Se hacen 30 min de limpieza entre que termina una pelicula e inicia la siguiente
    SELECT f.id_funcion, f.fecha_hora_inicio INTO v_funcion_choque, v_inicio_choque
    FROM funcion f
    JOIN pelicula p ON p.id_pelicula = f.id_pelicula
    WHERE f.id_sala = p_id_sala
      AND f.estado = 'programada'
      AND p_inicio < f.fecha_hora_inicio + (p.duracion_min + 30) * INTERVAL '1 minute'
      AND f.fecha_hora_inicio < p_inicio + (v_duracion + 30) * INTERVAL '1 minute'
    LIMIT 1;
    IF v_funcion_choque IS NOT NULL THEN
        RAISE EXCEPTION 'Traslape con la función % de esa sala (inicia %)', v_funcion_choque, v_inicio_choque;
    END IF;
    INSERT INTO funcion (fecha_hora_inicio, id_pelicula, id_sala)
    VALUES (p_inicio, p_id_pelicula, p_id_sala)
    RETURNING id_funcion INTO v_id_funcion;
    INSERT INTO admin_operacion_audit (accion, tabla_afectada, id_registro_afectado, detalle, rol, direccion_ip, id_usuario)
    VALUES ('crear_funcion', 'funcion', v_id_funcion,
            'Programa ' || v_titulo || ' en la sala ' || p_id_sala || ' el ' || p_inicio,
            v_rol, p_direccion_ip, p_id_admin);
    RETURN v_id_funcion;
END;
$$ LANGUAGE plpgsql;