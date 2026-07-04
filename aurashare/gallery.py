import os
import platform
import subprocess
import customtkinter as ctk
try:
    from PIL import Image
except ImportError:
    pass

def open_file_in_os(filepath):
    if not os.path.exists(filepath): return
    try:
        if platform.system() == 'Windows': os.startfile(filepath)
        elif platform.system() == 'Darwin': subprocess.call(('open', filepath))
        else: subprocess.call(('xdg-open', filepath))
    except Exception as e: print(e)

class GalleryScreen(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.loaded_images = list()
        self.cards = list()
        self._build_ui()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(header, text="My Files", font=("SF Pro Display", 32, "bold")).pack(side="left")
        ctk.CTkButton(header, text="↻ Refresh", width=80, fg_color="#2C2C2E", hover_color="#3A3A3C", command=self._load_files).pack(side="right")
        
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=15)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.scroll_frame.bind("<Configure>", self._on_resize)

    def on_focus(self):
        self._load_files()

    def off_focus(self): pass

    def _on_resize(self, event):
        if not self.cards: return
        width = event.width
        max_cols = max(1, width // 130)  # 110 card width + 20 padding
        for i, card in enumerate(self.cards):
            card.grid(row=i // max_cols, column=i % max_cols, padx=10, pady=10)

    def _load_files(self):
        for widget in self.scroll_frame.winfo_children(): widget.destroy()
        self.loaded_images.clear()
        self.cards.clear()

        target_dir = getattr(self.app.config_obj, 'save_dir', os.getcwd())
        if not os.path.exists(target_dir): return
        
        files = os.listdir(target_dir)
        if not files:
            ctk.CTkLabel(self.scroll_frame, text="Gallery Empty.", font=("SF Pro", 16), text_color="#8E8E93").pack(pady=50)
            return

        img_exts = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')

        # Get current width for initial layout, fallback to 3 columns
        scroll_width = self.scroll_frame.winfo_width()
        max_cols = max(1, scroll_width // 130) if scroll_width > 130 else 3

        for i, file in enumerate(files):
            path = os.path.join(target_dir, file)
            size_mb = os.path.getsize(path) / 1048576
            card = ctk.CTkButton(self.scroll_frame, text="", fg_color="#2C2C2E", hover_color="#3A3A3C", corner_radius=10, width=110, height=140, command=lambda p=path: open_file_in_os(p))
            card.grid(row=i // max_cols, column=i % max_cols, padx=10, pady=10)
            card.grid_propagate(False)
            self.cards.append(card)
            
            if file.lower().endswith(img_exts):
                try:
                    img = Image.open(path)
                    img.thumbnail((80, 80)) 
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 80))
                    self.loaded_images.append(ctk_img)
                    ctk.CTkLabel(card, text="", image=ctk_img).pack(pady=(10, 5))
                except:
                    ctk.CTkLabel(card, text="🖼️\nERR", font=("SF Pro", 20), text_color="#FF453A").pack(pady=(20, 10))
            else:
                ext = file.split('.')[-1].upper()[ :4 ]
                ctk.CTkLabel(card, text=f"📄\n{ext}", font=("SF Pro Display", 24, "bold"), text_color="#0A84FF").pack(pady=(20, 10))

            short_name = file[:10] + "..." if len(file) > 13 else file
            ctk.CTkLabel(card, text=short_name, font=("SF Pro", 11), text_color="#FFFFFF").pack()
            ctk.CTkLabel(card, text=f"{size_mb:.1f} MB", font=("SF Pro", 10), text_color="#8E8E93").pack()