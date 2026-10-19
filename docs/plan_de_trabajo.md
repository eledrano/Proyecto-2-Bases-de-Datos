# Plan de trabajo — Proyecto 2 (Licitación IMAX)

Entrega: **domingo 25/10/2026, 23:59** (meta interna: dejar todo en `main` a las 18:00 de ese día).

## Reparto del trabajo

### Luis — Diseño e implementación de la base de datos (Fases 3 y 4)
- Diagrama Entidad-Relación (DER) conceptual.
- Modelo lógico / relacional documentado (normalización, PK y FK).
- Script DDL con todas las restricciones de integridad, incluida la restricción de unicidad que impide vender el mismo asiento dos veces para la misma función.
- Tablas de bitácora con los nombres del enunciado: `transaccion_log`, `asiento_auditoria_log`, `acceso_puerta_log`, `admin_operacion_audit`.
- Funciones, procedimientos y triggers: bloqueo temporal de asientos (2 min) y su liberación, compra con pago simulado (aprobado / rechazado con ROLLBACK), emisión del código único del boleto, validación en puerta (uso único, función correcta, tolerancia de horario), cancelación y reembolso, registro en bitácoras.
- Roles de PostgreSQL según la matriz de privilegio mínimo (RBAC).
- Datos de prueba.
- Script de prueba de concurrencia en Python (20 a 50 hilos intentando el mismo asiento).

### P1 — Documento técnico: factibilidad, requisitos, operación y rendimiento (Fases 1, 2 y 5)
- Dictamen técnico de rechazo de la infraestructura legada.
- Factibilidad técnica, económica y operativa.
- Comparativa de al menos dos proveedores cloud (base de datos, almacenamiento de logs a 5 años, balanceador/WAF), con fuentes citadas.
- Proyección financiera a 3 años (CAPEX + OPEX) y justificación del ROI.
- Matriz única de riesgo y mitigación (probabilidad, impacto, estrategia, RTO/RPO).
- Tabla de cálculo de almacenamiento (GB/TB mensual y acumulado a 5 años).
- Requerimientos funcionales y no funcionales; volúmenes esperados (usuarios concurrentes, TPS, histórico, auditoría).
- Fase 5: respaldos, recuperación ante desastres, RTO, RPO, SLA y frecuencia de respaldo, con justificación.
- Índices, las 4 consultas analíticas y la comparativa EXPLAIN ANALYZE antes/después.
- Ensamblar el documento técnico final.

### P2 — Interfaz gráfica en Python (CustomTkinter)
- Conexión a la BD y pantalla de inicio de sesión por rol.
- Vista de cartelera con filtros (ubicación, fecha, género).
- Mapa interactivo de la sala: verde (disponible), gris (ocupado), amarillo (bloqueado), azul (seleccionado), con temporizador de 2 minutos.
- Módulo de pago simulado con desglose de tarifas y promociones.
- Pantalla de confirmación con el boleto y el QR generado con la librería `qrcode`.
- Pantalla de validación en puerta (check-in) con el mensaje "Entrada ya utilizada".
- Panel de administración: métricas, alta de películas, programación de funciones, salas y precios.
- Restricción de pantallas según el rol del usuario.

## Cronograma

| Día | Luis | P1 | P2 |
|---|---|---|---|
| **Lun 19** | Reunión de arranque (todos): clonar repo, crear ramas, acordar lista de entidades y nombres de tablas. DER conceptual. | Dictamen de rechazo. Requerimientos funcionales y no funcionales. | Entorno (requerimientos.txt, config.py). Esqueleto de la app: conexión, login por rol y navegación. |
| **Mar 20** | Modelo lógico/relacional. Script DDL con restricciones. | Volúmenes esperados y tabla de almacenamiento a 5 años. | Vista de cartelera con filtros. |
| **Mié 21** | Funciones de bloqueo, compra y pago simulado; emisión del código del boleto; bitácoras. Datos de prueba. **Integrar a main.** | Comparativa de proveedores cloud y proyección CAPEX/OPEX a 3 años. | Mapa interactivo de asientos con colores y temporizador. |
| **Jue 22** | Validación en puerta, cancelación/reembolso, control de traslapes de funciones. Roles PostgreSQL (RBAC). **Integrar a main.** | Matriz de riesgo y mitigación. Fase 5 (respaldos, DR, RTO/RPO, SLA). | Pago simulado y pantalla de confirmación con QR. |
| **Vie 23** | Script de prueba de concurrencia (20–50 hilos) y evidencias. | Índices, 4 consultas analíticas y EXPLAIN ANALYZE antes/después. | Pantalla de puerta (check-in) y panel de administración. Restricción por roles. |
| **Sáb 24** | Imagen del modelo relacional documentado. Integración y pruebas de la pauta completa (todos). | Ensamblar el documento técnico. Integración y pruebas (todos). | Correcciones de la interfaz. Integración y pruebas (todos). |
| **Dom 25** | Revisión final de coherencia (todos). README final y evidencias en `capturas/`. Entrega del enlace en TecDigital antes de las 23:59. | Revisión final del documento. | Grabación de la demostración de los flujos (si se entrega grabada). |

## Dependencias a tener en cuenta

- P2 puede avanzar lunes y martes sin el DDL final (esqueleto, cartelera con pocos datos); desde el miércoles necesita el DDL y las funciones en `main`.
- P1 necesita el DDL y los datos de prueba en `main` para las consultas analíticas y EXPLAIN ANALYZE del viernes.
- Los requerimientos de P1 y el DER de Luis deben usar las mismas entidades y nombres.
