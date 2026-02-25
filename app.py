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
import sqlite3, socket, json
from datetime import datetime

DB = "inventario.db"
PORT = 5050

# ---------- BASE DE DATOS ----------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS items(
        id TEXT,
        categoria TEXT,
        cantidad INTEGER,
        fecha TEXT
    )""")
    conn.commit()
    conn.close()

def obtener_items(cat, filtro=""):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if filtro:
        c.execute("SELECT * FROM items WHERE categoria=? AND id LIKE ?", (cat, f"%{filtro}%"))
    else:
        c.execute("SELECT * FROM items WHERE categoria=?", (cat,))
    data = c.fetchall()
    conn.close()
    return data

def actualizar_db(data):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM items")
    for item in data:
        c.execute("INSERT INTO items VALUES (?,?,?,?)", item)
    conn.commit()
    conn.close()

# ---------- SINCRONIZACIÓN WIFI ----------
def obtener_ip_red():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        base = ".".join(ip.split(".")[:3])
        return base
    except:
        return None

def buscar_servidor():
    base = obtener_ip_red()
    if not base:
        return None
    for i in range(1, 255):
        ip = f"{base}.{i}"
        try:
            s = socket.socket()
            s.settimeout(0.2)
            s.connect((ip, PORT))
            return ip
        except:
            pass
    return None

def iniciar_servidor():
    try:
        s = socket.socket()
        s.bind(("", PORT))
        s.listen(5)
        while True:
            conn, addr = s.accept()
            data = json.dumps(obtener_items("Inventario") + obtener_items("Herramientas") + obtener_items("Cosas para llevar"))
            conn.send(data.encode())
            conn.close()
    except:
        pass

def sincronizar():
    ip = buscar_servidor()
    if not ip:
        return
    try:
        s = socket.socket()
        s.connect((ip, PORT))
        data = s.recv(999999)
        actualizar_db(json.loads(data.decode()))
        s.close()
    except:
        pass

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
        self.cantidad = MDTextField(hint_text="Cantidad")
        self.add_widget(self.id_input)
        self.add_widget(self.cantidad)

        fila = MDBoxLayout(size_hint_y=None, height=50, spacing=10)
        fila.add_widget(MDRaisedButton(text="Agregar", on_release=self.agregar))
        fila.add_widget(MDRaisedButton(text="Eliminar", on_release=self.eliminar))
        fila.add_widget(MDIconButton(icon="plus", on_release=self.sumar))
        fila.add_widget(MDIconButton(icon="minus", on_release=self.restar))
        self.add_widget(fila)

        self.scroll = MDScrollView()
        self.lista = MDList()
        self.scroll.add_widget(self.lista)
        self.add_widget(self.scroll)

        self.refrescar()

    def refrescar(self, *args):
        self.lista.clear_widgets()
        for item in obtener_items(self.categoria, self.buscar.text):
            texto = f"{item[0]} | {item[2]} | {item[3]}"
            self.lista.add_widget(OneLineListItem(text=texto, on_release=lambda x, i=item: self.seleccionar(i)))

    def seleccionar(self, item):
        self.seleccionado = item
        self.id_input.text = item[0]
        self.cantidad.text = str(item[2])

    def agregar(self, *args):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO items VALUES (?,?,?,?)",
                  (self.id_input.text, self.categoria, int(self.cantidad.text), datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        conn.close()
        self.refrescar()

    def eliminar(self, *args):
        if not self.seleccionado:
            return
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("DELETE FROM items WHERE id=? AND categoria=?", (self.seleccionado[0], self.categoria))
        conn.commit()
        conn.close()
        self.refrescar()

    def sumar(self, *args):
        if not self.seleccionado:
            return
        nueva = int(self.seleccionado[2]) + int(self.cantidad.text or 0)
        self.actualizar(nueva)

    def restar(self, *args):
        if not self.seleccionado:
            return
        nueva = max(0, int(self.seleccionado[2]) - int(self.cantidad.text or 0))
        self.actualizar(nueva)

    def actualizar(self, nueva):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE items SET cantidad=?, fecha=? WHERE id=? AND categoria=?",
                  (nueva, datetime.now().strftime("%Y-%m-%d"), self.seleccionado[0], self.categoria))
        conn.commit()
        conn.close()
        self.refrescar()

class InventarioApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        init_db()

        layout = MDBoxLayout(orientation="vertical")
        layout.add_widget(MDTopAppBar(title="Inventario"))

        tabs = MDTabs()
        for nombre in ["Inventario", "Herramientas", "Cosas para llevar"]:
            tab = Tab(title=nombre)
            tab.add_widget(Panel(nombre))
            tabs.add_widget(tab)

        layout.add_widget(tabs)

        Clock.schedule_interval(lambda dt: sincronizar(), 10)
        return layout

InventarioApp().run()