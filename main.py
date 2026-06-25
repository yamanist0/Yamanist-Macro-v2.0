import customtkinter as ctk
import tkinter as tk
import time
import json
import os
import ctypes
import threading
import random
from pynput.mouse import Button, Controller as MouseController, Listener as MouseListener
from pynput.keyboard import Key, Controller as KeyboardController, Listener as KeyboardListener, KeyCode

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG_DARK = "#0d0d0d"
BG_CARD = "#1a1a2e"
BG_CARD_HOVER = "#1f1f3a"
ACCENT = "#e94560"
ACCENT_HOVER = "#ff6b81"
ACCENT_DIM = "#c23152"
TEXT_PRIMARY = "#eaeaea"
TEXT_SECONDARY = "#8888aa"
BORDER_COLOR = "#2a2a4a"
SLIDER_TRACK = "#16213e"
TOGGLE_ON = "#e94560"
TOGGLE_OFF = "#333355"

class MacroApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Macro")
        self.geometry("420x600")
        self.resizable(False, False)
        self.overrideredirect(True)
        self.configure(fg_color=BG_DARK)

        self.cps_var = tk.DoubleVar(value=10)
        self.keybind_var = tk.StringVar(value="mouse4")
        self.mode_var = tk.StringVar(value="Toggle")
        self.turbo_var = tk.BooleanVar(value=False)
        self.rand_var = tk.BooleanVar(value=False)
        self.rand_percent_var = tk.DoubleVar(value=5)
        self.macro_type_var = tk.StringVar(value="click_e")
        self.custom_key_var = tk.StringVar(value="e")
        self.suppress_var = tk.BooleanVar(value=False)
        self.manual_var = tk.BooleanVar(value=False)
        self.delay_click_e_var = tk.StringVar(value="25")
        self.delay_wait_var = tk.StringVar(value="25")
        self.waiting_for_key = False
        self.waiting_for_custom_key = False

        self._load_settings()

        self._build_status_bar()

        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.pack(fill="both", expand=True)
        self.scroll_velocity = 0.0
        self.scroll_running = False
        self.scroll_remainder = 0.0
        self.SCROLL_FRICTION = 0.88
        
        self.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self._build_header()
        self._build_cps_section()
        self._build_keybind_section()
        self._build_mode_section()
        self._build_macro_type_section()

        self._init_physics()

        self.after(10, self._set_appwindow)

        self.lift()
        self.attributes("-topmost", True)
        self.after(500, lambda: self.attributes("-topmost", False))

        self._init_macro_engine()
        self._apply_loaded_settings()

    def _build_header(self):
        header = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(28, 0))
        
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(fill="x")

        title = ctk.CTkLabel(
            title_frame,
            text="MACRO",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=ACCENT,
        )
        title.pack(side="left")

        close_btn = ctk.CTkButton(
            title_frame, text="✕", width=36, height=36, 
            fg_color="transparent", hover_color="#e94560", 
            command=self._quit_app, font=ctk.CTkFont(size=14, weight="bold")
        )
        close_btn.pack(side="right")
        
        min_btn = ctk.CTkButton(
            title_frame, text="—", width=36, height=36, 
            fg_color="transparent", hover_color="#333355", 
            command=self._minimize_app, font=ctk.CTkFont(size=14, weight="bold")
        )
        min_btn.pack(side="right", padx=(0, 2))

        subtitle = ctk.CTkLabel(
            header,
            text="MACRO TOOL (FULLY OPENSOURCE)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=TEXT_SECONDARY,
        )
        subtitle.pack(anchor="w", pady=(0, 2))

        line = ctk.CTkFrame(self.main_scroll, height=2, fg_color=ACCENT, corner_radius=1)
        line.pack(fill="x", padx=30, pady=(8, 0))

    def _on_mouse_wheel(self, event):
        added_velocity = -1 * (event.delta / 120) * 8.0
        self.scroll_velocity += added_velocity
        
        # Cap velocity
        if self.scroll_velocity > 40: self.scroll_velocity = 40
        elif self.scroll_velocity < -40: self.scroll_velocity = -40
            
        if not self.scroll_running:
            self.scroll_running = True
            self._scroll_physics_loop()

    def _scroll_physics_loop(self):
        if not self.scroll_running:
            return
            
        if abs(self.scroll_velocity) < 0.1:
            self.scroll_velocity = 0.0
            self.scroll_running = False
            self.scroll_remainder = 0.0
            return
            
        total_delta = self.scroll_velocity + self.scroll_remainder
        scroll_amount = int(total_delta)
        self.scroll_remainder = total_delta - scroll_amount
        
        if scroll_amount != 0:
            try:
                self.main_scroll._parent_canvas.yview_scroll(scroll_amount, "units")
            except Exception:
                pass
                
        self.scroll_velocity *= self.SCROLL_FRICTION
        self.after(16, self._scroll_physics_loop)

    def _quit_app(self):
        self._save_settings()
        self.destroy()

    def _set_appwindow(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style & ~WS_EX_TOOLWINDOW
            style = style | WS_EX_APPWINDOW
            
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            
            self.withdraw()
            self.deiconify()
        except Exception:
            pass

    def _minimize_app(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.user32.ShowWindow(hwnd, 6)
        except Exception:
            self.iconify()

    def _build_cps_section(self):
        card = self._create_card()

        self.cps_top_row = ctk.CTkFrame(card, fg_color="transparent")
        self.cps_top_row.pack(fill="x")

        self.cps_title_label = ctk.CTkLabel(
            self.cps_top_row,
            text="⚡ Speed",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
        )
        self.cps_title_label.pack(side="left")

        self.cps_display = ctk.CTkLabel(
            self.cps_top_row,
            text="10",
            font=ctk.CTkFont(family="Consolas", size=22, weight="bold"),
            text_color=ACCENT,
        )
        self.cps_display.pack(side="right")

        self.cps_slider = ctk.CTkSlider(
            card,
            from_=1,
            to=25,
            number_of_steps=49,
            variable=self.cps_var,
            command=self._on_cps_change,
            width=340,
            height=18,
            fg_color=SLIDER_TRACK,
            progress_color=ACCENT,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
        )
        self.cps_slider.pack(pady=(12, 4))

        self.range_row = ctk.CTkFrame(card, fg_color="transparent")
        self.range_row.pack(fill="x")
        ctk.CTkLabel(self.range_row, text="1", font=ctk.CTkFont(size=10), text_color=TEXT_SECONDARY).pack(side="left")
        self.cps_max_label = ctk.CTkLabel(self.range_row, text="25", font=ctk.CTkFont(size=10), text_color=TEXT_SECONDARY)
        self.cps_max_label.pack(side="right")

        turbo_row = ctk.CTkFrame(card, fg_color="transparent")
        turbo_row.pack(fill="x", pady=(10, 0))

        self.turbo_check = ctk.CTkCheckBox(
            turbo_row,
            text="Turbo",
            variable=self.turbo_var,
            command=self._on_turbo_toggle,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ff4444",
            fg_color=TOGGLE_OFF,
            hover_color="#ff4444",
            checkmark_color="#ffffff",
            border_color="#ff4444",
            corner_radius=4,
        )
        self.turbo_check.pack(side="left")

        ctk.CTkLabel(
            turbo_row,
            text="(not rec)",
            font=ctk.CTkFont(size=10),
            text_color="#ff4444",
        ).pack(side="left", padx=(6, 0))

        self.rand_row = ctk.CTkFrame(card, fg_color="transparent")
        self.rand_row.pack(fill="x", pady=(8, 0))

        self.rand_check = ctk.CTkCheckBox(
            self.rand_row,
            text="Randomize",
            variable=self.rand_var,
            command=self._on_rand_toggle,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#00ffcc",
            fg_color=TOGGLE_OFF,
            hover_color="#00ffcc",
            checkmark_color="#ffffff",
            border_color="#00ffcc",
            corner_radius=4,
        )
        self.rand_check.pack(side="left")

        self.rand_frame = ctk.CTkFrame(card, fg_color="transparent")
        
        self.rand_val_label = ctk.CTkLabel(self.rand_frame, text="5% Rand", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00ffcc")
        self.rand_val_label.pack(side="top", anchor="w", padx=4)

        self.rand_slider = ctk.CTkSlider(
            self.rand_frame,
            from_=0, to=15, number_of_steps=15,
            variable=self.rand_percent_var,
            command=self._on_rand_slide,
            width=340, height=14,
            fg_color=SLIDER_TRACK,
            progress_color="#00ffcc", button_color="#00ffcc", button_hover_color="#00ffee"
        )
        self.rand_slider.pack(pady=(2, 4))
        
        manual_row = ctk.CTkFrame(card, fg_color="transparent")
        manual_row.pack(fill="x", pady=(8, 0))

        self.manual_check = ctk.CTkCheckBox(
            manual_row,
            text="Manual (ms)",
            variable=self.manual_var,
            command=self._on_manual_toggle,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffaa00",
            fg_color=TOGGLE_OFF,
            hover_color="#ffaa00",
            checkmark_color="#ffffff",
            border_color="#ffaa00",
            corner_radius=4,
        )
        self.manual_check.pack(side="left")

        self.manual_frame = ctk.CTkFrame(card, fg_color="transparent")

        self._build_manual_inputs()

    def _on_cps_change(self, value):
        self.cps_display.configure(text=str(int(value)))

    def _on_turbo_toggle(self):
        if self.turbo_var.get():
            new_max = 500
            steps = 499
        else:
            new_max = 25
            steps = 49
            if self.cps_var.get() > 25:
                self.cps_var.set(25)
                self.cps_display.configure(text="25")

        self.cps_slider.configure(to=new_max, number_of_steps=steps)
        self.cps_max_label.configure(text=str(new_max))

        current = self.cps_var.get()
        self.cps_slider.set(current)

    def _on_rand_toggle(self):
        if self.rand_var.get():
            self.rand_frame.pack(fill="x", after=self.rand_row)
        else:
            self.rand_frame.pack_forget()

    def _on_rand_slide(self, val):
        self.rand_val_label.configure(text=f"{int(val)}% Rand")

    def _on_manual_toggle(self):
        if self.manual_var.get():
            self._hide_slider_area()
            self._refresh_manual_inputs()
            self.manual_frame.pack(fill="x", pady=(10, 0))
        else:
            self.manual_frame.pack_forget()
            self._show_slider_area()

    def _hide_slider_area(self):
        self.cps_slider.pack_forget()
        self.cps_display.pack_forget()
        self.range_row.pack_forget()

    def _show_slider_area(self):
        self.cps_display.pack(side="right")
        self.cps_slider.pack(pady=(12, 4), after=self.cps_top_row)
        self.range_row.pack(fill="x", after=self.cps_slider)

    def _build_manual_inputs(self):
        # build widgets
        self._refresh_manual_inputs()

    def _refresh_manual_inputs(self):
        for w in self.manual_frame.winfo_children():
            w.destroy()

        mtype = self.macro_type_var.get()

        if mtype == "click_e":
            row1 = ctk.CTkFrame(self.manual_frame, fg_color="transparent")
            row1.pack(fill="x", pady=(0, 6))
            ctk.CTkLabel(
                row1, text="Click -> E wait:",
                font=ctk.CTkFont(size=11), text_color=TEXT_SECONDARY,
            ).pack(side="left")
            e1 = ctk.CTkEntry(
                row1, textvariable=self.delay_click_e_var,
                width=70, height=30,
                font=ctk.CTkFont(family="Consolas", size=13),
                fg_color=BG_DARK, border_color=ACCENT, border_width=1,
            )
            e1.pack(side="right")
            ctk.CTkLabel(
                row1, text="ms", font=ctk.CTkFont(size=10), text_color=TEXT_SECONDARY,
            ).pack(side="right", padx=(0, 4))

            row2 = ctk.CTkFrame(self.manual_frame, fg_color="transparent")
            row2.pack(fill="x")
            ctk.CTkLabel(
                row2, text="Loop wait:",
                font=ctk.CTkFont(size=11), text_color=TEXT_SECONDARY,
            ).pack(side="left")
            e2 = ctk.CTkEntry(
                row2, textvariable=self.delay_wait_var,
                width=70, height=30,
                font=ctk.CTkFont(family="Consolas", size=13),
                fg_color=BG_DARK, border_color=ACCENT, border_width=1,
            )
            e2.pack(side="right")
            ctk.CTkLabel(
                row2, text="ms", font=ctk.CTkFont(size=10), text_color=TEXT_SECONDARY,
            ).pack(side="right", padx=(0, 4))
        else:
            row1 = ctk.CTkFrame(self.manual_frame, fg_color="transparent")
            row1.pack(fill="x")
            ctk.CTkLabel(
                row1, text="Click wait:",
                font=ctk.CTkFont(size=11), text_color=TEXT_SECONDARY,
            ).pack(side="left")
            e1 = ctk.CTkEntry(
                row1, textvariable=self.delay_wait_var,
                width=70, height=30,
                font=ctk.CTkFont(family="Consolas", size=13),
                fg_color=BG_DARK, border_color=ACCENT, border_width=1,
            )
            e1.pack(side="right")
            ctk.CTkLabel(
                row1, text="ms", font=ctk.CTkFont(size=10), text_color=TEXT_SECONDARY,
            ).pack(side="right", padx=(0, 4))

    def _build_keybind_section(self):
        card = self._create_card()

        ctk.CTkLabel(
            card,
            text="🎯 Trigger",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))

        self.keybind_button = ctk.CTkButton(
            btn_frame,
            textvariable=self.keybind_var,
            font=ctk.CTkFont(family="Consolas", size=16, weight="bold"),
            width=200,
            height=44,
            fg_color=BG_DARK,
            hover_color=BG_CARD_HOVER,
            border_width=2,
            border_color=ACCENT,
            corner_radius=10,
            command=self._start_keybind_listen,
        )
        self.keybind_button.pack(side="left")

        self.keybind_hint = ctk.CTkLabel(
            btn_frame,
            text="Click to\nchange",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_SECONDARY,
            justify="left",
        )
        self.keybind_hint.pack(side="left", padx=(14, 0))

        suppress_row = ctk.CTkFrame(card, fg_color="transparent")
        suppress_row.pack(fill="x", pady=(12, 0))

        self.suppress_check = ctk.CTkCheckBox(
            suppress_row,
            text="Block original key input",
            variable=self.suppress_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ff4444",
            fg_color=TOGGLE_OFF,
            hover_color="#ff4444",
            checkmark_color="#ffffff",
            border_color="#ff4444",
            corner_radius=4,
        )
        self.suppress_check.pack(side="left")

    def _start_keybind_listen(self):
        if self.waiting_for_key:
            return
        self.waiting_for_key = True
        self.keybind_var.set("Press key...")
        self.keybind_button.configure(border_color=ACCENT_HOVER, fg_color="#1a0a10")
        self.keybind_hint.configure(text="Wait...")

        self.bind("<ButtonPress>", self._on_mouse_press)
        self.bind("<KeyPress>", self._on_key_press)

    def _on_key_press(self, event):
        if not self.waiting_for_key:
            return
        key_name = event.keysym.lower()
        self._set_keybind(key_name)

    def _on_mouse_press(self, event):
        if not self.waiting_for_key:
            return

        mouse_map = {
            2: "mouse3",
            3: "mouse2",
            4: "mouse4",
            5: "mouse5",
        }

        if event.num in mouse_map:
            self._set_keybind(mouse_map[event.num])
        elif event.num == 1:
            widget = event.widget
            if widget != self.keybind_button:
                self._set_keybind("mouse1")

    def _set_keybind(self, key_name):
        self.waiting_for_key = False
        self.keybind_var.set(key_name)
        self.keybind_button.configure(border_color=ACCENT, fg_color=BG_DARK)
        self.keybind_hint.configure(text="Click to\nchange")
        self.unbind("<ButtonPress>")
        self.unbind("<KeyPress>")

    def _build_mode_section(self):
        card = self._create_card()

        ctk.CTkLabel(
            card,
            text="🔄 Mode",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")

        mode_frame = ctk.CTkFrame(card, fg_color="transparent")
        mode_frame.pack(fill="x", pady=(10, 0))

        self.toggle_btn = ctk.CTkButton(
            mode_frame,
            text="Toggle",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=160,
            height=42,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            corner_radius=10,
            command=lambda: self._set_mode("Toggle"),
        )
        self.toggle_btn.pack(side="left", padx=(0, 8))

        self.hold_btn = ctk.CTkButton(
            mode_frame,
            text="Hold",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=160,
            height=42,
            fg_color=TOGGLE_OFF,
            hover_color=BG_CARD_HOVER,
            corner_radius=10,
            command=lambda: self._set_mode("Hold"),
        )
        self.hold_btn.pack(side="left")

        self.mode_desc = ctk.CTkLabel(
            card,
            text="Press -> Start, Press -> Stop",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_SECONDARY,
        )
        self.mode_desc.pack(anchor="w", pady=(8, 0))

    def _set_mode(self, mode):
        self.mode_var.set(mode)
        if mode == "Toggle":
            self.toggle_btn.configure(fg_color=ACCENT, hover_color=ACCENT_HOVER)
            self.hold_btn.configure(fg_color=TOGGLE_OFF, hover_color=BG_CARD_HOVER)
            self.mode_desc.configure(text="Press -> Start, Press -> Stop")
        else:
            self.hold_btn.configure(fg_color=ACCENT, hover_color=ACCENT_HOVER)
            self.toggle_btn.configure(fg_color=TOGGLE_OFF, hover_color=BG_CARD_HOVER)
            self.mode_desc.configure(text="Hold -> Run, Release -> Stop")

    def _build_macro_type_section(self):
        card = self._create_card()

        ctk.CTkLabel(
            card,
            text="🖱 Macro Type",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")

        type_frame = ctk.CTkFrame(card, fg_color="transparent")
        type_frame.pack(fill="x", pady=(10, 0))

        self.click_e_btn = ctk.CTkButton(
            type_frame,
            text="Left Click + E",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=160,
            height=42,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            corner_radius=10,
            command=lambda: self._set_macro_type("click_e"),
        )
        self.click_e_btn.pack(side="left", padx=(0, 8))

        self.click_only_btn = ctk.CTkButton(
            type_frame,
            text="Left Click Only",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=160,
            height=42,
            fg_color=TOGGLE_OFF,
            hover_color=BG_CARD_HOVER,
            corner_radius=10,
            command=lambda: self._set_macro_type("click_only"),
        )
        self.click_only_btn.pack(side="left")

        type_frame2 = ctk.CTkFrame(card, fg_color="transparent")
        type_frame2.pack(fill="x", pady=(8, 0))

        self.e_only_btn = ctk.CTkButton(
            type_frame2,
            text="E Only",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=160,
            height=42,
            fg_color=TOGGLE_OFF,
            hover_color=BG_CARD_HOVER,
            corner_radius=10,
            command=lambda: self._set_macro_type("e_only"),
        )
        self.e_only_btn.pack(side="left", padx=(0, 8))

        self.custom_key_btn = ctk.CTkButton(
            type_frame2,
            text=f"[{self.custom_key_var.get().upper()}]",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=160,
            height=42,
            fg_color=TOGGLE_OFF,
            hover_color=BG_CARD_HOVER,
            corner_radius=10,
            command=self._on_custom_key_btn_click,
        )
        self.custom_key_btn.pack(side="left")

        self.macro_type_desc = ctk.CTkLabel(
            card,
            text="Click -> Wait -> E",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_SECONDARY,
        )
        self.macro_type_desc.pack(anchor="w", pady=(8, 0))

    def _on_custom_key_btn_click(self):
        mtype = self.macro_type_var.get()
        if mtype != "custom_key":
            self._set_macro_type("custom_key")
            return
        self._start_custom_key_listen()

    def _start_custom_key_listen(self):
        if self.waiting_for_custom_key:
            return
        self.waiting_for_custom_key = True
        self.custom_key_btn.configure(text="Press key...", border_color=ACCENT_HOVER, fg_color="#1a0a10")
        self.bind("<KeyPress>", self._on_custom_key_press)

    def _on_custom_key_press(self, event):
        if not self.waiting_for_custom_key:
            return
        key_name = event.keysym.lower()
        self.custom_key_var.set(key_name)
        self.waiting_for_custom_key = False
        self.custom_key_btn.configure(
            text=f"[{key_name.upper()}]",
            border_color=BORDER_COLOR,
            fg_color=ACCENT,
        )
        self.unbind("<KeyPress>")
        self.macro_type_desc.configure(text=f"Spam {key_name.upper()} key")

    def _abort_custom_key_listen(self):
        if not self.waiting_for_custom_key:
            return
        self.waiting_for_custom_key = False
        self.unbind("<KeyPress>")
        ck = self.custom_key_var.get()
        self.custom_key_btn.configure(
            text=f"[{ck.upper()}]",
            border_color=BORDER_COLOR,
        )

    def _set_macro_type(self, mtype):
        if mtype != "custom_key":
            self._abort_custom_key_listen()
            
        self.macro_type_var.set(mtype)
        all_btns = {
            "click_e": self.click_e_btn,
            "click_only": self.click_only_btn,
            "e_only": self.e_only_btn,
            "custom_key": self.custom_key_btn,
        }
        for key, btn in all_btns.items():
            if key == mtype:
                btn.configure(fg_color=ACCENT, hover_color=ACCENT_HOVER)
            else:
                btn.configure(fg_color=TOGGLE_OFF, hover_color=BG_CARD_HOVER)

        descs = {
            "click_e": "Click -> Wait -> E",
            "click_only": "Left click spam",
            "e_only": "Spam E key",
            "custom_key": f"Spam {self.custom_key_var.get().upper()} key",
        }
        self.macro_type_desc.configure(text=descs.get(mtype, ""))

        if hasattr(self, 'cps_title_label'):
            if mtype == "click_e":
                self.cps_title_label.configure(text="⚡ Speed")
            else:
                self.cps_title_label.configure(text="⚡ CPS")

        if mtype == "custom_key":
            self.after(100, self._start_custom_key_listen)

        if self.manual_var.get():
            self._refresh_manual_inputs()

    def _build_status_bar(self):
        bar = ctk.CTkFrame(self, fg_color=BG_CARD, height=36, corner_radius=0)
        bar.pack(fill="x", side="bottom")

        self.status_dot = ctk.CTkLabel(
            bar,
            text="*",
            font=ctk.CTkFont(size=10),
            text_color="#555577",
        )
        self.status_dot.pack(side="left", padx=(16, 6))

        self.status_label = ctk.CTkLabel(
            bar,
            text="Ready - OFF - made by yamanist",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_SECONDARY,
        )
        self.status_label.pack(side="left")

        ver_label = ctk.CTkLabel(
            bar,
            text="2.0",
            font=ctk.CTkFont(size=10),
            text_color="#444466",
        )
        ver_label.pack(side="right", padx=(0, 16))

    def _get_settings_path(self):
        folder = os.path.join(os.environ.get("APPDATA", "."), "macrosettings")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, "settings.json")

    def _load_settings(self):
        path = self._get_settings_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.cps_var.set(data.get("cps", 10))
            self.keybind_var.set(data.get("keybind", "mouse4"))
            self.mode_var.set(data.get("mode", "Toggle"))
            self.macro_type_var.set(data.get("macro_type", "click_e"))
            self.custom_key_var.set(data.get("custom_key", "e"))
            self.suppress_var.set(data.get("suppress", False))
            self.turbo_var.set(data.get("turbo", False))
            self.rand_var.set(data.get("randomize", False))
            self.rand_percent_var.set(data.get("rand_percent", 5))
            self.manual_var.set(data.get("manual", False))
            self.delay_click_e_var.set(data.get("delay_click_e", "25"))
            self.delay_wait_var.set(data.get("delay_wait", "25"))
        except Exception:
            pass

    def _save_settings(self):
        data = {
            "cps": self.cps_var.get(),
            "keybind": self.keybind_var.get(),
            "mode": self.mode_var.get(),
            "macro_type": self.macro_type_var.get(),
            "custom_key": self.custom_key_var.get(),
            "suppress": self.suppress_var.get(),
            "turbo": self.turbo_var.get(),
            "randomize": self.rand_var.get(),
            "rand_percent": self.rand_percent_var.get(),
            "manual": self.manual_var.get(),
            "delay_click_e": self.delay_click_e_var.get(),
            "delay_wait": self.delay_wait_var.get(),
        }
        try:
            with open(self._get_settings_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _apply_loaded_settings(self):
        # sync UI buttons/panels to loaded values
        self._set_mode(self.mode_var.get())

        # for custom_key, update button text first to avoid listen prompt
        mtype = self.macro_type_var.get()
        if mtype == "custom_key":
            ck = self.custom_key_var.get()
            self.custom_key_btn.configure(text=f"[{ck.upper()}]")
            # set buttons without triggering listen
            all_btns = {
                "click_e": self.click_e_btn,
                "click_only": self.click_only_btn,
                "e_only": self.e_only_btn,
                "custom_key": self.custom_key_btn,
            }
            for key, btn in all_btns.items():
                if key == mtype:
                    btn.configure(fg_color=ACCENT, hover_color=ACCENT_HOVER)
                else:
                    btn.configure(fg_color=TOGGLE_OFF, hover_color=BG_CARD_HOVER)
            self.macro_type_desc.configure(text=f"Spam {ck.upper()} key")
            if hasattr(self, 'cps_title_label'):
                self.cps_title_label.configure(text="⚡ CPS")
        else:
            self._set_macro_type(mtype)

        self._on_turbo_toggle()
        self.cps_display.configure(text=str(int(self.cps_var.get())))
        if self.rand_var.get():
            self.rand_frame.pack(fill="x", after=self.rand_row)
            self.rand_val_label.configure(text=f"{int(self.rand_percent_var.get())}% Rand")
        if self.manual_var.get():
            self._hide_slider_area()
            self._refresh_manual_inputs()
            self.manual_frame.pack(fill="x", pady=(10, 0))

    def _init_macro_engine(self):
        self.macro_active = False
        self.macro_thread = None
        self._mouse_ctrl = MouseController()
        self._kb_ctrl = KeyboardController()

        self._mouse_button_map = {
            "mouse1": Button.left,
            "mouse2": Button.right,
            "mouse3": Button.middle,
            "mouse4": Button.x1,
            "mouse5": Button.x2,
        }

        self._kb_listener = KeyboardListener(
            on_press=self._on_global_key_press,
            on_release=self._on_global_key_release,
            win32_event_filter=self._kb_win32_event_filter,
        )
        self._kb_listener.daemon = True
        self._kb_listener.start()

        self._mouse_listener = MouseListener(
            on_click=self._on_global_mouse_click,
            win32_event_filter=self._mouse_win32_event_filter,
        )
        self._mouse_listener.daemon = True
        self._mouse_listener.start()

    def _kb_win32_event_filter(self, msg, data):
        if not getattr(self, "suppress_var", None) or not self.suppress_var.get():
            return True
        keybind = self._resolve_keybind()
        if keybind.startswith("mouse"):
            return True
            
        try:
            target_vk = KeyCode.from_char(keybind).vk
            if data.vkCode == target_vk:
                return False
        except Exception:
            try:
                # If from_char fails, sometimes it's because it's a special key
                pass
            except Exception:
                pass
        return True

    def _mouse_win32_event_filter(self, msg, data):
        if not getattr(self, "suppress_var", None) or not self.suppress_var.get():
            return True
        keybind = self._resolve_keybind()
        if not keybind.startswith("mouse"):
            return True
            
        # 0x0201: WM_LBUTTONDOWN, 0x0202: WM_LBUTTONUP
        # 0x0204: WM_RBUTTONDOWN, 0x0205: WM_RBUTTONUP
        # 0x0207: WM_MBUTTONDOWN, 0x0208: WM_MBUTTONUP
        # 0x020B: WM_XBUTTONDOWN, 0x020C: WM_XBUTTONUP
        
        if keybind == "mouse1" and msg in (0x0201, 0x0202): return False
        if keybind == "mouse2" and msg in (0x0204, 0x0205): return False
        if keybind == "mouse3" and msg in (0x0207, 0x0208): return False
        
        if keybind in ("mouse4", "mouse5") and msg in (0x020B, 0x020C, 0x020D): # double click too
            xbutton = (data.mouseData >> 16) & 0xFFFF
            if keybind == "mouse4" and xbutton == 1: return False
            if keybind == "mouse5" and xbutton == 2: return False
            
        return True

    def _resolve_keybind(self):
        return self.keybind_var.get().strip().lower()

    def _key_matches_keybind(self, key, keybind):
        if keybind.startswith("mouse"):
            return False
        
        try:
            if hasattr(key, 'char') and key.char:
                return key.char.lower() == keybind
            elif hasattr(key, 'name') and key.name:
                return key.name.lower() == keybind
        except AttributeError:
            pass
        return False

    def _on_global_key_press(self, key):
        if self.waiting_for_key:
            return
        keybind = self._resolve_keybind()
        if not self._key_matches_keybind(key, keybind):
            return

        mode = self.mode_var.get()
        if mode == "Toggle":
            if self.macro_active:
                self._stop_macro()
            else:
                self._start_macro()
        else:
            if not self.macro_active:
                self._start_macro()

    def _on_global_key_release(self, key):
        if self.waiting_for_key:
            return
        keybind = self._resolve_keybind()
        if not self._key_matches_keybind(key, keybind):
            return

        mode = self.mode_var.get()
        if mode == "Hold":
            self._stop_macro()

    def _on_global_mouse_click(self, x, y, button, pressed):
        if self.waiting_for_key:
            return
        keybind = self._resolve_keybind()
        if not keybind.startswith("mouse"):
            return

        expected_btn = self._mouse_button_map.get(keybind)
        if button != expected_btn:
            return

        mode = self.mode_var.get()
        if mode == "Toggle":
            if pressed:
                if self.macro_active:
                    self._stop_macro()
                else:
                    self._start_macro()
        else:
            if pressed:
                if not self.macro_active:
                    self._start_macro()
            else:
                self._stop_macro()

    def _start_macro(self):
        self.macro_active = True
        self.after(0, self._update_status_active)
        self.macro_thread = threading.Thread(target=self._macro_loop, daemon=True)
        self.macro_thread.start()

    def _stop_macro(self):
        self.macro_active = False
        self.after(0, self._update_status_inactive)

    def _update_status_active(self):
        self.status_dot.configure(text_color="#00ff88")
        self.status_label.configure(text="Active - ON - made by yamanist", text_color="#00ff88")

    def _update_status_inactive(self):
        self.status_dot.configure(text_color="#555577")
        self.status_label.configure(text="Ready - OFF - made by yamanist", text_color=TEXT_SECONDARY)

    def _get_delays(self):
        # calc delays
        is_manual = self.manual_var.get()
        macro_type = self.macro_type_var.get()

        if is_manual:
            if macro_type == "click_e":
                try:
                    delay_click_e = max(1, int(self.delay_click_e_var.get())) / 1000.0
                except (ValueError, TypeError):
                    delay_click_e = 0.05
                try:
                    delay_wait = max(1, int(self.delay_wait_var.get())) / 1000.0
                except (ValueError, TypeError):
                    delay_wait = 0.05
                return delay_click_e, delay_wait
            else:
                try:
                    delay_wait = max(1, int(self.delay_wait_var.get())) / 1000.0
                except (ValueError, TypeError):
                    delay_wait = 0.05
                return delay_wait, None
        else:
            cps = max(1, int(self.cps_var.get()))
            loop_delay = 1.0 / cps
            if macro_type == "click_e":
                half = loop_delay / 2.0
                return half, half
            elif macro_type in ("e_only", "custom_key", "click_only"):
                return loop_delay, None
            else:
                return loop_delay, None

    def _macro_loop(self):
        # run loop
        while self.macro_active:
            try:
                cycle_start = time.perf_counter()
                macro_type = self.macro_type_var.get()
                delay1, delay2 = self._get_delays()

                if self.rand_var.get():
                    rand_val = self.rand_percent_var.get() / 100.0
                    if delay1: delay1 *= random.uniform(1 - rand_val, 1 + rand_val)
                    if delay2: delay2 *= random.uniform(1 - rand_val, 1 + rand_val)

                if macro_type == "click_e":
                    self._mouse_ctrl.click(Button.left)
                    elapsed = time.perf_counter() - cycle_start
                    self._precise_sleep(max(0, delay1 - elapsed))
                    if not self.macro_active:
                        break
                    mid_point = time.perf_counter()
                    self._kb_ctrl.press('e')
                    self._kb_ctrl.release('e')
                    e_elapsed = time.perf_counter() - mid_point
                    self._precise_sleep(max(0, delay2 - e_elapsed))
                elif macro_type == "click_only":
                    self._mouse_ctrl.click(Button.left)
                    elapsed = time.perf_counter() - cycle_start
                    self._precise_sleep(max(0, delay1 - elapsed))
                elif macro_type == "e_only":
                    self._kb_ctrl.press('e')
                    self._kb_ctrl.release('e')
                    elapsed = time.perf_counter() - cycle_start
                    self._precise_sleep(max(0, delay1 - elapsed))
                elif macro_type == "custom_key":
                    ck = self.custom_key_var.get()
                    self._kb_ctrl.press(ck)
                    self._kb_ctrl.release(ck)
                    elapsed = time.perf_counter() - cycle_start
                    self._precise_sleep(max(0, delay1 - elapsed))
            except Exception:
                pass

    def _precise_sleep(self, duration):
        if duration <= 0:
            return
        end_time = time.perf_counter() + duration
        while time.perf_counter() < end_time:
            if not self.macro_active:
                return
            remaining = end_time - time.perf_counter()
            if remaining > 0.005:
                time.sleep(0.002)
            elif remaining > 0:
                time.sleep(remaining)
                return
            else:
                return

    def _create_card(self):
        card = ctk.CTkFrame(
            self.main_scroll,
            fg_color=BG_CARD,
            corner_radius=14,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card.pack(fill="x", padx=24, pady=(18, 0))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)
        return inner

    def _init_physics(self):
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.last_drag_time = 0.0
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.is_dragging = False
        self.physics_running = False
        self.drag_history = []

        self.FRICTION = 0.97
        self.BOUNCE_DAMPING = 0.7
        self.MIN_VELOCITY = 0.5
        self.PHYSICS_FPS = 16

        self.bind("<ButtonPress-1>", self._on_drag_start)
        self.bind("<B1-Motion>", self._on_drag_motion)
        self.bind("<ButtonRelease-1>", self._on_drag_end)

    def _on_drag_start(self, event):
        widget_path = str(event.widget).lower()
        interactives = ["button", "scrollbar", "slider", "entry", "checkbox", "switch"]
        if any(x in widget_path for x in interactives):
            self._ignore_drag = True
            return
            
        self._ignore_drag = False
        
        self.physics_running = False
        self.is_dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.last_mouse_x = event.x_root
        self.last_mouse_y = event.y_root
        self.last_drag_time = time.time()
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.drag_history = [(time.time(), event.x_root, event.y_root)]

    def _on_drag_motion(self, event):
        if getattr(self, '_ignore_drag', False) or not self.is_dragging:
            return

        now = time.time()
        
        self.drag_history.append((now, event.x_root, event.y_root))
        self.drag_history = [h for h in self.drag_history if now - h[0] <= 0.1]

        x = self.winfo_x() + (event.x - self.drag_start_x)
        y = self.winfo_y() + (event.y - self.drag_start_y)
        self.geometry(f"+{x}+{y}")

        self.last_mouse_x = event.x_root
        self.last_mouse_y = event.y_root
        self.last_drag_time = now

    def _on_drag_end(self, event):
        if getattr(self, '_ignore_drag', False):
            return
            
        self.is_dragging = False
        
        now = time.time()
        self.drag_history = [h for h in self.drag_history if now - h[0] <= 0.1]
        
        if len(self.drag_history) >= 2:
            total_wx = 0.0
            total_wy = 0.0
            total_w = 0.0
            
            for i in range(1, len(self.drag_history)):
                t1, x1, y1 = self.drag_history[i-1]
                t2, x2, y2 = self.drag_history[i]
                
                dt = t2 - t1
                if dt <= 0: continue
                
                mid_t = (t1 + t2) / 2.0
                age = max(0.0, min(0.1, now - mid_t))
                
                weight = 3.0 - 2.0 * (age / 0.1)
                
                vx = (x2 - x1) / dt
                vy = (y2 - y1) / dt
                
                w_dt = weight * dt
                
                total_wx += vx * w_dt
                total_wy += vy * w_dt
                total_w += w_dt
                
            if total_w > 0:
                self.vel_x = total_wx / total_w
                self.vel_y = total_wy / total_w
            else:
                self.vel_x = 0
                self.vel_y = 0
        else:
            self.vel_x = 0
            self.vel_y = 0

        speed = (self.vel_x ** 2 + self.vel_y ** 2) ** 0.5
        if speed > 50:
            frame_dt = self.PHYSICS_FPS / 1000.0
            self.vel_x *= frame_dt * 1
            self.vel_y *= frame_dt * 1
            self.physics_running = True
            self._physics_loop()

    def _physics_loop(self):
        if not self.physics_running:
            return

        win_x = self.winfo_x()
        win_y = self.winfo_y()
        win_w = self.winfo_width()
        win_h = self.winfo_height()

        scr_w = self.winfo_screenwidth()
        scr_h = self.winfo_screenheight()

        new_x = win_x + self.vel_x
        new_y = win_y + self.vel_y

        if new_x < 0:
            new_x = 0
            if self.vel_x < 0: 
                self.vel_x = abs(self.vel_x) * self.BOUNCE_DAMPING
        elif new_x + win_w > scr_w:
            new_x = scr_w - win_w
            if self.vel_x > 0: 
                self.vel_x = -abs(self.vel_x) * self.BOUNCE_DAMPING
            
        if new_y < 0:
            new_y = 0
            if self.vel_y < 0: 
                self.vel_y = abs(self.vel_y) * self.BOUNCE_DAMPING
        elif new_y + win_h > scr_h:
            new_y = scr_h - win_h
            if self.vel_y > 0: 
                self.vel_y = -abs(self.vel_y) * self.BOUNCE_DAMPING

        self.vel_x *= self.FRICTION
        self.vel_y *= self.FRICTION

        self.geometry(f"+{int(new_x)}+{int(new_y)}")

        speed = (self.vel_x ** 2 + self.vel_y ** 2) ** 0.5
        if speed < self.MIN_VELOCITY:
            self.physics_running = False
            return

        self.after(self.PHYSICS_FPS, self._physics_loop)

if __name__ == "__main__":
    app = MacroApp()
    app.mainloop()


#made for a friend of mine

#made with ❤️ by yamanist