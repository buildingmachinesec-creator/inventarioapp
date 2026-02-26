[app]
title = InventarioPro
package.name = inventario
package.domain = org.tuusuario
source.dir = .
source.include_exts = py,png,jpg,kv,db,json
version = 1.0

# 1. CAMBIO CRÍTICO: Añadimos 'pyjnius' (para hablar con Android)
requirements = python3, kivy==2.3.0, kivymd==1.2.0, pillow, sqlite3, pyjnius

orientation = portrait
fullscreen = 0

# 2. PERMISOS: Añadimos permisos de almacenamiento para la base de datos
android.permissions = INTERNET, ACCESS_NETWORK_STATE, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# CONFIGURACIÓN ANDROID ESTABLE
android.api = 33
android.minapi = 21
android.sdk = 33
android.build_tools_version = 33.0.2
android.accept_sdk_license = True
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
