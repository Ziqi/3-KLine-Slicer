import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, END, LEFT, BOTH, TOP, BOTTOM, RIGHT, X, Y
import os
import pandas as pd
import numpy as np
import pickle
import threading
import time
import datetime
from pathlib import Path
from sklearn.preprocessing import StandardScaler
import ttkbootstrap as tb

# =================================================================
# [ KLine-Slicer: DATA PRODUCTION TERMINAL ]
# Designed for Kronos MoE (X-Matrix) Pipeline
# =================================================================

class SlicerMatrixGUI(tb.Window):
    def __init__(self):
        super().__init__(themename="cyborg")
        self.title("全市场 K线数据切片生产终端 (5min ▷ Transformer)")
        self.geometry("1100x860")
        self.minsize(1050, 800)
        
        # --- UI Colors & Styles (Flat Dark Gold) ---
        self.c_bg = "#080808"        # 终极深邃黑
        self.c_panel = "#101010"     # 面板底色更沉
        self.c_gold = "#F0B90B"      # 极客明黄亮金
        self.c_gold_dim = "#715A2B"  # 昏暗辅助金
        self.c_fg = "#E1C699"        # 【全局非白】黑金体系替代白色
        self.c_green = "#00D47C"     # 荧光极客绿
        self.c_red = "#FF3B30"       # 警报红
        
        self.font_title = ("Menlo", 36, "bold")
        self.font_base = ("Menlo", 14)
        self.font_base_lg = ("Menlo", 16)
        self.font_log = ("Menlo", 13)
        
        self._setup_styles()
        
        # --- Paths & State ---
        self.root_dir = Path(__file__).resolve().parent
        self.src_dir = self.root_dir.parent / "2-KLine-Resample" / "gui_out_5m"
        self.expert_dir = Path("/Users/xiaoziqi/X-Matrix/data/processed")
        self.out_dir = self.root_dir / "gui_out_slices"
        
        if not self.out_dir.exists(): self.out_dir.mkdir(parents=True)
        
        self.src_var = tk.StringVar(value=str(self.src_dir))
        self.expert_var = tk.StringVar(value="expert_02_ai") # Default to AI
        self.lookback_var = tk.IntVar(value=90)
        self.pred_var = tk.IntVar(value=10)
        
        self.expert_options = {
            "expert_01_chem": "新材料与化工",
            "expert_02_ai": "AI与半导体",
            "expert_03_robotics": "机器人与智造",
            "expert_04_aerospace": "航天与军工"
        }
        
        self.stop_requested = False
        self.process_thread = None
        self._file_mapping = {}
        
        self._build_ui()
        self.after(500, self.poll_source_dir)

    def _setup_styles(self):
        style = self.style
        style.configure(".", font=self.font_base, background=self.c_bg, foreground=self.c_fg)
        
        style.configure("TLabelframe", background=self.c_bg, bordercolor=self.c_gold_dim, borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", font=("Menlo", 15, "bold"), foreground=self.c_gold, background=self.c_bg)
        
        style.configure("FlatGold.TButton", font=self.font_base_lg, background=self.c_bg, foreground=self.c_gold, bordercolor=self.c_gold, borderwidth=1)
        style.map("FlatGold.TButton", background=[("active", "#1A140B")], foreground=[("active", "#FFD700")])
        style.configure("FlatRed.TButton", font=self.font_base_lg, background=self.c_bg, foreground=self.c_red, bordercolor=self.c_red, borderwidth=1)
        style.map("FlatRed.TButton", background=[("active", "#1A0505")])
        
        # Custom Scrollbar
        style.layout('Hidden.Vertical.TScrollbar', [('Vertical.Scrollbar.trough', {'children': [('Vertical.Scrollbar.thumb', {'expand': '1', 'sticky': 'nswe'})], 'sticky': 'ns'})])
        style.configure("Hidden.Vertical.TScrollbar", background=self.c_gold_dim, troughcolor=self.c_bg, bordercolor=self.c_bg, relief="flat")
        style.map("Hidden.Vertical.TScrollbar", background=[("active", self.c_gold)])
        
        style.configure("Treeview", background=self.c_panel, foreground=self.c_fg, fieldbackground=self.c_panel, borderwidth=0, font=self.font_base, rowheight=32)
        style.map("Treeview", background=[("selected", "#2A2111")], foreground=[("selected", self.c_gold)])
        style.configure("Treeview.Heading", font=("Menlo", 13, "bold"), background=self.c_bg, foreground=self.c_gold, borderwidth=1)
        
        style.configure("Horizontal.TProgressbar", thickness=10, background=self.c_gold, troughcolor="#222")

    def _build_ui(self):
        self.configure(bg=self.c_bg)
        
        # Force macOS to bring this window to the very front
        self.lift()
        self.attributes('-topmost', True)
        self.after(1000, lambda: self.attributes('-topmost', False))
        os.system('''osascript -e 'tell application "System Events" to set frontmost of the first process whose unix id is %d to true' ''' % os.getpid())

        main_container = tk.Frame(self, bg=self.c_bg, padx=20, pady=20)
        main_container.pack(fill=BOTH, expand=True)
        
        # --- HEADER ---
        header_frame = tk.Frame(main_container, bg=self.c_bg, pady=15)
        header_frame.pack(fill=X)
        tk.Label(header_frame, text="X-MATRIX V3.0 SLICER · 数据切片矩阵", font=self.font_title, fg=self.c_gold, bg=self.c_bg).pack(side=LEFT)
        self.status_sign = tk.Label(header_frame, text="系统就绪", font=("Menlo", 16, "bold"), fg=self.c_gold_dim, bg=self.c_bg)
        self.status_sign.pack(side=RIGHT, anchor=tk.S)

        # --- BODY ---
        body_frame = tk.Frame(main_container, bg=self.c_bg)
        body_frame.pack(fill=BOTH, expand=True, pady=(10, 0))
        
        # --- LEFT PANEL: CONFIG ---
        left_panel = tk.Frame(body_frame, bg=self.c_bg, width=380)
        left_panel.pack(side=LEFT, fill=tk.Y, padx=(0, 20))
        left_panel.pack_propagate(False)
        
        # [ MOUNTS ]
        mount_lf = DashFrame(left_panel, title=" 存储挂载点 MOUNTS ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        mount_lf.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(mount_lf.content, text="5分钟K线来源:", bg=self.c_bg, fg=self.c_fg, font=self.font_base).pack(anchor=tk.W)
        src_fr = tk.Frame(mount_lf.content, bg=self.c_bg)
        src_fr.pack(fill=tk.X, pady=(2, 10))
        tk.Entry(src_fr, textvariable=self.src_var, font=self.font_log, bg=self.c_panel, fg=self.c_gold, relief="flat", highlightthickness=1, highlightbackground=self.c_gold_dim).pack(side=LEFT, fill=tk.X, expand=True)
        ttk.Button(src_fr, text="打开", style="FlatGold.TButton", command=self.on_browse_src).pack(side=RIGHT, padx=(5,0))
        
        # [ PARAMETERS ]
        param_lf = DashFrame(left_panel, title=" 专家参数 CONFIG ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        param_lf.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(param_lf.content, text="目标脑核 (Target Expert):", bg=self.c_bg, fg=self.c_fg, font=self.font_base).pack(anchor=tk.W)
        self.expert_combo = ttk.Combobox(param_lf.content, textvariable=self.expert_var, values=list(self.expert_options.keys()), font=self.font_base)
        self.expert_combo.pack(fill=tk.X, pady=(2, 10))
        
        # Window Params
        win_frame = tk.Frame(param_lf.content, bg=self.c_bg)
        win_frame.pack(fill=tk.X)
        tk.Label(win_frame, text="Lookback:", bg=self.c_bg, fg=self.c_gold, font=self.font_base).pack(side=LEFT)
        ttk.Entry(win_frame, textvariable=self.lookback_var, width=5, font=self.font_base).pack(side=LEFT, padx=5)
        tk.Label(win_frame, text="Predict:", bg=self.c_bg, fg=self.c_gold, font=self.font_base).pack(side=LEFT)
        ttk.Entry(win_frame, textvariable=self.pred_var, width=5, font=self.font_base).pack(side=LEFT, padx=5)
        
        # [ CONTROL ]
        ctrl_lf = DashFrame(left_panel, title=" 切片点火 CORE ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        ctrl_lf.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(ctrl_lf.content, text="开始切片生产", style="FlatGold.TButton", command=self.on_start_click)
        self.start_btn.pack(fill=tk.X, pady=(15, 10), ipady=5)
        
        ttk.Button(ctrl_lf.content, text="熔断中止 (停止生产)", style="FlatRed.TButton", command=self.on_stop).pack(fill=tk.X, pady=(0, 5), ipady=5)
        
        # --- RIGHT PANEL: DISPLAY ---
        right_panel = tk.Frame(body_frame, bg=self.c_bg)
        right_panel.pack(side=LEFT, fill=BOTH, expand=True)
        
        # [ SOURCE LIST ]
        list_lf = DashFrame(right_panel, title=" 5分钟K线资产库 (支持勾选板块批量切片) ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        list_lf.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        columns = ("name", "size", "health")
        tree_container = tk.Frame(list_lf.content, bg=self.c_bg)
        tree_container.pack(fill=BOTH, expand=True)
        
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings")
        self.tree.heading("name", text="文件名称")
        self.tree.heading("size", text="物理大小")
        self.tree.heading("health", text="数据体检")
        self.tree.column("name", width=220)
        self.tree.column("size", width=100, anchor=tk.E)
        self.tree.column("health", width=120, anchor=tk.CENTER)
        
        tree_yscroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview, style="Hidden.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=tree_yscroll.set)
        tree_yscroll.pack(side=RIGHT, fill=tk.Y)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        
        # [ LOGS ]
        log_lf = DashFrame(right_panel, title=" 运行日志 MATRIX ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"), height=220)
        log_lf.pack_propagate(False)
        log_lf.pack(fill=tk.X)
        
        txt_frame = tk.Frame(log_lf.content, bg=self.c_panel)
        txt_frame.pack(fill=BOTH, expand=True, padx=5)
        
        self.log_widget = tk.Text(txt_frame, font=self.font_log, bg=self.c_panel, fg=self.c_fg, insertbackground=self.c_fg, wrap=tk.WORD, borderwidth=0, highlightthickness=0, spacing1=4, spacing3=4)
        txt_scroll = ttk.Scrollbar(txt_frame, orient=tk.VERTICAL, command=self.log_widget.yview, style="Hidden.Vertical.TScrollbar")
        self.log_widget.configure(yscrollcommand=txt_scroll.set)
        
        txt_scroll.pack(side=RIGHT, fill=tk.Y)
        self.log_widget.pack(side=LEFT, fill=BOTH, expand=True)
        
        self.log_widget.tag_configure("info", foreground=self.c_fg)
        self.log_widget.tag_configure("sys", foreground=self.c_gold, font=("Menlo", 13, "bold"))
        self.log_widget.tag_configure("succ", foreground=self.c_green, font=("Menlo", 13, "bold"))
        self.log_widget.tag_configure("err", foreground=self.c_red, font=("Menlo", 13, "bold"))
        self.log_widget.configure(state='disabled')

        # [ FOOTER ]
        self.status_bar = tk.Label(main_container, text="待命：准备生产数据", bg=self.c_bg, fg=self.c_gold_dim, font=("Menlo", 10))
        self.status_bar.pack(side=BOTTOM, anchor=tk.W, pady=(10, 0))

    def log_msg(self, msg, level="info"):
        self.log_widget.configure(state='normal')
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_widget.insert(tk.END, f"[{ts}] {msg}\n", level)
        self.log_widget.see(tk.END)
        self.log_widget.configure(state='disabled')

    def on_browse_src(self):
        d = filedialog.askdirectory(initialdir=self.src_var.get())
        if d:
            self.src_var.set(d)
            self.poll_source_dir()

    def poll_source_dir(self):
        p = Path(self.src_var.get())
        if not p.exists() or not p.is_dir(): return
        
        for i in self.tree.get_children(): self.tree.delete(i)
        self._file_mapping = {}
        
        files = sorted(p.glob("*_5m_*.csv"), key=os.path.getmtime, reverse=True)
        for f in files:
            size_kb = f.stat().st_size / 1024.0
            name = f.name
            
            iid = self.tree.insert("", tk.END, values=(name, f"{size_kb:.1f} KB", "待体检"))
            self._file_mapping[iid] = f.name
        
        self.tree.selection_set(self.tree.get_children()) if self.tree.get_children() else None

    def on_stop(self):
        if self.process_thread and self.process_thread.is_alive():
            self.stop_requested = True
            self.log_msg("[!] 收到熔断指令，正在中止生产线...", "err")

    def on_start_click(self):
        if self.process_thread and self.process_thread.is_alive():
            return
        
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先在右侧列表中选择需要切片的标的。")
            return
        
        self.stop_requested = False
        self.start_btn.config(state='disabled')
        self.stats_sign_update("生产中...", self.c_gold)
        self.process_thread = threading.Thread(target=self._run_slicing_batch, args=(selection,), daemon=True)
        self.process_thread.start()

    def stats_sign_update(self, text, color):
        self.status_sign.config(text=text, fg=color)

    def _run_slicing_batch(self, selection):
        self.log_msg(f"[*] 启动批量切片生产线，计划处理 {len(selection)} 个物理核心...", "sys")
        self.log_msg(f"[>] 目标架构: {self.expert_options.get(self.expert_var.get())}", "succ")
        
        # 0. Load Scaler
        expert_id = self.expert_var.get()
        short_name = expert_id.split('_')[-1]
        scaler_name = f"scaler_{short_name}.pkl"
        scaler_path = self.expert_dir / scaler_name
        
        scaler = None
        if scaler_path.exists():
            try:
                with open(scaler_path, 'rb') as f: scaler = pickle.load(f)
                self.log_msg(f"[+] 鉴权成功：加载专家级归一化密钥: {scaler_name}", "succ")
            except:
                self.log_msg(f"[-] 降级运作：无法读取密钥 {scaler_name}，开启本地自适应归一化。", "err")
        else:
            self.log_msg(f"[-] 降级运作：未发现预设密钥 ({scaler_name})，开启 Local Fit 自适应归一化。", "err")

        lookback = self.lookback_var.get()
        pred = self.pred_var.get()
        all_slices = []
        
        for i, iid in enumerate(selection):
            if self.stop_requested: break
            
            fname = self._file_mapping.get(iid)
            fpath = Path(self.src_var.get()) / fname
            
            self.log_msg(f"[*] 正在裂解 [{i+1}/{len(selection)}]: {fname}...", "info")
            self.tree.item(iid, values=(self.tree.item(iid)['values'][0], self.tree.item(iid)['values'][1], "处理中"))

            try:
                df = pd.read_csv(fpath)
                
                # 1. Health Check
                if df.isnull().values.any():
                    self.log_msg(f"[x] 拒绝处理: {fname} 包含 NaN 数据碎块。", "err")
                    self.tree.item(iid, values=(self.tree.item(iid)['values'][0], self.tree.item(iid)['values'][1], "数据碎块"))
                    continue
                
                # Continuity check (48 bars per day for 5m)
                df['timestamps'] = pd.to_datetime(df['timestamps'])
                daily_counts = df.groupby(df['timestamps'].dt.date).size()
                if (daily_counts != 48).any():
                    broken_days = daily_counts[daily_counts != 48].index.tolist()
                    self.log_msg(f"[!] 时间缺口警告: {fname} 有 {len(broken_days)}天数据不完整 (如 {broken_days[0]})", "err")

                zero_vol = (df['volume'] == 0).sum()
                if zero_vol > 0:
                    self.log_msg(f"[!] 钝化警告: {fname} 发现 {zero_vol} 根无量 K 线，模型可能进入无休眠死循环。", "err")
                
                # 2. Preprocess
                features = ['open', 'high', 'low', 'close', 'volume', 'amount']
                for col in features:
                    if col not in df.columns:
                        if col == 'amount': df['amount'] = df['volume'] * df['close']
                        else: df[col] = 0.0
                
                data = df[features].values
                
                # 3. Scaling
                if scaler:
                    data_scaled = scaler.transform(data)
                else:
                    data_scaled = StandardScaler().fit_transform(data)
                
                # 4. Slicing (Sliding Window)
                seq_len = lookback + pred
                if len(data_scaled) < seq_len:
                    self.log_msg(f"[-] 长度不足: {fname} 数据总量无法支撑一次完整前向传播。", "err")
                    self.tree.item(iid, values=(self.tree.item(iid)['values'][0], self.tree.item(iid)['values'][1], "长度不足"))
                    continue

                for start_idx in range(len(data_scaled) - seq_len + 1):
                    chunk = data_scaled[start_idx : start_idx + seq_len]
                    all_slices.append(chunk)
                
                self.tree.item(iid, values=(self.tree.item(iid)['values'][0], self.tree.item(iid)['values'][1], "通过检测"))
                
            except Exception as e:
                self.log_msg(f"[x] 处理 {fname} 时灾难性崩溃: {str(e)}", "err")
                self.tree.item(iid, values=(self.tree.item(iid)['values'][0], self.tree.item(iid)['values'][1], "处理崩溃"))

        # 5. Save Batch
        if not self.stop_requested and all_slices:
            final_array = np.array(all_slices).astype(np.float32)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            out_name = f"slices_{expert_id}_{timestamp}.npy"
            np.save(self.out_dir / out_name, final_array)
            self.log_msg(f"[+] 切片合成完成！共生成序列: {len(all_slices)} 条", "succ")
            self.log_msg(f"[>] 最终张量物理位置: {self.out_dir / out_name}", "succ")
            self.stats_sign_update("生产完成", self.c_green)
        else:
            self.stats_sign_update("系统就绪", self.c_gold_dim)
        
        self.start_btn.config(state='normal')
        self.log_msg("[*] 数据生产阵列已离线挂起。", "sys")

class DashFrame(tk.Frame):
    def __init__(self, master, title, bg_color, fg_color, dash_color, font, **kwargs):
        super().__init__(master, bg=bg_color, **kwargs)
        self.bg_color = bg_color
        self.dash_color = dash_color
        
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0)
        self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        self.content = tk.Frame(self, bg=bg_color)
        self.content.pack(fill=BOTH, expand=True, padx=12, pady=(25, 12)) 
        
        self.bind("<Configure>", self._draw)
        
        self.title_text = title
        self.fg_color = fg_color
        self.font = font
        
    def _draw(self, event=None):
        self.canvas.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10: return
        
        self.canvas.create_rectangle(2, 10, w-2, h-2, outline=self.dash_color, dash=(5, 5))
        self.canvas.create_rectangle(15, 0, 15 + len(self.title_text)*10, 20, fill=self.bg_color, outline="")
        self.canvas.create_text(20, 10, text=self.title_text, anchor="nw", font=self.font, fill=self.fg_color)

if __name__ == "__main__":
    app = SlicerMatrixGUI()
    app.mainloop()
