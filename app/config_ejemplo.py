# Plantilla de conexión a PostgreSQL.
# Cada integrante copia este archivo como config.py (en esta misma carpeta)
# y coloca sus propios datos. config.py está en .gitignore y no se sube a GitHub.

DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "dbname": "cine",
    "user": "creador",
    "password": "ProyectoCine2026",
    "options": "-c search_path=prototipo",
}
