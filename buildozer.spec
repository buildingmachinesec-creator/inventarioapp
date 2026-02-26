[app]
title = InventarioPro
package.name = inventario
package.domain = org.tuusuario
source.dir = .
# Agregamos db y json para que tu base de datos y backup entren al APK
source.include_exts = py,png,jpg,kv,db,json
version = 1.0

# REQUERIMIENTOS CRÍTICOS: Sin estos, la app se cierra al abrir
requirements = python3, kivy==2.3.0, kivymd==1.2.0, pillow, sqlite3

orientation = portrait
fullscreen = 0

# PERMISOS: Necesarios para la sincronización WiFi que pusimos en el código
android.permissions = INTERNET, ACCESS_NETWORK_STATE

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

