"""Single-window Tk front end for the image converter.

``launch_gui()`` builds one window where the user picks images (individual
files or a whole folder), an output folder, and a target format, then converts.
When finished a summary dialog reports how many images were converted, where
they were saved, and how many were skipped (and why).
"""

import os
import queue
import threading
from pathlib import Path
from tkinter import (
    Tk, Label, Button, Frame, StringVar, BooleanVar,
    filedialog, messagebox, ttk,
)

from custom_modules.constants import COMMON_TARGET_EXTS, INPUT_FILETYPES
from custom_modules.converter import convert_path


def launch_gui(_on_ready=None):
    """Open the converter window and run until closed.

    ``_on_ready`` is a test-only hook: if given, it is scheduled once the window
    is built and receives a namespace exposing ``root``, ``selection``,
    ``set_format(ext)`` and ``start()`` so the flow can be driven headlessly.
    """
    root = Tk()
    root.title("Image Converter")
    root.geometry("560x340")
    root.resizable(False, False)

    # --- state shared between callbacks -------------------------------------
    mode = StringVar(value="files")          # "files" or "folder"
    recursive = BooleanVar(value=False)
    status = StringVar(value="Choose images, an output folder and a format.")
    selection = {"input": None, "output": None}  # input: list[str] | str | None

    ev_queue: "queue.Queue" = queue.Queue()

    pad = {"padx": 10, "pady": 6}

    # --- mode row -----------------------------------------------------------
    mode_frame = Frame(root)
    mode_frame.grid(row=0, column=0, columnspan=3, sticky="w", **pad)
    Label(mode_frame, text="Convert:").pack(side="left")
    ttk.Radiobutton(mode_frame, text="Individual images", variable=mode,
                    value="files", command=lambda: _on_mode_change()).pack(side="left", padx=6)
    ttk.Radiobutton(mode_frame, text="A folder", variable=mode,
                    value="folder", command=lambda: _on_mode_change()).pack(side="left", padx=6)
    recursive_chk = ttk.Checkbutton(mode_frame, text="include sub-folders",
                                    variable=recursive)

    # --- input row ----------------------------------------------------------
    input_btn = Button(root, width=22, command=lambda: _pick_input())
    input_btn.grid(row=1, column=0, sticky="w", **pad)
    input_lbl = Label(root, text="No images selected", anchor="w", fg="gray")
    input_lbl.grid(row=1, column=1, columnspan=2, sticky="w", **pad)

    # --- output row ---------------------------------------------------------
    Button(root, text="Choose output folder...", width=22,
           command=lambda: _pick_output()).grid(row=2, column=0, sticky="w", **pad)
    output_lbl = Label(root, text="(defaults to the input location)",
                       anchor="w", fg="gray")
    output_lbl.grid(row=2, column=1, columnspan=2, sticky="w", **pad)

    # --- format row ---------------------------------------------------------
    Label(root, text="Convert to:").grid(row=3, column=0, sticky="w", **pad)
    fmt_cb = ttk.Combobox(root, values=list(COMMON_TARGET_EXTS),
                          state="readonly", width=12)
    fmt_cb.grid(row=3, column=1, sticky="w", **pad)
    fmt_cb.current(0)

    # --- convert + status ---------------------------------------------------
    convert_btn = Button(root, text="Convert", width=20, height=2,
                         command=lambda: _start_convert())
    convert_btn.grid(row=4, column=0, columnspan=3, pady=14)

    progress = ttk.Progressbar(root, mode="indeterminate", length=520)
    progress.grid(row=5, column=0, columnspan=3, padx=10)
    progress.grid_remove()

    status_lbl = Label(root, textvariable=status, anchor="w", fg="gray",
                       wraplength=520, justify="left")
    status_lbl.grid(row=6, column=0, columnspan=3, sticky="w", **pad)

    # --- callbacks ----------------------------------------------------------
    def _on_mode_change():
        selection["input"] = None
        if mode.get() == "files":
            input_btn.config(text="Choose images...")
            input_lbl.config(text="No images selected")
            recursive_chk.pack_forget()
        else:
            input_btn.config(text="Choose folder...")
            input_lbl.config(text="No folder selected")
            recursive_chk.pack(side="left", padx=12)

    def _pick_input():
        if mode.get() == "files":
            paths = filedialog.askopenfilenames(
                title="Select images to convert...", filetypes=INPUT_FILETYPES)
            if paths:
                selection["input"] = list(paths)
                input_lbl.config(text=f"{len(paths)} image(s) selected", fg="black")
        else:
            folder = filedialog.askdirectory(title="Select input folder...")
            if folder:
                selection["input"] = folder
                input_lbl.config(text=os.path.basename(folder) or folder, fg="black")

    def _pick_output():
        folder = filedialog.askdirectory(title="Select output folder...")
        if folder:
            selection["output"] = folder
            output_lbl.config(text=os.path.basename(folder) or folder, fg="black")

    def _default_output():
        inp = selection["input"]
        if isinstance(inp, list):
            return str(Path(inp[0]).parent) if inp else None
        if inp:
            p = Path(inp)
            return str(p if p.is_dir() else p.parent)
        return None

    def _start_convert():
        inp = selection["input"]
        if not inp:
            messagebox.showwarning("Nothing selected",
                                   "Please choose the image(s) or folder to convert.")
            return
        out = selection["output"] or _default_output()
        if not out:
            messagebox.showwarning("No output folder",
                                   "Please choose an output folder.")
            return

        # Read all Tk variables here on the main thread; the worker thread must
        # not touch Tk. Remember the format actually used so the summary is
        # correct even if the dropdown is changed mid-run.
        ext = fmt_cb.get()
        rec = recursive.get()
        run["ext"] = ext
        convert_btn.config(state="disabled")
        fmt_cb.config(state="disabled")
        progress.grid()
        progress.start(12)
        status.set("Converting...")

        def worker():
            try:
                report = convert_path(
                    inp, out, ext,
                    recursive=rec,
                    on_event=lambda kind, r: ev_queue.put(("progress", r)),
                )
                ev_queue.put(("done", report))
            except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
                ev_queue.put(("error", exc))

        threading.Thread(target=worker, daemon=True).start()
        root.after(100, _poll)

    done = {"n": 0}
    run = {"ext": ""}

    def _poll():
        finished = None
        try:
            while True:
                kind, payload = ev_queue.get_nowait()
                if kind == "progress":
                    done["n"] += 1
                    status.set(f"Converting... {done['n']} file(s) processed")
                else:
                    finished = (kind, payload)
        except queue.Empty:
            pass

        if finished is None:
            root.after(100, _poll)
            return

        progress.stop()
        progress.grid_remove()
        convert_btn.config(state="normal")
        fmt_cb.config(state="readonly")
        done["n"] = 0
        kind, payload = finished
        if kind == "error":
            status.set("Error.")
            messagebox.showerror("Conversion failed", str(payload))
        else:
            _show_summary(payload, run["ext"])
            status.set("Done. Ready for another conversion.")

    def _show_summary(report, ext):
        lines = [f"Converted: {report.converted} image(s)"]
        if report.converted and report.output_dir is not None:
            lines.append(f"Saved to: {report.output_dir}")
        lines.append("")
        lines.append(f"Skipped - can't convert to .{ext}: {report.skipped_incompatible}")
        lines.append(f"Skipped - not images: {report.skipped_not_image}")
        messagebox.showinfo("Conversion complete", "\n".join(lines))

    _on_mode_change()
    root.protocol("WM_DELETE_WINDOW", root.quit)

    if _on_ready is not None:
        from types import SimpleNamespace
        ctx = SimpleNamespace(
            root=root,
            selection=selection,
            set_format=lambda e: fmt_cb.set(e),
            start=_start_convert,
        )
        root.after(0, lambda: _on_ready(ctx))

    root.mainloop()
    try:
        root.destroy()
    except Exception:
        pass
