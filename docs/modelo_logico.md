# Modelo Lógico

- CINE (id_cine[PK], nombre, pais, ciudad, direccion)
- SALA (id_sala[PK], nombre, capacidad, id_cine[FK])
- ASIENTO (id_asiento[PK], fila, numero, zona, id_sala[FK])
- PELICULA (id_pelicula[PK], titulo, sinopsis, clasificacion, duracion_min, poster_url, activa)
- PELICULA_GENEROS (id_pelicula[PK/FK], genero[PK])
- FUNCION (id_funcion[PK], fecha_hora_inicio, estado, id_pelicula[FK], id_sala[FK])
- USUARIO (id_usuario[PK], primer_nombre, primer_apellido, segundo_apellido, correo, contrasena, rol, activo)
- TARIFA (id_tarifa[PK], tipo_entrada, zona, precio)
- BLOQUEO_ASIENTO (id_bloqueo[PK], fecha_hora_inicio, fecha_hora_expira, estado, id_funcion[FK], id_asiento[FK], id_usuario[FK])
- COMPRA (id_compra[PK], fecha_hora, canal, subtotal, descuento, cargo_servicio, total, estado, id_usuario_cliente[FK], id_usuario_vendedor[FK])
- COMPRA_PROMOCIONES (id_compra[PK/FK], promoción[PK])
- PAGO (id_pago[PK], metodo_pago, monto, estado, referencia_pasarela, fecha_hora, id_compra[FK])
- BOLETO (id_boleto[PK], codigo_qr, precio, estado, fecha_emision, monto_reembolsado, fecha_anulacion, id_funcion[FK], id_asiento[FK], id_tarifa[FK], id_compra[FK])
- TRANSACCION_LOG (id_log[PK], evento, monto, estado, fecha_hora, id_pago[FK])
- ASIENTO_AUDITORIA_LOG (id_log[PK], evento, fecha_hora, id_bloqueo[FK])
- ACCESO_PUERTA_LOG (id_log[PK], codigo_leido, puerta, resultado, fecha_hora, id_boleto[FK])
- ADMIN_OPERACION_AUDIT (id_log[PK], accion, tabla_afectada, id_registro_afectado, detalle, rol, direccion_ip, fecha_hora, id_usuario[FK])

## Transformación del Modelo Conceptual

**Relación tripartita:** `emite` es 1 : 1 : N, por lo que se absorbe en BOLETO. Esa tabla recibe las FK de FUNCION y ASIENTO, y también el atributo de la relación, `codigo_qr`. Así cada comprobante queda asociado de forma unívoca a la función, al asiento y, a través de él, a su localidad (zona), cumpliendo la RN-12.

**Atributo multivaluado:** `genero` sale a la tabla PELICULA_GENEROS con llave compuesta (id_pelicula, genero), de modo que una película puede tener varios géneros y `promocion` de COMPRA se convierte en la tabla COMPRA_PROMOCIONES 

**Atributos compuestos:** `ubicacion` de CINE y `nombre` de USUARIO se separan en sus componentes simples, lo que permite filtrar la cartelera por país o ciudad.

**Atributos derivados:** `fecha_hora_expira` (inicio del bloqueo + 2 minutos), `subtotal` (suma de los precios de los boletos), `descuento` (calculado sobre las promociones) y `total` (subtotal − descuento + cargo por servicio) se guardan como columnas. No se ingresan manualmente: los calculan las funciones SQL de bloqueo y de compra. `fecha_hora_expira` se consulta constantemente para liberar asientos vencidos, por lo que conviene tenerla almacenada.

**Doble relación usuario–compra:** como `realiza` y `vende` unen las mismas tablas, las FK se distinguen por su rol: `id_usuario_cliente` e `id_usuario_vendedor`.

**Bitácoras:** cada una conserva el nombre exigido por el enunciado y referencia solo a la tabla que la origina, separándolas de las tablas de operación diaria.

## Normalización

El modelo cumple la Tercera Forma Normal (3FN). Las columnas que podrían parecer redundantes no lo son:

- `zona` en ASIENTO y en TARIFA: en ASIENTO es la zona física del asiento; en TARIFA es una de las dos columnas que definen el precio.
- `precio` en BOLETO: es el precio cobrado en el momento de la compra. Si la tarifa cambia después, el boleto conserva lo que se pagó.
- `rol` en ADMIN_OPERACION_AUDIT: es el rol que tenía el usuario al realizar la acción, como exige el enunciado, y no depende del rol actual del usuario.
