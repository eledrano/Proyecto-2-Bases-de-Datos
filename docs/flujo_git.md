# Flujo de trabajo con Git

Cada integrante trabaja en **su propia rama** y sube sus avances a `main` mediante un **Pull Request** en GitHub. Así nadie sobrescribe el trabajo de otro y queda un historial de commits ordenado.

| Integrante | Rama |
|---|---|
| Luis | `luis` |
| P1 | `p1` |
| P2 | `p2` |

## 1. Configuración (una sola vez por computadora)

En PowerShell:

```powershell
git config --global user.name "Tu Nombre"
git config --global user.email "tucorreo@ejemplo.com"
git config --global pull.rebase false
```

Ubicarse en la carpeta donde va a vivir el proyecto y clonar:

```powershell
git clone https://github.com/eledrano/Proyecto-2-Bases-de-Datos.git
cd Proyecto-2-Bases-de-Datos
```

Crear la rama propia y subirla (cambiar `p1` por la rama que corresponda):

```powershell
git checkout -b p1
git push -u origin p1
```

Preparar la conexión local a la BD: copiar `app\config_ejemplo.py` como `app\config.py` y poner la contraseña y el puerto propios.

```powershell
Copy-Item app\config_ejemplo.py app\config.py
pip install -r requerimientos.txt
```

## 2. Cada vez que se va a trabajar

```powershell
git checkout p1              # asegurarse de estar en la rama propia
git pull origin main         # traer lo que los demás ya integraron
```

Trabajar normalmente y, cada vez que se termina algo pequeño:

```powershell
git add .
git commit -m "Descripción corta de lo que se hizo"
git push
```

## 3. Integrar un avance a main

Cuando una parte está lista y probada:

1. Entrar al repositorio en GitHub → pestaña **Pull requests** → **New pull request**.
2. En **base** dejar `main` y en **compare** elegir la rama propia.
3. **Create pull request** → revisar que no haya conflictos → **Merge pull request**.
4. Avisar al grupo para que los demás hagan `git pull origin main` en su rama.

## Reglas del equipo

- No hacer commits directos a `main`.
- Commits pequeños y frecuentes, con mensajes que digan qué se hizo (el historial progresivo se revisa).
- No subir `app/config.py` ni contraseñas.
- Si aparece un conflicto al hacer `git pull origin main` o en el Pull Request, avisar al grupo antes de resolverlo.
- Los nombres de tablas y columnas deben ser **los mismos** en el DER, el modelo relacional, los scripts SQL, la aplicación y el documento.
