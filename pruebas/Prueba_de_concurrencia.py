# Prueba de concurrencia: Asientos con doble venta

# Ejecutar desde la carpeta raíz del repositorio:
#   pruebas/Prueba_de_concurrencia.py          (30 hilos)
#   pruebas/Prueba_de_concurrencia 50       (50 hilos)

# Prueba 1 - Bloqueo simultáneo:
#   N clientes intentar tener el mismo asiento a la vez

# Prueba 2 - Inserción simultánea del boleto (BEGIN / COMMIT / ROLLBACK):
#   Se intentan registrar N compras simultaneas con boleto a un mismo asiento

import os
import sys
import threading
import getpass
import datetime
import psycopg2

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "app"))
from config import DB_CONFIG

HILOS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
EVIDENCIA = os.path.join(RAIZ, "capturas", "evidencia_concurrencia.txt")

lineas = []

def registrar(texto=""):
    print(texto)
    lineas.append(texto)

def conectar_app():
    # Usa el usuario creado en roles de seguridad
    con = psycopg2.connect(**DB_CONFIG)
    con.cursor().execute("SET search_path TO prototipo")
    return con

def conectar_admin(clave):
    # Conexion a postgres
    datos = dict(DB_CONFIG)
    datos["user"] = "postgres"
    datos["password"] = clave
    datos.pop("options", None)
    con = psycopg2.connect(**datos)
    con.cursor().execute("SET search_path TO prototipo")
    return con

# Elige una función basada en asientos disponibles
def preparar(con):
    cur = con.cursor()
    cur.execute("""
        SELECT v.id_funcion, v.id_asiento, v.fila || v.numero, v.zona, p.titulo, f.fecha_hora_inicio
        FROM vista_estado_asientos v
        JOIN funcion f  ON f.id_funcion  = v.id_funcion
        JOIN pelicula p ON p.id_pelicula = f.id_pelicula
        WHERE v.estado = 'disponible' AND f.estado = 'programada' AND f.fecha_hora_inicio > NOW()
        ORDER BY f.fecha_hora_inicio, v.id_asiento
        LIMIT 2
    """)
    asientos = cur.fetchall()
    if len(asientos) < 2 or asientos[0][0] != asientos[1][0]:
        sys.exit("No hay una función futura con al menos 2 asientos disponibles.")
    cur.execute("SELECT id_usuario FROM usuario WHERE rol = 'cliente' AND activo ORDER BY id_usuario")
    clientes = [fila[0] for fila in cur.fetchall()]
    if not clientes:
        sys.exit("No hay clientes registrados.")

    cur.execute("SELECT id_tarifa, precio FROM tarifa WHERE tipo_entrada = 'adulto' AND zona = %s", (asientos[1][3],))
    tarifa = cur.fetchone()
    con.commit()
    return asientos, clientes, tarifa

# Prueba 1 - Bloqueo simultáneo
def hilo_bloqueo(n, id_funcion, id_asiento, id_cliente, barrera, resultados):
    con = None
    try:
        con = conectar_app()
        cur = con.cursor()
        cur.execute("SET ROLE rol_cliente")
        cur.execute("SELECT set_config('app.id_usuario', %s, false)", (str(id_cliente),))
        con.commit()
        barrera.wait()   # todos los hilos arrancan al mismo tiempo
        cur.execute("SELECT fn_bloquear_asiento(%s, %s, %s)", (id_funcion, id_asiento, id_cliente))
        id_bloqueo = cur.fetchone()[0]
        con.commit()
        resultados[n] = ("ÉXITO", f"bloqueo {id_bloqueo} a nombre del cliente {id_cliente}")
    except psycopg2.Error as e:
        if con:
            con.rollback()
        resultados[n] = ("RECHAZADO", e.diag.message_primary or str(e).strip())
    finally:
        if con:
            con.close()

# Prueba 2: inserción simultánea
def hilo_boleto(n, clave, id_funcion, id_asiento, zona, id_tarifa, precio, id_cliente, barrera, resultados):
    con = None
    try:
        con = conectar_admin(clave)
        cur = con.cursor()
        con.commit()
        barrera.wait()
        cur.execute("""INSERT INTO compra (canal, subtotal, total, estado, id_usuario_cliente)
                       VALUES ('online', %s, %s, 'pagada', %s) RETURNING id_compra""",
                    (precio, precio, id_cliente))
        id_compra = cur.fetchone()[0]
        cur.execute("""INSERT INTO boleto (codigo_qr, precio, id_funcion, id_asiento, id_tarifa, id_compra)
                       VALUES (fn_generar_codigo_qr(%s, %s, %s), %s, %s, %s, %s, %s)
                       RETURNING codigo_qr""",
                    (id_funcion, id_asiento, zona, precio, id_funcion, id_asiento, id_tarifa, id_compra))
        codigo = cur.fetchone()[0]
        con.commit()     # COMMIT
        resultados[n] = ("COMMIT", f"compra {id_compra}, boleto {codigo}")
    except psycopg2.Error as e:
        if con:
            con.rollback() # Deshace la compra
        resultados[n] = ("ROLLBACK", e.diag.message_primary or str(e).strip())
    finally:
        if con:
            con.close()

def ejecutar(objetivo, argumentos_por_hilo):
    barrera = threading.Barrier(HILOS)
    resultados = {}
    hilos = [threading.Thread(target=objetivo, args=(n, *argumentos_por_hilo(n), barrera, resultados))
             for n in range(1, HILOS + 1)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return resultados

def mostrar(resultados, exito):
    for n in sorted(resultados):
        estado, detalle = resultados[n]
        registrar(f"  Hilo {n:02d}: {estado:<9} {detalle}")
    exitos = sum(1 for e, _ in resultados.values() if e == exito)
    registrar(f"  Resumen: {exitos} {exito} y {len(resultados) - exitos} rechazados de {len(resultados)} hilos")
    return exitos

def main():
    clave = getpass.getpass("Contraseña del usuario postgres (para la prueba 2): ")
    admin = conectar_admin(clave)
    asientos, clientes, (id_tarifa, precio) = preparar(admin)

    registrar("=" * 78)
    registrar("PRUEBA DE CONCURRENCIA - DOBLE VENTA DE ASIENTOS")
    registrar(f"Fecha: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}    Hilos simultáneos: {HILOS}")
    registrar("=" * 78)

    # Prueba 1
    f1, a1, nombre1, zona1, titulo, inicio = asientos[0]
    registrar()
    registrar(f"PRUEBA 1 - Bloqueo simultáneo: función {f1} ({titulo}, {inicio:%d/%m %H:%M}), "
              f"asiento {nombre1} ({zona1}, id {a1})")
    res1 = ejecutar(hilo_bloqueo, lambda n: (f1, a1, clientes[n % len(clientes)]))
    ok1 = mostrar(res1, "ÉXITO")
    cur = admin.cursor()
    cur.execute("SELECT count(*) FROM bloqueo_asiento WHERE id_funcion = %s AND id_asiento = %s AND estado = 'activo'",
                (f1, a1))
    registrar(f"  Verificación en la BD: {cur.fetchone()[0]} bloqueo(s) activo(s) para ese asiento")
    admin.commit()

    # Prueba 2
    f2, a2, nombre2, zona2, _, _ = asientos[1]
    cur.execute("SELECT count(*) FROM compra")
    compras_antes = cur.fetchone()[0]
    admin.commit()
    registrar()
    registrar(f"PRUEBA 2 - Inserción simultánea del boleto: función {f2}, asiento {nombre2} ({zona2}, id {a2})")
    res2 = ejecutar(hilo_boleto, lambda n: (clave, f2, a2, zona2, id_tarifa, precio, clientes[n % len(clientes)]))
    ok2 = mostrar(res2, "COMMIT")
    cur.execute("SELECT count(*) FROM boleto WHERE id_funcion = %s AND id_asiento = %s AND estado <> 'anulado'",
                (f2, a2))
    boletos = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM compra")
    compras_nuevas = cur.fetchone()[0] - compras_antes
    admin.commit()
    registrar(f"  Verificación en la BD: {boletos} boleto(s) vigente(s) para ese asiento y "
              f"{compras_nuevas} compra(s) nueva(s) (las {HILOS - 1} restantes se deshicieron con ROLLBACK)")

    registrar()
    aprobado = ok1 == 1 and ok2 == 1 and boletos == 1 and compras_nuevas == 1
    registrar("RESULTADO: " + ("APROBADO - no hubo doble venta" if aprobado else "REVISAR - el resultado no es el esperado"))
    registrar("=" * 78)
    admin.close()

    os.makedirs(os.path.dirname(EVIDENCIA), exist_ok=True)
    with open(EVIDENCIA, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas) + "\n")
    print(f"\nEvidencia guardada en {EVIDENCIA}")

if __name__ == "__main__":
    main()