SET search_path TO prototipo;

--- Funciones de venta: bloqueo temporal de asientos, compra con pago simulado y emisión de boletos

--- 1. Liberar bloqueos vencidos (RN-05) que transcurrieron los 2 minutos limite
CREATE OR REPLACE FUNCTION fn_liberar_bloqueos_expirados()
RETURNS INT AS $$
DECLARE
    v_cantidad INT;
BEGIN
    INSERT INTO asiento_auditoria_log (evento, id_bloqueo)
    SELECT 'expirado', id_bloqueo
    FROM bloqueo_asiento
    WHERE estado = 'activo' AND fecha_hora_expira < NOW();
    UPDATE bloqueo_asiento
    SET estado = 'expirado'
    WHERE estado = 'activo' AND fecha_hora_expira < NOW();
    GET DIAGNOSTICS v_cantidad = ROW_COUNT;
    RETURN v_cantidad;
END;
$$ LANGUAGE plpgsql;

--- 2. Bloquear un asiento por 2 minutos (RN-03, RN-04, RN-05)
CREATE OR REPLACE FUNCTION fn_bloquear_asiento(p_id_funcion INT, p_id_asiento INT, p_id_usuario INT)
RETURNS INT AS $$
DECLARE
    v_estado_funcion VARCHAR(15);
    v_sala_funcion   INT;
    v_sala_asiento   INT;
    v_bloqueos       INT;
    v_id_bloqueo     INT;
BEGIN
    PERFORM fn_liberar_bloqueos_expirados();
    SELECT estado, id_sala INTO v_estado_funcion, v_sala_funcion
    FROM funcion WHERE id_funcion = p_id_funcion;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'La función % no existe', p_id_funcion;
    END IF;
    IF v_estado_funcion <> 'programada' THEN
        RAISE EXCEPTION 'La función % está cancelada', p_id_funcion;
    END IF;

    SELECT id_sala INTO v_sala_asiento
    FROM asiento WHERE id_asiento = p_id_asiento;
    IF v_sala_asiento IS NULL OR v_sala_asiento <> v_sala_funcion THEN
        RAISE EXCEPTION 'El asiento % no pertenece a la sala de la función %', p_id_asiento, p_id_funcion;
    END IF;
    IF EXISTS (SELECT 1 FROM boleto
               WHERE id_funcion = p_id_funcion AND id_asiento = p_id_asiento AND estado <> 'anulado') THEN
        RAISE EXCEPTION 'Asiento ocupado: ya fue vendido para esta función';
    END IF;

    SELECT COUNT(*) INTO v_bloqueos
    FROM bloqueo_asiento
    WHERE id_funcion = p_id_funcion AND id_usuario = p_id_usuario AND estado = 'activo';
    IF v_bloqueos >= 6 THEN
        RAISE EXCEPTION 'Límite alcanzado: máximo 6 asientos por compra';
    END IF;
    BEGIN
        INSERT INTO bloqueo_asiento (fecha_hora_expira, id_funcion, id_asiento, id_usuario)
        VALUES (NOW() + INTERVAL '2 minutes', p_id_funcion, p_id_asiento, p_id_usuario)
        RETURNING id_bloqueo INTO v_id_bloqueo;
    EXCEPTION
        WHEN unique_violation THEN
            RAISE EXCEPTION 'Asiento bloqueado: otro usuario lo está comprando en este momento';
    END;
    INSERT INTO asiento_auditoria_log (evento, id_bloqueo) VALUES ('bloqueado', v_id_bloqueo);
    RETURN v_id_bloqueo;
END;
$$ LANGUAGE plpgsql;

--- 3. Liberar un asiento (si el usuario que lo reservo lo desmarca)
CREATE OR REPLACE FUNCTION fn_liberar_asiento(p_id_bloqueo INT, p_id_usuario INT)
RETURNS VOID AS $$
BEGIN
    UPDATE bloqueo_asiento
    SET estado = 'liberado'
    WHERE id_bloqueo = p_id_bloqueo AND id_usuario = p_id_usuario AND estado = 'activo';
 
    IF NOT FOUND THEN
        RAISE EXCEPTION 'El bloqueo % no está activo o no pertenece a este usuario', p_id_bloqueo;
    END IF;
 
    INSERT INTO asiento_auditoria_log (evento, id_bloqueo) VALUES ('liberado', p_id_bloqueo);
END;
$$ LANGUAGE plpgsql;

--- 4. Generar el código QR del boleto (RN-12)
CREATE OR REPLACE FUNCTION fn_generar_codigo_qr(p_id_funcion INT, p_id_asiento INT, p_zona VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    v_caracteres VARCHAR := 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    v_aleatorio  VARCHAR := '';
    v_inicial    VARCHAR(2);
BEGIN
    v_inicial := CASE p_zona
                     WHEN 'general' THEN 'G'
                     WHEN 'platea'  THEN 'PL'
                     WHEN 'palco'   THEN 'PC'
                     WHEN 'vip'     THEN 'V'
                 END;
    FOR i IN 1..4 LOOP
        v_aleatorio := v_aleatorio || substr(v_caracteres, 1 + floor(random() * 36)::INT, 1);
    END LOOP;
-- Formato: QR-{id_funcion}-{id_asiento}-{inicia de zona}-{4 caracteres aleatorios}
    RETURN 'QR-' || p_id_funcion || '-' || p_id_asiento || '-' || v_inicial || '-' || v_aleatorio;
END;
$$ LANGUAGE plpgsql;

--- 5. Procesar una compra con pago simulado (RN-07, RN-08, RN-10, RN-11) 
CREATE OR REPLACE FUNCTION fn_procesar_compra(
    p_id_usuario_cliente  INT,
    p_id_usuario_vendedor INT,
    p_canal               VARCHAR,
    p_metodo_pago         VARCHAR,
    p_pago_aprobado       BOOLEAN,
    p_bloqueos            INT[],
    p_tipos_entrada       VARCHAR[]
)
RETURNS INT AS $$
DECLARE
    v_cantidad        INT;
    v_usuario_bloqueo INT;
    v_id_funcion      INT;
    v_fecha_funcion   TIMESTAMP;
    v_funcion_actual  INT;
    v_estado_bloqueo  VARCHAR(15);
    v_dueno_bloqueo   INT;
    v_id_asiento      INT;
    v_zona            VARCHAR(10);
    v_id_tarifa       INT;
    v_precio          NUMERIC(10,2);
    v_asientos        INT[]           := '{}';
    v_zonas           VARCHAR[]       := '{}';
    v_tarifas         INT[]           := '{}';
    v_precios         NUMERIC(10,2)[] := '{}';
    v_subtotal        NUMERIC(10,2)   := 0;
    v_desc_2x1        NUMERIC(10,2)   := 0;
    v_desc_dia        NUMERIC(10,2)   := 0;
    v_cargo           NUMERIC(10,2);
    v_total           NUMERIC(10,2);
    v_id_compra       INT;
    v_id_pago         INT;
BEGIN
    PERFORM fn_liberar_bloqueos_expirados();
    -- Validaciones generales
    v_cantidad := COALESCE(array_length(p_bloqueos, 1), 0);
    IF v_cantidad = 0 OR v_cantidad <> COALESCE(array_length(p_tipos_entrada, 1), 0) THEN
        RAISE EXCEPTION 'Debe indicar un tipo de entrada por cada asiento';
    END IF;
    IF v_cantidad > 6 THEN
        RAISE EXCEPTION 'Límite alcanzado: máximo 6 asientos por compra';
    END IF;
    IF p_canal = 'taquilla' AND p_id_usuario_vendedor IS NULL THEN
        RAISE EXCEPTION 'Una venta en taquilla debe indicar el taquillero';
    END IF;
    IF p_canal = 'online' AND p_id_usuario_vendedor IS NOT NULL THEN
        RAISE EXCEPTION 'Una compra online no lleva taquillero';
    END IF;
    v_usuario_bloqueo := COALESCE(p_id_usuario_vendedor, p_id_usuario_cliente);
    -- Revisar cada bloqueo y buscar su tarifa según la zona del asiento y el tipo de entrada
    FOR i IN 1..v_cantidad LOOP
        SELECT b.estado, b.id_usuario, b.id_funcion, b.id_asiento, a.zona
        INTO v_estado_bloqueo, v_dueno_bloqueo, v_funcion_actual, v_id_asiento, v_zona
        FROM bloqueo_asiento b
        JOIN asiento a ON a.id_asiento = b.id_asiento
        WHERE b.id_bloqueo = p_bloqueos[i];
 
        IF NOT FOUND OR v_estado_bloqueo <> 'activo' THEN
            RAISE EXCEPTION 'El bloqueo % no está activo (pudo haber expirado)', p_bloqueos[i];
        END IF;
        IF v_dueno_bloqueo <> v_usuario_bloqueo THEN
            RAISE EXCEPTION 'El bloqueo % pertenece a otro usuario', p_bloqueos[i];
        END IF;
 
        IF i = 1 THEN
            v_id_funcion := v_funcion_actual;
        ELSIF v_funcion_actual <> v_id_funcion THEN
            RAISE EXCEPTION 'Todos los asientos de una compra deben ser de la misma función';
        END IF;
 
        SELECT id_tarifa, precio INTO v_id_tarifa, v_precio
        FROM tarifa
        WHERE tipo_entrada = p_tipos_entrada[i] AND zona = v_zona;
 
        IF NOT FOUND THEN
            RAISE EXCEPTION 'No existe tarifa para la entrada % en zona %', p_tipos_entrada[i], v_zona;
        END IF;
        v_asientos[i] := v_id_asiento;
        v_zonas[i]   := v_zona;
        v_tarifas[i] := v_id_tarifa;
        v_precios[i] := v_precio;
        v_subtotal   := v_subtotal + v_precio;
    END LOOP;
    -- Promoción 2x1: por cada par de entradas con la misma tarifa, se descuenta una
    SELECT COALESCE(SUM((t.cantidad / 2) * t.precio), 0) INTO v_desc_2x1
    FROM (SELECT x.id_tarifa, tf.precio, COUNT(*) AS cantidad
          FROM unnest(v_tarifas) AS x(id_tarifa)
          JOIN tarifa tf ON tf.id_tarifa = x.id_tarifa
          GROUP BY x.id_tarifa, tf.precio) t;
    -- Promoción día de descuento: 20% si la función es miércoles (ISODOW 3)
    SELECT fecha_hora_inicio INTO v_fecha_funcion FROM funcion WHERE id_funcion = v_id_funcion;
    IF EXTRACT(ISODOW FROM v_fecha_funcion) = 3 THEN
        v_desc_dia := ROUND((v_subtotal - v_desc_2x1) * 0.20, 2);
    END IF;
    v_cargo := CASE WHEN p_canal = 'online' THEN 500 ELSE 0 END;
    v_total := v_subtotal - v_desc_2x1 - v_desc_dia + v_cargo;
    -- Registrar la compra, sus promociones y el pago
    INSERT INTO compra (canal, subtotal, descuento, cargo_servicio, total, estado,
                        id_usuario_cliente, id_usuario_vendedor)
    VALUES (p_canal, v_subtotal, v_desc_2x1 + v_desc_dia, v_cargo, v_total,
            CASE WHEN p_pago_aprobado THEN 'pagada' ELSE 'rechazada' END,
            p_id_usuario_cliente, p_id_usuario_vendedor)
    RETURNING id_compra INTO v_id_compra;
    IF v_desc_2x1 > 0 THEN
        INSERT INTO compra_promociones (id_compra, promocion) VALUES (v_id_compra, '2x1');
    END IF;
    IF v_desc_dia > 0 THEN
        INSERT INTO compra_promociones (id_compra, promocion) VALUES (v_id_compra, 'dia_descuento');
    END IF;
    INSERT INTO pago (metodo_pago, monto, estado, referencia_pasarela, id_compra)
    VALUES (p_metodo_pago, v_total,
            CASE WHEN p_pago_aprobado THEN 'aprobado' ELSE 'rechazado' END,
            'SIM-' || v_id_compra, v_id_compra)
    RETURNING id_pago INTO v_id_pago;
    -- Pago rechazado: se liberan los asientos y no se emite ningún boleto (RN-10, RN-11)
    IF NOT p_pago_aprobado THEN
        INSERT INTO transaccion_log (evento, monto, estado, id_pago)
        VALUES ('pago_rechazado', v_total, 'rechazado', v_id_pago);
        UPDATE bloqueo_asiento SET estado = 'liberado' WHERE id_bloqueo = ANY (p_bloqueos);
        INSERT INTO asiento_auditoria_log (evento, id_bloqueo)
        SELECT 'liberado', unnest(p_bloqueos);
        RAISE NOTICE 'Pago rechazado: la compra % fue cancelada y los asientos quedaron libres', v_id_compra;
        RETURN v_id_compra;
    END IF;
    -- Pago aprobado: se emiten los boletos con su código QR (RN-11, RN-12)
    INSERT INTO transaccion_log (evento, monto, estado, id_pago)
    VALUES ('pago_aprobado', v_total, 'aprobado', v_id_pago);

    FOR i IN 1..v_cantidad LOOP
        INSERT INTO boleto (codigo_qr, precio, id_funcion, id_asiento, id_tarifa, id_compra)
        VALUES (fn_generar_codigo_qr(v_id_funcion, v_asientos[i], v_zonas[i]),
                v_precios[i], v_id_funcion, v_asientos[i], v_tarifas[i], v_id_compra);
        UPDATE bloqueo_asiento SET estado = 'comprado' WHERE id_bloqueo = p_bloqueos[i];
        INSERT INTO asiento_auditoria_log (evento, id_bloqueo) VALUES ('comprado', p_bloqueos[i]);
    END LOOP;
    RAISE NOTICE 'Pago aprobado: compra % con % boleto(s) emitido(s)', v_id_compra, v_cantidad;
    RETURN v_id_compra;
END;
$$ LANGUAGE plpgsql;