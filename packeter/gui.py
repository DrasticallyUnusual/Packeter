# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Tkinter desktop GUI for Packeter."""

import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from .downloader import DownloadManager, JobStatus
from .logger import PacketerLogger
from .scriptgen import generate_sh, generate_bat

COLORS = {
    "bg": "#1a1d27",
    "surface": "#242836",
    "surface2": "#2e3348",
    "border": "#363b52",
    "text": "#e4e6f0",
    "dim": "#8b8fa8",
    "primary": "#6c8cff",
    "primary_hover": "#5a7af0",
    "success": "#4ade80",
    "error": "#f87171",
    "warning": "#fbbf24",
    "info": "#60a5fa",
    "log_bg": "#12141c",
}


class PacketerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Packeter")
        self.root.geometry("780x680")
        self.root.minsize(600, 520)
        self.root.configure(bg=COLORS["bg"])

        self._msg_queue: queue.Queue = queue.Queue()
        self._poll_interval = 50

        base_dir = Path(__file__).resolve().parent.parent
        self.manager = DownloadManager(base_dir / "output")
        self.logger = PacketerLogger(base_dir / "output")

        self._build_ui()
        self._poll_queue()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Surface.TFrame", background=COLORS["surface"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"],
                         font=("Segoe UI", 10))
        style.configure("Dim.TLabel", background=COLORS["bg"], foreground=COLORS["dim"],
                         font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=COLORS["bg"], foreground=COLORS["text"],
                         font=("Segoe UI", 13, "bold"))
        style.configure("Tag.TLabel", background=COLORS["surface2"],
                         foreground=COLORS["dim"], font=("Consolas", 8))

        style.configure("Primary.TButton", background=COLORS["primary"], foreground="#fff",
                         font=("Segoe UI", 10, "bold"), padding=(16, 6))
        style.map("Primary.TButton",
                   background=[("active", COLORS["primary_hover"]),
                               ("disabled", COLORS["surface2"])],
                   foreground=[("disabled", COLORS["dim"])])

        style.configure("Secondary.TButton", background=COLORS["surface2"],
                         foreground=COLORS["text"], font=("Segoe UI", 9, "bold"),
                         padding=(12, 6))
        style.map("Secondary.TButton",
                   background=[("active", COLORS["border"]),
                               ("disabled", COLORS["surface2"])],
                   foreground=[("disabled", COLORS["dim"])])

        style.configure("Browse.TButton", background=COLORS["surface2"],
                         foreground=COLORS["text"], font=("Segoe UI", 9), padding=(8, 4))
        style.map("Browse.TButton", background=[("active", COLORS["border"])])

        # --- Header ---
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=16, pady=(14, 4))
        ttk.Label(header, text="Packeter", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="Download packages for offline installation",
                  style="Dim.TLabel").pack(side="left", padx=(10, 0), pady=(3, 0))

        quit_btn = tk.Button(header, text="Quit", bg="#450a0a", fg="#fca5a5",
                              activebackground="#7f1d1d", activeforeground="#fca5a5",
                              font=("Segoe UI", 9, "bold"), relief="flat",
                              padx=12, pady=2, command=self._quit_app,
                              cursor="hand2")
        quit_btn.pack(side="right")

        # --- Input section ---
        input_frame = ttk.Frame(self.root)
        input_frame.pack(fill="x", padx=16, pady=(8, 4))

        # Source
        ttk.Label(input_frame, text="SOURCE").grid(row=0, column=0, sticky="w",
                                                     pady=(0, 3), columnspan=4)
        self.source_var = tk.StringVar()
        source_entry = tk.Entry(input_frame, textvariable=self.source_var,
                                bg=COLORS["surface"], fg=COLORS["text"],
                                insertbackground=COLORS["text"],
                                font=("Consolas", 10), relief="flat",
                                highlightthickness=1,
                                highlightbackground=COLORS["border"],
                                highlightcolor=COLORS["primary"])
        source_entry.grid(row=1, column=0, columnspan=4, sticky="ew", ipady=5, pady=(0, 8))
        source_entry.bind("<Return>", lambda e: self._start_download())

        # Output
        ttk.Label(input_frame, text="OUTPUT FOLDER").grid(row=2, column=0, sticky="w",
                                                            pady=(0, 3), columnspan=3)
        self.output_var = tk.StringVar(value=str(self.manager.output_dir))
        output_entry = tk.Entry(input_frame, textvariable=self.output_var,
                                bg=COLORS["surface"], fg=COLORS["text"],
                                insertbackground=COLORS["text"],
                                font=("Consolas", 10), relief="flat",
                                highlightthickness=1,
                                highlightbackground=COLORS["border"],
                                highlightcolor=COLORS["primary"])
        output_entry.grid(row=3, column=0, columnspan=2, sticky="ew", ipady=5, pady=(0, 8))

        browse_btn = ttk.Button(input_frame, text="Browse", style="Browse.TButton",
                                command=self._browse_output)
        browse_btn.grid(row=3, column=2, padx=(6, 0), pady=(0, 8))

        # Format selector + buttons row
        ttk.Label(input_frame, text="FORMAT").grid(row=4, column=0, sticky="w",
                                                     pady=(0, 3))
        self.format_var = tk.StringVar(value=".sh")
        format_frame = tk.Frame(input_frame, bg=COLORS["bg"])
        format_frame.grid(row=5, column=0, sticky="w", pady=(0, 8))

        self.sh_radio = tk.Radiobutton(
            format_frame, text=".sh (Linux/macOS)", variable=self.format_var,
            value=".sh", bg=COLORS["bg"], fg=COLORS["text"],
            selectcolor=COLORS["surface2"], activebackground=COLORS["bg"],
            activeforeground=COLORS["text"], font=("Segoe UI", 9),
            highlightthickness=0,
        )
        self.sh_radio.pack(side="left", padx=(0, 12))

        self.bat_radio = tk.Radiobutton(
            format_frame, text=".bat (Windows)", variable=self.format_var,
            value=".bat", bg=COLORS["bg"], fg=COLORS["text"],
            selectcolor=COLORS["surface2"], activebackground=COLORS["bg"],
            activeforeground=COLORS["text"], font=("Segoe UI", 9),
            highlightthickness=0,
        )
        self.bat_radio.pack(side="left")

        # Buttons
        btn_frame = tk.Frame(input_frame, bg=COLORS["bg"])
        btn_frame.grid(row=5, column=1, columnspan=3, sticky="e", pady=(0, 8))

        self.gen_btn = ttk.Button(btn_frame, text="Generate Install Script",
                                   style="Secondary.TButton",
                                   command=self._generate_script, state="disabled")
        self.gen_btn.pack(side="right", padx=(6, 0))

        dl_btn = ttk.Button(btn_frame, text="Download", style="Primary.TButton",
                            command=self._start_download)
        dl_btn.pack(side="right")

        input_frame.columnconfigure(0, weight=1)
        input_frame.columnconfigure(1, weight=1)

        # Tags
        tags_frame = ttk.Frame(self.root)
        tags_frame.pack(fill="x", padx=16, pady=(0, 8))
        for tag_text in ["git clone", "npm install", "pip install", "cargo install",
                         "winget install", "choco install", "go install", "gem install",
                         "docker pull", "composer", "apt download", "dnf download",
                         "wsl install", "curl | sh", "URL"]:
            lbl = ttk.Label(tags_frame, text=f" {tag_text} ", style="Tag.TLabel")
            lbl.pack(side="left", padx=(0, 3), pady=(0, 3))

        # --- Separator ---
        sep = tk.Frame(self.root, height=1, bg=COLORS["border"])
        sep.pack(fill="x", padx=16, pady=(4, 8))

        # --- Jobs header ---
        jobs_header = ttk.Frame(self.root)
        jobs_header.pack(fill="x", padx=16, pady=(0, 6))
        ttk.Label(jobs_header, text="Downloads", style="Dim.TLabel",
                  font=("Segoe UI", 10, "bold")).pack(side="left")

        # --- Scrollable jobs area ---
        container = tk.Frame(self.root, bg=COLORS["bg"])
        container.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        canvas = tk.Canvas(container, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.jobs_frame = tk.Frame(canvas, bg=COLORS["bg"])

        self.jobs_frame.bind("<Configure>",
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.jobs_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_linux_scroll_up(event):
            canvas.yview_scroll(-1, "units")

        def _on_linux_scroll_down(event):
            canvas.yview_scroll(1, "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", _on_linux_scroll_up)
        canvas.bind("<Button-5>", _on_linux_scroll_down)

        # Empty state
        self.empty_label = ttk.Label(self.jobs_frame,
                                      text="No downloads yet. Add a source above.",
                                      style="Dim.TLabel")
        self.empty_label.pack(pady=40)

        self._job_widgets: dict[str, dict] = {}
        self._job_count = 0

    def _browse_output(self):
        path = filedialog.askdirectory(initialdir=self.output_var.get())
        if path:
            self.output_var.set(path)
            self.manager.set_output_dir(Path(path))
            self.logger.set_output_dir(Path(path))

    def _quit_app(self):
        self.root.quit()
        self.root.destroy()

    def _start_download(self):
        source = self.source_var.get().strip()
        if not source:
            messagebox.showwarning("Packeter", "Please enter a source command or URL.")
            return

        output = self.output_var.get().strip()
        if output:
            self.manager.set_output_dir(Path(output))
            self.logger.set_output_dir(Path(output))

        self.logger.log_query(source)
        self.source_var.set("")
        self.empty_label.pack_forget()

        self.manager.add_job(source, self._emit_callback)

    def _generate_script(self):
        jobs = self.manager.get_successful_jobs()
        if not jobs:
            messagebox.showinfo("Packeter", "No successful downloads to generate a script for.")
            return

        output = Path(self.output_var.get().strip() or str(self.manager.output_dir))
        fmt = self.format_var.get()

        try:
            if fmt == ".sh":
                path = generate_sh(jobs, output)
            else:
                path = generate_bat(jobs, output)
            messagebox.showinfo("Packeter", f"Install script generated:\n{path}")
        except Exception as e:
            messagebox.showerror("Packeter", f"Failed to generate script:\n{e}")

    def _emit_callback(self, job_id: str, entry: dict):
        self._msg_queue.put((job_id, entry))

    def _poll_queue(self):
        while not self._msg_queue.empty():
            job_id, entry = self._msg_queue.get_nowait()
            self._handle_event(job_id, entry)
        self._check_gen_button()
        self.root.after(self._poll_interval, self._poll_queue)

    def _check_gen_button(self):
        jobs = self.manager.get_successful_jobs()
        if jobs:
            self.gen_btn.configure(state="normal")
        else:
            self.gen_btn.configure(state="disabled")

    def _handle_event(self, job_id: str, entry: dict):
        level = entry.get("level", "")
        message = entry.get("message", "")

        if level == "status":
            self._update_status(job_id, message)
            if message == "success":
                self._log_successful_download(job_id)
            return

        if job_id not in self._job_widgets:
            self._create_job_widget(job_id)

        widgets = self._job_widgets[job_id]
        log_text = widgets["log"]

        tag = level
        log_text.configure(state="normal")
        log_text.insert("end", message + "\n", tag)
        log_text.see("end")
        log_text.configure(state="disabled")

    def _create_job_widget(self, job_id: str):
        card = tk.Frame(self.jobs_frame, bg=COLORS["surface"],
                         highlightthickness=1, highlightbackground=COLORS["border"])
        card.pack(fill="x", pady=(0, 6))

        # Header row
        header = tk.Frame(card, bg=COLORS["surface"])
        header.pack(fill="x", padx=10, pady=(8, 2))

        id_label = tk.Label(header, text=job_id, bg=COLORS["surface"],
                             fg=COLORS["dim"], font=("Consolas", 9))
        id_label.pack(side="left")

        status_label = tk.Label(header, text="running", bg="#1e3a5f",
                                 fg=COLORS["info"], font=("Segoe UI", 8, "bold"),
                                 padx=8, pady=1)
        status_label.pack(side="right")

        # Source line
        job = self.manager.get_all_jobs()
        source_text = ""
        for j in job:
            if j.id == job_id:
                source_text = j.source
                break

        src_label = tk.Label(card, text=source_text, bg=COLORS["surface"],
                              fg=COLORS["text"], font=("Consolas", 9),
                              anchor="w", wraplength=700)
        src_label.pack(fill="x", padx=10, pady=(0, 4))

        # Log area
        log = tk.Text(card, bg=COLORS["log_bg"], fg=COLORS["text"],
                       font=("Consolas", 9), relief="flat", height=1,
                       state="disabled", wrap="word", padx=8, pady=6,
                       highlightthickness=1, highlightbackground=COLORS["border"])
        log.pack(fill="x", padx=10, pady=(0, 8))

        log.tag_configure("info", foreground=COLORS["info"])
        log.tag_configure("success", foreground=COLORS["success"])
        log.tag_configure("error", foreground=COLORS["error"])
        log.tag_configure("warning", foreground=COLORS["warning"])

        self._job_widgets[job_id] = {
            "card": card,
            "status": status_label,
            "log": log,
        }

    def _update_status(self, job_id: str, status: str):
        if job_id not in self._job_widgets:
            self._create_job_widget(job_id)

        widgets = self._job_widgets[job_id]
        status_label = widgets["status"]

        color_map = {
            "running": (COLORS["info"], "#1e3a5f"),
            "success": (COLORS["success"], "#14532d"),
            "failed": (COLORS["error"], "#450a0a"),
        }
        fg, bg = color_map.get(status, (COLORS["dim"], COLORS["surface2"]))
        status_label.configure(text=status, fg=fg, bg=bg)

    def _log_successful_download(self, job_id: str):
        job = None
        for j in self.manager.get_all_jobs():
            if j.id == job_id:
                job = j
                break
        if not job or not job.result:
            return

        result = job.result
        source = job.source
        filepath = result.get("path", "")

        if not filepath or not Path(filepath).exists():
            return

        p = Path(filepath)
        filename = p.name

        if p.is_dir():
            url = source
        else:
            url = source

        self.logger.log_download(url, filename, filepath)


def run():
    root = tk.Tk()
    PacketerGUI(root)
    root.mainloop()
