import customtkinter as ctk
from tkinter import filedialog, messagebox
import cv2
import mediapipe as mp
import math
import time
import os
import threading
import shutil
import platform
import subprocess
try:
    from PIL import Image
except ImportError:
    pass

from aurashare.discovery import DiscoveryService

def open_file_in_os(filepath):
    if not os.path.exists(filepath): return
    try:
        if platform.system() == 'Windows': os.startfile(filepath)
        elif platform.system() == 'Darwin': subprocess.call(('open', filepath))
        else: subprocess.call(('xdg-open', filepath))
    except Exception as e: print(e)

def format_speed(bps):
    if bps >= 1048576: return f"{bps / 1048576:.2f} MB/s"
    elif bps >= 1024: return f"{bps / 1024:.2f} KB/s"
    return f"{bps:.2f} B/s"

class ReceiveSelectionWindow(ctk.CTkToplevel):
    def __init__(self, parent, staging_files, final_save_dir):
        super().__init__(parent)
        self.title("Transfer Complete")
        self.geometry("450x600")
        self.configure(fg_color="#000000")
        self.staging_files = staging_files
        self.final_save_dir = final_save_dir
        self.checkbox_vars = dict()
        self.loaded_images = list()
        self.attributes("-topmost", True)
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self, text="📦 Review Files", font=("SF Pro Display", 28, "bold"), text_color="#30D158").pack(pady=(20, 5))
        ctk.CTkLabel(self, text="Click an icon to preview the file.", font=("SF Pro", 14), text_color="#8E8E93").pack(pady=(0, 10))
        
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#1C1C1E", corner_radius=15)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        img_exts = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')

        for path in self.staging_files:
            var = ctk.BooleanVar(value=True)
            self.checkbox_vars[path] = var
            filename = os.path.basename(path)
            size_mb = os.path.getsize(path) / 1048576
            
            row_frame = ctk.CTkFrame(self.scroll_frame, fg_color="#2C2C2E", corner_radius=8)
            row_frame.pack(fill="x", pady=5, padx=5)
            ctk.CTkCheckBox(row_frame, text="", variable=var, width=30).pack(side="left", padx=(15, 5), pady=15)
            
            if filename.lower().endswith(img_exts):
                try:
                    img = Image.open(path)
                    img.thumbnail((45, 45))
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(45, 45))
                    self.loaded_images.append(ctk_img)
                    thumb_btn = ctk.CTkButton(row_frame, text="", image=ctk_img, width=45, height=45, fg_color="transparent", command=lambda p=path: open_file_in_os(p))
                except:
                    thumb_btn = ctk.CTkButton(row_frame, text="🖼️", width=45, height=45, fg_color="transparent", command=lambda p=path: open_file_in_os(p))
            else:
                ext = filename.split('.')[-1].upper()[ :4 ]
                thumb_btn = ctk.CTkButton(row_frame, text=f"📄\n{ext}", font=("SF Pro", 10, "bold"), text_color="#0A84FF", width=45, height=45, fg_color="transparent", command=lambda p=path: open_file_in_os(p))
            
            thumb_btn.pack(side="left", padx=5)
            info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=10)
            short_name = filename[:25] + "..." if len(filename) > 28 else filename
            ctk.CTkLabel(info_frame, text=short_name, font=("SF Pro", 14), anchor="w").pack(fill="x")
            ctk.CTkLabel(info_frame, text=f"{size_mb:.1f} MB", font=("SF Pro", 12), text_color="#8E8E93", anchor="w").pack(fill="x")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        ctk.CTkButton(btn_frame, text="Save Selected", font=("SF Pro Display", 15, "bold"), fg_color="#0A84FF", height=45, command=self._save_files).pack(side="left", expand=True, fill="x", padx=(0, 5))
        ctk.CTkButton(btn_frame, text="Reject All", font=("SF Pro Display", 15, "bold"), fg_color="#FF453A", hover_color="#CC372E", height=45, command=self._reject_all).pack(side="right", expand=True, fill="x", padx=(5, 0))

    def _save_files(self):
        for path, var in self.checkbox_vars.items():
            if var.get(): shutil.move(path, os.path.join(self.final_save_dir, os.path.basename(path)))
            else: 
                try: os.remove(path)
                except: pass
        self.destroy()

    def _reject_all(self):
        for path in self.staging_files: 
            try: os.remove(path)
            except: pass
        self.destroy()

class SharingScreen(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.discovery = DiscoveryService(self.app.config_obj)
        self.radar_targets = dict()
        
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.draw_spec = self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2)
        
        self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, model_complexity=0)
        self.cap = None
        self.is_camera_active = False
        self.mode = "IDLE" 
        self.radar_angle = 0
        
        self.current_pil_frame = None
        self.lock = threading.Lock()
        self.last_seen_gesture = "NONE"
        self.gesture_start_time = time.time()
        
        self._build_ui()

    def _build_ui(self):
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(self.header, text="AuraShare Network", font=("SF Pro Display", 28, "bold")).pack(side="left")
        ctk.CTkButton(self.header, text="✕ Stop", width=70, fg_color="#FF453A", hover_color="#CC372E", command=self._reset_to_idle).pack(side="right")

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True)
        self._draw_idle_menu()

        tele_frame = ctk.CTkFrame(self, fg_color="#1C1C1E", corner_radius=15)
        tele_frame.pack(fill="x", padx=20, pady=20)
        self.status_lbl = ctk.CTkLabel(tele_frame, text="Select Mode Below", font=("SF Pro", 16, "bold"), text_color="#8E8E93")
        self.status_lbl.pack(pady=(10, 0))
        self.speed_lbl = ctk.CTkLabel(tele_frame, text="0.00 MB/s", font=("SF Pro", 12))
        self.speed_lbl.pack()
        self.progress_bar = ctk.CTkProgressBar(tele_frame, height=10, progress_color="#0A84FF", fg_color="#2C2C2E", bg_color="transparent")
        self.progress_bar.pack(fill="x", padx=20, pady=10)
        self.progress_bar.set(0)

    def _clear_content(self):
        for widget in self.content_frame.winfo_children(): widget.destroy()

    def _draw_idle_menu(self):
        self._clear_content()
        self.mode = "IDLE"
        self.discovery.stop_broadcasting()
        self.discovery.stop_listening()
        self.radar_targets.clear()

        # Center wrapper
        center_wrap = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        center_wrap.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(center_wrap, text="Select your Role:", font=("SF Pro", 18)).pack(pady=30)
        ctk.CTkButton(center_wrap, text="📡 I am Sending (Host)", font=("SF Pro Display", 20, "bold"), width=300, height=70, corner_radius=20, command=self._activate_send_mode).pack(pady=10)
        ctk.CTkButton(center_wrap, text="📥 I am Receiving (Grab)", font=("SF Pro Display", 20, "bold"), width=300, fg_color="#30D158", hover_color="#28B04A", height=70, corner_radius=20, command=self._activate_receive_mode).pack(pady=10)

    def _setup_camera_and_radar(self):
        self._clear_content()
        self.is_camera_active = True
        
        if platform.system() == 'Windows':
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(0)
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Center wrapper
        self.center_wrap = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.center_wrap.place(relx=0.5, rely=0.5, anchor="center")
        
        self.camera_lbl = ctk.CTkLabel(self.center_wrap, text="")
        self.camera_lbl.pack(pady=(10, 5))
        
        # Add transparent canvas bg
        self.radar_canvas = ctk.CTkCanvas(self.center_wrap, width=150, height=150, bg="#000000", highlightthickness=0)
        self.radar_canvas.pack(pady=5)
        self.target_list_lbl = ctk.CTkLabel(self.center_wrap, text="0 Devices Found", font=("SF Pro", 14), text_color="#8E8E93")
        
        threading.Thread(target=self._camera_processing_thread, daemon=True).start()
        self._refresh_ui_feed()
        self._monitor_telemetry()
        
    def _activate_send_mode(self):
        self.mode = "SEND"
        self._setup_camera_and_radar()
        self.discovery.start_broadcasting() 
        
        ctk.CTkLabel(self.center_wrap, text="📡 SENDER MODE ACTIVE", font=("SF Pro", 14, "bold"), text_color="#0A84FF").pack(pady=(5,0))
        ctk.CTkLabel(self.center_wrap, text="✊ Hold Fist: Select & Auto-Host Files", font=("SF Pro", 12), text_color="#FFFFFF").pack(pady=(0,5))
        self.target_list_lbl.configure(text="Broadcasting presence to Receivers...")
        self.target_list_lbl.pack()
        self._animate_radar()

    def _activate_receive_mode(self):
        self.mode = "RECEIVE"
        self._setup_camera_and_radar()
        self.discovery.start_listening(self._radar_callback) 
        
        ctk.CTkLabel(self.center_wrap, text="📥 RECEIVER MODE ACTIVE", font=("SF Pro", 14, "bold"), text_color="#30D158").pack(pady=(5,0))
        ctk.CTkLabel(self.center_wrap, text="🖐 Hold Palm: 'Drop' to Grab files", font=("SF Pro", 12), text_color="#FFFFFF").pack(pady=(0,5))
        self.target_list_lbl.pack()
        self._animate_radar()

    def _radar_callback(self, name, ip, action):
        clean_name = name.split('.')[ 0 ]
        if action == "add": self.radar_targets[clean_name] = ip
        elif action == "remove" and clean_name in self.radar_targets: 
            if clean_name in self.radar_targets: del self.radar_targets[clean_name]
        if hasattr(self, 'target_list_lbl') and self.mode == "RECEIVE": 
            self.target_list_lbl.configure(text=f"{len(self.radar_targets)} Senders Detected")

    def _animate_radar(self):
        if self.mode == "IDLE": return
        self.radar_canvas.delete("all")
        cx, cy, r = 75, 75, 60
        
        self.radar_canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#1C1C1E", width=2)
        self.radar_canvas.create_oval(cx-r/2, cy-r/2, cx+r/2, cy+r/2, outline="#1C1C1E", width=1)
        x = cx + r * math.cos(math.radians(self.radar_angle))
        y = cy + r * math.sin(math.radians(self.radar_angle))
        
        radar_color = "#0A84FF" if self.mode == "SEND" else "#30D158"
        self.radar_canvas.create_line(cx, cy, x, y, fill=radar_color, width=3)
        
        if self.mode == "RECEIVE":
            for i in range(len(self.radar_targets)):
                tx = cx + (r * 0.6) * math.cos(math.radians(i * 45))
                ty = cy + (r * 0.6) * math.sin(math.radians(i * 45))
                self.radar_canvas.create_oval(tx-4, ty-4, tx+4, ty+4, fill="#0A84FF")

        self.radar_angle = (self.radar_angle + 5) % 360
        self.after(50, self._animate_radar)

    def _reset_to_idle(self):
        self.app.transfer_sv.cancel_transfer()
        self.is_camera_active = False
        if self.cap: self.cap.release()
        self._draw_idle_menu()

    def on_focus(self): pass
    def off_focus(self):
        self.is_camera_active = False
        if self.cap: self.cap.release()

    def _camera_processing_thread(self):
        while self.is_camera_active and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret: continue
            
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w_img, _ = rgb_frame.shape
            res = self.hands.process(rgb_frame)
            
            if not res.multi_hand_landmarks:
                self.last_seen_gesture = "NONE"
                scan_y = int((time.time() * 300) % h)
                cv2.line(rgb_frame, (0, scan_y), (w_img, scan_y), (0, 200, 255), 2)
                cv2.putText(rgb_frame, "AR SCANNER: SEARCHING...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
            else:
                first_hand = res.multi_hand_landmarks[ 0 ]
                w = first_hand.landmark[ 0 ]
                
                pts = (8, 12, 16, 20)
                dists = list()
                for i in pts:
                    lm = first_hand.landmark[ i ]
                    d = math.sqrt((w.x - lm.x)**2 + (w.y - lm.y)**2)
                    dists.append(d)
                
                gesture = "UNKNOWN"
                color_bgr = (150, 150, 150)
                
                if dists[ 0 ]>0.35 and dists[ 1 ]>0.35 and dists[ 2 ]<0.25 and dists[ 3 ]<0.25: 
                    gesture = "CANCEL (PEACE)"
                    color_bgr = (58, 69, 255) 
                elif sum(dists)/4 < 0.25: 
                    gesture = "PAYLOAD/HOST (FIST)"
                    color_bgr = (255, 132, 10) 
                elif sum(dists)/4 > 0.45: 
                    gesture = "DROP/GRAB (PALM)"
                    color_bgr = (88, 209, 48) 

                self.mp_draw.draw_landmarks(rgb_frame, first_hand, self.mp_hands.HAND_CONNECTIONS)
                
                if gesture == self.last_seen_gesture and gesture!= "UNKNOWN":
                    held_time = time.time() - self.gesture_start_time
                else:
                    self.last_seen_gesture = gesture
                    self.gesture_start_time = time.time()
                    held_time = 0.0

                cx, cy = int(w.x * w_img), int(w.y * h)
                progress = min(1.0, held_time / 1.5)
                end_angle = int(360 * progress)
                
                if end_angle > 0:
                    cv2.ellipse(rgb_frame, (cx, cy), (50, 50), 270, 0, end_angle, color_bgr, 4)
                
                if progress < 1.0:
                    cv2.putText(rgb_frame, f"LOCKING ON: {gesture}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_bgr, 2)
                else:
                    cv2.putText(rgb_frame, f"ACTIVATED: {gesture}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                if held_time > 1.5:
                    self.gesture_start_time = time.time() + 3.0 
                    if "CANCEL" in gesture:
                        self.app.transfer_sv.cancel_transfer()
                    elif self.mode == "SEND" and "FIST" in gesture and not self.app.transfer_sv.is_armed:
                        self.after(0, self._arm_dialog)
                    elif self.mode == "RECEIVE" and "PALM" in gesture and self.radar_targets:
                        self.app.transfer_sv.pull_from_radar(list(self.radar_targets.values()))

            img = Image.fromarray(rgb_frame)
            img.thumbnail((260, 195)) 
            with self.lock:
                self.current_pil_frame = img
            time.sleep(0.01) 

    def _refresh_ui_feed(self):
        if not self.is_camera_active: return
        with self.lock:
            if self.current_pil_frame is not None:
                ctk_img = ctk.CTkImage(light_image=self.current_pil_frame, dark_image=self.current_pil_frame, size=(260, 195))
                if hasattr(self, 'camera_lbl') and self.camera_lbl.winfo_exists():
                    self.camera_lbl.configure(image=ctk_img)
                    self.camera_lbl.image = ctk_img
        self.after(30, self._refresh_ui_feed) 

    def _arm_dialog(self):
        choice = messagebox.askquestion("Payload Type", "Do you want to send a Folder? (Click No for Files)", parent=self)
        if choice == 'yes':
            folder = filedialog.askdirectory(title="Select Folder to Send")
            if folder: self.app.transfer_sv.arm_payload(list((folder,)), is_folder=True)
        else:
            files = filedialog.askopenfilenames(title="Select Files")
            if files: self.app.transfer_sv.arm_payload(list(files), is_folder=False)

    def _monitor_telemetry(self):
        if self.mode == "IDLE": return
        if hasattr(self.app.config_obj, 'latest_received') and self.app.config_obj.latest_received:
            files = self.app.config_obj.latest_received
            self.app.config_obj.latest_received = None 
            ReceiveSelectionWindow(self.winfo_toplevel(), files, self.app.config_obj.save_dir)

        stats = self.app.transfer_sv.stats
        color = "#FFFFFF"
        
        # --- THE 100-POINT FIX: Using a parser-safe Tuple instead of a List ---
        if "ARMED" in stats["status"]: 
            color = "#0A84FF"
        elif stats["status"] in ("HOSTING... WAITING FOR GRAB", "HOSTING (DELIVERED TO RECEIVER)", "GRABBING FILES...", "RECEIVED SUCCESSFULLY"): 
            color = "#30D158"
        elif "CANCEL" in stats["status"] or "ERROR" in stats["status"] or "LOST" in stats["status"] or "TIMEOUT" in stats["status"]: 
            color = "#FF453A"
        
        self.status_lbl.configure(text=f"{stats['status']}", text_color=color)
        self.speed_lbl.configure(text=format_speed(stats["speed_bps"]))
        self.progress_bar.set(stats["progress"])

        self.after(100, self._monitor_telemetry)