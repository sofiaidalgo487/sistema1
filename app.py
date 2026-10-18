"""
Inventario informático — EET N.º 1 Palpalá
Todo en Python (Flask): backend + tu página web.

Carpeta del proyecto (todo junto, en el mismo lugar):
    app.py                  ← este archivo (servidor + base de datos + lógica)
    templates/index.html    ← la página (HTML)
    static/style.css        ← tus estilos
    static/ajustes.css      ← pequeños ajustes (no toca tu style.css)
    static/logo.png         ← el escudo
(script.js ya no hace falta: la lógica está en este archivo.)

Qué hace:
  - Muestra tu diseño (templates/index.html + static/style.css) armado desde el servidor
  - Base de datos MySQL/MariaDB `login` + tabla `usuarios` (se crea sola al
    iniciar, con los usuarios del volcado original)
  - Login con contraseñas bcrypt (compatible con los hashes $2y$ de PHP)
  - Roles: alumno (solo lectura) y docente (puede editar)
  - Búsqueda por ID, ficha del equipo, enlace directo (NFC) y edición
  - Login en JSON (reemplaza a login.php):  POST /api/login
  - Generador de hash (reemplaza a hash.php):  python app.py hash 1234

Instalación:   pip install flask bcrypt pymysql
Ejecución:     python app.py      →  http://127.0.0.1:5000
"""
import os
import sys
from datetime import date

import bcrypt
import pymysql
from flask import (Flask, request, redirect, url_for, session, flash,
                   jsonify, render_template)

# ----------------------------------------------------------------------
# Configuración (equivale a tu db.php). Podés cambiarla con variables
# de entorno sin tocar el código.
# ----------------------------------------------------------------------
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASS", "joce301124"),
    "database": os.environ.get("DB_NAME", "login"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "connect_timeout": 5,
}

SQL_CREAR_TABLA = """
CREATE TABLE IF NOT EXISTS `usuarios` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `correo` varchar(120) NOT NULL,
  `contrasena` varchar(255) NOT NULL,
  `rol` enum('alumno','docente') NOT NULL DEFAULT 'alumno',
  PRIMARY KEY (`id`),
  UNIQUE KEY `correo` (`correo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
"""

# Usuarios del volcado original (id, correo, hash bcrypt, rol)
USUARIOS_INICIALES = [
    (7, "chavez@eet1saviopalpala.edu.ar", "morder", "docente"),
    (8, "gabriel@eet1saviopalpala.edu.ar", "venta_de_pene", "alumno"),
    (9, "juan@eet1saviopalpala.edu.ar", "Elpepe", "alumno"),
    (10, "sofia@eet1saviopalpala.edu.ar", "sofiaaaaaaa", "docente"),
    (11, "kevin@eet1saviopalpala.edu.ar", "dalekevin", "alumno"),
    (12, "fernando@eet1saviopalpala.edu.ar", "traemeunfernandito", "docente"),
]


def inicializar_base_de_datos():
    config = dict(DB_CONFIG)
    nombre_bd = config.pop("database")
    conexion = pymysql.connect(**config)

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{nombre_bd}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
            )
            cursor.execute(f"USE `{nombre_bd}`")
            cursor.execute(SQL_CREAR_TABLA)

            usuarios_cifrados = []

            for id_usuario, correo, clave, rol in USUARIOS_INICIALES:
                clave_cifrada = bcrypt.hashpw(
                    clave.encode("utf-8"),
                    bcrypt.gensalt()
                ).decode("utf-8")

                usuarios_cifrados.append(
                    (id_usuario, correo, clave_cifrada, rol)
                )

            cursor.executemany(
                "INSERT INTO usuarios (id, correo, contrasena, rol) "
                "VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE "
                "contrasena = VALUES(contrasena), rol = VALUES(rol)",
                usuarios_cifrados
            )

        conexion.commit()

    finally:
        conexion.close()

def generar_hash(clave):
    """Equivale a password_hash() de PHP (bcrypt, formato $2y$)."""
    hash_bcrypt = bcrypt.hashpw(clave.encode("utf-8"), bcrypt.gensalt(rounds=10))
    return "$2y$" + hash_bcrypt.decode("utf-8")[4:]


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esta-clave-por-una-segura")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SEND_FILE_MAX_AGE_DEFAULT=0)

INVENTARIO = [
    {"id": "906784", "aula": "Taller de Informática — Puesto 1", "estado": "operativo",
     "cpu": "Intel Core i3-10100", "ram": "8 GB DDR4", "disco": "SSD 240 GB",
     "so": "Windows 10 Pro", "inventario": "INV-2021-114", "fecha": "12/03/2026",
     "obs": "Sin observaciones."},
    {"id": "906785", "aula": "Taller de Informática — Puesto 2", "estado": "revision",
     "cpu": "Intel Core i3-10100", "ram": "4 GB DDR4", "disco": "HDD 500 GB",
     "so": "Windows 10 Pro", "inventario": "INV-2021-115", "fecha": "05/08/2026",
     "obs": "Lentitud reportada por 5° año. Pendiente ampliar RAM."},
    {"id": "906786", "aula": "Taller de Informática — Puesto 3", "estado": "operativo",
     "cpu": "AMD Ryzen 3 3200G", "ram": "8 GB DDR4", "disco": "SSD 240 GB",
     "so": "Ubuntu 22.04 LTS", "inventario": "INV-2022-031", "fecha": "20/07/2026",
     "obs": "Dual boot habilitado para Electrónica."},
    {"id": "906787", "aula": "Sala de Proyectos", "estado": "fuera de servicio",
     "cpu": "Intel Core i3-4130", "ram": "4 GB DDR3", "disco": "HDD 500 GB",
     "so": "Windows 10 Pro", "inventario": "INV-2018-009", "fecha": "14/02/2026",
     "obs": "Fuente de alimentación dañada. Esperando repuesto."},
    {"id": "906788", "aula": "Taller de Informática — Puesto 5", "estado": "operativo",
     "cpu": "Intel Core i5-10400", "ram": "16 GB DDR4", "disco": "SSD 480 GB",
     "so": "Windows 11 Pro", "inventario": "INV-2023-002", "fecha": "18/08/2026",
     "obs": "Equipo destinado a diseño asistido (CAD)."},
    {"id": "906789", "aula": "Biblioteca", "estado": "operativo",
     "cpu": "Intel Celeron N4020", "ram": "4 GB DDR4", "disco": "eMMC 64 GB",
     "so": "Windows 10 Pro", "inventario": "INV-2020-077", "fecha": "02/06/2026",
     "obs": "Uso exclusivo de consulta y catálogo."},
]

ESTADOS = {
    "operativo": "Operativo",
    "revision": "En revisión",
    "fuera de servicio": "Fuera de servicio",
}



CLASES_ESTADO = {
    "operativo": "ok",
    "revision": "warn",
    "fuera de servicio": "off",
}



# ----------------------------------------------------------------------
# Base de datos y contraseñas
# ----------------------------------------------------------------------
def obtener_usuario(correo):
    """Busca un usuario en MySQL. Devuelve un dict o None."""
    conexion = pymysql.connect(**DB_CONFIG)
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT * FROM usuarios WHERE correo = %s", (correo,))
            return cursor.fetchone()
    finally:
        conexion.close()


def verificar_contrasena(clave, hash_guardado):
    """Equivale a password_verify de PHP. Acepta hashes $2y$ de PHP."""
    if isinstance(hash_guardado, bytes):
        hash_guardado = hash_guardado.decode("utf-8")
    hash_guardado = (hash_guardado or "").strip()
    if hash_guardado.startswith("$2y$"):
        hash_guardado = "$2b$" + hash_guardado[4:]
    try:
        return bcrypt.checkpw(clave.encode("utf-8"), hash_guardado.encode("utf-8"))
    except ValueError as e:
        print("DEBUG hash inválido:", e, "| largo:", len(hash_guardado))
        return False


def buscar_equipo(id_buscado):
    id_normalizado = "".join(id_buscado.upper().split())
    for equipo in INVENTARIO:
        if "".join(equipo["id"].upper().split()) == id_normalizado:
            return equipo
    return None


# ----------------------------------------------------------------------
# Rutas
# ----------------------------------------------------------------------
@app.route("/")
def inicio():
    usuario = session.get("correo")
    rol = session.get("rol")
    busqueda = request.args.get("id", "").strip()
    equipo = buscar_equipo(busqueda) if usuario and busqueda else None
    editando = bool(equipo) and rol == "docente" and request.args.get("editar") == "1"
    enlace = url_for("inicio", id=equipo["id"], _external=True) if equipo else ""
    return render_template(
        "index.html", usuario=usuario, rol=rol, busqueda=busqueda, equipo=equipo,
        editando=editando, enlace=enlace, inventario=INVENTARIO,
        estados=ESTADOS, clases=CLASES_ESTADO,
    )


@app.route("/login", methods=["POST"])
def login():
    correo = request.form.get("correo", "").strip().lower()
    contrasena = request.form.get("contrasena", "")
    id_pendiente = request.form.get("id", "").strip()  # ficha abierta desde un enlace NFC
    destino = url_for("inicio", id=id_pendiente) if id_pendiente else url_for("inicio")
    if not correo or not contrasena:
        flash("Completá el correo y la contraseña.", "error")
        return redirect(destino)
    try:
        usuario = obtener_usuario(correo)
    except pymysql.MySQLError:
        flash("No se pudo conectar con la base de datos. "
              "Revisá que MySQL/XAMPP esté encendido.", "error")
        return redirect(destino)
    if usuario and verificar_contrasena(contrasena, usuario["contrasena"]):
        session.clear()
        session["correo"] = usuario["correo"]
        session["rol"] = usuario["rol"]
        flash("Acceso concedido.", "ok")
    else:
        flash("Correo o contraseña incorrectos.", "error")
    return redirect(destino)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Cerraste sesión correctamente.", "ok")
    return redirect(url_for("inicio"))


@app.route("/editar/<equipo_id>", methods=["POST"])
def editar(equipo_id):
    if not session.get("correo") or session.get("rol") != "docente":
        flash("No tenés permiso para editar equipos.", "error")
        return redirect(url_for("inicio"))
    equipo = buscar_equipo(equipo_id)
    if not equipo:
        flash("No se encontró el equipo.", "error")
        return redirect(url_for("inicio"))
    estado = request.form.get("estado", "")
    if estado not in ESTADOS:
        flash("El estado seleccionado no es válido.", "error")
        return redirect(url_for("inicio", id=equipo["id"], editar=1))
    equipo["estado"] = estado
    equipo["obs"] = request.form.get("obs", "").strip()[:500] or "Sin observaciones."
    equipo["fecha"] = date.today().strftime("%d/%m/%Y")  # última revisión
    flash(f"Ficha de {equipo['id']} actualizada.", "ok")
    return redirect(url_for("inicio", id=equipo["id"]))


@app.route("/api/login", methods=["POST"])
def api_login():
    """Versión en Python del login.php original: responde en JSON."""
    datos = request.get_json(silent=True)
    datos = datos if isinstance(datos, dict) else request.form
    correo = (datos.get("correo") or "").strip().lower()
    clave = datos.get("contrasena") or ""
    if not correo or not clave:
        return jsonify(ok=False, error="Faltan datos")
    try:
        usuario = obtener_usuario(correo)
    except pymysql.MySQLError:
        return jsonify(ok=False, error="Error de conexión")
    if usuario and verificar_contrasena(clave, usuario["contrasena"]):
        session.clear()
        session["correo"] = usuario["correo"]
        session["rol"] = usuario["rol"]
        return jsonify(ok=True, correo=usuario["correo"], rol=usuario["rol"])
    return jsonify(ok=False, error="Correo o contraseña incorrectos")


if __name__ == "__main__":
    # python app.py hash 1234  →  imprime el hash de esa contraseña
    if len(sys.argv) >= 3 and sys.argv[1] == "hash":
        print(generar_hash(sys.argv[2]))
        sys.exit(0)

    try:
        inicializar_base_de_datos()
        print("Base de datos lista.")
    except pymysql.MySQLError as error:
        print(f"AVISO: no se pudo preparar la base de datos ({error}).\n"
              "Encendé MySQL/XAMPP y reiniciá la app.")

    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
