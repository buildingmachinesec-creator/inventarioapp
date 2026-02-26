from kivymd.app import MDApp
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDFillRoundFlatButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import TwoLineAvatarIconListItem, IconLeftWidget
from kivymd.uix.dialog import MDDialog
from kivy.clock import Clock
from kivy.utils import platform
import sqlite3, os
from datetime import datetime

# --- CONFIGURACIÓN DE RUTA ---
if platform == 'android':
    try:
        from jnius import autoclass
        activity = autoclass('org.kivy.android.PythonActivity').mActivity
        FOLDER = str(activity.getFilesDir().getAbsolutePath())
    except: FOLDER = "."
else:
    FOLDER = "."

DB = os.path.join(FOLDER, "inventario.db")

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS items(id TEXT, categoria TEXT, cantidad INTEGER, fecha TEXT)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_fast ON items(categoria, id)")
    conn.commit()
    conn.close()

class Tab(MDBoxLayout, MDTabsBase):
    pass

class Panel(MDBoxLayout):
    def __init__(self, categoria, app_instance, **kwargs):
        super().__init__(orientation="vertical", spacing="8dp", padding="10dp", **kwargs)
        self.categoria = categoria
        self.app = app_instance
        self.dialog = None
        
        # Inputs rápidos
        self.id_in = MDTextField(hint_text="Nombre del producto", mode="rectangle", size_hint_y=None, height="50dp")
        self.cant_in = MDTextField(hint_text="Cant.", input_filter="int", text="1", size_hint_y=None, height="50dp", size_hint_x=0.3)
        
        h_box = MDBoxLayout(spacing="10dp", size_hint_y=None, height="50dp")
        h_box.add_widget(self.id_in)
        h_box.add_widget(self.cant_in)
        self.add_widget(h_box)
        
        btn_add = MDFillRoundFlatButton(text="REGISTRAR PRODUCTO", pos_hint={"center_x": .5})
        btn_add.bind(on_release=self.agregar)
        self.add_widget(btn_add)
        
        self.lista = MDBoxLayout(orientation="vertical", spacing="4dp", size_hint_y=None)
        self.lista.bind(minimum_height=self.lista.setter('height'))
        
        from kivymd.uix.scrollview import MDScrollView
        scroll = MDScrollView()
        scroll.add_widget(self.lista)
        self.add_widget(scroll)
        Clock.schedule_once(self.refrescar)

    def refrescar(self, *args):
        self.lista.clear_widgets()
        filtro = self.app.search_bar.text.lower() if self.app.search_bar else ""
        
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM items WHERE categoria=? AND id LIKE ? ORDER BY id ASC", (self.categoria, f"%{filtro}%"))
        
        for item in c.fetchall():
            # El item principal: Al tocar el texto, sale el menú de ELIMINAR
            row = TwoLineAvatarIconListItem(
                text=f"[b]{item[0]}[/b]", 
                secondary_text=f"Stock: [color=0000ff]{item[2]}[/color]  |  {item[3]}",
                on_release=lambda x, i=item: self.menu_eliminar(i)
            )
            row.add_widget(IconLeftWidget(icon="cube-outline"))
            
            # CONTENEDOR DE BOTONES INDIVIDUALES (+ y -)
            # Los ponemos a la derecha de cada fila
            btns = MDBoxLayout(adaptive_width=True, spacing="10dp", padding=[0, 10, 10, 0])
            
            # Botón MENOS (-1) - Rojo
            btn_minus = MDIconButton(
                icon="minus-circle", 
                user_font_size="32sp",
                theme_text_color="Custom", 
                text_color=(1, 0, 0, 1)
            )
            btn_minus.bind(on_release=lambda x, i=item: self.modificar_stock(i, -1))
            
            # Botón MÁS (+1) - Verde
            btn_plus = MDIconButton(
                icon="plus-circle", 
                user_font_size="32sp",
                theme_text_color="Custom", 
                text_color=(0, .7, 0, 1)
            )
            btn_plus.bind(on_release=lambda x, i=item: self.modificar_stock(i, 1))
            
            btns.add_widget(btn_minus)
            btns.add_widget(btn_plus)
            row.add_widget(btns)
            
            self.lista.add_widget(row)
        conn.close()

    def modificar_stock(self, item, cambio):
        nueva_cant = max(0, item[2] + cambio)
        fecha = datetime.now().strftime("%H:%M")
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE items SET cantidad=?, fecha=? WHERE id=? AND categoria=?", 
                  (nueva_cant, f"Hoy {fecha}", item[0], item[1]))
        conn.commit()
        conn.close()
        self.refrescar() # Refresca solo esta pestaña para ahorrar recursos

    def menu_eliminar(self, item):
        self.dialog = MDDialog(
            title="Opciones de producto",
            text=f"¿Qué deseas hacer con '{item[0]}'?",
            buttons=[
                MDFlatButton(text="CANCELAR", on_release=lambda x: self.dialog.dismiss()),
                MDFlatButton(text="BORRAR PRODUCTO", text_color=(1, 0, 0, 1), 
                             on_release=lambda x, i=item: self.ejecutar_borrado(i)),
            ],
        )
        self.dialog.open()

    def ejecutar_borrado(self, item):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("DELETE FROM items WHERE id=? AND categoria=?", (item[0], item[1]))
        conn.commit()
        conn.close()
        self.dialog.dismiss()
        self.refrescar()

    def agregar(self, *args):
        if not self.id_in.text: return
        fecha = datetime.now().strftime("%d/%m %H:%M")
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO items VALUES (?,?,?,?)", 
                 (self.id_in.text, self.categoria, int(self.cant_in.text or 0), fecha))
        conn.commit()
        conn.close()
        self.id_in.text = ""
        self.refrescar()

class InventarioApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        init_db()
        
        main_ui = MDBoxLayout(orientation="vertical")
        main_ui.add_widget(MDTopAppBar(title="Inventario Pro (Optimizado)", elevation=4))
        
        # BUSCADOR QUE ACTUALIZA TODO
        self.search_bar = MDTextField(
            hint_text="🔍 Escribe para buscar en todas las listas...", 
            mode="fill", fill_color_normal=(.9, .9, .9, 1),
            size_hint_y=None, height="60dp"
        )
        self.search_bar.bind(text=self.refrescar_todo)
        main_ui.add_widget(self.search_bar)
        
        self.tabs = MDTabs()
        self.tab_list = []
        for n in ["📦 Stock", "🛠 Herramientas", "📑 Otros"]:
            tab = Tab(title=n)
            p = Panel(n, self)
            tab.add_widget(p)
            self.tabs.add_widget(tab)
            self.tab_list.append(p)
            
        main_ui.add_widget(self.tabs)
        return main_ui

    def refrescar_todo(self, *args):
        for p in self.tab_list: p.refrescar()

if __name__ == "__main__":
    InventarioApp().run()
