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
import sqlite3, os
from datetime import datetime

# --- CONFIGURACIÓN DE RUTA ---
if platform == 'android':
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        FOLDER = str(activity.getFilesDir().getAbsolutePath())
    except: FOLDER = "."
else:
    FOLDER = "."

DB = os.path.join(FOLDER, "inventario.db")

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS items(id TEXT, categoria TEXT, cantidad INTEGER, fecha TEXT)")
    conn.commit()
    conn.close()

class Tab(MDBoxLayout, MDTabsBase):
    pass

class Panel(MDBoxLayout):
    def __init__(self, categoria, app_instance, **kwargs):
        super().__init__(orientation="vertical", spacing=10, padding=10, **kwargs)
        self.categoria = categoria
        self.app = app_instance
        
        self.id_in = MDTextField(hint_text="Nombre del Producto", mode="rectangle")
        self.cant_in = MDTextField(hint_text="Cantidad Inicial", input_filter="int", text="1")
        self.add_widget(self.id_in)
        self.add_widget(self.cant_in)
        
        btn = MDRaisedButton(text="AGREGAR NUEVO", pos_hint={"center_x": .5})
        btn.bind(on_release=self.agregar)
        self.add_widget(btn)
        
        self.scroll = MDScrollView()
        self.lista = MDList()
        self.scroll.add_widget(self.lista)
        self.add_widget(self.scroll)
        Clock.schedule_once(self.refrescar)

    def refrescar(self, *args):
        self.lista.clear_widgets()
        filtro = self.app.search_bar.text.lower() if self.app.search_bar else ""
        
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM items WHERE categoria=? AND id LIKE ?", (self.categoria, f"%{filtro}%"))
        for item in c.fetchall():
            row = TwoLineAvatarIconListItem(
                text=f"{item[0]} | Stock: {item[2]}", 
                secondary_text=f"Modificado: {item[3]}"
            )
            row.add_widget(IconLeftWidget(icon="package-variant"))
            
            # Contenedor para botones de acción
            btns_cont = MDBoxLayout(adaptive_width=True, spacing="2dp")
            
            # BOTÓN MENOS (-1)
            btn_m = MDIconButton(icon="minus-circle-outline", theme_text_color="Custom", text_color=(.8, .2, .2, 1))
            btn_m.bind(on_release=lambda x, i=item: self.modificar(i, -1))
            
            # BOTÓN MÁS (+1)
            btn_p = MDIconButton(icon="plus-circle-outline", theme_text_color="Custom", text_color=(.2, .6, .2, 1))
            btn_p.bind(on_release=lambda x, i=item: self.modificar(i, 1))

            # BOTÓN ELIMINAR PRODUCTO (Basura)
            btn_del = MDIconButton(icon="trash-can", theme_text_color="Custom", text_color=(1, 0, 0, 1))
            btn_del.bind(on_release=lambda x, i=item: self.eliminar_producto(i))
            
            btns_cont.add_widget(btn_m)
            btns_cont.add_widget(btn_p)
            btns_cont.add_widget(btn_del)
            row.add_widget(btns_cont)
            
            self.lista.add_widget(row)
        conn.close()

    def agregar(self, *args):
        if not self.id_in.text: return
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO items VALUES (?,?,?,?)", (self.id_in.text, self.categoria, int(self.cant_in.text or 0), fecha))
        conn.commit()
        conn.close()
        self.id_in.text = ""
        self.app.refrescar_todo()

    def modificar(self, item, cambio):
        nueva_cant = max(0, item[2] + cambio)
        fecha_act = datetime.now().strftime("%d/%m/%Y %H:%M")
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE items SET cantidad=?, fecha=? WHERE id=? AND categoria=?", (nueva_cant, fecha_act, item[0], item[1]))
        conn.commit()
        conn.close()
        self.app.refrescar_todo()

    def eliminar_producto(self, item):
        # Borra el registro completo de la DB
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("DELETE FROM items WHERE id=? AND categoria=?", (item[0], item[1]))
        conn.commit()
        conn.close()
        self.app.refrescar_todo()

class InventarioApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        init_db()
        self.search_bar = None
        
        layout = MDBoxLayout(orientation="vertical")
        layout.add_widget(MDTopAppBar(title="Inventario Pro"))
        
        # BUSCADOR UNIVERSAL
        self.search_bar = MDTextField(hint_text="Buscador Universal (Nombre)", mode="fill", size_hint_y=None, height="60dp")
        self.search_bar.bind(text=self.refrescar_todo)
        layout.add_widget(self.search_bar)
        
        self.tabs = MDTabs()
        self.tab_objs = []
        for n in ["Inventario", "Herramientas", "Otros"]:
            tab = Tab(title=n)
            p = Panel(n, self)
            tab.add_widget(p)
            self.tabs.add_widget(tab)
            self.tab_objs.append(p)
            
        layout.add_widget(self.tabs)
        return layout

    def refrescar_todo(self, *args):
        for p in self.tab_objs: p.refrescar()

if __name__ == "__main__":
    InventarioApp().run()
