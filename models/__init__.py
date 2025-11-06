# models/__init__.py

from flask_sqlalchemy import SQLAlchemy

# Instancia global de la base de datos
db = SQLAlchemy()

# Nota:
# No importamos los modelos aquí directamente para evitar ciclos.
# Los modelos se registrarán automáticamente cuando se importen
# en app.py o dentro de create_app().

# Ejemplo en app.py:
# from models.usuario import Usuario
# from models.placa import Placa
# from models.operacion import Operacion
# from models.movimiento import Movimiento