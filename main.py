from kivymd.app import MDApp
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import MDList, TwoLineAvatarIconListItem, IconLeftWidget, IconRightWidget
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.tab import MDTabs
from kivy.clock import Clock
from kivy.utils import platform
import sqlite3, socket, json, os, threading
from datetime import datetime

# --- CONFIGURACIÓN DE RUTA PARA ANDROID ---
if platform == 'android':
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        FOLDER = str(activity.getFilesDir().getAbsolutePath())
    except Exception as e:
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

# ---------- SINCRONIZACIÓN ----------
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
    def __init__(self, categoria, app_instance, **kwargs):
        super().__init__(orientation="vertical", spacing=10, padding=10, **kwargs)
        self.categoria = categoria
        self.app = app_instance
        
        # Inputs para agregar
        self.id_input = MDTextField(hint_text="Nombre / ID del producto", mode="rectangle")
        self.cantidad = MDTextField(hint_text="Cantidad inicial", input_filter="int", text="1")
        self.add_widget(self.id_input)
        self.add_widget(self.cantidad)
        
        btn_add = MDRaisedButton(text="AGREGAR NUEVO", pos_hint={"center_x": .5})
        btn_add.bind(on_release=self.agregar)
        self.add_widget(btn_add)
        
        self.scroll = MDScrollView()
        self.lista = MDList()
        self.scroll.add_widget(self.lista)
        self.add_widget(self.scroll)
        Clock.schedule_once(self.refrescar)

    def refrescar(self, *args):
        self.lista.clear_widgets()
        filtro = self.app.root.ids.search_universal.text.lower()
        
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM items WHERE categoria=? AND id LIKE ?", (self.categoria, f"%{filtro}%"))
        items = c.fetchall()
        
        for item in items:
            # Lista de dos líneas: Nombre y Fecha
            item_ui = TwoLineAvatarIconListItem(
                text=f"{item[0]} | Stock: {item[2]}",
                secondary_text=f"Última vez: {item[3]}"
            )
            item_ui.add_widget(IconLeftWidget(icon="package-variant"))
            
            # Contenedor de botones a la derecha
            btns = MDBoxLayout(adaptive_width=True, spacing="5dp")
            
            # Botón de más
            btn_plus = MDIconButton(icon="plus-thick", theme_text_color="Custom", text_color=(0, .7, 0, 1))
            btn_plus.bind(on_release=lambda x, i=item: self.modificar_stock(i, 1))
            
            # Botón de menos
            btn_minus = MDIconButton(icon="minus-thick", theme_text_color="Custom", text_color=(.7, 0, 0, 1))
            btn_minus.bind(on_release=lambda x, i=item: self.modificar_stock(i, -1))
            
            item_ui.add_widget(IconRightWidget(icon="chevron-right", on_release=lambda x, i=item: self.modificar_stock(i, 1)))
            # Para mantenerlo simple y que no crashee, el IconRightWidget sumará 1 al tocarlo
            # El botón "Del" lo manejaremos con click largo si lo necesitas luego
            
            self.lista.add_widget(item_ui)
        conn.close()

    def agregar(self, *args):
        if not self.id_input.text: return
        # Fecha con Hora exacta
        fecha_completa = datetime.now().strftime("%d/%m/%Y %H:%M")
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO items VALUES (?,?,?,?)",
                  (self.id_input.text, self.categoria, int(self.cantidad.text or 0), fecha_completa))
        conn.commit()
        conn.close()
        self.id_input.text = ""
        self.app.refrescar_todo()

    def modificar_stock(self, item, cambio):
        nueva = max(0, item[2] + cambio)
        fecha_act = datetime.now().strftime("%d/%m/%Y %H:%M")
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE items SET cantidad=?, fecha=? WHERE id=? AND categoria=?",
                  (nueva, fecha_act, item[0], item[1]))
        conn.commit()
        conn.close()
        self.app.refrescar_todo()

class InventarioApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        init_db()
        
        # Layout Principal
        self.root_layout = MDBoxLayout(orientation="vertical")
        self.root_layout.add_widget(MDTopAppBar(title="Inventario Pro"))
        
        # BUSCADOR UNIVERSAL (ARRIBA)
        self.search_bar = MDTextField(
            id="search_universal",
            hint_text="Buscador Universal (ID / Nombre)",
            mode="fill",
            size_hint_y=None, height="60dp"
        )
        self.search_bar.bind(text=self.refrescar_todo)
        self.root_layout.add_widget(self.search_bar)
        
        self.tabs = MDTabs()
        self.tab_objects = []
        for nombre in ["Inventario", "Herramientas", "Otros"]:
            tab = Tab(title=nombre)
            panel = Panel(nombre, self)
            tab.add_widget(panel)
            self.tabs.add_widget(tab)
            self.tab_objects.append(panel)
            
        self.root_layout.add_widget(self.tabs)
        
        Clock.schedule_interval(lambda dt: threading.Thread(target=thread_sincronizar).start(), 30)
        return self.root_layout

    def refrescar_todo(self, *args):
        for panel in self.tab_objects:
            panel.refrescar()

if __name__ == "__main__":
    InventarioApp().run()
