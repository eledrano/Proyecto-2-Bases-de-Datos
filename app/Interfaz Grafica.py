from logging import RootLogger, root
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import psycopg2
from psycopg2 import Error

def crear_conexion():
    try:
        conexion = psycopg2.connect(
            host="localhost",
            port="5432",
            database="cine",
            user="postgres",
            password="winbo07",
            options="-c search_path=prototipo"
        )
        print("Conexión exitosa a la base de datos")
        return conexion
    except Error as e:
        print("Error al conectar a la base de datos:", e)
        return None


def cargar_datos_tablas(tree, consulta):
    for item in tree.get_children():
        tree.delete(item)
    conexion = crear_conexion()
    if not conexion:
        messagebox.showerror("Error de conexión", "No se pudo conectar a la base de datos.")
        return
    try: 
        cursor = conexion.cursor()
        cursor.execute(consulta)
        filas = cursor.fetchall()
        for fila in filas:
            tree.insert("", tk.END, values=fila)
        cursor.close()
        conexion.close()
    except Error as e:
        messagebox.showerror("Error de consulta", f"No se pudo ejecutar la consulta:\n{e}")
        if conexion:
            conexion.close()


def crear_interfaz():
    root = tk.Tk()
    root.title("Sistema Gestión de Cine")
    root.geometry("800x600")

    style = ttk.Style()
    style.theme_use('clam')

    lbl_titulo = tk.Label(root, text="Sistema de Gestión de Cine-PRINCIPAL", font=("Arial", 24, "bold"))
    lbl_titulo.pack(pady=20)

    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True, padx=10, pady=10)
#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#SECCION DE PELICULAS
    frame_peliculas = ttk.Frame(notebook)
    notebook.add(frame_peliculas, text="Películas") 
    tk.Label(frame_peliculas, text="Gestión de Cartelera", font=("Arial", 18)).pack(pady=10)

    tk.Label(frame_peliculas, text="Cartelera", font=("Arial", 14, "bold")).pack(pady=10)

    cols_peliculas = ("ID", "Título", "Clasificación", "Duración (min)", "Activa")
    tree_peliculas = ttk.Treeview(frame_peliculas, columns=cols_peliculas, show="headings", height=12)
    for col in cols_peliculas:
        tree_peliculas.heading(col, text=col)
        tree_peliculas.column(col, width=160, anchor=tk.CENTER)
    tree_peliculas.pack(pady=10, fill="x", padx=20)

    def actualizar_tabla_peliculas():
        cargar_datos_tablas(tree_peliculas, "SELECT id, titulo, clasificacion, duracion_min, activa FROM peliculas")

    btn_frame_peli = ttk.Frame(frame_peliculas)
    btn_frame_peli.pack(pady=5)
    ttk.Button(btn_frame_peli, text="Cargar / Actualizar Cartelera", command=actualizar_tabla_peliculas).grid(row=0, column=0, padx=5)

#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#SECCION DE FUNCIONES

    frame_funciones = ttk.Frame(notebook)
    notebook.add(frame_funciones, text="Funciones")
    tk.Label(frame_funciones, text="Horarios y Salas", font=("Arial", 18, "bold")).pack(pady=10)

    cols_funciones = ("ID Función", "Fecha y Hora Inicio", "Estado", "ID Película", "ID Sala")
    tree_funciones = ttk.Treeview(frame_funciones, columns=cols_funciones, show="headings", height=12)
    for col in cols_funciones:
        tree_funciones.heading(col, text=col)
        tree_funciones.column(col, width=160, anchor=tk.CENTER)
    tree_funciones.pack(pady=10, fill="x", padx=20)

    def actualizar_tabla_funciones():
        cargar_datos_tablas(tree_funciones, "SELECT id, fecha_hora_inicio, estado, id_pelicula, id_sala FROM funciones")

    btn_frame_func = ttk.Frame(frame_funciones)
    btn_frame_func.pack(pady=5)
    ttk.Button(btn_frame_func, text="Cargar / Actualizar Funciones", command=actualizar_tabla_funciones).grid(row=0, column=0, padx=5)

#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#SECCION DE VENTAS DE BOLETOS

    frame_ventas = ttk.Frame(notebook)
    notebook.add(frame_ventas, text="Ventas Boletos")
    tk.Label(frame_ventas, text="Seleccion de asientos-Tarifas-Pagos", font=("Arial", 18, "bold")).pack(pady=10)

    cols_ventas = ("ID Compra", "Fecha / Hora", "Canal", "Subtotal", "Total", "Estado")
    tree_ventas = ttk.Treeview(frame_ventas, columns=cols_ventas, show="headings", height=12)
    for col in cols_ventas:
        tree_ventas.heading(col, text=col)
        tree_ventas.column(col, width=150, anchor=tk.CENTER)
    tree_ventas.pack(pady=10, fill="x", padx=20)

    def actualizar_tabla_ventas():
        cargar_datos_tablas(tree_ventas, "SELECT id, fecha_hora, canal, subtotal, total, estado FROM ventas_boletos")

    btn_frame_ventas = ttk.Frame(frame_ventas)
    btn_frame_ventas.pack(pady=5)
    ttk.Button(btn_frame_ventas, text="Cargar / Actualizar Compras", command=actualizar_tabla_ventas).grid(row=0, column=0, padx=5)

#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#SECCION DE ADMINISTRACION

    frame_administracion = ttk.Frame(notebook)
    notebook.add(frame_administracion, text="Administración")
    tk.Label(frame_administracion, text="Control de tarifas-Cines-Registros de auditoría", font=("Arial", 18, "bold")).pack(pady=10)

    cols_admin = ("ID Log", "Acción", "Tabla Afectada", "Rol", "Fecha y Hora")
    tree_admin = ttk.Treeview(frame_administracion, columns=cols_admin, show="headings", height=12)
    for col in cols_admin:
        tree_admin.heading(col, text=col)
        tree_admin.column(col, width=160, anchor=tk.CENTER)
    tree_admin.pack(pady=10, fill="x", padx=20)

    def actualizar_tabla_auditoria():
        cargar_datos_tablas(tree_admin, "SELECT id, accion, tabla_afectada, rol, fecha_hora FROM auditoria")

    btn_frame_admin = ttk.Frame(frame_administracion)
    btn_frame_admin.pack(pady=5)
    ttk.Button(btn_frame_admin, text="Cargar / Actualizar Auditoría", command=actualizar_tabla_auditoria).grid(row=0, column=0, padx=5)

#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
    #ESTADO DE CONEXION SQL
    conn_prueba = crear_conexion()
    if conn_prueba:
        estado_texto = "Estado: Conexión activa con PostgreSQL (Esquema: prototipo)"
        conn_prueba.close()
    else:
        estado_texto = "Estado: Error al conectar con la Base de Datos"

    lbl_estado = tk.Label(root, text=estado_texto, bd=1, relief=tk.SUNKEN, anchor=tk.W)
    lbl_estado.pack(side=tk.BOTTOM, fill=tk.X)

    root.mainloop()

if __name__ == "__main__":
    conn = crear_conexion()
    if conn:
        conn.close()
        print("Conexión cerrada correctamente.")

if __name__ == "__main__":
    crear_interfaz()
