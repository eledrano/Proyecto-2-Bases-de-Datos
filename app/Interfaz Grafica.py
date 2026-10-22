import tkinter as tk
from tkinter import ttk
import psycopg2
from psycopg2 import Error

def crear_conexion():
    try:
        conexion = psycopg2.connect(
            host="localhost",
            port="5432",
            database="cine",
            user="postgres",
            password="postgres"
            options="-c search_path=prototipo"
        )
        print("Conexión exitosa a la base de datos")
        return conexion
    except Error as e:
        print("Error al conectar a la base de datos:", e)
        return None

def crear_interfaz():
    root = tk.Tk()
    root.title("Sistema Gestión de Cine")
    root.geometry("800x600")

    style = ttk.Style()
    style.theme_use('clam')

    lbl_titulo = tk.Label(root, text="Sistema de Gestión de Cine--PRINCIPAL", font=("Arial", 24, "bold"))
    lbl_titulo.pack(pady=20)

    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True, padx=10, pady=10)

    frame_peliculas = ttk.Frame(notebook)
    notebook.add(frame_peliculas, text="Películas") 
    tk.Label(frame_peliculas, text="Gestión de Cartelera", font=("Arial", 18)).pack(pady=10)

    frame_funciones = ttk.Frame(notebook)
    notebook.add(frame_funciones, text="Funciones")
    tk.Label(frame_funciones, text="Horarios y Salas", font=("Arial", 18)).pack(pady=10)

    frame_ventas = ttk.Frame(notebook)
    notebook.add(frame_ventas, text="Ventas Boletos")
    tk.Label(frame_ventas, text="Seleccion de asientos-Tarifas-Pagos", font=("Arial", 18)).pack(pady=10)

    frame_administracion = ttk.Frame(notebook)
    notebook.add(frame_administracion, text="Administración")
    tk.Label(frame_administracion, text="Control de tarifas-Cines-Registros de auditoría", font=("Arial", 18)).pack(pady=10)

    lbl_estado = tk.Label(root, text="Estado: Modo visual inicial (Sin conexión SQL activa)", bd=1, relief=tk.SUNKEN, anchor=tk.W)
    lbl_estado.pack(side=tk.BOTTOM, fill=tk.X)

    root.mainloop()

if __name__ == "__main__":
    crear_interfaz()
    