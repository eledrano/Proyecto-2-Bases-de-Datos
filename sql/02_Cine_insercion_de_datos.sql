SET search_path TO prototipo;
 
--- Inserción de datos (Cines físicos)
 
INSERT INTO cine (nombre, pais, ciudad, direccion) VALUES
    ('IMAX Centro', 'Costa Rica', 'San José', 'Avenida Central, calle 5'),
    ('IMAX Oeste', 'Costa Rica', 'Escazú', 'Centro Comercial del Oeste, nivel 3'),
    ('IMAX Pacífico', 'Panamá', 'Ciudad de Panamá', 'Avenida Balboa, torre 2');
 
INSERT INTO sala (nombre, capacidad, id_cine) VALUES
    ('Sala 1', 40, 1),
    ('Sala 2', 40, 1),
    ('Sala 1', 40, 2),
    ('Sala 1', 40, 3);

-- Sala 1 Cine 1
INSERT INTO asiento (fila, numero, zona, id_sala) VALUES
    ('A', 1, 'general', 1), ('A', 2, 'general', 1), ('A', 3, 'general', 1), ('A', 4, 'general', 1), ('A', 5, 'general', 1),
    ('A', 6, 'general', 1), ('A', 7, 'general', 1), ('A', 8, 'general', 1), ('B', 1, 'general', 1), ('B', 2, 'general', 1), 
    ('B', 3, 'general', 1), ('B', 4, 'general', 1), ('B', 5, 'general', 1), ('B', 6, 'general', 1), ('B', 7, 'general', 1), 
    ('B', 8, 'general', 1), ('C', 1, 'platea', 1), ('C', 2, 'platea', 1), ('C', 3, 'platea', 1), ('C', 4, 'platea', 1),
    ('C', 5, 'platea', 1), ('C', 6, 'platea', 1), ('C', 7, 'platea', 1), ('C', 8, 'platea', 1), ('D', 1, 'palco', 1), 
    ('D', 2, 'palco', 1), ('D', 3, 'palco', 1), ('D', 4, 'palco', 1), ('D', 5, 'palco', 1), ('D', 6, 'palco', 1),
    ('D', 7, 'palco', 1), ('D', 8, 'palco', 1), ('E', 1, 'vip', 1), ('E', 2, 'vip', 1), ('E', 3, 'vip', 1),
	('E', 4, 'vip', 1), ('E', 5, 'vip', 1), ('E', 6, 'vip', 1), ('E', 7, 'vip', 1), ('E', 8, 'vip', 1);
 
-- Sala 2 Cine 1
INSERT INTO asiento (fila, numero, zona, id_sala) VALUES
    ('A', 1, 'general', 2), ('A', 2, 'general', 2), ('A', 3, 'general', 2), ('A', 4, 'general', 2), ('A', 5, 'general', 2),
    ('A', 6, 'general', 2), ('A', 7, 'general', 2), ('A', 8, 'general', 2), ('B', 1, 'general', 2), ('B', 2, 'general', 2), 
    ('B', 3, 'general', 2), ('B', 4, 'general', 2), ('B', 5, 'general', 2), ('B', 6, 'general', 2), ('B', 7, 'general', 2),
    ('B', 8, 'general', 2), ('C', 1, 'platea', 2), ('C', 2, 'platea', 2), ('C', 3, 'platea', 2), ('C', 4, 'platea', 2),
    ('C', 5, 'platea', 2), ('C', 6, 'platea', 2), ('C', 7, 'platea', 2), ('C', 8, 'platea', 2), ('D', 1, 'palco', 2),
    ('D', 2, 'palco', 2), ('D', 3, 'palco', 2), ('D', 4, 'palco', 2), ('D', 5, 'palco', 2), ('D', 6, 'palco', 2),
    ('D', 7, 'palco', 2), ('D', 8, 'palco', 2), ('E', 1, 'vip', 2), ('E', 2, 'vip', 2), ('E', 3, 'vip', 2),
	('E', 4, 'vip', 2), ('E', 5, 'vip', 2), ('E', 6, 'vip', 2), ('E', 7, 'vip', 2), ('E', 8, 'vip', 2);
 
-- Sala 1 Cine 2
INSERT INTO asiento (fila, numero, zona, id_sala) VALUES
    ('A', 1, 'general', 3), ('A', 2, 'general', 3), ('A', 3, 'general', 3), ('A', 4, 'general', 3), ('A', 5, 'general', 3),
    ('A', 6, 'general', 3), ('A', 7, 'general', 3), ('A', 8, 'general', 3), ('B', 1, 'general', 3), ('B', 2, 'general', 3),
    ('B', 3, 'general', 3), ('B', 4, 'general', 3), ('B', 5, 'general', 3), ('B', 6, 'general', 3), ('B', 7, 'general', 3),
    ('B', 8, 'general', 3), ('C', 1, 'platea', 3), ('C', 2, 'platea', 3), ('C', 3, 'platea', 3), ('C', 4, 'platea', 3),
    ('C', 5, 'platea', 3), ('C', 6, 'platea', 3), ('C', 7, 'platea', 3), ('C', 8, 'platea', 3), ('D', 1, 'palco', 3),
    ('D', 2, 'palco', 3), ('D', 3, 'palco', 3), ('D', 4, 'palco', 3), ('D', 5, 'palco', 3), ('D', 6, 'palco', 3),
    ('D', 7, 'palco', 3), ('D', 8, 'palco', 3), ('E', 1, 'vip', 3), ('E', 2, 'vip', 3), ('E', 3, 'vip', 3), 
	('E', 4, 'vip', 3), ('E', 5, 'vip', 3), ('E', 6, 'vip', 3), ('E', 7, 'vip', 3), ('E', 8, 'vip', 3);
 
-- Sala 1 Cine 3
INSERT INTO asiento (fila, numero, zona, id_sala) VALUES
    ('A', 1, 'general', 4), ('A', 2, 'general', 4), ('A', 3, 'general', 4), ('A', 4, 'general', 4), ('A', 5, 'general', 4),
    ('A', 6, 'general', 4), ('A', 7, 'general', 4), ('A', 8, 'general', 4), ('B', 1, 'general', 4), ('B', 2, 'general', 4),
    ('B', 3, 'general', 4), ('B', 4, 'general', 4), ('B', 5, 'general', 4), ('B', 6, 'general', 4), ('B', 7, 'general', 4),
    ('B', 8, 'general', 4), ('C', 1, 'platea', 4), ('C', 2, 'platea', 4), ('C', 3, 'platea', 4), ('C', 4, 'platea', 4),
    ('C', 5, 'platea', 4), ('C', 6, 'platea', 4), ('C', 7, 'platea', 4), ('C', 8, 'platea', 4), ('D', 1, 'palco', 4),
    ('D', 2, 'palco', 4), ('D', 3, 'palco', 4), ('D', 4, 'palco', 4), ('D', 5, 'palco', 4), ('D', 6, 'palco', 4),
    ('D', 7, 'palco', 4), ('D', 8, 'palco', 4), ('E', 1, 'vip', 4), ('E', 2, 'vip', 4), ('E', 3, 'vip', 4),
	('E', 4, 'vip', 4), ('E', 5, 'vip', 4), ('E', 6, 'vip', 4), ('E', 7, 'vip', 4), ('E', 8, 'vip', 4);
 
--- Inserción de datos (Peliculas)
 
INSERT INTO pelicula (titulo, sinopsis, clasificacion, duracion_min, poster_url, activa) VALUES
    ('Dune: Parte Dos', 'Paul Atreides se une a los Fremen para vengar a su familia.', 'PG-13', 166, NULL, TRUE),
    ('Intensamente 2', 'Riley entra a la adolescencia y llegan nuevas emociones.', 'G', 96, NULL, TRUE),
    ('Oppenheimer', 'La historia del físico que dirigió el Proyecto Manhattan.', 'R', 180, NULL, TRUE),
    ('Interestelar', 'Un grupo de exploradores viaja por un agujero de gusano.', 'PG-13', 169, NULL, TRUE),
    ('Coco', 'Miguel viaja a la Tierra de los Muertos para conocer su historia.', 'PG', 105, NULL, FALSE);
 
INSERT INTO pelicula_generos (id_pelicula, genero) VALUES
    (1, 'Ciencia ficción'), (1, 'Aventura'),
    (2, 'Animación'), (2, 'Comedia'), (2, 'Familiar'),
    (3, 'Drama'), (3, 'Historia'),
    (4, 'Ciencia ficción'), (4, 'Drama'),
    (5, 'Animación'), (5, 'Familiar'), (5, 'Musical');

 
INSERT INTO funcion (fecha_hora_inicio, estado, id_pelicula, id_sala) VALUES
    ('2026-10-24 18:00', 'programada', 1, 1),
    ('2026-10-24 21:30', 'programada', 1, 1),
    ('2026-10-24 17:00', 'programada', 2, 2),
    ('2026-10-24 19:00', 'programada', 3, 3),
    ('2026-10-25 20:00', 'programada', 4, 4),
    ('2026-10-25 15:00', 'programada', 2, 2),
    ('2026-10-25 19:00', 'programada', 3, 1),
    ('2026-10-26 19:30', 'cancelada',  4, 3);
 
--- Inserción de datos (Usuarios)
 
INSERT INTO usuario (primer_nombre, primer_apellido, segundo_apellido, correo, contrasena, rol) VALUES
    ('Luis', 'Medrano', 'Gonzalez', 'admin@imax.com', 'bbno$2468', 'administrador'),
    ('Carlos', 'Vargas', 'Rojas', 'contador@imax.com', 'Clave123*', 'contador'),
    ('María', 'Jiménez', 'Castro', 'taquilla1@imax.com', 'Clave123*', 'taquillero'),
    ('José', 'Araya', NULL, 'taquilla2@imax.com', 'Clave123*', 'taquillero'),
    ('Daniel', 'Quesada', 'Brenes',   'puerta1@imax.com', 'Clave123*', 'operador_sala'),
    ('Laura', 'Méndez', 'Vega', 'laura.mendez@correo.com', 'Clave123*', 'cliente'),
    ('Pablo', 'Chaves', 'Ruiz', 'pablo.chaves@correo.com', 'Clave123*', 'cliente'),
    ('Sofía', 'Herrera', 'Mata', 'sofia.herrera@correo.com', 'Clave123*', 'cliente'),
    ('Diego', 'Ramírez', 'Soto', 'diego.ramirez@correo.com', 'Clave123*', 'cliente');

--- Inserción de datos (Precios)
 
INSERT INTO tarifa (tipo_entrada, zona, precio) VALUES
    ('adulto', 'general', 4500), ('nino', 'general', 3500), ('tercera_edad', 'general', 3000), ('estudiante', 'general', 3800), ('cortesia', 'general', 0),
    ('adulto', 'platea', 5500), ('nino', 'platea', 4500), ('tercera_edad', 'platea', 4000), ('estudiante', 'platea', 4800), ('cortesia', 'platea', 0),
    ('adulto', 'palco', 7000), ('nino', 'palco', 6000), ('tercera_edad', 'palco', 5500), ('estudiante', 'palco', 6300), ('cortesia', 'palco', 0), 
    ('adulto', 'vip', 8500), ('nino', 'vip', 7500), ('tercera_edad', 'vip', 7000), ('estudiante', 'vip', 7800), ('cortesia', 'vip', 0);

--- Inserción (Bloqueos y Compras)
 
INSERT INTO bloqueo_asiento (fecha_hora_inicio, fecha_hora_expira, estado, id_funcion, id_asiento, id_usuario) VALUES
    ('2026-10-20 10:13', '2026-10-20 10:15', 'comprado', 1, 33, 6),
    ('2026-10-20 10:13', '2026-10-20 10:15', 'comprado', 1, 34, 6),
    ('2026-10-20 11:00', '2026-10-20 11:02', 'liberado', 4, 81, 8),
    ('2026-10-20 09:00', '2026-10-20 09:02', 'expirado', 2, 1, 6),
    ('2026-10-20 12:00', '2026-10-20 12:02', 'comprado', 5, 145, 9),
    ('2026-10-20 12:00', '2026-10-20 12:02', 'comprado', 5, 146, 9);
 
INSERT INTO compra (fecha_hora, canal, subtotal, descuento, cargo_servicio, total, estado, id_usuario_cliente, id_usuario_vendedor) VALUES
    ('2026-10-20 10:15', 'online', 17000, 0, 500, 17500, 'pagada', 6, NULL),
    ('2026-10-20 14:30', 'taquilla', 11000, 5500, 0, 5500, 'pagada', 7, 3),
    ('2026-10-20 11:02', 'online', 3800, 0, 500, 4300, 'rechazada', 8, NULL),
    ('2026-10-20 12:02', 'online', 13000, 0, 500, 13500, 'pagada', 9, NULL);
 
INSERT INTO compra_promociones (id_compra, promocion) VALUES
    (2, '2x1');
 
INSERT INTO pago (metodo_pago, monto, estado, referencia_pasarela, fecha_hora, id_compra) VALUES
    ('tarjeta', 17500, 'aprobado', 'SIM-0001', '2026-10-20 10:15', 1),
    ('tarjeta', 5500, 'aprobado', 'SIM-0002', '2026-10-20 14:30', 2),
    ('tarjeta', 4300, 'rechazado', 'SIM-0003', '2026-10-20 11:02', 3),
    ('paypal', 13500, 'aprobado', 'SIM-0004', '2026-10-20 12:02', 4);
 
INSERT INTO boleto (codigo_qr, precio, estado, fecha_emision, id_funcion, id_asiento, id_tarifa, id_compra) VALUES
    ('QR-0000001', 8500, 'valido', '2026-10-20 10:15', 1, 33, 16, 1),
    ('QR-0000002', 8500, 'valido', '2026-10-20 10:15', 1, 34, 16, 1),
    ('QR-0000003', 5500, 'valido', '2026-10-20 14:30', 3, 60, 6, 2),
    ('QR-0000004', 5500, 'valido', '2026-10-20 14:30', 3, 61, 6, 2),
    ('QR-0000005', 7000, 'usado',  '2026-10-20 12:02', 5, 145, 11, 4),
    ('QR-0000006', 6000, 'valido', '2026-10-20 12:02', 5, 146, 12, 4);
 
--- Bitácoras
 
INSERT INTO transaccion_log (evento, monto, estado, fecha_hora, id_pago) VALUES
    ('pago_aprobado', 17500, 'aprobado', '2026-10-20 10:15', 1),
    ('pago_aprobado', 5500, 'aprobado', '2026-10-20 14:30', 2),
    ('pago_rechazado', 4300, 'rechazado', '2026-10-20 11:02', 3),
    ('pago_aprobado', 13500, 'aprobado', '2026-10-20 12:02', 4);
 
INSERT INTO asiento_auditoria_log (evento, fecha_hora, id_bloqueo) VALUES
    ('bloqueado', '2026-10-20 10:13', 1), ('comprado', '2026-10-20 10:15', 1),
    ('bloqueado', '2026-10-20 10:13', 2), ('comprado', '2026-10-20 10:15', 2),
    ('bloqueado', '2026-10-20 11:00', 3), ('liberado', '2026-10-20 11:02', 3),
    ('bloqueado', '2026-10-20 09:00', 4), ('expirado', '2026-10-20 09:02', 4),
    ('bloqueado', '2026-10-20 12:00', 5), ('comprado', '2026-10-20 12:02', 5),
    ('bloqueado', '2026-10-20 12:00', 6), ('comprado', '2026-10-20 12:02', 6);
 
INSERT INTO acceso_puerta_log (codigo_leido, puerta, resultado, fecha_hora, id_boleto) VALUES
    ('QR-0000005', 'Puerta 1', 'exitoso', '2026-10-25 19:40', 5),
    ('QR-0000005', 'Puerta 1', 'ya_utilizada', '2026-10-25 19:45', 5),
    ('QR-9999999', 'Puerta 1', 'no_existe', '2026-10-25 19:50', NULL);
 
INSERT INTO admin_operacion_audit (accion, tabla_afectada, id_registro_afectado, detalle, rol, direccion_ip, fecha_hora, id_usuario) VALUES
    ('crear_funcion', 'funcion', 8, 'Programa Interestelar en IMAX Oeste el 26/10 19:30', 'administrador', '192.168.1.10', '2026-10-19 09:00', 1),
    ('cancelar_funcion', 'funcion', 8, 'Cancelada por mantenimiento de la sala', 'administrador', '192.168.1.10', '2026-10-20 08:30', 1);