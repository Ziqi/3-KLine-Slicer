import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, END, LEFT, BOTH, TOP, BOTTOM, RIGHT, X, Y, W, E, S, CENTER, WORD, DISABLED, NORMAL
import os
import pandas as pd
import numpy as np
import pickle
import threading
import time
import datetime
import glob
import re
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
        self.c_bg = "#080808"        
        self.c_panel = "#101010"     
        self.c_gold = "#F0B90B"      
        self.c_gold_dim = "#715A2B"  
        self.c_fg = "#E1C699"        
        self.c_green = "#00D47C"     
        self.c_red = "#FF3B30"       
        
        self.font_title = ("Menlo", 32, "bold")
        self.font_base = ("Menlo", 14)
        self.font_base_lg = ("Menlo", 16)
        self.font_log = ("Menlo", 13)
        
        # --- Paths & State ---
        self.root_dir = Path(__file__).resolve().parent
        self.src_dir = self.root_dir.parent / "2-KLine-Resample" / "gui_out_5m"
        self.expert_dir = Path("/Users/xiaoziqi/X-Matrix/data/processed")
        self.out_dir = self.root_dir / "gui_out_slices"
        
        if not self.out_dir.exists(): self.out_dir.mkdir(parents=True)
        if not self.expert_dir.exists(): self.expert_dir.mkdir(parents=True)
        
        self.src_var = tk.StringVar(value=str(self.src_dir))
        self.expert_var = tk.StringVar(value="expert_02_ai")
        self.new_expert_name = tk.StringVar()
        self.lookback_var = tk.IntVar(value=90)
        self.pred_var = tk.IntVar(value=10)
        
        self.expert_options = {
            "expert_01_chem": "新材料与化工",
            "expert_02_ai": "AI与半导体",
            "expert_03_robotics": "机器人与智造",
            "expert_04_aerospace": "航天与军工",
            "NEW_EXPERT": "[+] 训练全新大脑 (Create New Expert)"
        }
        
        self.stop_requested = False
        self.process_thread = None
        self._file_mapping = {}
        self._target_mapping = {}
        
        self._setup_styles()
        self._build_ui()
        
        # Initial scan
        self.after(500, self.poll_source_dir)
        self.after(1000, self.poll_target_dir)

    def _setup_styles(self):
        style = self.style
        style.configure(".", font=self.font_base, background=self.c_bg, foreground=self.c_fg)
        
        style.configure("FlatGold.TButton", font=self.font_base_lg, background=self.c_bg, foreground=self.c_gold, bordercolor=self.c_gold, borderwidth=1)
        style.map("FlatGold.TButton", background=[("active", "#1A140B")], foreground=[("active", "#FFD700")])
        style.configure("FlatRed.TButton", font=self.font_base_lg, background=self.c_bg, foreground=self.c_red, bordercolor=self.c_red, borderwidth=1)
        style.map("FlatRed.TButton", background=[("active", "#1A0505")])
        
        # Scrollbars
        style.layout('Hidden.Vertical.TScrollbar', [('Vertical.Scrollbar.trough', {'children': [('Vertical.Scrollbar.thumb', {'expand': '1', 'sticky': 'nswe'})], 'sticky': 'ns'})])
        style.configure("Hidden.Vertical.TScrollbar", background=self.c_gold_dim, troughcolor=self.c_bg, bordercolor=self.c_bg, relief="flat")
        style.map("Hidden.Vertical.TScrollbar", background=[("active", self.c_gold)])
        
        style.configure("Treeview", background=self.c_panel, foreground=self.c_fg, fieldbackground=self.c_panel, borderwidth=0, font=self.font_base, rowheight=32)
        style.map("Treeview", background=[("selected", "#2A2111")], foreground=[("selected", self.c_gold)])
        style.configure("Treeview.Heading", font=("Menlo", 13, "bold"), background=self.c_bg, foreground=self.c_gold, borderwidth=1)

    def _build_ui(self):
        self.configure(bg=self.c_bg)
        
        # macOS Frontmost
        self.lift()
        self.attributes('-topmost', True)
        self.after(500, lambda: self.attributes('-topmost', False))
        os.system('''osascript -e 'tell application "System Events" to set frontmost of the first process whose unix id is %d to true' ''' % os.getpid())

        # --- HEADER ---
        header_frame = tk.Frame(self, bg=self.c_bg, pady=15)
        header_frame.pack(fill=X, padx=20)
        tk.Label(header_frame, text="X-MATRIX SLICER · 数据切片生产终端", font=self.font_title, fg=self.c_gold, bg=self.c_bg).pack(side=LEFT)
        self.status_sign = tk.Label(header_frame, text="系统就绪", font=("Menlo", 16, "bold"), fg=self.c_gold_dim, bg=self.c_bg)
        self.status_sign.pack(side=RIGHT, anchor=S)

        # --- BODY ---
        body_frame = tk.Frame(self, bg=self.c_bg)
        body_frame.pack(fill=BOTH, expand=True, padx=20, pady=(0, 20))
        
        # --- LEFT PANEL: CONTROLS ---
        left_panel = tk.Frame(body_frame, width=400, bg=self.c_bg)
        left_panel.pack(side=LEFT, fill=Y, padx=(0, 20))
        left_panel.pack_propagate(False)
        
        # 1. Mounts
        mount_lf = DashFrame(left_panel, title=" 存储挂载点 MOUNTS ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        mount_lf.pack(fill=X, pady=(0, 15))
        
        tk.Label(mount_lf.content, text="5分钟K线来源:", font=self.font_base, fg=self.c_fg, bg=self.c_bg).pack(anchor=W)
        src_fr = tk.Frame(mount_lf.content, bg=self.c_bg)
        src_fr.pack(fill=X, pady=(2, 10))
        tk.Entry(src_fr, textvariable=self.src_var, font=self.font_log, bg=self.c_panel, fg=self.c_gold, relief="flat", highlightthickness=1, highlightbackground=self.c_gold_dim).pack(side=LEFT, fill=X, expand=True)
        ttk.Button(src_fr, text="打开", style="FlatGold.TButton", command=self.on_browse_src).pack(side=RIGHT, padx=(5,0))
        
        # 2. Expert Config
        param_lf = DashFrame(left_panel, title=" 专家参数 CONFIG ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        param_lf.pack(fill=X, pady=(0, 15))
        
        tk.Label(param_lf.content, text="目标大脑 (Target Expert):", font=self.font_base, fg=self.c_fg, bg=self.c_bg).pack(anchor=W)
        self.expert_combo = ttk.Combobox(param_lf.content, textvariable=self.expert_var, values=list(self.expert_options.keys()), font=self.font_base)
        self.expert_combo.pack(fill=X, pady=(2, 10))
        self.expert_combo.bind("<<ComboboxSelected>>", self._on_expert_change)
        
        # New Expert Name Entry (hidden by default)
        self.new_exp_frame = tk.Frame(param_lf.content, bg=self.c_bg)
        tk.Label(self.new_exp_frame, text="新专家代号:", font=self.font_base, fg=self.c_green, bg=self.c_bg).pack(side=LEFT)
        tk.Entry(self.new_exp_frame, textvariable=self.new_expert_name, font=self.font_log, bg=self.c_panel, fg=self.c_green, relief="flat", highlightthickness=1, highlightbackground=self.c_green).pack(side=LEFT, fill=X, expand=True, padx=5)
        
        # Window Params
        win_frame = tk.Frame(param_lf.content, bg=self.c_bg)
        win_frame.pack(fill=X, pady=(10, 0))
        tk.Label(win_frame, text="Lookback:", font=self.font_base, fg=self.c_gold, bg=self.c_bg).pack(side=LEFT)
        tk.Entry(win_frame, textvariable=self.lookback_var, width=5, font=self.font_base, bg=self.c_panel, fg=self.c_fg, relief="flat").pack(side=LEFT, padx=5)
        tk.Label(win_frame, text="Predict:", font=self.font_base, fg=self.c_gold, bg=self.c_bg).pack(side=LEFT)
        tk.Entry(win_frame, textvariable=self.pred_var, width=5, font=self.font_base, bg=self.c_panel, fg=self.c_fg, relief="flat").pack(side=LEFT, padx=5)

        # 3. Action Controls
        ctrl_lf = DashFrame(left_panel, title=" 操作面板 ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        ctrl_lf.pack(fill=X, pady=(0, 15))

        self.start_btn = ttk.Button(ctrl_lf.content, text="开始切片生产 (To Tensor)", style="FlatGold.TButton", command=self.on_start_click)
        self.start_btn.pack(fill=X, pady=(15, 10), ipady=5)
        
        self.stop_btn = ttk.Button(ctrl_lf.content, text="熔断中止", style="FlatRed.TButton", command=self.on_stop, state=DISABLED)
        self.stop_btn.pack(fill=X, pady=(0, 5), ipady=5)

        # 4. Console Logs
        log_lf = DashFrame(left_panel, title=" 运行日志 ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        log_lf.pack(fill=BOTH, expand=True)
        
        txt_frame = tk.Frame(log_lf.content, bg=self.c_panel)
        txt_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        self.log_widget = tk.Text(txt_frame, font=self.font_log, bg=self.c_panel, fg=self.c_fg, insertbackground=self.c_fg, wrap=WORD, borderwidth=0, highlightthickness=0, spacing1=4, spacing3=4)
        txt_scroll = ttk.Scrollbar(txt_frame, orient=tk.VERTICAL, command=self.log_widget.yview, style="Hidden.Vertical.TScrollbar")
        self.log_widget.configure(yscrollcommand=txt_scroll.set)
        
        txt_scroll.pack(side=RIGHT, fill=Y)
        self.log_widget.pack(side=LEFT, fill=BOTH, expand=True)
        
        self.log_widget.tag_config("info", foreground=self.c_fg)
        self.log_widget.tag_config("sys", foreground=self.c_gold, font=("Menlo", 13, "bold"))
        self.log_widget.tag_config("succ", foreground=self.c_green, font=("Menlo", 13, "bold"))
        self.log_widget.tag_config("err", foreground=self.c_red, font=("Menlo", 13, "bold"))
        self.log_widget.configure(state=DISABLED)

        # --- RIGHT PANEL ---
        right_panel = tk.Frame(body_frame, bg=self.c_bg)
        right_panel.pack(side=LEFT, fill=BOTH, expand=True)
        
        # 1. TOP: Source Files
        assets_lf = DashFrame(right_panel, title=" 5分钟K线资产库 (待处理标的) ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        assets_lf.pack(side=TOP, fill=BOTH, expand=True, pady=(0, 10))
        
        tb = tk.Frame(assets_lf.content, bg=self.c_bg)
        tb.pack(fill=X, pady=(0, 5))
        ttk.Button(tb, text="[ 全选 ]", style="FlatGold.TButton", command=self.on_select_all).pack(side=LEFT, padx=(0,5))
        ttk.Button(tb, text="[ 取消 ]", style="FlatGold.TButton", command=self.on_unselect_all).pack(side=LEFT)
        
        columns = ("name", "size", "health", "delete")
        src_container = tk.Frame(assets_lf.content, bg=self.c_bg)
        src_container.pack(fill=BOTH, expand=True)
        
        self.tree = ttk.Treeview(src_container, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("name", text="文件名称")
        self.tree.heading("size", text="物理大小")
        self.tree.heading("health", text="数据体检")
        self.tree.heading("delete", text="[ 删除 ]")
        self.tree.column("name", width=250, anchor=W)
        self.tree.column("size", width=100, anchor=E)
        self.tree.column("health", width=120, anchor=CENTER)
        self.tree.column("delete", width=70, anchor=CENTER)
        
        src_yscroll = ttk.Scrollbar(src_container, orient=tk.VERTICAL, command=self.tree.yview, style="Hidden.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=src_yscroll.set)
        src_yscroll.pack(side=RIGHT, fill=Y)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        self.tree.bind('<ButtonRelease-1>', self.on_src_tree_click)

        # 2. BOTTOM: Output Tensors
        target_lf = DashFrame(right_panel, title=" 张量产出陈列室 (Tensors .npy) ", bg_color=self.c_bg, fg_color=self.c_green, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        target_lf.pack(side=TOP, fill=BOTH, expand=True)
        
        tgt_columns = ("name", "expert", "size", "time", "delete")
        tgt_container = tk.Frame(target_lf.content, bg=self.c_bg)
        tgt_container.pack(fill=BOTH, expand=True)
        
        self.tgt_tree = ttk.Treeview(tgt_container, columns=tgt_columns, show="headings", selectmode="browse")
        self.tgt_tree.heading("name", text="文件名称")
        self.tgt_tree.heading("expert", text="归属专家")
        self.tgt_tree.heading("size", text="数组大小")
        self.tgt_tree.heading("time", text="生成时间")
        self.tgt_tree.heading("delete", text="[ 删除 ]")
        
        self.tgt_tree.column("name", width=250, anchor=W)
        self.tgt_tree.column("expert", width=120, anchor=CENTER)
        self.tgt_tree.column("size", width=100, anchor=E)
        self.tgt_tree.column("time", width=150, anchor=CENTER)
        self.tgt_tree.column("delete", width=70, anchor=CENTER)
        
        tgt_yscroll = ttk.Scrollbar(tgt_container, orient=tk.VERTICAL, command=self.tgt_tree.yview, style="Hidden.Vertical.TScrollbar")
        self.tgt_tree.configure(yscrollcommand=tgt_yscroll.set)
        tgt_yscroll.pack(side=RIGHT, fill=Y)
        self.tgt_tree.pack(side=LEFT, fill=BOTH, expand=True)
        self.tgt_tree.bind('<ButtonRelease-1>', self.on_tgt_tree_click)

        # Footer
        self.status_bar = tk.Label(self, text="待命：准备生产数据", bg=self.c_bg, fg=self.c_gold_dim, font=("Menlo", 10))
        self.status_bar.pack(side=BOTTOM, anchor=W, padx=20, pady=(0, 5))

    def _on_expert_change(self, event=None):
        if self.expert_var.get() == "NEW_EXPERT":
            self.new_exp_frame.pack(fill=X, pady=(2, 5))
            self.expert_combo.config(foreground=self.c_green)
        else:
            self.new_exp_frame.pack_forget()
            self.expert_combo.config(foreground=self.c_fg)

    def log_msg(self, msg, level="info"):
        self.log_widget.configure(state=NORMAL)
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_widget.insert(END, f"[{ts}] ", "sys")
        self.log_widget.insert(END, msg + "\n", level)
        self.log_widget.see(END)
        self.log_widget.configure(state=DISABLED)

    def on_browse_src(self):
        d = filedialog.askdirectory(initialdir=self.src_var.get())
        if d:
            self.src_var.set(d)
            self.poll_source_dir()

    def on_select_all(self):
        self.tree.selection_set(self.tree.get_children())

    def on_unselect_all(self):
        self.tree.selection_remove(self.tree.get_children())

    def poll_source_dir(self):
        p = Path(self.src_var.get())
        if not p.exists() or not p.is_dir(): return
        
        current_iids = self.tree.get_children()
        for iid in current_iids: self.tree.delete(iid)
        
        self._file_mapping = {}
        files = sorted(p.glob("*_5m_*.csv"), key=os.path.getmtime, reverse=True)
        for f in files:
            size_kb = f.stat().st_size / 1024.0
            iid = self.tree.insert("", END, values=(f.name, f"{size_kb:.1f} KB", "待体检", "[ 删除 ]"))
            self._file_mapping[iid] = f.name
        self.on_select_all()

    def poll_target_dir(self):
        p = Path(self.out_dir)
        if not p.exists() or not p.is_dir(): return
        
        current_iids = self.tgt_tree.get_children()
        for iid in current_iids: self.tgt_tree.delete(iid)
        
        self._target_mapping = {}
        files = sorted(p.glob("*.npy"), key=os.path.getmtime, reverse=True)
        for f in files:
            size_mb = f.stat().st_size / (1024.0 * 1024.0)
            time_str = datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            
            # Extract expert from slices_EXPERT_ID_...
            expert_match = re.search(r"slices_(.*?)_\d", f.name)
            expert_name = expert_match.group(1) if expert_match else "Unknown"
            
            iid = self.tgt_tree.insert("", END, values=(f.name, expert_name, f"{size_mb:.1f} MB", time_str, "[ 删除 ]"))
            self._target_mapping[iid] = f.name
        
        # Poll again in 5 seconds
        self.after(5000, self.poll_target_dir)

    def on_src_tree_click(self, event):
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id or column != "#4": return
        
        filename = self._file_mapping.get(item_id)
        if messagebox.askyesno("机密操作", f"确定要永久粉碎源文件 {filename} 吗？"):
            try:
                os.remove(Path(self.src_var.get()) / filename)
                self.tree.delete(item_id)
                self.log_msg(f"[*] 已粉碎物理标的: {filename}", "sys")
            except Exception as e:
                messagebox.showerror("中断", f"粉碎失败: {e}")

    def on_tgt_tree_click(self, event):
        item_id = self.tgt_tree.identify_row(event.y)
        column = self.tgt_tree.identify_column(event.x)
        if not item_id or column != "#5": return
        
        filename = self._target_mapping.get(item_id)
        if messagebox.askyesno("机密操作", f"确定要销毁该张量产出 {filename} 吗？"):
            try:
                os.remove(self.out_dir / filename)
                self.tgt_tree.delete(item_id)
                self.log_msg(f"[*] 已移除产出张量: {filename}", "sys")
            except Exception as e:
                messagebox.showerror("中断", f"销毁失败: {e}")

    def on_start_click(self):
        if self.process_thread and self.process_thread.is_alive(): return
        
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先在资产库中勾选需要加工的标的。")
            return
            
        # Check Expert
        expert_id = self.expert_var.get()
        if expert_id == "NEW_EXPERT":
            new_name = self.new_expert_name.get().strip()
            if not new_name:
                messagebox.showerror("错误", "请指定新专家的代号！")
                return
            expert_id = new_name
            
        self.stop_requested = False
        self.start_btn.config(state=DISABLED)
        self.stop_btn.config(state=NORMAL)
        self.status_sign.config(text="切片生产中...", fg=self.c_gold)
        
        self.process_thread = threading.Thread(target=self._run_slicing_batch, args=(selection, expert_id), daemon=True)
        self.process_thread.start()

    def on_stop(self):
        self.stop_requested = True
        self.log_msg("[!] 熔断指令下达，正在尝试平滑停机...", "err")

    def _run_slicing_batch(self, selection, expert_id):
        is_new_expert = self.expert_var.get() == "NEW_EXPERT"
        self.log_msg(f"[*] 启动切片生产流水线 ({expert_id})...", "sys")
        
        scaler_path = self.expert_dir / f"scaler_{expert_id}.pkl"
        scaler = None
        
        # 1. Scaler Handling
        if not is_new_expert and scaler_path.exists():
            try:
                with open(scaler_path, 'rb') as f: scaler = pickle.load(f)
                self.log_msg(f"[+] 挂载已有专家密钥: {scaler_path.name}", "succ")
            except:
                self.log_msg(f"[-] 密钥解析失败，启用自适应拟合。", "err")
        elif is_new_expert:
            self.log_msg(f"[*] 模式：训练全新大脑。将从本次数据中拟合新密钥。", "sys")

        lookback = self.lookback_var.get()
        pred = self.pred_var.get()
        all_slices = []
        raw_data_for_scaler = [] # Only used if fitting new scaler
        
        for i, iid in enumerate(selection):
            if self.stop_requested: break
            fname = self._file_mapping.get(iid)
            fpath = Path(self.src_var.get()) / fname
            
            self.tree.item(iid, values=(self.tree.item(iid)['values'][0], self.tree.item(iid)['values'][1], "读取中", "[ 删除 ]"))
            try:
                df = pd.read_csv(fpath)
                # Quick health check
                if df.isnull().values.any():
                    self.tree.item(iid, values=(self.tree.item(iid)['values'][0], self.tree.item(iid)['values'][1], "[x] 毁损", "[ 删除 ]"))
                    continue
                
                features = ['open', 'high', 'low', 'close', 'volume', 'amount']
                data = df[features].values
                
                if is_new_expert:
                    raw_data_for_scaler.append(data)
                
                # We defer scaling until we processed all files if fitting new expert
                if not is_new_expert:
                    data_scaled = scaler.transform(data) if scaler else StandardScaler().fit_transform(data)
                    seq_len = lookback + pred
                    if len(data_scaled) >= seq_len:
                        for idx in range(len(data_scaled) - seq_len + 1):
                            all_slices.append(data_scaled[idx : idx + seq_len])
                
                self.tree.item(iid, values=(self.tree.item(iid)['values'][0], self.tree.item(iid)['values'][1], "检测通过", "[ 删除 ]"))
            except Exception as e:
                self.log_msg(f"[-] 致命错误 {fname}: {str(e)}", "err")

        # 2. Logic for New Expert
        if is_new_expert and raw_data_for_scaler:
            self.log_msg(f"[*] 正在为新专家 [{expert_id}] 计算归一化特征...", "sys")
            all_raw = np.concatenate(raw_data_for_scaler, axis=0)
            scaler = StandardScaler()
            scaler.fit(all_raw)
            with open(scaler_path, 'wb') as f: pickle.dump(scaler, f)
            self.log_msg(f"[+] 新专家密钥已存盘: {scaler_path.name}", "succ")
            
            # Now slice with the newly fitted scaler
            for i, data in enumerate(raw_data_for_scaler):
                data_scaled = scaler.transform(data)
                seq_len = lookback + pred
                if len(data_scaled) >= seq_len:
                    for idx in range(len(data_scaled) - seq_len + 1):
                        all_slices.append(data_scaled[idx : idx + seq_len])

        # 3. Finalize Save
        if not self.stop_requested and all_slices:
            final_arr = np.array(all_slices).astype(np.float32)
            out_file = f"slices_{expert_id}_{datetime.datetime.now().strftime('%m%d_%H%M')}.npy"
            np.save(self.out_dir / out_file, final_arr)
            self.log_msg(f"[+] 生产大功告成！生成条目: {len(all_slices)} 条", "succ")
            self.status_sign.config(text="生产完成", fg=self.c_green)
            self.poll_target_dir()
        else:
            self.status_sign.config(text="系统就绪", fg=self.c_gold_dim)
            
        self.start_btn.config(state=NORMAL)
        self.stop_btn.config(state=DISABLED)

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
