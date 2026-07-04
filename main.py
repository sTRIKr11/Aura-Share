import os
import sys
import webbrowser
import customtkinter as ctk
import pywinstyles

# --- BULLETPROOF ABSOLUTE PATH INJECTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from aurashare.config import Config
from aurashare.transfer import TransferServer
from aurashare.sharing import SharingScreen
from aurashare.gallery import GalleryScreen

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class GalShareApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AuraShare V4.0")
        self.geometry("800x600")
        self.minsize(500, 600)
        # Apply Windows 11 Acrylic blur effect
        pywinstyles.apply_style(self, "acrylic")
        pywinstyles.change_header_color(self, color="#1C1C1E")

        # Set the application icon
        try:
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, "app_icon.ico")
            else:
                icon_path = os.path.join(current_dir, "app_icon.ico")
            self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Could not load icon: {e}")

        self.config_obj = Config()
        self.transfer_sv = TransferServer(self.config_obj)

        self._build_ui()
        self.show_tab("sharing")

    def _build_ui(self):
        self.header = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0, height=50)
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)

        ctk.CTkLabel(self.header, text="AuraShare", font=("SF Pro Display", 20, "bold")).pack(side="left", padx=20, pady=10)
        
        self.status_dot = ctk.CTkLabel(self.header, text="● Online", text_color="#30D158", font=("SF Pro Display", 14))
        self.status_dot.pack(side="right", padx=(10, 20), pady=10)
        
        self.info_btn = ctk.CTkButton(self.header, text="ⓘ Info", width=60, fg_color="transparent", hover_color="#2C2C2E", font=("SF Pro Display", 14), command=self.toggle_info_sheet)
        self.info_btn.pack(side="right", padx=(0, 10), pady=10)

        self.info_sheet = ctk.CTkFrame(self, fg_color="#1A1A2E", corner_radius=15, border_width=1, border_color="#2A2A4A")

        # --- Sheet Header ---
        sheet_header = ctk.CTkFrame(self.info_sheet, fg_color="transparent")
        sheet_header.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(sheet_header, text="📖  Quick Guide", font=("SF Pro Display", 16, "bold"), text_color="#FFFFFF").pack(side="left")
        ctk.CTkButton(sheet_header, text="✕", width=28, height=28, font=("SF Pro Display", 14), fg_color="#2C2C3E", hover_color="#3A3A5C", corner_radius=14, command=self.toggle_info_sheet).pack(side="right")

        # --- Separator ---
        ctk.CTkFrame(self.info_sheet, fg_color="#2A2A4A", height=1).pack(fill="x", padx=16, pady=(0, 8))

        # --- Scrollable content area ---
        info_scroll = ctk.CTkScrollableFrame(self.info_sheet, fg_color="transparent")
        info_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # --- SEND Section ---
        send_card = ctk.CTkFrame(info_scroll, fg_color="#162040", corner_radius=12, border_width=1, border_color="#1E3A6E")
        send_card.pack(fill="x", padx=8, pady=(4, 6))

        ctk.CTkLabel(send_card, text="📡  Sending Files", font=("SF Pro Display", 14, "bold"), text_color="#5AC8FA").pack(anchor="w", padx=14, pady=(12, 6))

        send_steps = [
            ("1", "Go to the  Share  tab"),
            ("2", "Pick a user from the network"),
            ("3", "Tap  Send Files  or  Send Folder"),
            ("4", "Choose what to send"),
        ]
        for num, txt in send_steps:
            row = ctk.CTkFrame(send_card, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=2)
            ctk.CTkLabel(row, text=num, width=22, height=22, font=("SF Pro Display", 11, "bold"), fg_color="#0A84FF", corner_radius=11, text_color="#FFFFFF").pack(side="left", padx=(0, 8))
            ctk.CTkLabel(row, text=txt, font=("SF Pro Display", 12), text_color="#C8C8D0", anchor="w").pack(side="left", fill="x", expand=True)
        # bottom padding inside card
        ctk.CTkFrame(send_card, fg_color="transparent", height=8).pack()

        # --- RECEIVE Section ---
        recv_card = ctk.CTkFrame(info_scroll, fg_color="#0F2E1F", corner_radius=12, border_width=1, border_color="#1E5E3A")
        recv_card.pack(fill="x", padx=8, pady=(4, 6))

        ctk.CTkLabel(recv_card, text="📥  Receiving Files", font=("SF Pro Display", 14, "bold"), text_color="#30D158").pack(anchor="w", padx=14, pady=(12, 6))

        recv_steps = [
            ("1", "Stay on the  Share  tab"),
            ("2", "Accept incoming transfer prompt"),
            ("3", "Files are saved automatically"),
            ("4", "View images in the  Gallery  tab"),
        ]
        for num, txt in recv_steps:
            row = ctk.CTkFrame(recv_card, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=2)
            ctk.CTkLabel(row, text=num, width=22, height=22, font=("SF Pro Display", 11, "bold"), fg_color="#30D158", corner_radius=11, text_color="#FFFFFF").pack(side="left", padx=(0, 8))
            ctk.CTkLabel(row, text=txt, font=("SF Pro Display", 12), text_color="#C8C8D0", anchor="w").pack(side="left", fill="x", expand=True)
        ctk.CTkFrame(recv_card, fg_color="transparent", height=8).pack()

        # --- Developer Credit ---
        ctk.CTkFrame(self.info_sheet, fg_color="#2A2A4A", height=1).pack(fill="x", padx=16, pady=(4, 0))
        dev_btn = ctk.CTkButton(
            self.info_sheet,
            text="Made with ❤️ by Sumantan",
            font=("SF Pro Display", 12),
            fg_color="transparent",
            text_color="#6E6E80",
            hover_color="#2C2C3E",
            height=36,
            command=lambda: webbrowser.open("https://www.linkedin.com/in/sumantan/")
        )
        dev_btn.pack(side="bottom", pady=(6, 12))

        self.content = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.content.pack(fill="both", expand=True)

        self.screens = {
            "gallery": GalleryScreen(self.content, self),
            "sharing": SharingScreen(self.content, self)
        }
        for screen in self.screens.values():
            screen.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.tab_bar = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0, height=80)
        self.tab_bar.pack(fill="x", side="bottom")
        self.tab_bar.pack_propagate(False)

        self.btn_gal = ctk.CTkButton(self.tab_bar, text="🖼 Gallery", font=("SF Pro", 14, "bold"), fg_color="transparent", hover_color="#2C2C2E", command=lambda: self.show_tab("gallery"))
        self.btn_gal.pack(side="left", expand=True, fill="both", padx=5, pady=5)

        self.btn_share = ctk.CTkButton(self.tab_bar, text="📡 Share", font=("SF Pro", 14, "bold"), fg_color="transparent", hover_color="#2C2C2E", command=lambda: self.show_tab("sharing"))
        self.btn_share.pack(side="right", expand=True, fill="both", padx=5, pady=5)

    def show_tab(self, tab_id):
        if hasattr(self, 'active_tab') and self.active_tab in self.screens:
            self.screens[self.active_tab].off_focus()
        self.active_tab = tab_id
        self.screens[tab_id].tkraise()
        self.screens[tab_id].on_focus()

    def toggle_info_sheet(self):
        self.info_sheet_visible = not getattr(self, "info_sheet_visible", False)
        if self.info_sheet_visible:
            self.info_sheet.place(relx=1, rely=0, relwidth=0.33, relheight=1, anchor="ne")
            self.info_sheet.tkraise()
        else:
            self.info_sheet.place_forget()

if __name__ == "__main__":
    app = GalShareApp()
    app.mainloop()