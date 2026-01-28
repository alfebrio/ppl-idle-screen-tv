"""
IDLE SCREEN TV CRT RETRO
Author: Alfebrio Setia Nugraha
Features:
  - Retro CRT TV Idle Screen GUI theme with auto-dark mode at night (6:00 PM - 6:00 AM)
  - Object color changes every each collision, silent mode (no reflection sound) at bedtime (10:00 PM - 6:00 AM)
  - Speed Boost System & Trail System (Tail) dynamic response according to speed
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import time, math, random, json, os, sys
from datetime import datetime

PALET = [
    "#000000", # 0: pure black
    "#E40027", # 1: red
    "#F8D034", # 2: yellow
    "#264BCC", # 3: blue
    "#2AA146", # 4: green
    "#B3B4B6", # 5: light gray
    "#2C2C2E", # 6: dark gray
]

DEFAULT_CANVAS_W = 800
DEFAULT_CANVAS_H = 600
DEFAULT_BALL_SIZE = 36
DEFAULT_BASE_SPEED = 5.0
BORDER_LAYER = 32
INNER_THIN = BORDER_LAYER // 4
SCANLINE_STEP = 3
TRAIL_MAX = 30
FRAME_SAVE_INTERVAL = 30
SPEED_BOOST_FRAMES = 12
SPEED_BOOST_MULT = 1.45
SILENT_START = 22
SILENT_END = 6
SILENT_SPEED_DIV = 2.0
FRAMES_DIR = 'frames_meta'
CONFIG_DEFAULT_PATH = 'zigzag_config.json'

os.makedirs(FRAMES_DIR, exist_ok=True)

def quantized_color_random(solid_bright=False):
    steps = [i*32 for i in range(8)]
    def q():
        v = random.choice(steps)
        return 255 if (v == 224 and random.random() < 0.25) else v
    r = q(); g = q(); b = q()
    if solid_bright:
        r = min(255, r + 40)
        g = min(255, g + 40)
        b = min(255, b + 40)
    return f"#{r:02x}{g:02x}{b:02x}"

def brighten_color(hex_color, factor=1.4):
    c = hex_color.lstrip('#')
    r = int(c[0:2], 16); g = int(c[2:4], 16); b = int(c[4:6], 16)
    r = min(255, int(r * factor)); g = min(255, int(g * factor)); b = min(255, int(b * factor))
    return f"#{r:02x}{g:02x}{b:02x}"

def dim_color(hex_color, factor=0.6):
    c = hex_color.lstrip('#')
    r = int(c[0:2], 16); g = int(c[2:4], 16); b = int(c[4:6], 16)
    r = max(0, int(r * factor)); g = max(0, int(g * factor)); b = max(0, int(b * factor))
    return f"#{r:02x}{g:02x}{b:02x}"

class ZigZagApp:
    def __init__(self, master):
        self.master = master
        master.title('ZigZag Retro — Full')
        master.configure(bg=PALET[0])

        try:
            master.minsize(640, 480)
        except:
            pass

        self.is_running = True
        self.is_fullscreen = False
        self.show_trail = True
        self.show_scanlines = True
        self.base_speed = DEFAULT_BASE_SPEED
        self.ball_size = DEFAULT_BALL_SIZE
        self.max_trail_len = TRAIL_MAX

        self.last_time = time.time()
        self.canvas = tk.Canvas(master, bg=PALET[0], highlightthickness=0)
        self.content_bbox = (0,0,DEFAULT_CANVAS_W,DEFAULT_CANVAS_H)
        self._init_ball()
        self.trail = []
        self.scan_ids = []
        self.collision_text_id = None
        self.silent_text_id = None
        self.frame_counter = 0
        self.speed_boost_timer = 0
        self.collision_phrases = ['BOOM!', 'CLANK!', 'TOK!', 'BAM!', 'DING!']

        self._build_control_bar()
        self.canvas.pack(fill='both', expand=True)

        master.bind('<Key>', self._on_key)
        self._root_resize_scheduled = False
        master.bind('<Configure>', self._on_root_configure)
        self.canvas.bind('<Configure>', self._on_canvas_resize)

        self.master.update_idletasks()
        self._on_canvas_resize(None)
        self._animate_loop()

    def _on_root_configure(self, event):
        if self._root_resize_scheduled:
            return
        self._root_resize_scheduled = True
        self.master.after(80, self._enforce_minimum_size)

    def _enforce_minimum_size(self):
        self._root_resize_scheduled = False
        try:
            w = self.master.winfo_width()
            h = self.master.winfo_height()
            need = False
            new_w, new_h = w, h
            if w < 640:
                new_w = 640; need = True
            if h < 480:
                new_h = 480; need = True
            if new_w / new_h < (4.0 / 3.0):
                new_w = int(new_h * 4.0 / 3.0)
                need = True
            if need:
                try:
                    x = self.master.winfo_x()
                    y = self.master.winfo_y()
                    geom = f"{new_w}x{new_h}+{x}+{y}"
                    self.master.geometry(geom)
                except:
                    try:
                        self.master.geometry(f"{new_w}x{new_h}")
                    except:
                        pass
        except:
            pass

    def _init_ball(self):
        self.ball_color = quantized_color_random(solid_bright=True)
        self.ball_x = DEFAULT_CANVAS_W * 0.25
        self.ball_y = DEFAULT_CANVAS_H * 0.4
        angle = random.uniform(-0.9, 0.9)
        dx = math.cos(angle); dy = math.sin(angle)
        if abs(dx) < 0.2: dx = 0.2 if dx >=0 else -0.2
        if abs(dy) < 0.2: dy = 0.2 if dy >=0 else -0.2
        mag = math.hypot(dx, dy) or 1.0
        self.dir_x = dx / mag
        self.dir_y = dy / mag
        self.ball_item_id = None

    def _build_control_bar(self):
        frame = tk.Frame(self.master, bg=PALET[5], bd=0, relief='flat')
        frame.pack(side='bottom', fill='x')
        self.control_frame = frame

        left_frame = tk.Frame(frame, bg=PALET[5])
        left_frame.pack(side='left', padx=6, pady=6)
        self.btn_pause = ttk.Button(left_frame, text='Pause', command=self.toggle_pause, width=10)
        self.btn_full = ttk.Button(left_frame, text='Fullscreen', command=self.toggle_fullscreen, width=12)
        self.btn_save = ttk.Button(left_frame, text='Save Config', command=self.save_config, width=12)
        self.btn_load = ttk.Button(left_frame, text='Load Config', command=self.load_config, width=12)
        self.btn_pause.pack(side='left', padx=6); self.btn_full.pack(side='left', padx=6)
        self.btn_save.pack(side='left', padx=6); self.btn_load.pack(side='left', padx=6)

        middle_frame = tk.Frame(frame, bg=PALET[5])
        middle_frame.pack(side='left', padx=12)
        ttk.Label(middle_frame, text='Speed', background=PALET[5]).pack(side='left', padx=(0,4))
        self.speed_var = tk.DoubleVar(value=self.base_speed)
        self.speed_slider = ttk.Scale(middle_frame, from_=1.0, to=24.0, variable=self.speed_var, command=self._on_speed_change, length=180)
        self.speed_slider.pack(side='left', padx=6, pady=6)

        self.trail_var = tk.BooleanVar(value=self.show_trail)
        self.scan_var = tk.BooleanVar(value=self.show_scanlines)
        self.trail_check = ttk.Checkbutton(middle_frame, text='Trail', variable=self.trail_var, command=self._on_toggle_trail)
        self.scan_check = ttk.Checkbutton(middle_frame, text='Scanlines', variable=self.scan_var, command=self._on_toggle_scan)
        self.trail_check.pack(side='left', padx=8); self.scan_check.pack(side='left', padx=8)

        right_frame = tk.Frame(frame, bg=PALET[5])
        right_frame.pack(side='right', padx=6)
        self.status_label = tk.Label(right_frame, text='Memulai...', bg=PALET[5], anchor='w', font=('Consolas',9))
        self.status_label.pack(side='right')

    def _on_toggle_trail(self):
        self.show_trail = bool(self.trail_var.get())
        if not self.show_trail:
            self.trail = []
            self.canvas.delete('trail')

    def _on_toggle_scan(self):
        self.show_scanlines = bool(self.scan_var.get())
        if self.show_scanlines:
            self._create_scanlines()
        else:
            for sid in getattr(self, 'scan_ids', []):
                try: self.canvas.delete(sid)
                except: pass
            self.scan_ids = []

    def _on_speed_change(self, v):
        try:
            self.base_speed = float(self.speed_var.get())
        except:
            pass

    def _on_key(self, event):
        k = event.keysym.lower()
        if k == 'space':
            self.toggle_pause()
        elif k == 'f11':
            self.toggle_fullscreen()
        elif k in ('escape', 'q'):
            self.quit_app()
        elif k == 't':
            self.trail_var.set(not self.trail_var.get()); self._on_toggle_trail()
        elif k == 's':
            self.scan_var.set(not self.scan_var.get()); self._on_toggle_scan()

    def save_config(self):
        cfg = {
            'base_speed': self.base_speed,
            'ball_size': self.ball_size,
            'show_trail': self.show_trail,
            'show_scanlines': self.show_scanlines,
            'canvas_w': self.content_bbox[2] - self.content_bbox[0],
            'canvas_h': self.content_bbox[3] - self.content_bbox[1],
        }
        fname = filedialog.asksaveasfilename(title='Simpan Konfigurasi', defaultextension='.json', filetypes=[('JSON files','*.json')])
        if not fname:
            return
        try:
            with open(fname, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2)
            messagebox.showinfo('Simpan Konfigurasi', f'Konfigurasi disimpan: {fname}')
        except Exception as e:
            messagebox.showerror('Error', f'Gagal menyimpan konfigurasi: {e}')

    def load_config(self):
        fname = filedialog.askopenfilename(title='Muat Konfigurasi', filetypes=[('JSON files','*.json')])
        if not fname:
            return
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            self.base_speed = float(cfg.get('base_speed', self.base_speed))
            self.ball_size = int(cfg.get('ball_size', self.ball_size))
            self.show_trail = bool(cfg.get('show_trail', self.show_trail))
            self.show_scanlines = bool(cfg.get('show_scanlines', self.show_scanlines))
            w = int(cfg.get('canvas_w', self.content_bbox[2]-self.content_bbox[0]))
            h = int(cfg.get('canvas_h', self.content_bbox[3]-self.content_bbox[1]))
            self.speed_var.set(self.base_speed)
            self.trail_var.set(self.show_trail)
            self.scan_var.set(self.show_scanlines)
            self._place_canvas_with_ratio(w, h)
            messagebox.showinfo('Muat Konfigurasi', 'Konfigurasi dimuat.')
        except Exception as e:
            messagebox.showerror('Error', f'Gagal memuat konfigurasi: {e}')

    def toggle_pause(self):
        self.is_running = not self.is_running
        self.btn_pause.config(text='Resume' if not self.is_running else 'Pause')

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        try:
            self.master.attributes('-fullscreen', self.is_fullscreen)
        except Exception:
            pass
        self.btn_full.config(text='Exit Fullscreen' if self.is_fullscreen else 'Fullscreen')

    def quit_app(self):
        self.master.quit()

    def _on_canvas_resize(self, event):
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())

        target_w = min(w, int(h * 4.0 / 3.0))
        target_h = int(target_w * 3.0 / 4.0)
        if target_w < 4:
            target_w = 4
            target_h = 3
        x0 = (w - target_w)//2
        y0 = (h - target_h)//2
        x1 = x0 + target_w
        y1 = y0 + target_h
        self.content_bbox = (x0, y0, x1, y1)

        self.canvas.delete('border')
        self.canvas.delete('content')
        for sid in getattr(self, 'scan_ids', []):
            try: self.canvas.delete(sid)
            except: pass
        self.scan_ids = []

        self.canvas.create_rectangle(0, 0, w, h, fill=PALET[0], outline='', tags='border')

        colors = [PALET[1], PALET[2], PALET[3], PALET[4]]
        multipliers = [4, 3, 2, 1]
        for mul, col in zip(multipliers, colors):
            bx0 = x0 - BORDER_LAYER * mul
            by0 = y0 - BORDER_LAYER * mul
            bx1 = x1 + BORDER_LAYER * mul
            by1 = y1 + BORDER_LAYER * mul
            bx0 = max(0, bx0); by0 = max(0, by0)
            bx1 = min(w, bx1); by1 = min(h, by1)
            self.canvas.create_rectangle(bx0, by0, bx1, by1, fill=col, outline='', tags='border')

        inner_bx0 = x0 - INNER_THIN
        inner_by0 = y0 - INNER_THIN
        inner_bx1 = x1 + INNER_THIN
        inner_by1 = y1 + INNER_THIN
        inner_bx0 = max(0, inner_bx0); inner_by0 = max(0, inner_by0)
        inner_bx1 = min(w, inner_bx1); inner_by1 = min(h, inner_by1)
        self.canvas.create_rectangle(inner_bx0, inner_by0, inner_bx1, inner_by1, fill=PALET[5], outline='', tags='border')

        self.canvas.create_rectangle(x0, y0, x1, y1, fill=PALET[6], outline='', tags='content')

        if self.show_scanlines:
            self._create_scanlines()
        else:
            for sid in getattr(self, 'scan_ids', []):
                try:
                    self.canvas.delete(sid)
                except:
                    pass
            self.scan_ids = []

        if self.silent_text_id is None:
            self.silent_text_id = self.canvas.create_text(x0+8, y0+8, anchor='nw', text='', fill='#ffffff', font=('Consolas',10,'bold'), tags='overlay')
        else:
            self.canvas.coords(self.silent_text_id, x0+8, y0+8)

        if self.collision_text_id is None:
            self.collision_text_id = self.canvas.create_text(x0+10, y0+10, text='', state='hidden', font=('Consolas',14,'bold'), tags='overlay')
        else:
            self._position_collision_text()

        if self.ball_item_id is None:
            self.ball_item_id = self.canvas.create_oval(0,0,0,0, fill=self.ball_color, outline='', tags='ball')

        cw = max(1, x1-x0); ch = max(1, y1-y0)
        if self.ball_x > cw - self.ball_size:
            self.ball_x = max(0, cw - self.ball_size)
        if self.ball_y > ch - self.ball_size:
            self.ball_y = max(0, ch - self.ball_size)
        self._update_ball_canvas_coords()

    def _place_canvas_with_ratio(self, w, h):
        self.master.update_idletasks()
        return

    def _create_scanlines(self):
        for sid in getattr(self, 'scan_ids', []):
            try: self.canvas.delete(sid)
            except: pass
        self.scan_ids = []
        x0, y0, x1, y1 = self.content_bbox
        step = max(1, SCANLINE_STEP)
        for yy in range(y0, y1, step):
            sid = self.canvas.create_line(x0, yy, x1, yy, fill='#0b0b0b', width=1, tags='scan_line')
            self.scan_ids.append(sid)

    def _position_collision_text(self):
        if self.collision_text_id is None:
            return
        x0, y0, x1, y1 = self.content_bbox
        gx, gy = self.local_to_global(self.ball_x, self.ball_y)
        if gy - y0 > 28:
            tx = gx + self.ball_size/2
            ty = gy - 18
        else:
            tx = gx + self.ball_size/2
            ty = gy + self.ball_size + 18
        try:
            self.canvas.coords(self.collision_text_id, tx, ty)
        except:
            pass

    def _show_collision_near(self, text):
        self._position_collision_text()
        try:
            self.canvas.itemconfig(self.collision_text_id, text=text, fill=PALET[5], state='normal')
        except:
            pass
        steps = 8
        duration = 450
        def fade(i=steps):
            if i <= 0:
                try: self.canvas.itemconfig(self.collision_text_id, state='hidden')
                except: pass
                return
            val = int(220 * (i/steps))
            col = f"#{val:02x}{int(val*0.3):02x}{int(val*0.3):02x}"
            try:
                self.canvas.itemconfig(self.collision_text_id, fill=col)
            except: pass
            self.master.after(int(duration/steps), lambda: fade(i-1))
        fade()

    def local_to_global(self, lx, ly):
        x0, y0, x1, y1 = self.content_bbox
        return x0 + lx, y0 + ly

    def _update_ball_canvas_coords(self):
        gx, gy = self.local_to_global(self.ball_x, self.ball_y)
        try:
            self.canvas.coords(self.ball_item_id, gx, gy, gx + self.ball_size, gy + self.ball_size)
            self.canvas.itemconfig(self.ball_item_id, fill=self.ball_color)
        except:
            pass

    def _backup_frame(self):
        try:
            idx = self.frame_counter // FRAME_SAVE_INTERVAL
            fname = os.path.join(FRAMES_DIR, f"frame_{idx:04d}.txt")
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(f"[Frame {self.frame_counter} | {datetime.now()}]\n")
                f.write(f"Ball Pos: ({self.ball_x:.2f}, {self.ball_y:.2f})\n")
                f.write(f"Dir: ({self.dir_x:.3f}, {self.dir_y:.3f})\n")
                f.write(f"Color: {self.ball_color}\n")
        except Exception as e:
            print('Backup frame error:', e)

    def _animate_loop(self):
        if not getattr(self.master, 'winfo_exists', lambda: True)():
            return

        now = time.time()
        dt = now - getattr(self, 'last_time', now)
        if dt > 0.5: dt = 1.0/60.0
        self.last_time = now

        if not self.is_running:
            try:
                self.status_label.config(text=f"Paused | Frame:{self.frame_counter}")
            except:
                pass
            self.master.after(100, self._animate_loop)
            return

        self.frame_counter += 1

        eff_speed = self.base_speed
        if self.speed_boost_timer > 0:
            eff_speed *= SPEED_BOOST_MULT
            self.speed_boost_timer -= 1

        hr = datetime.now().hour
        if (hr >= SILENT_START) or (hr < SILENT_END):
            eff_speed /= SILENT_SPEED_DIV
            try: self.canvas.itemconfig(self.silent_text_id, text='[Silent Mode]')
            except: pass
        else:
            try: self.canvas.itemconfig(self.silent_text_id, text='')
            except: pass

        move = eff_speed * dt * 60.0

        prev_x, prev_y = self.ball_x, self.ball_y
        nx = prev_x + move * self.dir_x
        ny = prev_y + move * self.dir_y

        x0, y0, x1, y1 = self.content_bbox
        cw = max(1, x1 - x0)
        ch = max(1, y1 - y0)

        collided = False

        if nx <= 0:
            nx = 0; self.dir_x = abs(self.dir_x) or 1.0; collided = True
        elif nx + self.ball_size >= cw:
            nx = cw - self.ball_size; self.dir_x = -abs(self.dir_x) or -1.0; collided = True

        if ny <= 0:
            ny = 0; self.dir_y = abs(self.dir_y) or 1.0; collided = True
        elif ny + self.ball_size >= ch:
            ny = ch - self.ball_size; self.dir_y = -abs(self.dir_y) or -1.0; collided = True

        self.ball_x, self.ball_y = nx, ny

        if collided:
            phrase = random.choice(self.collision_phrases)
            self._show_collision_near(phrase)
            self.speed_boost_timer = SPEED_BOOST_FRAMES
            self.ball_color = quantized_color_random(solid_bright=True)
            jitter = random.uniform(-0.35, 0.35)
            nxv = self.dir_x + jitter * 0.25
            nyv = self.dir_y - jitter * 0.25
            mag = math.hypot(nxv, nyv) or 1.0
            self.dir_x = nxv / mag
            self.dir_y = nyv / mag

        self._update_ball_canvas_coords()

        dx = self.ball_x - prev_x; dy = self.ball_y - prev_y
        dist = math.hypot(dx, dy)
        if dist > 0 and self.show_trail:
            interp_count = min(12, max(1, int(dist // 2)))
            head_col = brighten_color(self.ball_color, factor=1.5)
            mid_col = brighten_color(self.ball_color, factor=1.35)
            for i in range(1, interp_count + 1):
                t = i / (interp_count + 1)
                ix = prev_x + dx * t; iy = prev_y + dy * t
                col = mid_col if i < interp_count else head_col
                self.trail.insert(0, (ix, iy, col))
            self.trail.insert(0, (self.ball_x, self.ball_y, head_col))

        if len(self.trail) > self.max_trail_len:
            self.trail = self.trail[:self.max_trail_len]

        self.canvas.delete('trail')
        total = len(self.trail) if self.trail else 1
        for idx, (tx, ty, tcol) in enumerate(self.trail):
            age = idx / total
            sz = self.ball_size * (0.85 - age * 0.6)
            color = dim_color(tcol, factor=0.45 + (1.0 - age) * 0.55)
            gx, gy = self.local_to_global(tx, ty)
            try:
                self.canvas.create_oval(gx + self.ball_size/2 - sz/2,
                                        gy + self.ball_size/2 - sz/2,
                                        gx + self.ball_size/2 + sz/2,
                                        gy + self.ball_size/2 + sz/2,
                                        fill=color, outline='', tags='trail')
            except:
                pass

        if self.frame_counter % FRAME_SAVE_INTERVAL == 0:
            self._backup_frame()

        status = f"Frame:{self.frame_counter} Pos:({int(self.ball_x)},{int(self.ball_y)}) Dir:({self.dir_x:.2f},{self.dir_y:.2f}) Speed:{eff_speed:.1f}"
        if (hr >= SILENT_START) or (hr < SILENT_END):
            status += ' | SILENT'
        if self.speed_boost_timer > 0:
            status += f' | BOOST:{self.speed_boost_timer}'
        try:
            self.status_label.config(text=status)
        except:
            pass

        self.master.after(16, self._animate_loop)

def main():
    root = tk.Tk()
    app = ZigZagApp(root)
    try:
        root.minsize(640, 480)
    except:
        pass
    root.mainloop()

if __name__ == '__main__':
    main()
