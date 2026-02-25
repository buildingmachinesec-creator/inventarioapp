[app]
title = InventarioApp
package.name = inventario
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv
version = 1.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0

# --- ESTO ES LO QUE ARREGLA EL ERROR ---
android.api = 33
android.minapi = 21
android.sdk = 33
android.build_tools_version = 33.0.2
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
# ---------------------------------------

[buildozer]
warn_on_root = 1
log_level = 2
