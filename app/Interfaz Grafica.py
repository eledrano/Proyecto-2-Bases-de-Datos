import csv, hashlib, json, os, re, secrets, socket, string, time
import tkinter as tk
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta
from tkinter import ttk, messagebox, filedialog
 
import psycopg2
from psycopg2 import Error
from psycopg2 import sql as pgsql
 
try:
    import qrcode
except ImportError:
    qrcode = None

# ----------------------------------------------------------------------------
# CONEXIÓN Y UTILIDADES DE BASE DE DATOS
# ----------------------------------------------------------------------------
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db_config.json")
DB = {"host": os.getenv("CINE_DB_HOST", "localhost"), "port": os.getenv("CINE_DB_PORT", "5432"),
      "database": os.getenv("CINE_DB_NAME", "cine"), "user": os.getenv("CINE_DB_USER", "postgres"),
      "password": os.getenv("CINE_DB_PASSWORD", "")}
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, encoding="utf-8") as fh:
            DB.update(json.load(fh))
    except (OSError, ValueError):
        pass

COLORES = {"disponible": "#4CAF50", "ocupado": "#9E9E9E", "bloqueado": "#FFC107", "mio": "#2196F3"}
TIPOS_ENTRADA = ["adulto", "nino", "tercera_edad", "estudiante"]
METODOS = ["tarjeta", "paypal", "transferencia", "billetera_digital"]

SESION = {"rol": None, "uid": None}   # se llena después del login


def conectar():
    con = psycopg2.connect(options="-c search_path=prototipo", connect_timeout=5, **DB)
    if SESION["rol"]:
        cur = con.cursor()
        cur.execute(pgsql.SQL("SET ROLE {}").format(pgsql.Identifier("rol_" + SESION["rol"])))
        cur.execute("SELECT set_config('app.id_usuario', %s, false)", (str(SESION["uid"]),))
        con.commit()
        cur.close()
    return con


@contextmanager
def transaccion():
    """Una transacción (BEGIN/COMMIT/ROLLBACK): si algo falla se revierte todo."""
    con = conectar()
    try:
        cur = con.cursor()
        yield cur
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()


def consultar(sql, params=None):
    with transaccion() as cur:
        cur.execute(sql, params)
        return cur.fetchall() if cur.description else []


def ejecutar(sql, params=None):
    with transaccion() as cur:
        cur.execute(sql, params)
        return cur.fetchone() if cur.description else None


def msg_error(e):
    texto = (getattr(e, "pgerror", None) or str(e)).strip()
    linea = re.sub(r"^ERROR:\s*", "", texto.splitlines()[0] if texto else "Error desconocido")
    codigo = getattr(e, "pgcode", None)
    if codigo == "23505":
        return "Ya existe un registro con esos datos (restricción de unicidad)."
    if codigo == "23503":
        return "No se puede completar: hay registros relacionados (funciones, boletos o bloqueos)."
    if codigo == "23514":
        return "El dato no cumple una restricción de la base de datos:\n" + linea
    if codigo == "42501":
        return "Su rol no tiene permiso para esta acción (permisos por rol o RN-18 en la base de datos)."
    if codigo == "42883":
        return "La base de datos no tiene la función requerida:\n" + linea
    return linea


def auditar(cur, app, accion, tabla, id_registro, detalle):
    """RN-20: toda acción manual del administrador queda en admin_operacion_audit."""
    cur.execute("""INSERT INTO admin_operacion_audit
                   (accion, tabla_afectada, id_registro_afectado, detalle, rol, direccion_ip, id_usuario)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (accion, tabla, id_registro, detalle, app.rol, app.ip, app.uid))


def sala_con_ventas(id_sala):
    ejecutar("SELECT fn_liberar_bloqueos_expirados()")
    return ejecutar("SELECT fn_sala_tiene_ventas(%s)", (id_sala,))[0]


def ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def colones(x):
    return f"₡{float(x):,.0f}"


# ----------------------------------------------------------------------------
# UTILIDADES DE INTERFAZ
# ----------------------------------------------------------------------------
def configurar_estilo(root):
    st = ttk.Style(root)
    st.theme_use("clam")
    st.configure("Titulo.TLabel", font=("Arial", 16, "bold"))
    st.configure("Sub.TLabel", font=("Arial", 12, "bold"))
    st.configure("Treeview", rowheight=24)
    st.configure("Treeview.Heading", font=("Arial", 10, "bold"))
    st.configure("Accion.TButton", font=("Arial", 10, "bold"), padding=6)


def tema(win):
    win.configure(bg=ttk.Style().lookup("TFrame", "background"))


def crear_tabla(parent, columnas, anchos=None, height=10):
    fr = ttk.Frame(parent)
    tv = ttk.Treeview(fr, columns=columnas, show="headings", height=height)
    sb = ttk.Scrollbar(fr, orient="vertical", command=tv.yview)
    tv.configure(yscrollcommand=sb.set)
    for i, c in enumerate(columnas):
        tv.heading(c, text=c)
        tv.column(c, width=anchos[i] if anchos else 110, anchor="center")
    tv.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    return fr, tv


def llenar(tv, filas):
    tv.delete(*tv.get_children())
    for f in filas:
        tv.insert("", "end", values=["" if v is None else v for v in f])


class Dialogo(tk.Toplevel):
    def __init__(self, parent, titulo, campos):
        super().__init__(parent)
        tema(self)
        self.title(titulo)
        self.resultado = None
        self.resizable(False, False)
        self.transient(parent)
        self.vars = {}
        for i, (k, et, ini, *resto) in enumerate(campos):
            ttk.Label(self, text=et).grid(row=i, column=0, sticky="w", padx=10, pady=4)
            v = tk.StringVar(value=ini)
            self.vars[k] = v
            if resto and resto[0]:
                w = ttk.Combobox(self, textvariable=v, values=resto[0], state="readonly", width=32)
            else:
                w = ttk.Entry(self, textvariable=v, width=35, show="*" if k == "password" else "")
            w.grid(row=i, column=1, padx=10, pady=4)
        bt = ttk.Frame(self)
        bt.grid(row=len(campos), column=0, columnspan=2, pady=10)
        ttk.Button(bt, text="Aceptar", command=self.aceptar).pack(side="left", padx=6)
        ttk.Button(bt, text="Cancelar", command=self.destroy).pack(side="left", padx=6)
        self.bind("<Return>", lambda e: self.aceptar())
        self.wait_visibility()
        self.grab_set()
        self.wait_window()

    def aceptar(self):
        self.resultado = {k: v.get().strip() for k, v in self.vars.items()}
        self.destroy()


def pedir(parent, titulo, campos):
    return Dialogo(parent, titulo, campos).resultado


def matriz_qr(texto):
    if qrcode:
        q = qrcode.QRCode(border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
        q.add_data(texto)
        q.make(fit=True)
        return q.get_matrix()
    # Respaldo visual si no está instalada la librería "qrcode" (no es escaneable)
    n = 25
    bits = "".join(f"{b:08b}" for b in hashlib.sha256(texto.encode()).digest() * 4)
    m = [[bits[(r * n + c) % len(bits)] == "1" for c in range(n)] for r in range(n)]
    for r0, c0 in ((0, 0), (0, n - 7), (n - 7, 0)):
        for r in range(7):
            for c in range(7):
                m[r0 + r][c0 + c] = r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4)
    return m


def dibujar_qr(canvas, texto, lado=170):
    m = matriz_qr(texto)
    n = len(m)
    t = max(1, lado // n)
    off = (lado - t * n) // 2
    canvas.delete("all")
    for r, fila in enumerate(m):
        for c, v in enumerate(fila):
            if v:
                canvas.create_rectangle(off + c * t, off + r * t, off + (c + 1) * t, off + (r + 1) * t,
                                        fill="black", outline="")


# ----------------------------------------------------------------------------
# PANELES GENÉRICOS (consulta + exportación + acciones)
# ----------------------------------------------------------------------------
class PanelConsulta(ttk.Frame):
    def __init__(self, parent, titulo, columnas, sql, params=None, anchos=None,
                 acciones=(), pie=None, exportar=True):
        super().__init__(parent, padding=8)
        self.sql, self.params, self.pie, self.filas = sql, params, pie, []
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text=titulo, style="Sub.TLabel").pack(side="left")
        if exportar:
            ttk.Button(top, text="Exportar CSV", command=self.exportar).pack(side="right")
        ttk.Button(top, text="Actualizar", command=self.cargar).pack(side="right", padx=4)
        fr, self.tv = crear_tabla(self, columnas, anchos)
        fr.pack(fill="both", expand=True, pady=6)
        self.lbl_pie = ttk.Label(self, text="")
        self.lbl_pie.pack(anchor="w")
        if acciones:
            bar = ttk.Frame(self)
            bar.pack(fill="x", pady=4)
            for texto, fn, req in acciones:
                ttk.Button(bar, text=texto, command=lambda f=fn, r=req: self.accion(f, r)).pack(side="left", padx=4)
            if acciones[0][2]:
                self.tv.bind("<Double-1>", lambda e: self.accion(acciones[0][1], True))
        self.cargar()

    def refrescar(self):
        self.cargar()

    def cargar(self):
        p = self.params() if callable(self.params) else self.params
        try:
            self.filas = consultar(self.sql, p)
        except Error as e:
            messagebox.showerror("Error de consulta", msg_error(e))
            return
        llenar(self.tv, self.filas)
        self.lbl_pie.config(text=self.pie(self.filas) if self.pie else f"{len(self.filas)} registro(s)")

    def accion(self, fn, requiere):
        vals = None
        if requiere:
            sel = self.tv.selection()
            if not sel:
                messagebox.showinfo("Seleccione una fila", "Seleccione primero una fila de la tabla.")
                return
            vals = self.tv.item(sel[0], "values")
        try:
            fn(vals)
        except Error as e:
            messagebox.showerror("No se pudo completar la acción", msg_error(e))
        self.cargar()

    def exportar(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not ruta:
            return
        with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(self.tv["columns"])
            w.writerows(self.filas)
        messagebox.showinfo("Exportación", f"Archivo guardado en:\n{ruta}")


class Grupo(ttk.Frame):
    def __init__(self, parent, paneles):
        super().__init__(parent)
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.hijos = []
        for titulo, fabrica in paneles:
            h = fabrica(self.nb)
            self.nb.add(h, text=titulo)
            self.hijos.append(h)

    def refrescar(self):
        for h in self.hijos:
            h.refrescar()


# ----------------------------------------------------------------------------
# CARTELERA (RN-01, RN-02)
# ----------------------------------------------------------------------------
class Cartelera(ttk.Frame):
    COLS = ("ID Función", "Película", "Clasif.", "Min", "Géneros", "Cine", "Ciudad", "Sala", "Inicio")

    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app, self.detalle = app, {}
        f = ttk.Frame(self)
        f.pack(fill="x")
        ttk.Label(f, text="Cine / ubicación:").pack(side="left")
        self.cb_cine = ttk.Combobox(f, state="readonly", width=28)
        self.cb_cine.pack(side="left", padx=4)
        ttk.Label(f, text="Fecha (AAAA-MM-DD):").pack(side="left", padx=(10, 0))
        self.e_fecha = ttk.Entry(f, width=12)
        self.e_fecha.pack(side="left", padx=4)
        ttk.Label(f, text="Género:").pack(side="left", padx=(10, 0))
        self.cb_gen = ttk.Combobox(f, state="readonly", width=16)
        self.cb_gen.pack(side="left", padx=4)
        ttk.Button(f, text="Buscar", command=self.buscar).pack(side="left", padx=4)
        ttk.Button(f, text="Limpiar", command=self.limpiar).pack(side="left")
        fr, self.tv = crear_tabla(self, self.COLS, (70, 190, 60, 50, 180, 110, 110, 70, 130), 10)
        fr.pack(fill="both", expand=True, pady=6)
        self.tv.bind("<<TreeviewSelect>>", self.mostrar)
        self.txt = tk.Text(self, height=7, wrap="word", state="disabled", bg="#FAFAFA")
        self.txt.pack(fill="x")
        if app.rol in ("cliente", "taquillero"):
            ttk.Button(self, text="Seleccionar asientos de la función…", style="Accion.TButton",
                       command=self.abrir_mapa).pack(pady=6)
        self.cines = {"Todos": None}
        for i, n, c in consultar("SELECT id_cine, nombre, ciudad FROM cine ORDER BY id_cine"):
            self.cines[f"{n} - {c}"] = i
        self.cb_cine["values"] = list(self.cines)
        gens = ["Todos"] + [g for (g,) in consultar("SELECT DISTINCT genero FROM pelicula_generos ORDER BY 1")]
        self.cb_gen["values"] = gens
        self.limpiar()

    def limpiar(self):
        self.cb_cine.set("Todos")
        self.cb_gen.set("Todos")
        self.e_fecha.delete(0, "end")
        self.buscar()

    def refrescar(self):
        self.buscar()

    def buscar(self):
        # RN-01: solo películas activas y funciones programadas con inicio futuro
        sql = """SELECT f.id_funcion, p.titulo, p.clasificacion, p.duracion_min,
                   COALESCE((SELECT string_agg(g.genero, ', ' ORDER BY g.genero)
                             FROM pelicula_generos g WHERE g.id_pelicula = p.id_pelicula), ''),
                   ci.nombre, ci.ciudad, s.nombre, to_char(f.fecha_hora_inicio, 'YYYY-MM-DD HH24:MI'),
                   p.sinopsis, ci.direccion, ci.pais
                 FROM funcion f JOIN pelicula p ON p.id_pelicula = f.id_pelicula
                 JOIN sala s ON s.id_sala = f.id_sala JOIN cine ci ON ci.id_cine = s.id_cine
                 WHERE p.activa AND f.estado = 'programada' AND f.fecha_hora_inicio > NOW()"""
        params = []
        id_cine = self.cines.get(self.cb_cine.get())
        if id_cine:
            sql += " AND ci.id_cine = %s"
            params.append(id_cine)
        fecha = self.e_fecha.get().strip()
        if fecha:
            try:
                datetime.strptime(fecha, "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning("Fecha inválida", "Use el formato AAAA-MM-DD (ej. 2026-10-24).")
                return
            sql += " AND f.fecha_hora_inicio::date = %s"
            params.append(fecha)
        if self.cb_gen.get() not in ("", "Todos"):
            sql += """ AND EXISTS (SELECT 1 FROM pelicula_generos g
                                   WHERE g.id_pelicula = p.id_pelicula AND g.genero = %s)"""
            params.append(self.cb_gen.get())
        sql += " ORDER BY f.fecha_hora_inicio"
        try:
            filas = consultar(sql, params)
        except Error as e:
            messagebox.showerror("Error de consulta", msg_error(e))
            return
        self.tv.delete(*self.tv.get_children())
        self.detalle = {}
        for f in filas:
            self.tv.insert("", "end", iid=str(f[0]), values=f[:9])
            self.detalle[str(f[0])] = f
        self.mostrar()

    def mostrar(self, _=None):
        sel = self.tv.selection()
        self.txt.config(state="normal")
        self.txt.delete("1.0", "end")
        if sel:
            f = self.detalle[sel[0]]
            self.txt.insert("end", f"{f[1]}  ({f[2]} · {f[3]} min)\nGéneros: {f[4]}\n\n{f[9] or 'Sin sinopsis'}\n\n"
                                   f"Ubicación: {f[5]} - {f[10]}, {f[6]}, {f[11]} · {f[7]}\nInicio: {f[8]}")
        else:
            self.txt.insert("end", "Seleccione una función para ver la sinopsis y la ubicación exacta de la sala.")
        self.txt.config(state="disabled")

    def abrir_mapa(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showinfo("Seleccione una función", "Elija primero una función de la tabla.")
            return
        MapaAsientos(self.app, int(sel[0]))


# ----------------------------------------------------------------------------
# MAPA INTERACTIVO DE LA SALA (RN-03, RN-04, RN-05)
# ----------------------------------------------------------------------------
SQL_MAPA = """
SELECT v.id_asiento, v.fila, v.numero, v.zona, v.estado
FROM vista_estado_asientos v
WHERE v.id_funcion = %s
ORDER BY v.fila, v.numero"""

class MapaAsientos(tk.Toplevel):
    def __init__(self, app, id_funcion):
        super().__init__(app)
        tema(self)
        self.app, self.id_funcion = app, id_funcion
        self.title("Mapa interactivo de la sala")
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        f = consultar("""SELECT p.titulo, p.clasificacion, ci.nombre, ci.direccion, s.nombre, f.fecha_hora_inicio
                         FROM funcion f JOIN pelicula p ON p.id_pelicula = f.id_pelicula
                         JOIN sala s ON s.id_sala = f.id_sala JOIN cine ci ON ci.id_cine = s.id_cine
                         WHERE f.id_funcion = %s""", (id_funcion,))[0]
        self.fecha = f[5]
        ttk.Label(self, text=f"{f[0]} ({f[1]})", style="Titulo.TLabel").pack(pady=(10, 0))
        ttk.Label(self, text=f"{f[2]} - {f[3]} · {f[4]} · {f[5]:%Y-%m-%d %H:%M}").pack()
        ley = ttk.Frame(self)
        ley.pack(pady=6)
        for clave, txt in (("disponible", "Disponible"), ("ocupado", "Ocupado"),
                           ("bloqueado", "Bloqueado (otro usuario)"), ("mio", "Seleccionado por usted")):
            tk.Label(ley, bg=COLORES[clave], width=2).pack(side="left", padx=(10, 2))
            ttk.Label(ley, text=txt).pack(side="left")
        tk.Label(self, text="P A N T A L L A", bg="#333", fg="white").pack(fill="x", padx=60, pady=8)
        self.frm = ttk.Frame(self)
        self.frm.pack(pady=8, padx=10)
        self.lbl_sel = ttk.Label(self, text="")
        self.lbl_sel.pack()
        self.lbl_t = ttk.Label(self, text="", font=("Arial", 11, "bold"))
        self.lbl_t.pack(pady=4)
        bt = ttk.Frame(self)
        bt.pack(pady=8)
        ttk.Button(bt, text="Continuar al pago", style="Accion.TButton", command=self.continuar).pack(side="left", padx=6)
        ttk.Button(bt, text="Cancelar y liberar", command=self.cerrar).pack(side="left", padx=6)
        self.widgets, self.estado, self.mios, self.n = {}, {}, {}, 0
        self.refrescar()
        self.tick()


    def construir(self, filas):
        self.info = {}
        por_fila = {}
        for r in filas:
            por_fila.setdefault(r[1], []).append(r)
        for i, (fila, asientos) in enumerate(sorted(por_fila.items())):
            ttk.Label(self.frm, text=fila, width=3).grid(row=i, column=0)
            for r in asientos:
                self.info[r[0]] = (r[1], r[2], r[3])
                lb = tk.Label(self.frm, text=f"{r[1]}{r[2]}", width=4, height=2, relief="raised", bd=2, cursor="hand2")
                lb.grid(row=i, column=r[2], padx=2, pady=2)
                lb.bind("<Button-1>", lambda e, a=r[0]: self.click(a))
                self.widgets[r[0]] = lb
            ttk.Label(self.frm, text=asientos[0][3], width=9).grid(row=i, column=100, padx=6)

    def refrescar(self):
        try:
            consultar("SELECT fn_liberar_bloqueos_expirados()")
            filas = consultar(SQL_MAPA, (self.id_funcion,))
        except Error as e:
            messagebox.showerror("Error", msg_error(e), parent=self)
            return
        if not self.widgets:
            self.construir(filas)
        ahora = time.time()
        for id_a, fila, num, zona, est in filas:
            if id_a in self.mios:
                if est == "bloqueado" and self.mios[id_a]["deadline"] > ahora:
                    est = "mio"                # es un bloqueo mío y sigue vigente
                else:
                    del self.mios[id_a]        # expiró, se liberó o ya se vendió
            self.estado[id_a] = est
            self.widgets[id_a].config(bg=COLORES[est])
        sel = sorted(f"{d['fila']}{d['numero']}" for d in self.mios.values())
        self.lbl_sel.config(text=f"Asientos seleccionados ({len(sel)}/6): " + (", ".join(sel) or "ninguno"))

    def click(self, id_asiento):
        est = self.estado.get(id_asiento)
        try:
            if est == "disponible":
                t0 = time.time()
                id_bl = ejecutar("SELECT fn_bloquear_asiento(%s,%s,%s)",
                                 (self.id_funcion, id_asiento, self.app.uid))[0]
                fila, num, zona = self.info[id_asiento]
                # La vista no dice quién bloqueó ni cuándo expira: se recuerda aquí (2 minutos desde el clic)
                self.mios[id_asiento] = {"bloqueo": id_bl, "deadline": t0 + 120, "fila": fila,
                                         "numero": num, "zona": zona}
            elif est == "mio":
                ejecutar("SELECT fn_liberar_asiento(%s,%s)", (self.mios[id_asiento]["bloqueo"], self.app.uid))
                del self.mios[id_asiento]
            else:
                messagebox.showinfo("Asiento no disponible",
                                    "Ese asiento está " + ("vendido." if est == "ocupado" else
                                                           "bloqueado por otro usuario."), parent=self)
        except Error as e:
            messagebox.showwarning("No se pudo seleccionar", msg_error(e), parent=self)
        self.refrescar()

    def tick(self):
        if not self.winfo_exists():
            return
        self.n += 1
        if self.mios:
            rest = min(d["deadline"] for d in self.mios.values()) - time.time()
            if rest <= 0:
                self.refrescar()
            else:
                self.lbl_t.config(text=f"Tiempo restante del bloqueo más próximo: {int(rest // 60):02d}:{int(rest % 60):02d}",
                                  foreground="#C62828" if rest < 30 else "#000000")
        else:
            self.lbl_t.config(text="Sin asientos bloqueados", foreground="#000000")
        if self.n % 5 == 0:
            self.refrescar()
        self.after(1000, self.tick)

    def continuar(self):
        self.refrescar()
        if not self.mios:
            messagebox.showinfo("Sin asientos", "Seleccione al menos un asiento disponible.", parent=self)
            return
        VentanaPago(self, sorted(self.mios.values(), key=lambda d: (d["fila"], d["numero"])))

    def cerrar(self):
        for d in list(self.mios.values()):
            try:
                ejecutar("SELECT fn_liberar_asiento(%s,%s)", (d["bloqueo"], self.app.uid))
            except Error:
                pass
        self.destroy()


# ----------------------------------------------------------------------------
# MÓDULO DE PAGO SIMULADO (RN-07, RN-08, RN-09, RN-10)
# ----------------------------------------------------------------------------
class VentanaPago(tk.Toplevel):
    def __init__(self, mapa, asientos):
        super().__init__(mapa)
        tema(self)
        self.mapa, self.app, self.asientos = mapa, mapa.app, asientos
        self.canal = "online" if self.app.rol == "cliente" else "taquilla"
        self.title("Módulo de pago (simulado)")
        self.tarifas = {(t, z): float(p) for t, z, p in consultar("SELECT tipo_entrada, zona, precio FROM tarifa")}
        cont = ttk.Frame(self, padding=12)
        cont.pack(fill="both", expand=True)
        ttk.Label(cont, text="Resumen de compra", style="Titulo.TLabel").pack()
        if self.canal == "taquilla":
            lf = ttk.LabelFrame(cont, text="Cliente", padding=6)
            lf.pack(fill="x", pady=4)
            self.cb_cli = ttk.Combobox(lf, state="readonly", width=45)
            self.cb_cli.pack(side="left")
            ttk.Button(lf, text="Nuevo cliente", command=self.nuevo_cliente).pack(side="left", padx=6)
            self.cargar_clientes()
        le = ttk.LabelFrame(cont, text="Entradas (tipo de entrada por asiento)", padding=6)
        le.pack(fill="x", pady=4)
        self.combos, self.lbl_p = [], []
        for i, d in enumerate(asientos):
            ttk.Label(le, text=f"Asiento {d['fila']}{d['numero']} ({d['zona']})").grid(row=i, column=0, sticky="w", padx=6)
            cb = ttk.Combobox(le, values=TIPOS_ENTRADA, state="readonly", width=14)
            cb.set("adulto")
            cb.grid(row=i, column=1, padx=6, pady=2)
            cb.bind("<<ComboboxSelected>>", lambda e: self.recalcular())
            lp = ttk.Label(le, text="")
            lp.grid(row=i, column=2, padx=6)
            self.combos.append(cb)
            self.lbl_p.append(lp)
        ld = ttk.LabelFrame(cont, text="Desglose (promociones aplicadas automáticamente)", padding=6)
        ld.pack(fill="x", pady=4)
        self.lbls = {}
        for i, k in enumerate(("Subtotal", "Promoción 2x1", "Día de descuento (miércoles 20%)",
                               "Cargo por servicio", "TOTAL")):
            fuente = ("Arial", 10, "bold" if k == "TOTAL" else "normal")
            ttk.Label(ld, text=k, font=fuente).grid(row=i, column=0, sticky="w", padx=6)
            self.lbls[k] = ttk.Label(ld, text="", font=fuente)
            self.lbls[k].grid(row=i, column=1, sticky="e", padx=30)
        lp = ttk.LabelFrame(cont, text="Datos de pago simulados (no se guardan en la BD - RN-09)", padding=6)
        lp.pack(fill="x", pady=4)
        ttk.Label(lp, text="Método:").grid(row=0, column=0, sticky="w")
        self.metodo = ttk.Combobox(lp, values=METODOS, state="readonly", width=20)
        self.metodo.set("tarjeta")
        self.metodo.grid(row=0, column=1, sticky="w", pady=2)
        self.metodo.bind("<<ComboboxSelected>>", self.cambio_metodo)
        self.e = {}
        for i, (k, et, ini, oculto) in enumerate((("num", "Número de tarjeta", "4111 1111 1111 1111", False),
                                                  ("tit", "Titular", self.app.nombre.upper(), False),
                                                  ("ven", "Vencimiento (MM/AA)", "12/30", False),
                                                  ("cvv", "CVV", "123", True)), start=1):
            ttk.Label(lp, text=et).grid(row=i, column=0, sticky="w")
            self.e[k] = ttk.Entry(lp, width=26, show="*" if oculto else "")
            self.e[k].insert(0, ini)
            self.e[k].grid(row=i, column=1, sticky="w", pady=2)
        self.resultado = tk.StringVar(value="aprobado")
        ttk.Label(lp, text="Respuesta simulada de la pasarela:").grid(row=5, column=0, sticky="w", pady=(6, 0))
        rf = ttk.Frame(lp)
        rf.grid(row=5, column=1, sticky="w", pady=(6, 0))
        ttk.Radiobutton(rf, text="Aprobar", variable=self.resultado, value="aprobado").pack(side="left")
        ttk.Radiobutton(rf, text="Rechazar", variable=self.resultado, value="rechazado").pack(side="left", padx=10)
        self.lbl_t = ttk.Label(cont, text="", font=("Arial", 11, "bold"))
        self.lbl_t.pack(pady=4)
        bt = ttk.Frame(cont)
        bt.pack()
        ttk.Button(bt, text="Pagar", style="Accion.TButton", command=self.pagar).pack(side="left", padx=6)
        ttk.Button(bt, text="Volver al mapa", command=self.destroy).pack(side="left", padx=6)
        self.recalcular()
        self.tick()
        self.transient(mapa)
        self.wait_visibility()
        self.grab_set()


    def cargar_clientes(self):
        try:
            filas = consultar("SELECT id_usuario, nombre, correo FROM fn_listar_clientes()")
        except Error:
            filas = [] 
        self.clientes = {f"{n} ({c})": i for i, n, c in filas}
        self.cb_cli["values"] = list(self.clientes)

    def nuevo_cliente(self):
        r = pedir(self, "Nuevo cliente", [("nombre", "Primer nombre", ""), ("apellido", "Primer apellido", ""),
                                          ("apellido2", "Segundo apellido (opcional)", ""), ("correo", "Correo", "")])
        self.grab_set()
        if not r:
            return
        if not (r["nombre"] and r["apellido"] and "@" in r["correo"]):
            messagebox.showwarning("Datos incompletos", "Indique nombre, apellido y un correo válido.", parent=self)
            return
        clave = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        try:
            nid = ejecutar("SELECT fn_registrar_usuario(%s,%s,%s,%s,%s,'cliente',%s)",
                           (r["nombre"], r["apellido"], r["apellido2"] or None, r["correo"], clave, self.app.uid))[0]
        except Error as e:
            messagebox.showerror("No se pudo registrar", msg_error(e), parent=self)
            return
        messagebox.showinfo("Cliente registrado",
                            f"Contraseña temporal del cliente: {clave}\nEntréguesela para que pueda iniciar sesión.",
                            parent=self)
        etiqueta = f"{r['nombre']} {r['apellido']} ({r['correo']})"
        self.clientes[etiqueta] = nid
        self.cb_cli["values"] = list(self.clientes)
        self.cb_cli.set(etiqueta)


    def cambio_metodo(self, _=None):
        estado = "normal" if self.metodo.get() == "tarjeta" else "disabled"
        for w in self.e.values():
            w.config(state=estado)

    def recalcular(self):
        claves = [(c.get(), d["zona"]) for c, d in zip(self.combos, self.asientos)]
        precios = [self.tarifas[k] for k in claves]
        for lb, p in zip(self.lbl_p, precios):
            lb.config(text=colones(p))
        sub = sum(precios)
        d2x1 = sum((n // 2) * self.tarifas[k] for k, n in Counter(claves).items())     
        d_dia = round((sub - d2x1) * 0.20, 2) if self.mapa.fecha.isoweekday() == 3 else 0
        cargo = 500 if self.canal == "online" else 0
        total = sub - d2x1 - d_dia + cargo                                        
        for k, v in (("Subtotal", sub), ("Promoción 2x1", -d2x1), ("Día de descuento (miércoles 20%)", -d_dia),
                     ("Cargo por servicio", cargo), ("TOTAL", total)):
            self.lbls[k].config(text=colones(v))

    def tick(self):
        if not self.winfo_exists():
            return
        rest = min(d["deadline"] for d in self.asientos) - time.time()
        if rest <= 0:
            messagebox.showwarning("Tiempo agotado", "El bloqueo de sus asientos expiró. Vuelva a seleccionarlos.",
                                   parent=self)
            self.mapa.refrescar()
            self.destroy()
            return
        self.lbl_t.config(text=f"Complete el pago en {int(rest // 60):02d}:{int(rest % 60):02d}",
                          foreground="#C62828" if rest < 30 else "#000000")
        self.after(1000, self.tick)

    def validar_formulario(self):
        if self.canal == "taquilla" and not self.cb_cli.get():
            messagebox.showwarning("Cliente", "Seleccione o registre al cliente.", parent=self)
            return False
        if self.metodo.get() == "tarjeta":
            num = self.e["num"].get().replace(" ", "")
            if not (num.isdigit() and 13 <= len(num) <= 19):
                messagebox.showwarning("Datos de pago", "Número de tarjeta inválido.", parent=self)
                return False
            if not re.fullmatch(r"(0[1-9]|1[0-2])/\d{2}", self.e["ven"].get()):
                messagebox.showwarning("Datos de pago", "Vencimiento inválido (use MM/AA).", parent=self)
                return False
            if not (self.e["cvv"].get().isdigit() and len(self.e["cvv"].get()) in (3, 4)):
                messagebox.showwarning("Datos de pago", "CVV inválido.", parent=self)
                return False
        return True

    def pagar(self):
        if not self.validar_formulario():
            return
        ids = [d["bloqueo"] for d in self.asientos]
        tipos = [c.get() for c in self.combos]
        aprobado = self.resultado.get() == "aprobado"
        cliente = self.clientes[self.cb_cli.get()] if self.canal == "taquilla" else self.app.uid
        vendedor = self.app.uid if self.canal == "taquilla" else None
        try:
            with transaccion() as cur:
                cur.execute("SELECT fn_procesar_compra(%s,%s,%s,%s,%s,%s::int[],%s::varchar[])",
                            (cliente, vendedor, self.canal, self.metodo.get(), aprobado, ids, tipos))
                id_compra = cur.fetchone()[0]
        except Error as e:
            messagebox.showerror("Compra no procesada", msg_error(e), parent=self)
            self.mapa.refrescar()
            return
        mapa, app = self.mapa, self.app
        self.destroy()
        mapa.refrescar()
        if aprobado:
            messagebox.showinfo("Pago aprobado", f"Compra #{id_compra} pagada. Se emitieron {len(ids)} boleto(s).", parent=mapa)
            VentanaBoletos(app, "b.id_compra = %s", (id_compra,), f"Compra #{id_compra} - Confirmación y entrada digital")
        else:          # RN-10
            messagebox.showwarning("Pago rechazado",
                                   f"La pasarela rechazó el pago (compra #{id_compra}).\n"
                                   "No se debitó dinero, no se emitió ningún boleto y los asientos quedaron libres.",
                                   parent=mapa)


# ----------------------------------------------------------------------------
# CONFIRMACIÓN Y ENTRADA DIGITAL (RN-12, RN-13)
# ----------------------------------------------------------------------------
SQL_BOLETOS = """
SELECT b.id_boleto, b.codigo_qr, p.titulo, ci.nombre, s.nombre, a.fila || a.numero, a.zona,
       to_char(f.fecha_hora_inicio, 'YYYY-MM-DD HH24:MI'), b.precio, b.estado
FROM boleto b JOIN funcion f ON f.id_funcion = b.id_funcion
JOIN pelicula p ON p.id_pelicula = f.id_pelicula JOIN sala s ON s.id_sala = f.id_sala
JOIN cine ci ON ci.id_cine = s.id_cine JOIN asiento a ON a.id_asiento = b.id_asiento
WHERE {} ORDER BY b.id_boleto"""


class VentanaBoletos(tk.Toplevel):
    def __init__(self, app, condicion, params, titulo):
        super().__init__(app)
        tema(self)
        self.title(titulo)
        try:
            filas = consultar(SQL_BOLETOS.format(condicion), params)
        except Error as e:
            messagebox.showerror("Error", msg_error(e))
            self.destroy()
            return
        ttk.Label(self, text=titulo, style="Sub.TLabel").pack(pady=8)
        cont = ttk.Frame(self)
        cont.pack(padx=10, pady=6)
        for i, (id_b, qr, peli, cine, sala, asiento, zona, inicio, precio, estado) in enumerate(filas):
            card = ttk.LabelFrame(cont, text=f"Boleto #{id_b}", padding=8)
            card.grid(row=i // 3, column=i % 3, padx=6, pady=6)
            cv = tk.Canvas(card, width=130, height=130, bg="white", highlightthickness=1)
            cv.pack()
            if estado == "anulado":
                cv.create_text(65, 65, text="ANULADO", fill="red", font=("Arial", 14, "bold"))
            else:
                dibujar_qr(cv, qr, 130)
            ttk.Label(card, text=peli, font=("Arial", 10, "bold")).pack()
            ttk.Label(card, text=f"{cine} · {sala}").pack()
            ttk.Label(card, text=f"Asiento {asiento} ({zona})").pack()
            ttk.Label(card, text=inicio).pack()
            ttk.Label(card, text=f"{colones(precio)} · {estado.upper()}").pack()
            ttk.Label(card, text=qr, font=("Consolas", 8)).pack()
        ttk.Button(self, text="Cerrar", command=self.destroy).pack(pady=8)


# ----------------------------------------------------------------------------
# PANELES POR ROL
# ----------------------------------------------------------------------------
def panel_mis_boletos(parent, app):
    sql = """SELECT b.id_boleto, p.titulo, ci.nombre, s.nombre, a.fila || a.numero,
                    to_char(f.fecha_hora_inicio, 'YYYY-MM-DD HH24:MI'), b.estado, b.precio, b.codigo_qr
             FROM boleto b JOIN compra c ON c.id_compra = b.id_compra
             JOIN funcion f ON f.id_funcion = b.id_funcion JOIN pelicula p ON p.id_pelicula = f.id_pelicula
             JOIN sala s ON s.id_sala = f.id_sala JOIN cine ci ON ci.id_cine = s.id_cine
             JOIN asiento a ON a.id_asiento = b.id_asiento
             WHERE c.id_usuario_cliente = %s ORDER BY b.fecha_emision DESC, b.id_boleto"""

    def ver(v):
        VentanaBoletos(app, "b.id_boleto = %s", (int(v[0]),), f"Boleto #{v[0]}")

    def anular(v):
        if not messagebox.askyesno("Anular boleto", f"¿Anular el boleto #{v[0]}? Se reembolsará según la política (RN-19)."):
            return
        monto = ejecutar("SELECT fn_anular_boleto(%s,%s)", (int(v[0]), app.uid))[0]
        messagebox.showinfo("Boleto anulado", f"Reembolso aplicado: {colones(monto)}. El asiento quedó libre.")

    return PanelConsulta(parent, "Mis boletos (entrada digital)",
                         ("ID", "Película", "Cine", "Sala", "Asiento", "Función", "Estado", "Precio", "Código QR"),
                         sql, lambda: (app.uid,), (50, 170, 110, 70, 60, 130, 70, 70, 170),
                         [("Ver boleto / QR", ver, True), ("Anular boleto", anular, True)], exportar=False)


def panel_corte(parent, app):
    sql = """SELECT c.id_compra, to_char(c.fecha_hora, 'YYYY-MM-DD HH24:MI'), c.id_usuario_cliente,
                    c.subtotal, c.descuento, c.total, c.estado,
                    (SELECT COUNT(*) FROM boleto b WHERE b.id_compra = c.id_compra)
             FROM compra c WHERE c.id_usuario_cliente IS NOT NULL AND c.id_usuario_vendedor = %s
             ORDER BY c.fecha_hora DESC"""
    pie = lambda fs: (f"{len(fs)} venta(s) · Total cobrado (pagadas): "
                      f"{colones(sum(f[5] for f in fs if f[6] == 'pagada'))}")
    return PanelConsulta(parent, "Corte de caja propio (ventas de taquilla)",
                         ("Compra", "Fecha", "ID cliente", "Subtotal", "Descuento", "Total", "Estado", "Boletos"),
                         sql, lambda: (app.uid,), None,
                         [("Ver / emitir boletos", lambda v: VentanaBoletos(app, "b.id_compra = %s", (int(v[0]),),
                                                                            f"Compra #{v[0]}"), True)], pie=pie)


SQL_OCUPACION = """
SELECT f.id_funcion, p.titulo, ci.nombre || ' / ' || s.nombre,
       to_char(f.fecha_hora_inicio, 'YYYY-MM-DD HH24:MI'), f.estado, s.capacidad,
       COUNT(b.id_boleto) FILTER (WHERE b.estado <> 'anulado'),
       ROUND(100.0 * COUNT(b.id_boleto) FILTER (WHERE b.estado <> 'anulado') / s.capacidad, 1),
       (SELECT COALESCE(SUM(c.total), 0) FROM compra c
         WHERE c.estado IN ('pagada', 'reembolsada')
           AND c.id_compra IN (SELECT id_compra FROM boleto WHERE id_funcion = f.id_funcion))
       - COALESCE(SUM(b.monto_reembolsado), 0)
FROM funcion f JOIN pelicula p ON p.id_pelicula = f.id_pelicula JOIN sala s ON s.id_sala = f.id_sala
JOIN cine ci ON ci.id_cine = s.id_cine LEFT JOIN boleto b ON b.id_funcion = f.id_funcion
GROUP BY f.id_funcion, p.titulo, ci.nombre, s.nombre, s.capacidad, f.fecha_hora_inicio, f.estado
ORDER BY f.fecha_hora_inicio"""

SQL_TOP5 = """
SELECT p.titulo, COUNT(b.id_boleto) AS boletos
FROM boleto b JOIN funcion f ON f.id_funcion = b.id_funcion JOIN pelicula p ON p.id_pelicula = f.id_pelicula
WHERE b.estado <> 'anulado' AND b.fecha_emision >= NOW() - INTERVAL '7 days'
GROUP BY p.id_pelicula, p.titulo ORDER BY boletos DESC LIMIT 5"""

SQL_METODOS = """
SELECT metodo_pago, COUNT(*), ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)
FROM pago WHERE estado = 'aprobado' GROUP BY metodo_pago ORDER BY 2 DESC"""

SQL_CONCILIACION = """
SELECT p.id_pago, p.referencia_pasarela, p.metodo_pago, p.monto, p.estado, c.id_compra, c.total, c.estado,
       CASE WHEN p.monto = c.total THEN 'OK' ELSE 'DIFERENCIA' END
FROM pago p JOIN compra c ON c.id_compra = p.id_compra ORDER BY p.id_pago DESC"""

SQL_INGRESOS_DIA = """
SELECT to_char(fecha_hora, 'YYYY-MM-DD'), canal, COUNT(*), SUM(subtotal), SUM(descuento), SUM(cargo_servicio), SUM(total)
FROM compra WHERE estado IN ('pagada', 'reembolsada') GROUP BY 1, 2 ORDER BY 1 DESC, 2"""


def crear_reportes(parent, app):
    P = PanelConsulta
    return Grupo(parent, [
        ("Ocupación y recaudación", lambda q: P(q, "Ocupación y recaudación por función",
            ("ID", "Película", "Cine / Sala", "Inicio", "Estado", "Capacidad", "Vendidos", "% Ocupación", "Recaudación neta"),
            SQL_OCUPACION, anchos=(40, 170, 160, 130, 90, 80, 70, 90, 110))),
        ("Top 5 (última semana)", lambda q: P(q, "Top 5 películas más vendidas en la última semana",
            ("Película", "Boletos vendidos"), SQL_TOP5, anchos=(300, 130))),
        ("Métodos de pago", lambda q: P(q, "Métodos de pago preferidos (pagos aprobados)",
            ("Método", "Pagos", "% del total"), SQL_METODOS, anchos=(200, 100, 100))),
        ("Conciliación", lambda q: P(q, "Conciliación pagos vs. compras",
            ("Pago", "Referencia", "Método", "Monto", "Estado pago", "Compra", "Total compra", "Estado compra", "Resultado"),
            SQL_CONCILIACION)),
        ("Ingresos por día", lambda q: P(q, "Ingresos diarios (corte y liquidación)",
            ("Fecha", "Canal", "Compras", "Subtotal", "Descuentos", "Cargos", "Total"), SQL_INGRESOS_DIA)),
    ])


def crear_auditoria(parent, app):
    P = PanelConsulta
    t = "to_char(fecha_hora, 'YYYY-MM-DD HH24:MI:SS')"
    return Grupo(parent, [
        ("Resumen por administrador", lambda q: P(q, "Operaciones manuales del último mes agrupadas por administrador",
            ("ID admin", "Administrador", "Acción", "Cantidad"),
            """SELECT a.id_usuario, u.primer_nombre || ' ' || u.primer_apellido, a.accion, COUNT(*)
               FROM admin_operacion_audit a JOIN usuario u ON u.id_usuario = a.id_usuario
               WHERE a.fecha_hora >= NOW() - INTERVAL '1 month'
               GROUP BY a.id_usuario, u.primer_nombre, u.primer_apellido, a.accion
               ORDER BY a.id_usuario, a.accion""")),
        ("Detalle (último mes)", lambda q: P(q, "Bitácora administrativa - último mes",
            ("ID log", "Fecha", "ID admin", "Administrador", "Acción", "Tabla", "Registro", "Detalle", "Rol", "IP"),
            """SELECT a.id_log, to_char(a.fecha_hora, 'YYYY-MM-DD HH24:MI'), a.id_usuario,
                      u.primer_nombre || ' ' || u.primer_apellido, a.accion, a.tabla_afectada,
                      a.id_registro_afectado, a.detalle, a.rol, a.direccion_ip
               FROM admin_operacion_audit a JOIN usuario u ON u.id_usuario = a.id_usuario
               WHERE a.fecha_hora >= NOW() - INTERVAL '1 month' ORDER BY a.id_usuario, a.fecha_hora DESC""",
            anchos=(50, 120, 60, 130, 120, 80, 60, 260, 100, 100))),
        ("Log de transacciones", lambda q: P(q, "transaccion_log (últimos 500)",
            ("ID", "Evento", "Monto", "Estado", "Fecha", "ID pago"),
            f"SELECT id_log, evento, monto, estado, {t}, id_pago FROM transaccion_log ORDER BY id_log DESC LIMIT 500")),
        ("Log de asientos", lambda q: P(q, "asiento_auditoria_log (últimos 500)",
            ("ID", "Evento", "Fecha", "ID bloqueo"),
            f"SELECT id_log, evento, {t}, id_bloqueo FROM asiento_auditoria_log ORDER BY id_log DESC LIMIT 500")),
        ("Log de puerta", lambda q: P(q, "acceso_puerta_log (últimos 500)",
            ("ID", "Código leído", "Puerta", "Resultado", "Fecha", "ID boleto"),
            f"SELECT id_log, codigo_leido, puerta, resultado, {t}, id_boleto FROM acceso_puerta_log ORDER BY id_log DESC LIMIT 500",
            anchos=(50, 200, 90, 120, 140, 70))),
    ])


# ----------------------------------------------------------------------------
# PUERTA / CHECK-IN (RN-14, RN-15, RN-16)
# ----------------------------------------------------------------------------
class Puerta(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.funciones = {}
        ttk.Label(self, text="Validación de acceso en puerta (escáner QR)", style="Sub.TLabel").pack(anchor="w")
        f = ttk.Frame(self)
        f.pack(fill="x", pady=6)
        ttk.Label(f, text="Función:").grid(row=0, column=0, sticky="w")
        self.cb_func = ttk.Combobox(f, state="readonly", width=70)
        self.cb_func.grid(row=0, column=1, padx=6, pady=2, sticky="w")
        ttk.Label(f, text="Puerta:").grid(row=0, column=2, padx=(10, 0))
        self.cb_puerta = ttk.Combobox(f, values=["Puerta 1", "Puerta 2", "Puerta 3"], state="readonly", width=10)
        self.cb_puerta.set("Puerta 1")
        self.cb_puerta.grid(row=0, column=3, padx=6)
        ttk.Label(f, text="Código QR leído:").grid(row=1, column=0, sticky="w")
        self.e_qr = ttk.Entry(f, width=38, font=("Consolas", 12))
        self.e_qr.grid(row=1, column=1, padx=6, pady=2, sticky="w")
        self.e_qr.bind("<Return>", lambda e: self.validar())
        ttk.Button(f, text="Validar acceso", style="Accion.TButton", command=self.validar).grid(row=1, column=2, columnspan=2)
        self.lbl = tk.Label(self, text="Esperando lectura…", font=("Arial", 22, "bold"), bg="#ECEFF1", height=2)
        self.lbl.pack(fill="x", pady=8)
        ttk.Label(self, text="Lecturas de esta sesión (el historial completo lo ve el administrador en Auditoría)",
                  style="Sub.TLabel").pack(anchor="w")
        fr, self.tv = crear_tabla(self, ("Hora", "Código leído", "Puerta", "Resultado"), (90, 240, 100, 320), 8)
        fr.pack(fill="both", expand=True, pady=6)
        self.refrescar()

    def refrescar(self):
        filas = consultar("""SELECT f.id_funcion, p.titulo, ci.nombre, s.nombre,
                                    to_char(f.fecha_hora_inicio, 'YYYY-MM-DD HH24:MI')
                             FROM funcion f JOIN pelicula p ON p.id_pelicula = f.id_pelicula
                             JOIN sala s ON s.id_sala = f.id_sala JOIN cine ci ON ci.id_cine = s.id_cine
                             WHERE f.estado = 'programada'
                             ORDER BY ABS(EXTRACT(EPOCH FROM (f.fecha_hora_inicio - NOW())))""")
        self.funciones = {f"#{i} · {t} · {c} {s} · {ini}": i for i, t, c, s, ini in filas}
        self.cb_func["values"] = list(self.funciones)
        if filas and not self.cb_func.get():
            self.cb_func.current(0)

    def validar(self):
        id_f = self.funciones.get(self.cb_func.get())
        codigo = self.e_qr.get().strip()
        if not id_f or not codigo:
            messagebox.showwarning("Datos incompletos", "Seleccione la función e indique el código QR.")
            return
        try:
            msg = ejecutar("SELECT fn_validar_acceso(%s,%s,%s)", (codigo, id_f, self.cb_puerta.get()))[0]
        except Error as e:
            messagebox.showerror("Error al validar", msg_error(e))
            return
        ok = msg == "Acceso permitido"
        self.lbl.config(text=("✔ " if ok else "✖ ") + msg, bg="#C8E6C9" if ok else "#FFCDD2",
                        fg="#1B5E20" if ok else "#B71C1C")
        self.tv.insert("", 0, values=(f"{datetime.now():%H:%M:%S}", codigo, self.cb_puerta.get(), msg))
        self.e_qr.delete(0, "end")
# ----------------------------------------------------------------------------
# DASHBOARD DEL ADMINISTRADOR (métricas casi en tiempo real)
# ----------------------------------------------------------------------------
class Dashboard(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        ttk.Label(self, text="Dashboard de gerencia", style="Titulo.TLabel").pack(anchor="w")
        self.lbl_act = ttk.Label(self, text="")
        self.lbl_act.pack(anchor="w")
        kp = ttk.Frame(self)
        kp.pack(fill="x", pady=8)
        self.kpis = {}
        for i, k in enumerate(("Ingresos netos", "Boletos vigentes", "Boletos usados (check-in)",
                               "Funciones futuras", "Compras pagadas hoy", "Pagos rechazados")):
            card = tk.Frame(kp, bg="#0D1B3E", padx=12, pady=8)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            kp.columnconfigure(i, weight=1)
            v = tk.Label(card, text="-", bg="#0D1B3E", fg="#FFC107", font=("Arial", 18, "bold"))
            v.pack()
            tk.Label(card, text=k, bg="#0D1B3E", fg="white", font=("Arial", 9)).pack()
            self.kpis[k] = v
        ttk.Label(self, text="Ocupación por función programada (%)", style="Sub.TLabel").pack(anchor="w", pady=(10, 0))
        self.cv = tk.Canvas(self, bg="white", height=300, highlightthickness=1)
        self.cv.pack(fill="both", expand=True, pady=6)
        self.refrescar()
        self.auto()

    def auto(self):
        if not self.winfo_exists():
            return
        self.refrescar()
        self.after(10000, self.auto)

    def refrescar(self):
        try:
            k = consultar("""SELECT
                (SELECT COALESCE(SUM(total),0) FROM compra WHERE estado IN ('pagada','reembolsada'))
                  - (SELECT COALESCE(SUM(monto_reembolsado),0) FROM boleto),
                (SELECT COUNT(*) FROM boleto WHERE estado='valido'),
                (SELECT COUNT(*) FROM boleto WHERE estado='usado'),
                (SELECT COUNT(*) FROM funcion WHERE estado='programada' AND fecha_hora_inicio > NOW()),
                (SELECT COUNT(*) FROM compra WHERE estado='pagada' AND fecha_hora::date = CURRENT_DATE),
                (SELECT COUNT(*) FROM pago WHERE estado='rechazado')""")[0]
            filas = consultar("""SELECT p.titulo, to_char(f.fecha_hora_inicio,'DD/MM HH24:MI'), s.nombre,
                                        ROUND(100.0 * COUNT(b.id_boleto) FILTER (WHERE b.estado<>'anulado') / s.capacidad, 1)
                                 FROM funcion f JOIN pelicula p ON p.id_pelicula = f.id_pelicula
                                 JOIN sala s ON s.id_sala = f.id_sala
                                 LEFT JOIN boleto b ON b.id_funcion = f.id_funcion
                                 WHERE f.estado = 'programada'
                                 GROUP BY f.id_funcion, p.titulo, s.nombre, s.capacidad, f.fecha_hora_inicio
                                 ORDER BY f.fecha_hora_inicio""")
        except Error as e:
            self.lbl_act.config(text="Error: " + msg_error(e))
            return
        for nombre, valor in zip(self.kpis, k):
            self.kpis[nombre].config(text=colones(valor) if nombre == "Ingresos netos" else str(valor))
        self.cv.delete("all")
        for i, (titulo, hora, sala, pct) in enumerate(filas):
            y = 15 + i * 32
            self.cv.create_text(8, y + 10, anchor="w", text=f"{titulo[:24]} · {hora} · {sala}", font=("Arial", 9))
            self.cv.create_rectangle(260, y, 760, y + 20, fill="#ECEFF1", outline="")
            self.cv.create_rectangle(260, y, 260 + 5 * float(pct), y + 20, fill="#2196F3", outline="")
            self.cv.create_text(770, y + 10, anchor="w", text=f"{pct}%", font=("Arial", 9, "bold"))
        self.lbl_act.config(text=f"Actualizado: {datetime.now():%H:%M:%S} (se refresca cada 10 s)")


# ----------------------------------------------------------------------------
# GESTIÓN (solo administrador): películas, funciones, salas, tarifas, reembolsos
# ----------------------------------------------------------------------------
class AdminPeliculas(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app, self.id_sel = app, None
        izq = ttk.Frame(self)
        izq.pack(side="left", fill="both", expand=True)
        fr, self.tv = crear_tabla(izq, ("ID", "Título", "Clasif.", "Min", "Activa", "Géneros"), (40, 190, 60, 50, 60, 190), 14)
        fr.pack(fill="both", expand=True)
        self.tv.bind("<<TreeviewSelect>>", self.seleccionar)
        der = ttk.LabelFrame(self, text="Datos de la película", padding=8)
        der.pack(side="right", fill="y", padx=(8, 0))
        self.v = {k: tk.StringVar() for k in ("titulo", "clasificacion", "duracion", "poster", "generos")}
        for i, (k, et) in enumerate((("titulo", "Título (máx. 50)"), ("clasificacion", "Clasificación"),
                                     ("duracion", "Duración (min)"), ("poster", "URL del póster"),
                                     ("generos", "Géneros (separados por coma)"))):
            ttk.Label(der, text=et).grid(row=i, column=0, sticky="w", pady=3)
            if k == "clasificacion":
                w = ttk.Combobox(der, textvariable=self.v[k], values=["G", "PG", "PG-13", "R", "NC-17"], width=30)
            else:
                w = ttk.Entry(der, textvariable=self.v[k], width=33)
            w.grid(row=i, column=1, pady=3, padx=4)
        ttk.Label(der, text="Sinopsis").grid(row=5, column=0, sticky="nw", pady=3)
        self.txt = tk.Text(der, width=32, height=7, wrap="word")
        self.txt.grid(row=5, column=1, pady=3, padx=4)
        bt = ttk.Frame(der)
        bt.grid(row=6, column=0, columnspan=2, pady=8)
        ttk.Button(bt, text="Nueva", command=self.nueva).pack(side="left", padx=3)
        ttk.Button(bt, text="Guardar", style="Accion.TButton", command=self.guardar).pack(side="left", padx=3)
        ttk.Button(bt, text="Activar / Desactivar", command=self.alternar).pack(side="left", padx=3)
        self.refrescar()

    def refrescar(self):
        llenar(self.tv, consultar("""SELECT p.id_pelicula, p.titulo, p.clasificacion, p.duracion_min,
                CASE WHEN p.activa THEN 'Sí' ELSE 'No' END,
                COALESCE((SELECT string_agg(genero, ', ' ORDER BY genero) FROM pelicula_generos g
                          WHERE g.id_pelicula = p.id_pelicula), '')
            FROM pelicula p ORDER BY p.id_pelicula"""))

    def nueva(self):
        self.id_sel = None
        for v in self.v.values():
            v.set("")
        self.txt.delete("1.0", "end")

    def seleccionar(self, _=None):
        sel = self.tv.selection()
        if not sel:
            return
        self.id_sel = int(self.tv.item(sel[0], "values")[0])
        t, c, d, p, s = consultar("""SELECT titulo, clasificacion, duracion_min, poster_url, sinopsis
                                     FROM pelicula WHERE id_pelicula = %s""", (self.id_sel,))[0]
        gens = [g for (g,) in consultar("SELECT genero FROM pelicula_generos WHERE id_pelicula=%s ORDER BY genero", (self.id_sel,))]
        for k, val in zip(("titulo", "clasificacion", "duracion", "poster"), (t, c, d, p or "")):
            self.v[k].set(val)
        self.v["generos"].set(", ".join(gens))
        self.txt.delete("1.0", "end")
        self.txt.insert("end", s or "")

    def guardar(self):
        titulo, clasif = self.v["titulo"].get().strip(), self.v["clasificacion"].get().strip()
        sinopsis = self.txt.get("1.0", "end").strip()
        generos = [g.strip() for g in self.v["generos"].get().split(",") if g.strip()]
        try:
            dur = int(self.v["duracion"].get())
        except ValueError:
            dur = 0
        if not titulo or len(titulo) > 50 or not clasif or dur <= 0:
            messagebox.showwarning("Datos inválidos", "Título (máx. 50), clasificación y duración (>0) son obligatorios.")
            return
        poster = self.v["poster"].get().strip() or None
        try:
            with transaccion() as cur:
                if self.id_sel is None:
                    cur.execute("""INSERT INTO pelicula (titulo, sinopsis, clasificacion, duracion_min, poster_url, activa)
                                   VALUES (%s,%s,%s,%s,%s,TRUE) RETURNING id_pelicula""",
                                (titulo, sinopsis, clasif, dur, poster))
                    idp = cur.fetchone()[0]
                    accion = "crear_pelicula"
                else:
                    idp = self.id_sel
                    cur.execute("""UPDATE pelicula SET titulo=%s, sinopsis=%s, clasificacion=%s, duracion_min=%s,
                                   poster_url=%s WHERE id_pelicula=%s""", (titulo, sinopsis, clasif, dur, poster, idp))
                    cur.execute("DELETE FROM pelicula_generos WHERE id_pelicula=%s", (idp,))
                    accion = "modificar_pelicula"
                for g in generos:
                    cur.execute("INSERT INTO pelicula_generos VALUES (%s,%s) ON CONFLICT DO NOTHING", (idp, g))
                auditar(cur, self.app, accion, "pelicula", idp, titulo)
        except Error as e:
            messagebox.showerror("No se pudo guardar", msg_error(e))
            return
        messagebox.showinfo("Cartelera", "Película guardada correctamente.")
        self.nueva()
        self.refrescar()

    def alternar(self):
        if self.id_sel is None:
            messagebox.showinfo("Seleccione", "Seleccione una película de la tabla.")
            return
        with transaccion() as cur:
            cur.execute("UPDATE pelicula SET activa = NOT activa WHERE id_pelicula=%s RETURNING activa", (self.id_sel,))
            activa = cur.fetchone()[0]
            auditar(cur, self.app, "activar_pelicula" if activa else "desactivar_pelicula", "pelicula", self.id_sel, "")
        self.refrescar()


class AdminFunciones(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        f = ttk.LabelFrame(self, text="Programar función (valida traslapes + 30 min de limpieza)", padding=8)
        f.pack(fill="x")
        ttk.Label(f, text="Película:").grid(row=0, column=0, sticky="w")
        self.cb_peli = ttk.Combobox(f, state="readonly", width=34)
        self.cb_peli.grid(row=0, column=1, padx=4, pady=2)
        ttk.Label(f, text="Sala:").grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.cb_sala = ttk.Combobox(f, state="readonly", width=28)
        self.cb_sala.grid(row=0, column=3, padx=4)
        ttk.Label(f, text="Fecha (AAAA-MM-DD):").grid(row=1, column=0, sticky="w")
        self.e_fecha = ttk.Entry(f, width=14)
        self.e_fecha.grid(row=1, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(f, text="Hora (HH:MM):").grid(row=1, column=2, sticky="w", padx=(10, 0))
        self.e_hora = ttk.Entry(f, width=8)
        self.e_hora.grid(row=1, column=3, sticky="w", padx=4)
        bt = ttk.Frame(f)
        bt.grid(row=2, column=0, columnspan=4, pady=6, sticky="w")
        ttk.Button(bt, text="Programar función", style="Accion.TButton", command=self.programar).pack(side="left", padx=4)
        ttk.Button(bt, text="Poner en 20 min (demo de puerta)", command=self.en_20_min).pack(side="left", padx=4)
        ttk.Button(bt, text="Cancelar función seleccionada", command=self.cancelar).pack(side="left", padx=4)
        fr, self.tv = crear_tabla(self, ("ID", "Película", "Cine", "Sala", "Inicio", "Estado", "Boletos vigentes"),
                                  (40, 190, 120, 80, 130, 90, 100), 12)
        fr.pack(fill="both", expand=True, pady=8)
        self.refrescar()

    def refrescar(self):
        self.pelis = {f"{i} - {t} ({d} min)": i for i, t, d in consultar(
            "SELECT id_pelicula, titulo, duracion_min FROM pelicula WHERE activa ORDER BY titulo")}
        self.salas = {f"{i} - {c} / {s}": i for i, c, s in consultar(
            "SELECT s.id_sala, ci.nombre, s.nombre FROM sala s JOIN cine ci ON ci.id_cine = s.id_cine ORDER BY 1")}
        self.cb_peli["values"], self.cb_sala["values"] = list(self.pelis), list(self.salas)
        llenar(self.tv, consultar("""SELECT f.id_funcion, p.titulo, ci.nombre, s.nombre,
                to_char(f.fecha_hora_inicio, 'YYYY-MM-DD HH24:MI'), f.estado,
                (SELECT COUNT(*) FROM boleto b WHERE b.id_funcion = f.id_funcion AND b.estado <> 'anulado')
            FROM funcion f JOIN pelicula p ON p.id_pelicula = f.id_pelicula JOIN sala s ON s.id_sala = f.id_sala
            JOIN cine ci ON ci.id_cine = s.id_cine ORDER BY f.fecha_hora_inicio"""))

    def en_20_min(self):
        t = datetime.now() + timedelta(minutes=20)
        self.e_fecha.delete(0, "end")
        self.e_fecha.insert(0, t.strftime("%Y-%m-%d"))
        self.e_hora.delete(0, "end")
        self.e_hora.insert(0, t.strftime("%H:%M"))

    def programar(self):
        try:
            inicio = datetime.strptime(f"{self.e_fecha.get().strip()} {self.e_hora.get().strip()}", "%Y-%m-%d %H:%M")
        except ValueError:
            messagebox.showwarning("Fecha u hora inválida", "Use AAAA-MM-DD y HH:MM.")
            return
        if not self.cb_peli.get() or not self.cb_sala.get():
            messagebox.showwarning("Datos incompletos", "Seleccione película y sala.")
            return
        try:
            idf = ejecutar("SELECT fn_programar_funcion(%s,%s,%s,%s,%s)",
                           (self.pelis[self.cb_peli.get()], self.salas[self.cb_sala.get()], inicio,
                            self.app.uid, self.app.ip))[0]
        except Error as e:
            messagebox.showerror("No se pudo programar", msg_error(e))
            return
        messagebox.showinfo("Función programada", f"Función #{idf} creada correctamente.")
        self.refrescar()

    def cancelar(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showinfo("Seleccione", "Seleccione una función de la tabla.")
            return
        vals = self.tv.item(sel[0], "values")
        id_f = int(vals[0])
        if vals[5] != "programada":
            messagebox.showinfo("Función", "La función ya está cancelada.")
            return
        n = consultar("SELECT COUNT(*) FROM boleto WHERE id_funcion=%s AND estado='valido'", (id_f,))[0][0]
        if not messagebox.askyesno("Cancelar función", f"Se cancelará la función #{id_f} y se reembolsarán {n} boleto(s) vigentes. ¿Continuar?"):
            return
        try:
            total = self.cancelar_en_bd(id_f)
        except Error as e:
            messagebox.showerror("No se pudo cancelar", msg_error(e))
            return
        messagebox.showinfo("Función cancelada", f"Reembolsos realizados: {n} boleto(s), total {colones(total)}.")
        self.refrescar()

    def cancelar_en_bd(self, id_f):
        try:   # lo ideal: que la BD haga todo en una sola función (fn_cancelar_funcion)
            return ejecutar("SELECT fn_cancelar_funcion(%s,%s,%s)", (id_f, self.app.uid, self.app.ip))[0]
        except Error as e:
            if e.pgcode != "42883":   # 42883 = la función aún no existe en la BD
                raise
        # Respaldo: cancela y reembolsa con lo que el rol administrador sí puede ejecutar
        with transaccion() as cur:
            cur.execute("UPDATE funcion SET estado='cancelada' WHERE id_funcion=%s AND estado='programada'", (id_f,))
            cur.execute("SELECT id_boleto FROM boleto WHERE id_funcion=%s AND estado='valido'", (id_f,))
            total = 0
            for (idb,) in cur.fetchall():
                cur.execute("SELECT fn_reembolso_forzado(%s,%s,%s,%s)",
                            (idb, self.app.uid, f"Cancelación de la función {id_f}", self.app.ip))
                total += cur.fetchone()[0]
            auditar(cur, self.app, "cancelar_funcion", "funcion", id_f, f"Función cancelada; reembolsos por {total}")
            return total


def panel_salas(parent, app):
    AVISO = "RN-18: la sala tiene boletos vendidos o bloqueos activos en funciones futuras; no se puede modificar."

    def nueva(_):
        cines = {f"{i} - {n}": i for i, n in consultar("SELECT id_cine, nombre FROM cine ORDER BY 1")}
        r = pedir(app, "Nueva sala", [("cine", "Cine", next(iter(cines)), list(cines)), ("nombre", "Nombre", "Sala 1"),
                                      ("filas", "Filas (1-26)", "5"), ("cols", "Asientos por fila", "8")])
        if not r:
            return
        try:
            filas, cols = int(r["filas"]), int(r["cols"])
        except ValueError:
            filas = cols = 0
        if not (1 <= filas <= 26 and cols >= 1 and r["nombre"]):
            messagebox.showwarning("Datos inválidos", "Revise nombre, filas (1-26) y asientos por fila.")
            return
        zonas = ["general", "general", "platea", "palco", "vip"]
        with transaccion() as cur:
            cur.execute("INSERT INTO sala (nombre, capacidad, id_cine) VALUES (%s,%s,%s) RETURNING id_sala",
                        (r["nombre"], filas * cols, cines[r["cine"]]))
            ids = cur.fetchone()[0]
            for i in range(filas):
                for n in range(1, cols + 1):
                    cur.execute("INSERT INTO asiento (fila, numero, zona, id_sala) VALUES (%s,%s,%s,%s)",
                                (chr(65 + i), n, zonas[min(i, 4)], ids))
            auditar(cur, app, "crear_sala", "sala", ids, f"{r['nombre']} con {filas * cols} asientos")

    def agregar(v):
        sid = int(v[0])
        if sala_con_ventas(sid):
            messagebox.showwarning("Sala con ventas activas", AVISO)
            return
        r = pedir(app, "Agregar asiento", [("fila", "Fila (ej. F)", ""), ("numero", "Número", ""),
                                           ("zona", "Zona", "general", ["general", "platea", "palco", "vip"])])
        if not r:
            return
        if not r["fila"] or not r["numero"].isdigit() or len(r["fila"]) > 2:
            messagebox.showwarning("Datos inválidos", "Indique fila (1-2 letras) y número positivo.")
            return
        with transaccion() as cur:
            cur.execute("INSERT INTO asiento (fila, numero, zona, id_sala) VALUES (%s,%s,%s,%s)",
                        (r["fila"].upper(), int(r["numero"]), r["zona"], sid))
            cur.execute("UPDATE sala SET capacidad=(SELECT COUNT(*) FROM asiento WHERE id_sala=%s) WHERE id_sala=%s", (sid, sid))
            auditar(cur, app, "agregar_asiento", "asiento", sid, f"{r['fila'].upper()}{r['numero']} ({r['zona']})")

    def eliminar_asiento(v):
        sid = int(v[0])
        if sala_con_ventas(sid):
            messagebox.showwarning("Sala con ventas activas", AVISO)
            return
        r = pedir(app, "Eliminar asiento", [("fila", "Fila", ""), ("numero", "Número", "")])
        if not r or not r["numero"].isdigit():
            return
        with transaccion() as cur:
            cur.execute("DELETE FROM asiento WHERE id_sala=%s AND fila=%s AND numero=%s", (sid, r["fila"].upper(), int(r["numero"])))
            if cur.rowcount == 0:
                messagebox.showinfo("Asiento", "No existe ese asiento en la sala.")
                return
            cur.execute("UPDATE sala SET capacidad=(SELECT COUNT(*) FROM asiento WHERE id_sala=%s) WHERE id_sala=%s", (sid, sid))
            auditar(cur, app, "eliminar_asiento", "asiento", sid, f"{r['fila'].upper()}{r['numero']}")

    def eliminar_sala(v):
        sid = int(v[0])
        if sala_con_ventas(sid):
            messagebox.showwarning("Sala con ventas activas", AVISO)
            return
        if not messagebox.askyesno("Eliminar sala", f"¿Eliminar la sala #{sid} y todos sus asientos?"):
            return
        with transaccion() as cur:
            cur.execute("DELETE FROM asiento WHERE id_sala=%s", (sid,))
            cur.execute("DELETE FROM sala WHERE id_sala=%s", (sid,))
            auditar(cur, app, "eliminar_sala", "sala", sid, "")

    sql = """SELECT s.id_sala, ci.nombre, ci.ciudad, s.nombre, s.capacidad,
                    (SELECT COUNT(*) FROM asiento a WHERE a.id_sala = s.id_sala),
                    (SELECT COUNT(*) FROM funcion f WHERE f.id_sala = s.id_sala AND f.estado='programada' AND f.fecha_hora_inicio > NOW()),
                    (SELECT COUNT(*) FROM boleto b JOIN funcion f ON f.id_funcion = b.id_funcion
                      WHERE f.id_sala = s.id_sala AND f.estado='programada' AND f.fecha_hora_inicio > NOW() AND b.estado <> 'anulado')
             FROM sala s JOIN cine ci ON ci.id_cine = s.id_cine ORDER BY s.id_sala"""
    return PanelConsulta(parent, "Salas y distribución de asientos (RN-18)",
                         ("ID", "Cine", "Ciudad", "Sala", "Capacidad", "Asientos", "Funciones futuras", "Boletos vigentes"),
                         sql, acciones=[("Agregar asiento", agregar, True), ("Eliminar asiento", eliminar_asiento, True),
                                        ("Eliminar sala", eliminar_sala, True), ("Nueva sala", nueva, False)])


def panel_tarifas(parent, app):
    def cambiar(v):
        r = pedir(app, "Cambiar tarifa", [("precio", f"Nuevo precio de {v[1]} / {v[2]}", str(v[3]))])
        if not r:
            return
        try:
            precio = float(r["precio"])
        except ValueError:
            precio = -1
        if precio < 0:
            messagebox.showwarning("Precio inválido", "Indique un número mayor o igual a 0.")
            return
        with transaccion() as cur:
            cur.execute("UPDATE tarifa SET precio=%s WHERE id_tarifa=%s", (precio, int(v[0])))
            auditar(cur, app, "modificar_tarifa", "tarifa", int(v[0]), f"{v[1]}/{v[2]}: {v[3]} -> {precio}")

    return PanelConsulta(parent, "Matriz de precios (tipo de entrada x zona)", ("ID", "Tipo de entrada", "Zona", "Precio"),
                         "SELECT id_tarifa, tipo_entrada, zona, precio FROM tarifa ORDER BY zona, id_tarifa",
                         acciones=[("Cambiar precio", cambiar, True)],
                         pie=lambda fs: "Promociones automáticas: 2x1 por pares de la misma tarifa · 20% de descuento los "
                                        "miércoles · cargo por servicio online ₡500")


def panel_reembolsos(parent, app):
    def forzado(v):
        if v[5] == "anulado":
            messagebox.showinfo("Boleto", "El boleto ya fue anulado.")
            return
        r = pedir(app, "Reembolso forzado", [("motivo", "Motivo (obligatorio)", "")])
        if not r or not r["motivo"]:
            return
        monto = ejecutar("SELECT fn_reembolso_forzado(%s,%s,%s,%s)", (int(v[0]), app.uid, r["motivo"], app.ip))[0]
        messagebox.showinfo("Reembolso realizado", f"Monto reembolsado: {colones(monto)}. Quedó registrado en la auditoría.")

    return PanelConsulta(parent, "Boletos - reembolso forzado (queda en la bitácora de auditoría)",
                         ("ID", "Compra", "Película", "Función", "Asiento", "Estado", "Precio", "Reembolsado", "Código QR"),
                         """SELECT b.id_boleto, b.id_compra, p.titulo, to_char(f.fecha_hora_inicio, 'YYYY-MM-DD HH24:MI'),
                                   a.fila || a.numero, b.estado, b.precio, b.monto_reembolsado, b.codigo_qr
                            FROM boleto b JOIN funcion f ON f.id_funcion = b.id_funcion
                            JOIN pelicula p ON p.id_pelicula = f.id_pelicula JOIN asiento a ON a.id_asiento = b.id_asiento
                            ORDER BY b.id_boleto DESC""",
                         anchos=(50, 60, 170, 130, 60, 70, 70, 90, 170),
                         acciones=[("Reembolso forzado", forzado, True)])


def crear_gestion(parent, app):
    return Grupo(parent, [("Películas", lambda q: AdminPeliculas(q, app)), ("Funciones", lambda q: AdminFunciones(q, app)),
                          ("Salas", lambda q: panel_salas(q, app)), ("Tarifas", lambda q: panel_tarifas(q, app)),
                          ("Reembolsos", lambda q: panel_reembolsos(q, app))])


# ----------------------------------------------------------------------------
# APLICACIÓN PRINCIPAL (login + RBAC por pestañas, RN-17)
# ----------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Cine IMAX")
        self.geometry("1150x700")
        self.minsize(1000, 620)
        configurar_estilo(self)
        tema(self)
        self.ip = ip_local()
        self.uid = self.rol = self.nombre = None
        self.mostrar_login()

    def limpiar(self):
        for w in list(self.winfo_children()):
            if hasattr(w, "cerrar"):
                w.cerrar()     
            else:
                w.destroy()

    def mostrar_login(self):
        self.limpiar()
        self.uid = self.rol = self.nombre = None
        fr = ttk.Frame(self, padding=30)
        fr.place(relx=0.5, rely=0.5, anchor="center")
        ttk.Label(fr, text="IMAX · Sistema de Cine", style="Titulo.TLabel").pack(pady=6)
        ttk.Label(fr, text="Ingrese sus credenciales para continuar").pack(pady=(0, 12))
        ttk.Label(fr, text="Correo electrónico:").pack(anchor="w")
        self.e_correo = ttk.Combobox(fr, width=36, values=["admin@imax.com", "contador@imax.com", "taquilla1@imax.com",
                                                           "taquilla2@imax.com", "puerta1@imax.com",
                                                           "laura.mendez@correo.com", "pablo.chaves@correo.com"])
        self.e_correo.pack(pady=4)
        ttk.Label(fr, text="Contraseña:").pack(anchor="w", pady=(8, 0))
        self.e_pass = ttk.Entry(fr, width=39, show="*")
        self.e_pass.pack(pady=4)
        self.e_pass.bind("<Return>", lambda e: self.login())
        ttk.Button(fr, text="Iniciar sesión", style="Accion.TButton", command=self.login).pack(fill="x", pady=(14, 4))
        ttk.Button(fr, text="Conexión a la base de datos", command=self.config_conexion).pack(fill="x")

    def config_conexion(self):
        r = pedir(self, "Conexión a PostgreSQL", [("host", "Host", DB["host"]), ("port", "Puerto", DB["port"]),
                                                   ("database", "Base de datos", DB["database"]),
                                                   ("user", "Usuario", DB["user"]), ("password", "Contraseña", DB["password"])])
        if not r:
            return
        DB.update(r)
        try:
            conectar().close()
        except Error as e:
            messagebox.showerror("Sin conexión", msg_error(e))
            return
        with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump(DB, fh)
        messagebox.showinfo("Conexión", "Conexión exitosa. Configuración guardada en db_config.json")

    def login(self):
        correo, pw = self.e_correo.get().strip(), self.e_pass.get()
        if not correo or not pw:
            messagebox.showwarning("Campos vacíos", "Complete el correo y la contraseña.")
            return
        SESION["rol"] = SESION["uid"] = None
        try:
            fila = ejecutar("SELECT id_usuario, rol, nombre FROM fn_iniciar_sesion(%s,%s)", (correo, pw))
        except psycopg2.OperationalError as e:
            messagebox.showerror("Error de conexión", msg_error(e) + "\n\nRevise 'Conexión a la base de datos'.")
            return
        except Error as e:
            messagebox.showerror("Autenticación", msg_error(e))
            return
        self.uid, self.rol, self.nombre = fila
        SESION["rol"], SESION["uid"] = self.rol, self.uid
        self.mostrar_principal()

    def logout(self):
        self.limpiar()                    
        SESION["rol"] = SESION["uid"] = None
        self.mostrar_login()

    def pestanas(self):
        a = self
        cart = ("Cartelera", lambda p: Cartelera(p, a))
        por_rol = {
            "cliente": [cart, ("Mis boletos", lambda p: panel_mis_boletos(p, a))],
            "taquillero": [("Cartelera / Venta", cart[1]), ("Corte de caja", lambda p: panel_corte(p, a))],
            "operador_sala": [cart, ("Puerta (QR)", lambda p: Puerta(p, a))],
            "contador": [cart, ("Reportes y finanzas", lambda p: crear_reportes(p, a))],
            "administrador": [("Dashboard", lambda p: Dashboard(p, a)), cart,
                              ("Gestión", lambda p: crear_gestion(p, a)),
                              ("Reportes", lambda p: crear_reportes(p, a)), ("Auditoría", lambda p: crear_auditoria(p, a))],
        }
        return por_rol.get(self.rol, [cart])

    def mostrar_principal(self):
        self.limpiar()
        top = tk.Frame(self, bg="#0D1B3E")
        top.pack(fill="x")
        tk.Label(top, text="IMAX · Sistema de Cine", bg="#0D1B3E", fg="#FFC107", font=("Arial", 16, "bold")).pack(side="left", padx=12, pady=8)
        ttk.Button(top, text="Cerrar sesión", command=self.logout).pack(side="right", padx=12)
        tk.Label(top, text=f"{self.nombre}  [{self.rol.upper()}]", bg="#0D1B3E", fg="white", font=("Arial", 11)).pack(side="right")
        lbl = tk.Label(self, text=f"Sesión activa como [{self.rol.upper()}] · Conectado a PostgreSQL ({DB['host']}/{DB['database']}) · IP {self.ip}",
                       bd=1, relief=tk.SUNKEN, anchor=tk.W)
        lbl.pack(side=tk.BOTTOM, fill=tk.X)
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)
        for nombre, fabrica in self.pestanas():
            self.nb.add(fabrica(self.nb), text=nombre)
        self.nb.bind("<<NotebookTabChanged>>", self.al_cambiar_tab)

    def al_cambiar_tab(self, _=None):
        try:
            self.nametowidget(self.nb.select()).refrescar()
        except (AttributeError, KeyError, tk.TclError):
            pass


if __name__ == "__main__":
    App().mainloop()