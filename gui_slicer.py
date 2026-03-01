#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import messagebox, filedialog
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
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# =================================================================
# [ KLine-Slicer: DATA PRODUCTION TERMINAL ]
# Designed for Kronos Pipeline (DataFrame Packers)
# =================================================================

class SlicerMatrixGUI(ttk.Window):
    def __init__(self):
        super().__init__(themename="cyborg")
        self.title("Kronos Slicer · 全市场数据打包终端")
        self.geometry("1100x860")
        self.minsize(1050, 800)

        
        try:
            self.createcommand('::tk::mac::ReopenApplication', self.deiconify)
        except Exception:
            pass

        
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
        self.out_dir = self.root_dir / "gui_out_slices"
        
        if not self.out_dir.exists(): self.out_dir.mkdir(parents=True)
        
        self.src_var = tk.StringVar(value=str(self.src_dir))
        self.dataset_name_var = tk.StringVar(value="my_dataset")
        
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
        style = ttk.Style()
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
        tk.Label(header_frame, text="KRONOS SLICER · 数据切片生产终端", font=self.font_title, fg=self.c_gold, bg=self.c_bg).pack(side=LEFT)

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
        
        # 2. Dataset Config
        param_lf = DashFrame(left_panel, title=" 数据集参数 CONFIG ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        param_lf.pack(fill=X, pady=(0, 15))
        
        tk.Label(param_lf.content, text="数据集名称 (Dataset Name):", font=self.font_base, fg=self.c_fg, bg=self.c_bg).pack(anchor=W)
        tk.Entry(param_lf.content, textvariable=self.dataset_name_var, font=self.font_log, bg=self.c_panel, fg=self.c_gold, relief="flat", highlightthickness=1, highlightbackground=self.c_gold_dim).pack(fill=X, pady=(4, 10))
        
        # Info label explaining new logic
        info_text = "Note: Kronos 模型会在训练时按需执行\n滑动切片和动态归一化。此处仅将清洗\n后的股票聚合为 .pkl 巨型字典字典包。"
        tk.Label(param_lf.content, text=info_text, font=("Menlo", 12), fg=self.c_gold_dim, bg=self.c_bg, justify=LEFT).pack(anchor=W, pady=(5, 0))

        # 3. Action Controls
        ctrl_lf = DashFrame(left_panel, title=" 操作面板 ", bg_color=self.c_bg, fg_color=self.c_gold, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        ctrl_lf.pack(fill=X, pady=(0, 15))

        self.check_btn = ttk.Button(ctrl_lf.content, text="[ 完整性复查 ]", style="FlatGold.TButton", command=self.on_integrity_check_click)
        self.check_btn.pack(fill=X, pady=(10, 5), ipady=3)

        self.start_btn = ttk.Button(ctrl_lf.content, text="开始打包 (To Dictionary .pkl)", style="FlatGold.TButton", command=self.on_start_click)
        self.start_btn.pack(fill=X, pady=(5, 10), ipady=5)
        
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
        self.log_widget.tag_config("warn", foreground="#FF9800", font=("Menlo", 13, "bold"))
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
        ttk.Button(tb, text="[ 取消 ]", style="FlatGold.TButton", command=self.on_unselect_all).pack(side=LEFT, padx=(0,5))
        ttk.Button(tb, text="[ 批量物理删除 ]", style="FlatRed.TButton", command=self.on_batch_delete_src).pack(side=LEFT)
        
        columns = ("name", "raw_name", "size", "health", "delete")
        src_container = tk.Frame(assets_lf.content, bg=self.c_bg)
        src_container.pack(fill=BOTH, expand=True)
        
        self.tree = ttk.Treeview(src_container, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("name", text="股票名称_代码")
        self.tree.heading("raw_name", text="原始文件名")
        self.tree.heading("size", text="物理大小")
        self.tree.heading("health", text="数据体检")
        self.tree.heading("delete", text="[ 删除 ]")
        self.tree.column("name", width=180, anchor=W)
        self.tree.column("raw_name", width=300, anchor=W)
        self.tree.column("size", width=100, anchor=E)
        self.tree.column("health", width=120, anchor=CENTER)
        self.tree.column("delete", width=70, anchor=CENTER)
        
        src_yscroll = ttk.Scrollbar(src_container, orient=tk.VERTICAL, command=self.tree.yview, style="Hidden.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=src_yscroll.set)
        src_yscroll.pack(side=RIGHT, fill=Y)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        self.tree.bind('<ButtonRelease-1>', self.on_src_tree_click)

        # 2. BOTTOM: Output Tensors
        target_lf = DashFrame(right_panel, title=" 巨型字典陈列室 (Dict .pkl) ", bg_color=self.c_bg, fg_color=self.c_green, dash_color=self.c_gold_dim, font=("Menlo", 15, "bold"))
        target_lf.pack(side=TOP, fill=BOTH, expand=True)
        
        tgt_columns = ("name", "count", "size", "time", "delete")
        tgt_container = tk.Frame(target_lf.content, bg=self.c_bg)
        tgt_container.pack(fill=BOTH, expand=True)
        
        self.tgt_tree = ttk.Treeview(tgt_container, columns=tgt_columns, show="headings", selectmode="browse")
        self.tgt_tree.heading("name", text="文件名称")
        self.tgt_tree.heading("count", text="包含股票数")
        self.tgt_tree.heading("size", text="物理大小")
        self.tgt_tree.heading("time", text="生成时间")
        self.tgt_tree.heading("delete", text="[ 删除 ]")
        
        self.tgt_tree.column("name", width=250, anchor=W)
        self.tgt_tree.column("count", width=120, anchor=CENTER)
        self.tgt_tree.column("size", width=100, anchor=E)
        self.tgt_tree.column("time", width=150, anchor=CENTER)
        self.tgt_tree.column("delete", width=70, anchor=CENTER)
        
        tgt_yscroll = ttk.Scrollbar(tgt_container, orient=tk.VERTICAL, command=self.tgt_tree.yview, style="Hidden.Vertical.TScrollbar")
        self.tgt_tree.configure(yscrollcommand=tgt_yscroll.set)
        tgt_yscroll.pack(side=RIGHT, fill=Y)
        self.tgt_tree.pack(side=LEFT, fill=BOTH, expand=True)
        self.tgt_tree.bind('<ButtonRelease-1>', self.on_tgt_tree_click)
        self.tgt_tree.bind('<Double-1>', self.on_tgt_tree_double_click)

        # Footer
        self.status_bar = tk.Label(self, text="待命：准备生产数据", bg=self.c_bg, fg=self.c_gold_dim, font=("Menlo", 10))
        self.status_bar.pack(side=BOTTOM, anchor=W, padx=20, pady=(0, 5))

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
        
        current_selection = self.tree.selection()
        current_iids = self.tree.get_children()
        for iid in current_iids: self.tree.delete(iid)
        
        self._file_mapping = {}
        files = sorted(p.glob("*_5m_*.csv"), key=os.path.getmtime, reverse=True)
        for f in files:
            size_kb = f.stat().st_size / 1024.0
            # Simplify name: Name_Code
            match = re.search(r"^(.*?)_(.*?)_5m", f.name)
            if match:
                disp_name = f"{match.group(1)}_{match.group(2)}"
            else:
                disp_name = f.name.split("_")[0]
                
            iid = self.tree.insert("", END, values=(disp_name, f.name, f"{size_kb:.1f} KB", "待体检", "[ 删除 ]"))
            self._file_mapping[iid] = f.name
            
        if not current_selection:
            self.on_select_all()

    def poll_target_dir(self):
        p = Path(self.out_dir)
        if not p.exists() or not p.is_dir(): return
        
        current_iids = self.tgt_tree.get_children()
        for iid in current_iids: self.tgt_tree.delete(iid)
        
        self._target_mapping = {}
        files = sorted(p.glob("*.pkl"), key=os.path.getmtime, reverse=True)
        for f in files:
            size_mb = f.stat().st_size / (1024.0 * 1024.0)
            time_str = datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            count_str = "Packed"
            iid = self.tgt_tree.insert("", END, values=(f.name, count_str, f"{size_mb:.1f} MB", time_str, "[ 删除 ]"))
            self._target_mapping[iid] = f.name
        self.after(5000, self.poll_target_dir)

    def on_src_tree_click(self, event):
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id or column != "#5": return
        
        filename = self._file_mapping.get(item_id)
        if messagebox.askyesno("机密操作", f"确定要永久粉碎源文件 {filename} 吗？"):
            try:
                os.remove(Path(self.src_var.get()) / filename)
                self.tree.delete(item_id)
                self.log_msg(f"[*] 已粉碎物理标的: {filename}", "sys")
            except Exception as e:
                messagebox.showerror("中断", f"粉碎失败: {e}")

    def on_batch_delete_src(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选定要销毁的标的。")
            return
            
        if not messagebox.askyesno("机密操作", f"确定要永久粉碎选中的 {len(selection)} 个源文件吗？"):
            return
            
        success_count = 0
        for iid in selection:
            filename = self._file_mapping.get(iid)
            try:
                os.remove(Path(self.src_var.get()) / filename)
                self.tree.delete(iid)
                success_count += 1
            except: pass
        
        self.log_msg(f"[!] 批量粉碎任务完成: 成功清理 {success_count} 个物理标的。", "warn")

    def on_tgt_tree_click(self, event):
        item_id = self.tgt_tree.identify_row(event.y)
        column = self.tgt_tree.identify_column(event.x)
        if not item_id or column != "#5": return
        
        filename = self._target_mapping.get(item_id)
        if not filename: return

        # Handle Delete (#5)
        if messagebox.askyesno("机密操作", f"确定要销毁该产出 {filename} 吗？"):
            try:
                os.remove(self.out_dir / filename)
                self.tgt_tree.delete(item_id)
                self.log_msg(f"[*] 已移除产出包: {filename}", "sys")
            except Exception as e:
                messagebox.showerror("中断", f"销毁失败: {e}")

    def on_tgt_tree_double_click(self, event):
        item_id = self.tgt_tree.identify_row(event.y)
        column = self.tgt_tree.identify_column(event.x)
        if not item_id or column == "#5": return
        
        filename = self._target_mapping.get(item_id)
        if not filename: return
        
        try:
            # On macOS, use 'open' to reveal the folder
            os.system(f'open "{self.out_dir}"')
            self.log_msg(f"[*] 已打开目标输出目录: {self.out_dir}", "info")
        except Exception as e:
            self.log_msg(f"[-] 无法打开目录: {e}", "err")

    def on_integrity_check_click(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先勾选需要检查的标的。")
            return
            
        self.log_msg(f"[*] 启动深度完整性复查 (共 {len(selection)} 项)...", "sys")
        threading.Thread(target=self._run_integrity_check, args=(selection,), daemon=True).start()

    def _run_integrity_check(self, selection):
        required = ['timestamps', 'open', 'high', 'low', 'close', 'volume', 'amount']
        for iid in selection:
            fname = self._file_mapping.get(iid)
            fpath = Path(self.src_var.get()) / fname
            try:
                df = pd.read_csv(fpath)
                status = "检测通过"
                if not all(col in df.columns for col in required):
                    status = "[x] 缺列"
                elif df.isnull().values.any():
                    status = "[x] 空值"
                elif len(df) < 10:
                    status = "[x] 数据过短"
                
                self.after(0, lambda i=iid, s=status: self.tree.item(i, values=(self.tree.item(i)['values'][0], self.tree.item(i)['values'][1], self.tree.item(i)['values'][2], s, "[ 删除 ]")))
            except:
                self.after(0, lambda i=iid: self.tree.item(i, values=(self.tree.item(i)['values'][0], self.tree.item(i)['values'][1], self.tree.item(i)['values'][2], "[x] 毁损", "[ 删除 ]")))
        self.log_msg("[+] 完整性复查完毕，请根据状态剔除异常标的。", "succ")

    def on_start_click(self):
        if self.process_thread and self.process_thread.is_alive(): return
        
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先在资产库中勾选需要加工的标的。")
            return
            
        dataset_name = self.dataset_name_var.get().strip()
        if not dataset_name:
            messagebox.showerror("错误", "请指定数据集名称！")
            return
            
        self.stop_requested = False
        self.start_btn.config(state=DISABLED)
        self.stop_btn.config(state=NORMAL)
        self.status_sign.config(text="打包生产中...", fg=self.c_gold)
        
        self.process_thread = threading.Thread(target=self._run_slicing_batch, args=(selection, dataset_name), daemon=True)
        self.process_thread.start()

    def on_stop(self):
        self.stop_requested = True
        self.log_msg("[!] 熔断指令下达，正在尝试平滑停机...", "err")

    def _run_slicing_batch(self, selection, dataset_name):
        self.log_msg(f"[*] 启动打包流水线: 目标格式字典 `.pkl` ({dataset_name})...", "sys")
        
        kronos_dict = {}
        success_ct = 0
        
        for i, iid in enumerate(selection):
            if self.stop_requested: break
            fname = self._file_mapping.get(iid)
            fpath = Path(self.src_var.get()) / fname
            
            # Skip if status is already error
            current_status = self.tree.item(iid)['values'][3]
            if "[x]" in current_status:
                self.log_msg(f"[-] 跳过异常标点: {fname} (状态: {current_status})", "warn")
                continue

            try:
                # Extract stock code
                match = re.search(r"_(.*?)_5m", fname)
                symbol = match.group(1) if match else fname.split("_")[0]
                
                df = pd.read_csv(fpath)
                
                # Double check columns (case insensitive renaming for Kronos)
                df.columns = [c.lower() for c in df.columns]
                rename_map = {'timestamps': 'datetime', 'volume': 'vol', 'amount': 'amt'}
                # Adjust for potential variations
                for k, v in rename_map.items():
                    if k in df.columns: df.rename(columns={k: v}, inplace=True)
                
                if 'datetime' not in df.columns:
                    self.log_msg(f"[-] 跳过 {fname}: 缺少时间戳列", "err")
                    continue
                    
                df['datetime'] = pd.to_datetime(df['datetime'])
                df.set_index('datetime', inplace=True)
                
                # Keep required OHLCVA
                cols = ['open', 'high', 'low', 'close', 'vol', 'amt']
                if not all(col in df.columns for col in cols):
                    self.log_msg(f"[-] 跳过 {fname}: 缺少 OHLCVA 必要列", "err")
                    continue
                
                df_clean = df[cols].copy()
                kronos_dict[symbol] = df_clean
                success_ct += 1
                
                if success_ct % 10 == 0:
                    self.log_msg(f"[*] 已注入 {success_ct} 支股票数据...")
            except Exception as e:
                self.log_msg(f"[-] 致命错误 {fname}: {str(e)}", "err")

        # 3. Finalize Save
        if not self.stop_requested and kronos_dict:
            out_file = f"kronos_dataset_{dataset_name}_{datetime.datetime.now().strftime('%m%d_%H%M')}.pkl"
            with open(self.out_dir / out_file, "wb") as f:
                pickle.dump(kronos_dict, f)
                
            self.log_msg(f"[+] 生产大功告成！巨型字典共打包股票数: {len(kronos_dict)} 支", "succ")
            self.status_sign.config(text="打包完成", fg=self.c_green)
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
    try:
        app = SlicerMatrixGUI()
        app.mainloop()
    except Exception as e:
        print(f"\n[致命错误] 程序启动失败:")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出 (Wait for input)...")


