import bcrypt
import pymysql
from app import obtener_usuario, verificar_contrasena, DB_CONFIG

correo = input("Correo: ").strip().lower()
clave = input("Contraseña que escribís en la web: ")

u = obtener_usuario(correo)
print("Usuario encontrado:", u is not None)

if u:
    h = u["contrasena"]
    print("Tipo:", type(h).__name__, "| largo:", len(h), "| inicio:", str(h)[:4])
    print("¿Coincide?:", verificar_contrasena(clave, h))

    if input("¿Guardar un hash nuevo con esa contraseña? (s/n): ").lower() == "s":
        nuevo = bcrypt.hashpw(clave.encode("utf-8"), bcrypt.gensalt()).decode()
        con = pymysql.connect(**DB_CONFIG)
        with con.cursor() as cur:
            cur.execute("UPDATE usuarios SET contrasena = %s WHERE correo = %s", (nuevo, correo))
        con.commit()
        con.close()
        print("Hash nuevo guardado. Probá entrar en la web.")