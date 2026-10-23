CREATE SCHEMA IF NOT EXISTS prototipo;
SET search_path TO prototipo;

DROP TABLE IF EXISTS admin_operacion_audit, acceso_puerta_log, asiento_auditoria_log,
    transaccion_log, boleto, pago, compra_promociones, compra, bloqueo_asiento,
    tarifa, usuario, funcion, pelicula_generos, pelicula, asiento, sala, cine CASCADE;

--- Creación de Tablas
CREATE TABLE cine (
    id_cine     SERIAL       PRIMARY KEY,
    nombre      VARCHAR(50) NOT NULL,
    pais        VARCHAR(50)  NOT NULL,
    ciudad      VARCHAR(60)  NOT NULL,
    direccion   VARCHAR(100) NOT NULL
);

CREATE TABLE sala (
    id_sala     SERIAL      PRIMARY KEY,
    nombre      VARCHAR(30) NOT NULL,
    capacidad   INT         NOT NULL,
    id_cine     INT         NOT NULL,
    CONSTRAINT ck_sala_capacidad CHECK (capacidad > 0),
    CONSTRAINT fk_sala_cine FOREIGN KEY (id_cine)
        REFERENCES cine (id_cine) ON DELETE RESTRICT
);

CREATE TABLE asiento (
    id_asiento  SERIAL      PRIMARY KEY,
    fila        VARCHAR(2)  NOT NULL,
    numero      INT         NOT NULL,
    zona        VARCHAR(10) NOT NULL,
    id_sala     INT         NOT NULL,
    CONSTRAINT ck_asiento_numero CHECK (numero > 0),
    CONSTRAINT ck_asiento_zona CHECK (zona IN ('general', 'platea', 'palco', 'vip')),
    CONSTRAINT uq_asiento_sala_fila_numero UNIQUE (id_sala, fila, numero),
    CONSTRAINT fk_asiento_sala FOREIGN KEY (id_sala)
        REFERENCES sala (id_sala) ON DELETE RESTRICT
);

CREATE TABLE pelicula (
    id_pelicula   SERIAL       PRIMARY KEY,
    titulo        VARCHAR(50) NOT NULL,
    sinopsis      TEXT,
    clasificacion VARCHAR(10)  NOT NULL,
    duracion_min  INT          NOT NULL,
    poster_url    VARCHAR(300),
    activa        BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT ck_pelicula_duracion CHECK (duracion_min > 0)
);

CREATE TABLE pelicula_generos (
    id_pelicula INT         NOT NULL,
    genero      VARCHAR(40) NOT NULL,
    CONSTRAINT pk_pelicula_generos PRIMARY KEY (id_pelicula, genero),
    CONSTRAINT fk_pelicula_generos_pelicula FOREIGN KEY (id_pelicula)
        REFERENCES pelicula (id_pelicula) ON DELETE CASCADE
);

CREATE TABLE funcion (
    id_funcion        SERIAL      PRIMARY KEY,
    fecha_hora_inicio TIMESTAMP   NOT NULL,
    estado            VARCHAR(15) NOT NULL DEFAULT 'programada',
    id_pelicula       INT         NOT NULL,
    id_sala           INT         NOT NULL,
    CONSTRAINT ck_funcion_estado CHECK (estado IN ('programada', 'cancelada')),
    CONSTRAINT fk_funcion_pelicula FOREIGN KEY (id_pelicula)
        REFERENCES pelicula (id_pelicula) ON DELETE RESTRICT,
    CONSTRAINT fk_funcion_sala FOREIGN KEY (id_sala)
        REFERENCES sala (id_sala) ON DELETE RESTRICT
);

CREATE TABLE usuario (
    id_usuario       SERIAL       PRIMARY KEY,
    primer_nombre    VARCHAR(20)  NOT NULL,
    primer_apellido  VARCHAR(30)  NOT NULL,
    segundo_apellido VARCHAR(30),
    correo           VARCHAR(50) NOT NULL,
    contrasena       VARCHAR(64) NOT NULL,
    rol              VARCHAR(20)  NOT NULL,
    activo           BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_usuario_correo UNIQUE (correo),
    CONSTRAINT ck_usuario_rol CHECK (rol IN ('cliente', 'taquillero', 'operador_sala', 'contador', 'administrador'))
);

CREATE TABLE tarifa (
    id_tarifa    SERIAL        PRIMARY KEY,
    tipo_entrada VARCHAR(20)   NOT NULL,
    zona         VARCHAR(10)   NOT NULL,
    precio       NUMERIC(10,2) NOT NULL,
    CONSTRAINT ck_tarifa_tipo_entrada CHECK (tipo_entrada IN ('adulto', 'nino', 'tercera_edad', 'estudiante', 'cortesia')),
    CONSTRAINT ck_tarifa_zona CHECK (zona IN ('general', 'platea', 'palco', 'vip')),
    CONSTRAINT ck_tarifa_precio CHECK (precio >= 0),
    CONSTRAINT uq_tarifa_tipo_zona UNIQUE (tipo_entrada, zona)
);

CREATE TABLE bloqueo_asiento (
    id_bloqueo        SERIAL      PRIMARY KEY,
    fecha_hora_inicio TIMESTAMP   NOT NULL DEFAULT NOW(),
    fecha_hora_expira TIMESTAMP   NOT NULL,
    estado            VARCHAR(15) NOT NULL DEFAULT 'activo',
    id_funcion        INT         NOT NULL,
    id_asiento        INT         NOT NULL,
    id_usuario        INT         NOT NULL,
    CONSTRAINT ck_bloqueo_estado CHECK (estado IN ('activo', 'expirado', 'liberado', 'comprado')),
    CONSTRAINT fk_bloqueo_funcion FOREIGN KEY (id_funcion)
        REFERENCES funcion (id_funcion) ON DELETE RESTRICT,
    CONSTRAINT fk_bloqueo_asiento FOREIGN KEY (id_asiento)
        REFERENCES asiento (id_asiento) ON DELETE RESTRICT,
    CONSTRAINT fk_bloqueo_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario (id_usuario) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_bloqueo_activo_funcion_asiento
    ON bloqueo_asiento (id_funcion, id_asiento)
    WHERE estado = 'activo';

CREATE TABLE compra (
    id_compra           SERIAL        PRIMARY KEY,
    fecha_hora          TIMESTAMP     NOT NULL DEFAULT NOW(),
    canal               VARCHAR(10)   NOT NULL,
    subtotal            NUMERIC(10,2) NOT NULL DEFAULT 0,
    descuento           NUMERIC(10,2) NOT NULL DEFAULT 0,
    cargo_servicio      NUMERIC(10,2) NOT NULL DEFAULT 0,
    total               NUMERIC(10,2) NOT NULL DEFAULT 0,
    estado              VARCHAR(15)   NOT NULL DEFAULT 'pendiente',
    id_usuario_cliente  INT           NOT NULL,
    id_usuario_vendedor INT, 
    CONSTRAINT ck_compra_canal CHECK (canal IN ('online', 'taquilla')),
    CONSTRAINT ck_compra_estado CHECK (estado IN ('pendiente', 'pagada', 'rechazada', 'reembolsada')),
    CONSTRAINT ck_compra_montos CHECK (subtotal >= 0 AND descuento >= 0 AND cargo_servicio >= 0 AND total >= 0),
    CONSTRAINT fk_compra_cliente FOREIGN KEY (id_usuario_cliente)
        REFERENCES usuario (id_usuario) ON DELETE RESTRICT,
    CONSTRAINT fk_compra_vendedor FOREIGN KEY (id_usuario_vendedor)
        REFERENCES usuario (id_usuario) ON DELETE RESTRICT
);

CREATE TABLE compra_promociones (
    id_compra  INT         NOT NULL,
    promocion  VARCHAR(20) NOT NULL,
    CONSTRAINT pk_compra_promociones PRIMARY KEY (id_compra, promocion),
    CONSTRAINT ck_compra_promociones_promocion CHECK (promocion IN ('2x1', 'dia_descuento')),
    CONSTRAINT fk_compra_promociones_compra FOREIGN KEY (id_compra)
        REFERENCES compra (id_compra) ON DELETE RESTRICT
);

CREATE TABLE pago (
    id_pago             SERIAL        PRIMARY KEY,
    metodo_pago         VARCHAR(20)   NOT NULL,
    monto               NUMERIC(10,2) NOT NULL,
    estado              VARCHAR(20)   NOT NULL,
    referencia_pasarela VARCHAR(100),
    fecha_hora          TIMESTAMP     NOT NULL DEFAULT NOW(),
    id_compra           INT           NOT NULL,
    CONSTRAINT ck_pago_metodo CHECK (metodo_pago IN ('tarjeta', 'paypal', 'transferencia', 'billetera_digital')),
    CONSTRAINT ck_pago_estado CHECK (estado IN ('aprobado', 'rechazado')),
    CONSTRAINT ck_pago_monto CHECK (monto >= 0),
    CONSTRAINT fk_pago_compra FOREIGN KEY (id_compra)
        REFERENCES compra (id_compra) ON DELETE RESTRICT
);

CREATE TABLE boleto (
    id_boleto         SERIAL        PRIMARY KEY,
    codigo_qr         VARCHAR(64)   NOT NULL,
    precio            NUMERIC(10,2) NOT NULL,
    estado            VARCHAR(10)   NOT NULL DEFAULT 'valido',
    fecha_emision     TIMESTAMP     NOT NULL DEFAULT NOW(),
    monto_reembolsado NUMERIC(10,2),
    fecha_anulacion   TIMESTAMP,
    id_funcion        INT           NOT NULL,
    id_asiento        INT           NOT NULL,
    id_tarifa         INT           NOT NULL,
    id_compra         INT           NOT NULL,
    CONSTRAINT uq_boleto_codigo_qr UNIQUE (codigo_qr),   -- RN-12
    CONSTRAINT ck_boleto_estado CHECK (estado IN ('valido', 'usado', 'anulado')),
    CONSTRAINT ck_boleto_precio CHECK (precio >= 0),
    CONSTRAINT ck_boleto_reembolso CHECK (monto_reembolsado IS NULL OR monto_reembolsado >= 0),
    CONSTRAINT fk_boleto_funcion FOREIGN KEY (id_funcion)
        REFERENCES funcion (id_funcion) ON DELETE RESTRICT,
    CONSTRAINT fk_boleto_asiento FOREIGN KEY (id_asiento)
        REFERENCES asiento (id_asiento) ON DELETE RESTRICT,
    CONSTRAINT fk_boleto_tarifa FOREIGN KEY (id_tarifa)
        REFERENCES tarifa (id_tarifa) ON DELETE RESTRICT,
    CONSTRAINT fk_boleto_compra FOREIGN KEY (id_compra)
        REFERENCES compra (id_compra) ON DELETE RESTRICT
);

-- Restricción para impedir la doble venta de asientos, y si se anula el boleto el asiento vuelve a la venta
CREATE UNIQUE INDEX uq_boleto_funcion_asiento
    ON boleto (id_funcion, id_asiento)
    WHERE estado <> 'anulado';

--- Tablas de bitacora

CREATE TABLE transaccion_log (
    id_log      SERIAL        PRIMARY KEY,
    evento      VARCHAR(50)   NOT NULL,
    monto       NUMERIC(10,2),
    estado      VARCHAR(20),
    fecha_hora  TIMESTAMP     NOT NULL DEFAULT NOW(),
    id_pago     INT           NOT NULL,
    CONSTRAINT fk_transaccion_log_pago FOREIGN KEY (id_pago)
        REFERENCES pago (id_pago) ON DELETE RESTRICT
);

CREATE TABLE asiento_auditoria_log (
    id_log      SERIAL      PRIMARY KEY,
    evento      VARCHAR(50) NOT NULL,
    fecha_hora  TIMESTAMP   NOT NULL DEFAULT NOW(),
    id_bloqueo  INT         NOT NULL,
    CONSTRAINT fk_asiento_auditoria_log_bloqueo FOREIGN KEY (id_bloqueo)
        REFERENCES bloqueo_asiento (id_bloqueo) ON DELETE RESTRICT
);

CREATE TABLE acceso_puerta_log (
    id_log       SERIAL      PRIMARY KEY,
    codigo_leido VARCHAR(64) NOT NULL,
    puerta       VARCHAR(30) NOT NULL,
    resultado    VARCHAR(20) NOT NULL,
    fecha_hora   TIMESTAMP   NOT NULL DEFAULT NOW(),
    id_boleto    INT,                     -- nulo si el código leído no existe
    CONSTRAINT ck_acceso_resultado CHECK (resultado IN ('exitoso', 'ya_utilizada', 'fuera_de_horario', 'otra_funcion', 'no_existe', 'anulada')),
    CONSTRAINT fk_acceso_puerta_log_boleto FOREIGN KEY (id_boleto)
        REFERENCES boleto (id_boleto) ON DELETE RESTRICT
);

CREATE TABLE admin_operacion_audit (
    id_log               SERIAL      PRIMARY KEY,
    accion               VARCHAR(50) NOT NULL,
    tabla_afectada       VARCHAR(50) NOT NULL,
    id_registro_afectado INT,
    detalle              TEXT,
    rol                  VARCHAR(20) NOT NULL, 
    direccion_ip         VARCHAR(45),
    fecha_hora           TIMESTAMP   NOT NULL DEFAULT NOW(),
    id_usuario           INT         NOT NULL,
    CONSTRAINT fk_admin_operacion_audit_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario (id_usuario) ON DELETE RESTRICT
);