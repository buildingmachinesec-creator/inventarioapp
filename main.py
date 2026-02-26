from kivymd.app import MDApp
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.tab import MDTabs
from kivy.clock import Clock
from kivy.utils import platform
import sqlite3, socket, json, os, threading
from datetime import datetime

# --- CONFIGURACIÓN DE RUTA PARA ANDROID (CORREGIDA) ---
if platform == 'android':
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        FOLDER = str(activity.getFilesDir().getAbsolutePath())
    except Exception as e:
        print(f"Error obteniendo ruta Android: {e}")
        FOLDER = "."
else:
    FOLDER = "."

DB = os.path.join(FOLDER, "inventario.db")
PORT = 5050

# ---------- BASE DE DATOS ----------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS items(
        id TEXT, categoria TEXT, cantidad INTEGER, fecha TEXT
    )""")
    conn.commit()
    conn.close()

def obtener_items(cat, filtro=""):
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        if filtro:
            c.execute("SELECT * FROM items WHERE categoria=? AND id LIKE ?", (cat, f"%{filtro}%"))
        else:
            c.execute("SELECT * FROM items WHERE categoria=?", (cat,))
        data = c.fetchall()
        conn.close()
        return data
    except: return []

def actualizar_db(data):
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("DELETE FROM items")
        for item in data:
            c.execute("INSERT INTO items VALUES (?,?,?,?)", item)
        conn.commit()
        conn.close()
    except: pass

# ---------- SINCRONIZACIÓN (EN SEGUNDO PLANO) ----------
def thread_sincronizar():
    base = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        base = ".".join(ip.split(".")[:3])
    except: pass

    if not base: return

    for i in range(1, 255):
        ip_test = f"{base}.{i}"
        try:
            s = socket.socket()
            s.settimeout(0.1)
            s.connect((ip_test, PORT))
            data = s.recv(999999)
            if data:
                actualizar_db(json.loads(data.decode()))
            s.close()
            break 
        except: pass

# ---------- UI ----------
class Tab(MDBoxLayout, MDTabsBase):
    pass

class Panel(MDBoxLayout):
    def __init__(self, categoria, **kwargs):
        super().__init__(orientation="vertical", spacing=10, padding=10, **kwargs)
        self.categoria = categoria
        self.seleccionado = None
        
        self.buscar = MDTextField(hint_text="Buscar ID")
        self.buscar.bind(text=self.refrescar)
        self.add_widget(self.buscar)
        
        self.id_input = MDTextField(hint_text="ID producto")
        self.cantidad = MDTextField(hint_text="Cantidad", input_filter="int")
        self.add_widget(self.id_input)
        self.add_widget(self.cantidad)
        
        fila = MDBoxLayout(size_hint_y=None, height=50, spacing=10)
        fila.add_widget(MDRaisedButton(text="Add", on_release=self.agregar))
        fila.add_widget(MDRaisedButton(text="Del", on_release=self.eliminar))
        self.add_widget(fila)
        
        self.scroll = MDScrollView()
        self.lista = MDList()
        self.scroll.add_widget(self.lista)
        self.add_widget(self.scroll)
        self.refrescar()

    def refrescar(self, *args):
        self.lista.clear_widgets()
        for item in obtener_items(self.categoria, self.buscar.text):
            self.lista.add_widget(OneLineListItem(
                text=f"{item[0]} | Cant: {item[2]}", 
                on_release=lambda x, i=item: self.seleccionar(i)
            ))

    def seleccionar(self, item):
        self.seleccionado = item
        self.id_input.text = item[0]
        self.cantidad.text = str(item[2])

    def agregar(self, *args):
        if not self.id_input.text: return
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO items VALUES (?,?,?,?)",
                  (self.id_input.text, self.categoria, int(self.cantidad.text or 0), datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        conn.close()
        self.refrescar()

    def eliminar(self, *args):
        if not self.seleccionado: return
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("DELETE FROM items WHERE id=? AND categoria=?", (self.seleccionado[0], self.categoria))
        conn.commit()
        conn.close()
        self.refrescar()

class InventarioApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        init_db()
        layout = MDBoxLayout(orientation="vertical")
        layout.add_widget(MDTopAppBar(title="Inventario Pro"))
        tabs = MDTabs()
        for nombre in ["Inventario", "Herramientas", "Otros"]:
            tab = Tab(title=nombre)
            tab.add_widget(Panel(nombre))
            tabs.add_widget(tab)
        layout.add_widget(tabs)
        
        # Sincronización cada 30 seg en un hilo separado
        Clock.schedule_interval(lambda dt: threading.Thread(target=thread_sincronizar).start(), 30)
        return layout

if __name__ == "__main__":
    InventarioApp().run()
