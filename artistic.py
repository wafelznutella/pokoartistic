import tkinter as tk
from tkinter import filedialog, messagebox, Scale, colorchooser, Listbox
from PIL import Image, ImageTk, ImageDraw
import configparser
import os
import sys
from collections import deque
import warnings

# Ignoruj ostrzeżenia o przestarzałych pakietach
warnings.filterwarnings("ignore", category=UserWarning)

# Sprawdzenie czy psd-tools jest dostępne
try:
    from psd_tools import PSDImage
    from psd_tools.user_api.layers import Group
    PSD_SUPPORT = True
except ImportError:
    PSD_SUPPORT = False

class SplashScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("Witamy")
        self.root.geometry("500x550")
        self.root.configure(bg='lightblue')
        self.root.resizable(False, False)
        
        # Ustawienie ikony
        try:
            assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
            icon_path = os.path.join(assets_dir, 'icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Błąd ładowania ikony: {e}")
        
        # Nagłówek
        header = tk.Label(root, text="Artistic - Program dla polskiej vtuberki 2poko2", 
                         font=("Arial", 14, "bold"), bg='lightblue')
        header.pack(pady=20)
        
        # Ramka z keybindingami
        keybind_frame = tk.LabelFrame(root, text="Keybindingi", font=("Arial", 12, "bold"),
                                     bg='lightblue', padx=10, pady=10)
        keybind_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Lista keybindów
        keybinds = [
            ("Zapisz obraz", "Ctrl + S"),
            ("Otwórz obraz", "Ctrl + O"),
            ("Nowy canvas", "Ctrl + N"),
            ("Cofnij", "Ctrl + Z"),
            ("Ponów", "Ctrl + Y"),
            ("Narzędzie pędzla", "Ctrl + B"),
            ("Narzędzie gumki", "Ctrl + E"),
            ("Zwiększ rozmiar pędzla", "Ctrl + ]"),
            ("Zmniejsz rozmiar pędzla", "Ctrl + ["),
            ("Przesuń canvas", "Spacja"),
            ("Powiększanie", "Z"),
            ("Obrót canvasa", "R"),
            ("Szybki eyedropper", "Alt (przytrzymaj)"),
            ("Dodaj warstwę", "Ctrl + L"),
            ("Usuń warstwę", "Ctrl + Shift + L")
        ]
        
        for i, (action, keybind) in enumerate(keybinds):
            row_frame = tk.Frame(keybind_frame, bg='lightblue')
            row_frame.pack(fill="x", pady=2)
            
            action_label = tk.Label(row_frame, text=action, width=25, 
                                   anchor="w", bg='lightblue')
            action_label.pack(side="left")
            
            keybind_label = tk.Label(row_frame, text=keybind, width=15,
                                    anchor="w", bg='lightblue', font=("Arial", 10, "bold"))
            keybind_label.pack(side="left")
        
        # Informacja o obsłudze PSD
        psd_info = tk.Label(root, text="Obsługa warstw i formatu PSD włączona" if PSD_SUPPORT else "Obsługa PSD niedostępna (zainstaluj psd-tools: pip install psd-tools)", 
                           bg='lightblue', font=("Arial", 10, "italic"))
        psd_info.pack(pady=5)
        
        # Przycisk rozpoczęcia
        start_button = tk.Button(root, text="Rozpocznij rysowanie", 
                                command=self.start_drawing, font=("Arial", 12),
                                bg="lightgreen", padx=20, pady=10)
        start_button.pack(pady=20)
        
        # Informacja o automatycznym zamknięciu
        self.auto_close_info = tk.Label(root, text="Okno zamknie się automatycznie za 10 sekund", 
                                       bg='lightblue', font=("Arial", 9))
        self.auto_close_info.pack(pady=5)
        
        # Timer do automatycznego zamknięcia
        self.countdown = 10
        self.update_countdown()
        
    def update_countdown(self):
        if self.countdown > 0:
            self.auto_close_info.config(text=f"Okno zamknie się automatycznie za {self.countdown} sekund")
            self.countdown -= 1
            self.root.after(1000, self.update_countdown)
        else:
            self.start_drawing()
    
    def start_drawing(self):
        self.root.destroy()
        self.root.quit()

class Layer:
    def __init__(self, name, width, height, visible=True, opacity=255):
        self.name = name
        self.image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        self.visible = visible
        self.opacity = opacity
        self.draw = ImageDraw.Draw(self.image)
        
    def get_image(self):
        if self.visible:
            if self.opacity < 255:
                # Adjust opacity
                alpha = self.image.split()[3]
                alpha = alpha.point(lambda p: p * self.opacity // 255)
                result = self.image.copy()
                result.putalpha(alpha)
                return result
            return self.image
        return None

class DrawingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Artistic - Program dla polskiej vtuberki 2poko2")
        
        # Ścieżka do folderu assets
        self.assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
        if not os.path.exists(self.assets_dir):
            os.makedirs(self.assets_dir)
        
        # Ładowanie konfiguracji - teraz z wbudowanych danych
        self.config = configparser.ConfigParser()
        self.load_config()
        
        # Ustawienie ikony
        try:
            icon_path = self.config.get('Settings', 'icon_path', fallback='icon.ico')
            icon_full_path = os.path.join(self.assets_dir, icon_path)
            if os.path.exists(icon_full_path):
                self.root.iconbitmap(icon_full_path)
        except Exception as e:
            print(f"Błąd ładowania ikony: {e}")

        # Tworzenie nowego canvasa
        self.canvas_width = int(self.config.get('Settings', 'canvas_width', fallback=800))
        self.canvas_height = int(self.config.get('Settings', 'canvas_height', fallback=600))
        
        # Inicjalizacja warstw
        self.layers = []
        self.active_layer_index = 0
        
        # Zmienne do rysowania
        self.last_x, self.last_y = None, None
        self.color = "black"
        self.brush_size = 5
        self.current_tool = "brush"
        self.is_drawing = False
        
        # Historia akcji dla undo/redo
        self.history = deque(maxlen=100)
        self.redo_history = deque(maxlen=100)
        
        # Setup UI - najpierw tworzymy interfejs
        self.setup_ui()
        
        # Dopiero teraz dodajemy warstwę domyślną
        self.add_layer("Warstwa 1")
        
        # Keybinds from config
        self.load_keybinds()
        
        # Aktualizacja wyświetlanego obrazu
        self.update_canvas()
        
    def add_layer(self, name):
        """Dodaje nową warstwę"""
        new_layer = Layer(name, self.canvas_width, self.canvas_height)
        self.layers.append(new_layer)
        self.active_layer_index = len(self.layers) - 1
        self.update_layer_list()
        self.save_state()
        
    def remove_layer(self, index):
        """Usuwa warstwę"""
        if len(self.layers) > 1:  # Zawsze zostaw przynajmniej jedną warstwę
            del self.layers[index]
            if self.active_layer_index >= index:
                self.active_layer_index = max(0, self.active_layer_index - 1)
            self.update_layer_list()
            self.save_state()
            self.update_canvas()
        
    def set_active_layer(self, index):
        """Ustawia aktywną warstwę"""
        if 0 <= index < len(self.layers):
            self.active_layer_index = index
            self.update_layer_list()
        
    def toggle_layer_visibility(self, index):
        """Przełącza widoczność warstwy"""
        if 0 <= index < len(self.layers):
            self.layers[index].visible = not self.layers[index].visible
            self.update_layer_list()
            self.update_canvas()
        
    def move_layer_up(self, index):
        """Przesuwa warstwę w górę"""
        if index > 0:
            self.layers[index], self.layers[index-1] = self.layers[index-1], self.layers[index]
            if self.active_layer_index == index:
                self.active_layer_index -= 1
            elif self.active_layer_index == index-1:
                self.active_layer_index += 1
            self.update_layer_list()
            self.update_canvas()
        
    def move_layer_down(self, index):
        """Przesuwa warstwę w dół"""
        if index < len(self.layers) - 1:
            self.layers[index], self.layers[index+1] = self.layers[index+1], self.layers[index]
            if self.active_layer_index == index:
                self.active_layer_index += 1
            elif self.active_layer_index == index+1:
                self.active_layer_index -= 1
            self.update_layer_list()
            self.update_canvas()
        
    def update_layer_list(self):
        """Aktualizuje listę warstw w UI"""
        # Sprawdź czy listbox istnieje przed próbą aktualizacji
        if hasattr(self, 'layer_listbox'):
            self.layer_listbox.delete(0, tk.END)
            for i, layer in enumerate(self.layers):
                visibility = "✓" if layer.visible else "✗"
                active_indicator = " > " if i == self.active_layer_index else "   "
                self.layer_listbox.insert(tk.END, f"{active_indicator}{visibility} {layer.name}")
        
    def get_composite_image(self):
        """Tworzy kompozytowy obraz z wszystkich widocznych warstw"""
        if not self.layers:
            return Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
            
        # Zacznij od białego tła zamiast przezroczystego :cite[2]
        composite = Image.new("RGBA", (self.canvas_width, self.canvas_height), (255, 255, 255, 255))
        
        # Połącz wszystkie widoczne warstwy
        for layer in self.layers:
            layer_image = layer.get_image()
            if layer_image:
                composite = Image.alpha_composite(composite, layer_image)
        
        # Konwertuj do RGB dla wyświetlania (Tkinter nie obsługuje alpha w Canvas)
        return composite.convert("RGB")
        
    def update_canvas(self):
        """Aktualizuje wyświetlany obraz na canvasie"""
        composite_image = self.get_composite_image()
        self.tk_image = ImageTk.PhotoImage(composite_image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        
    def save_state(self):
        """Zapisuje aktualny stan wszystkich warstw do historii"""
        state = []
        for layer in self.layers:
            state.append((layer.name, layer.image.copy(), layer.visible, layer.opacity))
        
        if hasattr(self, 'current_state'):
            self.history.append(self.current_state)
        self.current_state = state
        self.redo_history.clear()
        
    def undo(self, event=None):
        """Cofnij ostatnią akcję"""
        if self.history:
            self.redo_history.append(self.current_state)
            self.current_state = self.history.pop()
            
            # Przywróć warstwy
            self.layers = []
            for name, image, visible, opacity in self.current_state:
                layer = Layer(name, self.canvas_width, self.canvas_height)
                layer.image = image
                layer.visible = visible
                layer.opacity = opacity
                layer.draw = ImageDraw.Draw(layer.image)
                self.layers.append(layer)
                
            self.update_layer_list()
            self.update_canvas()
        
    def redo(self, event=None):
        """Przywróć ostatnio cofniętą akcję"""
        if self.redo_history:
            self.history.append(self.current_state)
            self.current_state = self.redo_history.pop()
            
            # Przywróć warstwy
            self.layers = []
            for name, image, visible, opacity in self.current_state:
                layer = Layer(name, self.canvas_width, self.canvas_height)
                layer.image = image
                layer.visible = visible
                layer.opacity = opacity
                layer.draw = ImageDraw.Draw(layer.image)
                self.layers.append(layer)
                
            self.update_layer_list()
            self.update_canvas()
        
    def load_config(self):
        """Wczytuje konfigurację z wbuiltowanych danych domyślnych"""
        default_config = """
[Settings]
icon_path = icon.ico
canvas_width = 800
canvas_height = 600

[Keybinds]
save = Control-s
open = Control-o
new = Control-n
undo = Control-z
redo = Control-y
brush_tool = Control-b
eraser_tool = Control-e
increase_brush = Control-bracketright
decrease_brush = Control-bracketleft
move_canvas = space
zoom_canvas = z
rotate_canvas = r
quick_eyedropper = Alt_L
add_layer = Control-l
remove_layer = Control-Shift-L
"""
        
        # Najpierw ładujemy domyślną konfigurację
        self.config.read_string(default_config)
        
        # Następnie próbujemy wczytać zewnętrzny plik config.ini jeśli istnieje
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
        if os.path.exists(config_path):
            self.config.read(config_path)
            
    def load_keybinds(self):
        """Ładuje skróty klawiszowe z konfiguracji"""
        keybinds = self.config['Keybinds']
        
        # Bind all keys with proper formatting
        self.root.bind(f"<{keybinds.get('save', 'Control-s')}>", self.save_image)
        self.root.bind(f"<{keybinds.get('open', 'Control-o')}>", self.open_image)
        self.root.bind(f"<{keybinds.get('new', 'Control-n')}>", self.new_canvas)
        self.root.bind(f"<{keybinds.get('undo', 'Control-z')}>", self.undo)
        self.root.bind(f"<{keybinds.get('redo', 'Control-y')}>", self.redo)
        self.root.bind(f"<{keybinds.get('brush_tool', 'Control-b')}>", lambda e: self.set_tool('brush'))
        self.root.bind(f"<{keybinds.get('eraser_tool', 'Control-e')}>", lambda e: self.set_tool('eraser'))
        self.root.bind(f"<{keybinds.get('increase_brush', 'Control-bracketright')}>", self.increase_brush_size)
        self.root.bind(f"<{keybinds.get('decrease_brush', 'Control-bracketleft')}>", self.decrease_brush_size)
        self.root.bind(f"<{keybinds.get('add_layer', 'Control-l')}>", lambda e: self.add_layer(f"Warstwa {len(self.layers)+1}"))
        self.root.bind(f"<{keybinds.get('remove_layer', 'Control-Shift-L')}>", lambda e: self.remove_layer(self.active_layer_index))
        
        # Special keybinds for canvas manipulation 
        self.root.bind(f"<KeyPress-{keybinds.get('move_canvas', 'space')}>", self.start_moving_canvas)
        self.root.bind(f"<KeyRelease-{keybinds.get('move_canvas', 'space')}>", self.stop_moving_canvas)
        self.root.bind(f"<KeyPress-{keybinds.get('zoom_canvas', 'z')}>", self.start_zooming_canvas)
        self.root.bind(f"<KeyRelease-{keybinds.get('zoom_canvas', 'z')}>", self.stop_zooming_canvas)
        self.root.bind(f"<KeyPress-{keybinds.get('rotate_canvas', 'r')}>", self.start_rotating_canvas)
        self.root.bind(f"<KeyRelease-{keybinds.get('rotate_canvas', 'r')}>", self.stop_rotating_canvas)
        
        # Quick eyedropper - hold Alt key
        self.root.bind(f"<KeyPress-{keybinds.get('quick_eyedropper', 'Alt_L')}>", self.start_eyedropper)
        self.root.bind(f"<KeyRelease-{keybinds.get('quick_eyedropper', 'Alt_L')}>", self.stop_eyedropper)
        
    def setup_ui(self):
        """Setup user interface"""
        # Main frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for layers
        left_panel = tk.Frame(main_frame, width=200)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left_panel.pack_propagate(False)
        
        # Layers label
        layers_label = tk.Label(left_panel, text="Warstwy", font=("Arial", 12, "bold"))
        layers_label.pack(pady=5)
        
        # Layers listbox
        self.layer_listbox = Listbox(left_panel, height=15)
        self.layer_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.layer_listbox.bind("<<ListboxSelect>>", self.on_layer_select)
        
        # Layer buttons frame
        layer_buttons_frame = tk.Frame(left_panel)
        layer_buttons_frame.pack(fill=tk.X, pady=5)
        
        add_layer_btn = tk.Button(layer_buttons_frame, text="+", command=lambda: self.add_layer(f"Warstwa {len(self.layers)+1}"))
        add_layer_btn.pack(side=tk.LEFT, padx=2, expand=True)
        
        remove_layer_btn = tk.Button(layer_buttons_frame, text="-", command=lambda: self.remove_layer(self.active_layer_index))
        remove_layer_btn.pack(side=tk.LEFT, padx=2, expand=True)
        
        up_layer_btn = tk.Button(layer_buttons_frame, text="↑", command=lambda: self.move_layer_up(self.active_layer_index))
        up_layer_btn.pack(side=tk.LEFT, padx=2, expand=True)
        
        down_layer_btn = tk.Button(layer_buttons_frame, text="↓", command=lambda: self.move_layer_down(self.active_layer_index))
        down_layer_btn.pack(side=tk.LEFT, padx=2, expand=True)
        
        toggle_visibility_btn = tk.Button(layer_buttons_frame, text="👁", command=lambda: self.toggle_layer_visibility(self.active_layer_index))
        toggle_visibility_btn.pack(side=tk.LEFT, padx=2, expand=True)
        
        # Right panel for canvas and tools
        right_panel = tk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Toolbar frame
        toolbar = tk.Frame(right_panel)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # Brush button
        self.brush_btn = tk.Button(toolbar, text="Brush", command=lambda: self.set_tool('brush'))
        self.brush_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Eraser button
        self.eraser_btn = tk.Button(toolbar, text="Eraser", command=lambda: self.set_tool('eraser'))
        self.eraser_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Color selection
        self.color_btn = tk.Button(toolbar, text="Color", command=self.choose_color)
        self.color_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Brush size slider
        self.size_slider = Scale(toolbar, from_=1, to=50, orient=tk.HORIZONTAL, 
                                label="Brush Size", command=self.change_brush_size)
        self.size_slider.set(self.brush_size)
        self.size_slider.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Undo/Redo buttons
        self.undo_btn = tk.Button(toolbar, text="Undo (Ctrl+Z)", command=self.undo)
        self.undo_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.redo_btn = tk.Button(toolbar, text="Redo (Ctrl+Y)", command=self.redo)
        self.redo_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Save/Open buttons
        self.save_btn = tk.Button(toolbar, text="Save (Ctrl+S)", command=self.save_image)
        self.save_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.open_btn = tk.Button(toolbar, text="Open (Ctrl+O)", command=self.open_image)
        self.open_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # PSD export button if supported
        if PSD_SUPPORT:
            self.psd_btn = tk.Button(toolbar, text="Export PSD", command=self.export_psd)
            self.psd_btn.pack(side=tk.LEFT, padx=2, pady=2)
        else:
            self.psd_btn = tk.Button(toolbar, text="Install PSD Support", command=self.install_psd_support)
            self.psd_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Canvas - ZMIANA: białe tło zamiast szarego :cite[2]
        self.canvas = tk.Canvas(right_panel, width=self.canvas_width, height=self.canvas_height, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Bind mouse events
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<ButtonPress-1>", self.start_drawing)
        self.canvas.bind("<ButtonRelease-1>", self.reset)
        self.canvas.bind("<MouseWheel>", self.zoom_canvas)
        self.canvas.bind("<Shift-MouseWheel>", self.rotate_canvas)
        
        # Status bar
        self.status_bar = tk.Label(self.root, text=f"Tool: {self.current_tool} | Size: {self.brush_size} | Color: {self.color} | Layer: {self.layers[self.active_layer_index].name if self.layers else 'Brak warstw'}", 
                                 bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def install_psd_support(self):
        """Instaluje obsługę PSD"""
        import subprocess
        import sys
        
        try:
            # Uruchom pip install w tle
            if sys.platform == "win32":
                subprocess.Popen([sys.executable, "-m", "pip", "install", "psd-tools"], 
                                creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen([sys.executable, "-m", "pip", "install", "psd-tools"])
                
            messagebox.showinfo("Instalacja", "psd-tools jest instalowane w tle. Proszę zrestartować program po zakończeniu instalacji.")
        except Exception as e:
            messagebox.showerror("Błąd instalacji", f"Nie udało się zainstalować psd-tools: {e}")
        
    def on_layer_select(self, event):
        """Obsługa wyboru warstwy z listy"""
        if self.layer_listbox.curselection():
            index = self.layer_listbox.curselection()[0]
            self.set_active_layer(index)
        
    def set_tool(self, tool):
        """Set current tool"""
        self.current_tool = tool
        self.update_status()
        
    def choose_color(self):
        """Choose color from dialog"""
        color = colorchooser.askcolor()
        if color[1]:
            self.color = color[1]
            self.update_status()
            
    def change_brush_size(self, value):
        """Change brush size"""
        self.brush_size = int(float(value))
        self.update_status()
        
    def increase_brush_size(self, event=None):
        """Increase brush size - Ctrl+]"""
        self.brush_size = min(50, self.brush_size + 1)
        self.size_slider.set(self.brush_size)
        self.update_status()
        
    def decrease_brush_size(self, event=None):
        """Decrease brush size - Ctrl+["""
        self.brush_size = max(1, self.brush_size - 1)
        self.size_slider.set(self.brush_size)
        self.update_status()
        
    def start_drawing(self, event):
        """Start drawing"""
        self.is_drawing = True
        self.last_x, self.last_y = event.x, event.y
        self.save_state()  # Zapisz stan przed rozpoczęciem rysowania
        
    def paint(self, event):
        """Handle painting"""
        if self.is_drawing and self.last_x and self.last_y and self.layers:
            # Rysuj na aktywnej warstwie
            active_layer = self.layers[self.active_layer_index]
            
            if self.current_tool == 'brush':
                active_layer.draw.line([(self.last_x, self.last_y), (event.x, event.y)], 
                              fill=self.color, width=self.brush_size)
            elif self.current_tool == 'eraser':
                # Dla gumki używamy przezroczystego koloru
                active_layer.draw.line([(self.last_x, self.last_y), (event.x, event.y)], 
                              fill=(0, 0, 0, 0), width=self.brush_size)
            
            # Rysuj na canvasie
            self.update_canvas()
            
        self.last_x = event.x
        self.last_y = event.y
        
    def reset(self, event):
        """Reset drawing state"""
        self.is_drawing = False
        self.last_x, self.last_y = None, None
        
    def update_status(self):
        """Update status bar"""
        if self.layers:
            layer_name = self.layers[self.active_layer_index].name
        else:
            layer_name = "Brak warstw"
        self.status_bar.config(text=f"Tool: {self.current_tool} | Size: {self.brush_size} | Color: {self.color} | Layer: {layer_name}")
        
    def save_image(self, event=None):
        """Save image"""
        file_path = filedialog.askssaveasfilename(defaultextension=".png", 
                                                filetypes=[("PNG files", "*.png"), 
                                                          ("JPEG files", "*.jpg"), 
                                                          ("All files", "*.*")])
        if file_path:
            composite_image = self.get_composite_image()
            composite_image.save(file_path)
            messagebox.showinfo("Sukces", "Obraz zapisany!")
            
    def export_psd(self, event=None):
        """Export to PSD format"""
        if not PSD_SUPPORT:
            messagebox.showerror("Błąd", "Obsługa PSD nie jest dostępna. Zainstaluj psd-tools: pip install psd-tools")
            return
            
        file_path = filedialog.askssaveasfilename(defaultextension=".psd", 
                                                filetypes=[("PSD files", "*.psd")])
        if file_path:
            try:
                # Create a new PSD image
                psd = PSDImage.new(self.canvas_width, self.canvas_height)
                
                # Add layers to PSD
                for layer in self.layers:
                    psd_layer = psd.add_layer(layer.name, layer.image)
                    psd_layer.visible = layer.visible
                    psd_layer.opacity = layer.opacity * 100 // 255  # Convert to percentage
                
                # Save PSD
                psd.save(file_path)
                messagebox.showinfo("Sukces", "Plik PSD zapisany!")
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się zapisać PSD: {e}")
            
    def open_image(self, event=None):
        """Open image"""
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.psd"), 
                                                         ("All files", "*.*")])
        if file_path:
            try:
                if file_path.lower().endswith('.psd') and PSD_SUPPORT:
                    # Open PSD file
                    psd = PSDImage.open(file_path)
                    
                    # Clear existing layers
                    self.layers = []
                    
                    # Add layers from PSD
                    for i, layer in enumerate(psd):
                        if not isinstance(layer, Group):  # Ignore group layers for now
                            new_layer = Layer(layer.name or f"Warstwa {i+1}", self.canvas_width, self.canvas_height)
                            new_layer.image = layer.topil().convert("RGBA")
                            new_layer.visible = layer.visible
                            new_layer.opacity = int(layer.opacity * 255 / 100)  # Convert from percentage
                            new_layer.draw = ImageDraw.Draw(new_layer.image)
                            self.layers.append(new_layer)
                    
                    if not self.layers:
                        # If no layers were added, create a default one
                        self.add_layer("Warstwa 1")
                    
                    self.active_layer_index = 0
                else:
                    # Open regular image file
                    image = Image.open(file_path).convert("RGBA")
                    
                    # Clear existing layers
                    self.layers = []
                    
                    # Create a new layer with the image
                    new_layer = Layer("Obraz", self.canvas_width, self.canvas_height)
                    new_layer.image = image
                    new_layer.draw = ImageDraw.Draw(new_layer.image)
                    self.layers.append(new_layer)
                    
                    self.active_layer_index = 0
                
                self.update_layer_list()
                self.update_canvas()
                self.save_state()  # Zapisz stan po załadowaniu obrazu
                
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się otworzyć pliku: {e}")
            
    def new_canvas(self, event=None):
        """Create new canvas"""
        # Clear all layers
        self.layers = []
        
        # Add a default layer
        self.add_layer("Warstwa 1")
        
        self.update_layer_list()
        self.update_canvas()
        self.save_state()  # Zapisz stan po utworzeniu nowego canvasa
        
    def start_moving_canvas(self, event):
        """Start moving canvas - Space key """
        self.canvas.config(cursor="fleur")
        self.canvas.bind("<B1-Motion>", self.move_canvas)
        
    def stop_moving_canvas(self, event):
        """Stop moving canvas"""
        self.canvas.config(cursor="")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.bind("<B1-Motion>", self.paint)
        
    def move_canvas(self, event):
        """Move canvas"""
        # Implementacja przesuwania canvasa
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        
    def start_zooming_canvas(self, event):
        """Start zooming canvas - Z key """
        self.canvas.config(cursor="plus")
        
    def stop_zooming_canvas(self, event):
        """Stop zooming canvas"""
        self.canvas.config(cursor="")
        
    def zoom_canvas(self, event):
        """Zoom canvas with mouse wheel """
        factor = 1.1 if event.delta > 0 else 0.9
        self.canvas.scale("all", event.x, event.y, factor, factor)
        
    def start_rotating_canvas(self, event):
        """Start rotating canvas - R key """
        self.canvas.config(cursor="exchange")
        
    def stop_rotating_canvas(self, event):
        """Stop rotating canvas"""
        self.canvas.config(cursor="")
        
    def rotate_canvas(self, event):
        """Rotate canvas with Shift+Mouse wheel """
        # Implementacja rotacji canvasa
        pass
        
    def start_eyedropper(self, event):
        """Start eyedropper tool - Hold Alt key """
        self.canvas.config(cursor="crosshair")
        self.prev_tool = self.current_tool
        self.set_tool('eyedropper')
        return "break"  # Zapobiega domyślnej akcji systemowej dla klawisza Alt
        
    def stop_eyedropper(self, event):
        """Stop eyedropper tool"""
        self.canvas.config(cursor="")
        self.set_tool(self.prev_tool)
        return "break"  # Zapobiega domyślnej akcji systemowej dla klawisza Alt

if __name__ == "__main__":
    # Najpierw pokazujemy ekran powitalny
    splash_root = tk.Tk()
    splash = SplashScreen(splash_root)
    splash_root.mainloop()
    
    # Po zamknięciu ekranu powitalnego, uruchamiamy główną aplikację
    root = tk.Tk()
    app = DrawingApp(root)
    root.mainloop()