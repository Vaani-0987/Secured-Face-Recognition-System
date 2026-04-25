import os
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from tkinter import simpledialog
import json


_script_processes: dict[str, subprocess.Popen] = {}


def project_dir() -> str:
    return str(Path(__file__).resolve().parent)


def is_running(script_name: str) -> bool:
    proc = _script_processes.get(script_name)
    return proc is not None and proc.poll() is None


def run_script(script_name: str) -> None:
    try:
        if is_running(script_name):
            messagebox.showinfo("Already running", f"{script_name} is already running.")
            return

        _script_processes[script_name] = subprocess.Popen([sys.executable, script_name], cwd=project_dir())
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start {script_name}\n\n{e}")


def run_enroll_with_name() -> None:
    name = simpledialog.askstring("Enroll new person", "Enter new user name:")
    if name is None:
        return
    name = name.strip()
    if not name:
        messagebox.showerror("Invalid name", "Name cannot be empty.")
        return

    script_name = "enroll.py"
    try:
        if is_running(script_name):
            messagebox.showinfo("Already running", f"{script_name} is already running.")
            return
        _script_processes[script_name] = subprocess.Popen([sys.executable, script_name, name], cwd=project_dir())
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start {script_name}\n\n{e}")


def stop_script(script_name: str) -> None:
    proc = _script_processes.get(script_name)
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _pill(canvas: tk.Canvas, x: int, y: int, w: int, h: int, r: int, fill: str) -> None:
    # Rounded rectangle on a Canvas
    canvas.create_arc(x, y, x + 2 * r, y + 2 * r, start=90, extent=90, fill=fill, outline=fill)
    canvas.create_arc(x + w - 2 * r, y, x + w, y + 2 * r, start=0, extent=90, fill=fill, outline=fill)
    canvas.create_arc(x, y + h - 2 * r, x + 2 * r, y + h, start=180, extent=90, fill=fill, outline=fill)
    canvas.create_arc(
        x + w - 2 * r, y + h - 2 * r, x + w, y + h, start=270, extent=90, fill=fill, outline=fill
    )
    canvas.create_rectangle(x + r, y, x + w - r, y + h, fill=fill, outline=fill)
    canvas.create_rectangle(x, y + r, x + w, y + h - r, fill=fill, outline=fill)


def main() -> None:
    root = tk.Tk()
    root.title("Face Recognition")
    root.geometry("760x460")
    root.minsize(720, 440)

    # Make sure subprocesses start from this folder even if UI is launched elsewhere
    os.chdir(project_dir())

    # ---- Styling ----
    root.configure(bg="#0b1220")
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure("TFrame", background="#0b1220")
    style.configure("Card.TFrame", background="#121a2b")
    style.configure("TLabel", background="#0b1220", foreground="#e8eefc", font=("Segoe UI", 10))
    style.configure("Header.TLabel", background="#0b1220", foreground="#ffffff", font=("Segoe UI", 22, "bold"))
    style.configure("Subheader.TLabel", background="#0b1220", foreground="#b9c6e4", font=("Segoe UI", 11))
    style.configure("CardTitle.TLabel", background="#121a2b", foreground="#ffffff", font=("Segoe UI", 13, "bold"))
    style.configure("CardBody.TLabel", background="#121a2b", foreground="#c7d3ee", font=("Segoe UI", 10))

    style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), padding=(14, 10))
    style.map(
        "Primary.TButton",
        background=[("active", "#2563eb"), ("!disabled", "#1d4ed8")],
        foreground=[("!disabled", "#ffffff")],
    )

    style.configure("Secondary.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 9))
    style.map(
        "Secondary.TButton",
        background=[("active", "#334155"), ("!disabled", "#1f2937")],
        foreground=[("!disabled", "#ffffff")],
    )

    # ---- Header ----
    header = ttk.Frame(root)
    header.pack(fill="x", padx=28, pady=(22, 10))

    title = ttk.Label(header, text="Face Recognition Access Control", style="Header.TLabel")
    title.pack(anchor="w")

    subtitle = ttk.Label(
        header,
        text="Enroll users and run recognition with liveness + PIN verification.",
        style="Subheader.TLabel",
    )
    subtitle.pack(anchor="w", pady=(6, 0))

    # ---- Content (2 cards) ----
    container = ttk.Frame(root)
    container.pack(expand=True, fill="both", padx=28, pady=18)
    container.columnconfigure(0, weight=1, uniform="col")
    container.columnconfigure(1, weight=1, uniform="col")
    container.rowconfigure(0, weight=1)

    def make_card(parent: ttk.Frame, title_text: str, body_text: str) -> tuple[ttk.Frame, ttk.Label, ttk.Label, ttk.Frame]:
        card = ttk.Frame(parent, style="Card.TFrame")
        inner = ttk.Frame(card, style="Card.TFrame")
        inner.pack(fill="both", expand=True, padx=18, pady=16)

        t = ttk.Label(inner, text=title_text, style="CardTitle.TLabel")
        t.pack(anchor="w")
        b = ttk.Label(inner, text=body_text, style="CardBody.TLabel", wraplength=320, justify="left")
        b.pack(anchor="w", pady=(8, 0))

        controls = ttk.Frame(card, style="Card.TFrame")
        controls.pack(fill="x", padx=18, pady=(0, 16))
        return card, t, b, controls

    enroll_card, _, _, enroll_controls = make_card(
        container,
        "Enrollment",
        "Register a new authorized user. This opens the webcam, captures face images, and trains the model.",
    )
    enroll_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

    recog_card, _, _, recog_controls = make_card(
        container,
        "Recognition",
        "Start live recognition with liveness check + PIN. You’ll see Access Granted/Denied on the video window.",
    )
    recog_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

    def add_buttons(controls: ttk.Frame, start_text: str, start_cmd, stop_cmd) -> tuple[ttk.Button, ttk.Button, ttk.Label]:
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)
        start_btn = ttk.Button(controls, text=start_text, style="Primary.TButton", command=start_cmd)
        start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        stop_btn = ttk.Button(controls, text="Stop", style="Secondary.TButton", command=stop_cmd)
        stop_btn.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        status = ttk.Label(controls, text="Status: Stopped", style="CardBody.TLabel")
        status.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        return start_btn, stop_btn, status

    enroll_btn, enroll_stop, enroll_status = add_buttons(
        enroll_controls,
        "Enroll new person",
        run_enroll_with_name,
        lambda: stop_script("enroll.py"),
    )
    recog_btn, recog_stop, recog_status = add_buttons(
        recog_controls,
        "Start recognition",
        lambda: run_script("main.py"),
        lambda: stop_script("main.py"),
    )

    # ---- Footer ----
    footer = ttk.Frame(root)
    footer.pack(fill="x", padx=28, pady=(0, 18))

    hint = ttk.Label(
        footer,
        text="Tip: If the PIN dialog is hidden, use Alt+Tab to bring it forward.",
        style="Subheader.TLabel",
    )
    hint.pack(side="left")

    pill_canvas = tk.Canvas(footer, width=210, height=26, highlightthickness=0, bg="#0b1220")
    pill_canvas.pack(side="right")

    # ---- Show last Access Granted/Denied in the UI (written by access_control.py) ----
    last_decision = ttk.Label(recog_controls, text="Last decision: —", style="CardBody.TLabel")
    last_decision.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

    status_path = os.path.join(project_dir(), "data", "status.json")
    last_status_mtime: float | None = None

    def refresh_ui() -> None:
        nonlocal last_status_mtime
        enroll_running = is_running("enroll.py")
        recog_running = is_running("main.py")

        enroll_status.configure(text=f"Status: {'Running' if enroll_running else 'Stopped'}")
        recog_status.configure(text=f"Status: {'Running' if recog_running else 'Stopped'}")

        enroll_btn.configure(state=("disabled" if enroll_running else "normal"))
        recog_btn.configure(state=("disabled" if recog_running else "normal"))
        enroll_stop.configure(state=("normal" if enroll_running else "disabled"))
        recog_stop.configure(state=("normal" if recog_running else "disabled"))

        pill_canvas.delete("all")
        any_running = enroll_running or recog_running
        fill = "#16a34a" if any_running else "#334155"
        _pill(pill_canvas, 0, 0, 210, 26, 13, fill)
        pill_canvas.create_text(
            105,
            13,
            text=("● Running" if any_running else "● Idle"),
            fill="#ffffff",
            font=("Segoe UI", 10, "bold"),
        )

        try:
            mtime = os.path.getmtime(status_path)
            if last_status_mtime is None or mtime != last_status_mtime:
                last_status_mtime = mtime
                with open(status_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                decision = data.get("decision", "—")
                name = data.get("name", "")
                ts = data.get("timestamp", "")
                conf = data.get("confidence", None)
                conf_txt = f" (conf={conf})" if conf is not None else ""
                who = f"{name} - " if name else ""
                last_decision.configure(text=f"Last decision: {who}{decision}{conf_txt}  {ts}")
        except Exception:
            pass

        root.after(500, refresh_ui)

    refresh_ui()

    root.mainloop()


if __name__ == "__main__":
    main()

