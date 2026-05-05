"""
transcribe_gui.py — 本地音频/视频文件 → 字幕文本
依赖: pip install groq
需要: ffmpeg 在系统 PATH 中
"""

import json
import math
import os
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from queue import Empty, Queue
from tkinter import filedialog, messagebox, ttk

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "transcribe_config.json")
MODEL = "whisper-large-v3-turbo"
MAX_CHUNK_BYTES = 20 * 1024 * 1024

LANGUAGES = {
    "自动检测": "",
    "中文": "zh",
    "英文": "en",
    "日文": "ja",
    "韩文": "ko",
    "法文": "fr",
    "德文": "de",
    "西班牙文": "es",
}

SUPPORTED_EXTS = (
    ".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".flac",
    ".webm", ".mkv", ".avi", ".mov", ".mpeg", ".mpga",
)


def load_config():
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def win_flags():
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


class TranscribeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("字幕提取工具")
        self.root.geometry("760x580")
        self.root.minsize(640, 500)

        self.cfg = load_config()
        self.queue = Queue()
        self.worker_thread = None

        self._setup_theme()
        self._build_vars()
        self._build_ui()
        self._poll_queue()

    def _setup_theme(self):
        style = ttk.Style()
        for preferred in ("vista", "xpnative", "winnative"):
            if preferred in style.theme_names():
                style.theme_use(preferred)
                break
        style.configure("Hint.TLabel", foreground="#666666")

    def _build_vars(self):
        self.file_var = tk.StringVar()
        self.api_key_var = tk.StringVar(value=self.cfg.get("api_key", ""))
        self.output_dir_var = tk.StringVar(
            value=self.cfg.get("output_dir", str(Path.home() / "Downloads"))
        )
        self.language_var = tk.StringVar(value=self.cfg.get("language", "自动检测"))
        self.show_key_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="就绪")

    def _build_ui(self):
        root_frame = ttk.Frame(self.root, padding=10)
        root_frame.pack(fill="both", expand=True)
        root_frame.columnconfigure(0, weight=1)
        root_frame.rowconfigure(2, weight=1)

        # ── 设置区 ──
        settings = ttk.LabelFrame(root_frame, text="设置", padding=10)
        settings.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Groq API Key").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        key_row = ttk.Frame(settings)
        key_row.grid(row=0, column=1, sticky="ew", pady=3)
        key_row.columnconfigure(0, weight=1)
        self.key_entry = ttk.Entry(key_row, textvariable=self.api_key_var, show="•")
        self.key_entry.grid(row=0, column=0, sticky="ew")
        ttk.Checkbutton(key_row, text="显示", variable=self.show_key_var,
                        command=self._toggle_key).grid(row=0, column=1, padx=(6, 0))
        ttk.Label(settings, text="console.groq.com/keys 免费申请",
                  style="Hint.TLabel").grid(row=0, column=2, padx=(8, 0), pady=3)

        ttk.Label(settings, text="输出目录").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(settings, textvariable=self.output_dir_var).grid(
            row=1, column=1, sticky="ew", pady=3)
        ttk.Button(settings, text="选择",
                   command=lambda: self._pick_dir(self.output_dir_var)).grid(
            row=1, column=2, padx=(8, 0), pady=3)

        lang_row = ttk.Frame(settings)
        lang_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(3, 0))
        ttk.Label(lang_row, text="语言").pack(side="left")
        ttk.Combobox(lang_row, textvariable=self.language_var, state="readonly",
                     values=list(LANGUAGES.keys()), width=12).pack(side="left", padx=(8, 0))
        ttk.Label(lang_row, text="不确定时选自动检测",
                  style="Hint.TLabel").pack(side="left", padx=(8, 0))
        ttk.Button(lang_row, text="保存设置",
                   command=self._save_settings).pack(side="right")

        # ── 文件区 ──
        file_block = ttk.LabelFrame(root_frame, text="文件", padding=10)
        file_block.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        file_block.columnconfigure(0, weight=1)

        file_row = ttk.Frame(file_block)
        file_row.grid(row=0, column=0, sticky="ew")
        file_row.columnconfigure(0, weight=1)
        ttk.Entry(file_row, textvariable=self.file_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(file_row, text="选择文件",
                   command=self._pick_file).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(file_block,
                  text="支持 mp3 / mp4 / wav / m4a / mkv / webm 等格式",
                  style="Hint.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))

        # ── 按钮行（固定，不伸缩）──
        btn_frame = ttk.Frame(file_block)
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        ttk.Button(btn_frame, text="开始转录", command=self.start).pack(side="left")
        ttk.Button(btn_frame, text="停止", command=self.stop).pack(side="left", padx=(8, 0))
        ttk.Button(btn_frame, text="打开输出目录",
                   command=self.open_output_dir).pack(side="left", padx=(8, 0))
        ttk.Label(btn_frame, textvariable=self.status_var).pack(side="right")
        self.progress = ttk.Progressbar(btn_frame, mode="indeterminate", length=130)
        self.progress.pack(side="right", padx=(0, 8))

        # ── 日志区（伸缩）──
        log_frame = ttk.LabelFrame(root_frame, text="日志", padding=(8, 4))
        log_frame.grid(row=2, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log = tk.Text(log_frame, wrap="word", state="disabled",
                           relief="solid", borderwidth=1,
                           bg="#ffffff", font=("Consolas", 10))
        self.log.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(log_frame, command=self.log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.log.config(yscrollcommand=sb.set)

    def _toggle_key(self):
        self.key_entry.config(show="" if self.show_key_var.get() else "•")

    def _pick_dir(self, var):
        path = filedialog.askdirectory(initialdir=var.get() or str(Path.home()))
        if path:
            var.set(path)

    def _pick_file(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_EXTS)
        path = filedialog.askopenfilename(
            filetypes=[("音频/视频文件", exts), ("所有文件", "*.*")]
        )
        if path:
            self.file_var.set(path)

    def _save_settings(self):
        self.cfg["api_key"] = self.api_key_var.get().strip()
        self.cfg["output_dir"] = self.output_dir_var.get().strip()
        self.cfg["language"] = self.language_var.get()
        save_config(self.cfg)
        self._log("设置已保存\n")

    def _log(self, text, reset=False):
        self.log.config(state="normal")
        if reset:
            self.log.delete("1.0", tk.END)
        if text:
            self.log.insert(tk.END, text)
            self.log.see(tk.END)
        self.log.config(state="disabled")

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "done":
                    self.progress.stop()
                    self.status_var.set("完成" if payload["ok"] else "失败")
                elif kind == "error":
                    self.progress.stop()
                    self.status_var.set("失败")
                    self._log(f"[错误] {payload}\n")
        except Empty:
            pass
        self.root.after(100, self._poll_queue)

    def start(self):
        file_path = self.file_var.get().strip()
        api_key = self.api_key_var.get().strip()
        output_dir = self.output_dir_var.get().strip()

        if not file_path:
            messagebox.showwarning("提示", "请先选择文件")
            return
        if not os.path.isfile(file_path):
            messagebox.showwarning("提示", f"文件不存在:\n{file_path}")
            return
        if not api_key:
            messagebox.showwarning("提示", "请填写 Groq API Key")
            return
        if not output_dir:
            messagebox.showwarning("提示", "请选择输出目录")
            return
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("提示", "当前已有任务在运行")
            return

        language_code = LANGUAGES[self.language_var.get()]
        os.makedirs(output_dir, exist_ok=True)

        self._log("", reset=True)
        self.status_var.set("运行中")
        self.progress.start(10)

        self.worker_thread = threading.Thread(
            target=self._worker,
            args=(file_path, api_key, output_dir, language_code),
            daemon=True,
        )
        self.worker_thread.start()

    def stop(self):
        self._log("[已请求停止，将在当前段完成后退出]\n")
        self.status_var.set("停止中...")

    def open_output_dir(self):
        path = self.output_dir_var.get().strip()
        if path and os.path.isdir(path):
            os.startfile(path)

    def _extract_audio(self, input_path: str, output_path: str):
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vn", "-ar", "16000", "-ac", "1", "-b:a", "64k",
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True,
                                creationflags=win_flags())
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg 转换失败:\n{result.stderr[-500:]}")

    def _split_audio(self, mp3_path: str, tmpdir: str) -> list:
        file_size = os.path.getsize(mp3_path)
        if file_size <= MAX_CHUNK_BYTES:
            return [mp3_path]

        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", mp3_path],
            capture_output=True, text=True, creationflags=win_flags()
        )
        total_seconds = float(result.stdout.strip())
        n_chunks = math.ceil(file_size / MAX_CHUNK_BYTES)
        chunk_duration = total_seconds / n_chunks
        self.queue.put(("log", f"文件较大，分为 {n_chunks} 段处理...\n"))

        chunks = []
        for i in range(n_chunks):
            start = i * chunk_duration
            chunk_path = os.path.join(tmpdir, f"chunk_{i:03d}.mp3")
            subprocess.run(
                ["ffmpeg", "-y", "-ss", str(start), "-t", str(chunk_duration),
                 "-i", mp3_path, "-acodec", "copy", chunk_path],
                capture_output=True, creationflags=win_flags()
            )
            if os.path.exists(chunk_path):
                chunks.append(chunk_path)
        return chunks

    def _worker(self, file_path, api_key, output_dir, language_code):
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            stem = Path(file_path).stem

            with tempfile.TemporaryDirectory() as tmpdir:
                self.queue.put(("log", f"处理文件: {file_path}\n"))
                mp3_path = os.path.join(tmpdir, "audio.mp3")
                self._extract_audio(file_path, mp3_path)
                size_mb = os.path.getsize(mp3_path) / 1024 / 1024
                self.queue.put(("log", f"音频准备完成 ({size_mb:.1f} MB)\n"))

                chunks = self._split_audio(mp3_path, tmpdir)
                texts = []

                for i, chunk in enumerate(chunks):
                    if len(chunks) > 1:
                        self.queue.put(("log", f"转录第 {i+1}/{len(chunks)} 段...\n"))
                    else:
                        self.queue.put(("log", "正在转录，请稍候...\n"))

                    with open(chunk, "rb") as f:
                        kwargs = {
                            "file": f,
                            "model": MODEL,
                            "response_format": "text",
                            "temperature": 0.0,
                        }
                        if language_code:
                            kwargs["language"] = language_code
                        result = client.audio.transcriptions.create(**kwargs)
                    texts.append(result)

                full_text = "\n".join(texts)

            safe_stem = "".join(c for c in stem if c not in r'\/:*?"<>|').strip()
            out_path = Path(output_dir) / (safe_stem + ".txt")
            out_path.write_text(full_text, encoding="utf-8")

            self.queue.put(("log", f"\n完成！字幕已保存: {out_path}\n共 {len(full_text)} 字符\n"))
            self.queue.put(("done", {"ok": True}))

        except Exception as e:
            self.queue.put(("error", str(e)))
            self.queue.put(("done", {"ok": False}))


def main():
    root = tk.Tk()
    TranscribeGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
