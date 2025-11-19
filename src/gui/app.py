"""
PDF Compressor - Desktop Application
Compress PDFs in a local folder before uploading to file sharing platforms
"""

import logging
import os
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from ..compression import compress_pdf_file
from .path_validator import is_path_restricted


class GUILogHandler(logging.Handler):
    def __init__(self, log_callback):
        super().__init__()
        self.log_callback = log_callback

    def emit(self, record):
        msg = self.format(record)
        if record.levelno >= logging.WARNING:
            self.log_callback(msg, "red")


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    handlers=[logging.StreamHandler()],
)


class PDFCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Compressor")
        self.root.geometry("800x750")
        self.root.resizable(True, True)

        self.set_window_icon()

        self.folder_path = tk.StringVar()
        self.image_quality = tk.IntVar(value=90)
        self.max_dpi = tk.IntVar(value=250)
        self.is_processing = False
        self.cancel_requested = False

        self.setup_ui()

    def set_window_icon(self):
        try:
            if getattr(sys, 'frozen', False):
                base_path = Path(sys._MEIPASS)
            else:
                base_path = Path(__file__).parent.parent.parent

            icon_path = base_path / "assets" / "icon.png"

            if icon_path.exists():
                icon_image = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.root.iconphoto(True, icon_photo)
                self.icon_photo = icon_photo
        except Exception:
            pass

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))  # type:ignore

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)

        title_label = ttk.Label(
            main_frame, text="PDF Compressor", font=("Segoe UI", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding="10")
        folder_frame.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky=(tk.W, tk.E),  # type:ignore
            pady=(0, 15),  # type:ignore
        )

        ttk.Label(folder_frame, text="Select folder:").grid(
            row=0, column=0, sticky=tk.W
        )
        ttk.Entry(folder_frame, textvariable=self.folder_path, width=50).grid(
            row=1,
            column=0,
            sticky=(tk.W, tk.E),  # type:ignore
            padx=(0, 10),  # type:ignore
        )
        ttk.Button(folder_frame, text="Browse...", command=self.browse_folder).grid(
            row=1, column=1
        )

        ttk.Label(
            folder_frame,
            text="All PDFs >5MB in this folder and subdirectories will be compressed",
            font=("Segoe UI", 8),
            foreground="gray",
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        settings_frame = ttk.LabelFrame(
            main_frame, text="Compression Settings", padding="10"
        )
        settings_frame.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky=(tk.W, tk.E),  # type:ignore
            pady=(0, 15),  # type:ignore
        )

        ttk.Label(settings_frame, text="Image Quality (50-100):").grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5)
        )
        quality_frame = ttk.Frame(settings_frame)
        quality_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))  # type:ignore

        ttk.Scale(
            quality_frame,
            from_=50,
            to=100,
            variable=self.image_quality,
            orient=tk.HORIZONTAL,
            length=300,
            command=lambda v: self.image_quality.set(int(float(v) // 2 * 2)),
        ).grid(row=0, column=0, sticky=(tk.W, tk.E))  # type:ignore
        ttk.Label(quality_frame, textvariable=self.image_quality, width=4).grid(
            row=0, column=1, padx=(10, 0)
        )

        ttk.Label(
            settings_frame,
            text="Lower values = smaller files, lower quality (default: 90)",
            font=("Segoe UI", 8),
            foreground="gray",
        ).grid(row=2, column=0, sticky=tk.W, pady=(0, 15))

        ttk.Label(settings_frame, text="Max DPI (50-600):").grid(
            row=3, column=0, sticky=tk.W, pady=(0, 5)
        )
        dpi_frame = ttk.Frame(settings_frame)
        dpi_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))  # type:ignore

        ttk.Scale(
            dpi_frame,
            from_=50,
            to=600,
            variable=self.max_dpi,
            orient=tk.HORIZONTAL,
            length=300,
            command=lambda v: self.max_dpi.set(int(float(v) // 10 * 10)),
        ).grid(row=0, column=0, sticky=(tk.W, tk.E))  # type:ignore
        ttk.Label(dpi_frame, textvariable=self.max_dpi, width=4).grid(
            row=0, column=1, padx=(10, 0)
        )

        ttk.Label(
            settings_frame,
            text="Lower DPI = smaller files, may affect print quality (default: 250)",
            font=("Segoe UI", 8),
            foreground="gray",
        ).grid(row=5, column=0, sticky=tk.W)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(0, 15))

        self.compress_button = ttk.Button(
            button_frame,
            text="Compress PDFs",
            command=self.start_compression,
            style="Accent.TButton",
        )
        self.compress_button.grid(row=0, column=0, padx=(0, 10))

        self.cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel_compression,
            state=tk.DISABLED,
        )
        self.cancel_button.grid(row=0, column=1)

        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky=(tk.W, tk.E, tk.N, tk.S),  # type:ignore
        )
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(1, weight=1)

        self.progress_bar = ttk.Progressbar(
            progress_frame, mode="determinate", length=640
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))  # type:ignore

        self.status_text = tk.Text(
            progress_frame,
            height=18,
            width=85,
            state=tk.DISABLED,
            font=("Consolas", 10),
            wrap=tk.WORD,
        )
        self.status_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))  # type:ignore

        scrollbar = ttk.Scrollbar(
            progress_frame, orient=tk.VERTICAL, command=self.status_text.yview
        )
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))  # type:ignore
        self.status_text.configure(yscrollcommand=scrollbar.set)

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select folder to compress PDFs")
        if folder:
            self.folder_path.set(folder)

    def log(self, message, color=None):
        self.status_text.configure(state=tk.NORMAL)
        if color:
            tag_name = f"color_{color}"
            self.status_text.tag_config(tag_name, foreground=color)
            self.status_text.insert(tk.END, f"{message}\n", tag_name)
        else:
            self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.status_text.configure(state=tk.DISABLED)
        self.root.update()

    def cancel_compression(self):
        if self.is_processing:
            self.cancel_requested = True
            self.log("Cancellation requested... stopping after current file", "orange")
            self.cancel_button.configure(state=tk.DISABLED)

    def start_compression(self):
        if self.is_processing:
            messagebox.showwarning(
                "Already Processing", "Compression is already running"
            )
            return

        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Invalid Folder", "Please select a valid folder")
            return

        is_restricted, restriction_msg = is_path_restricted(folder)
        if is_restricted:
            messagebox.showerror("Restricted Path", restriction_msg)
            return

        self.is_processing = True
        self.cancel_requested = False
        self.compress_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        self.status_text.configure(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.configure(state=tk.DISABLED)
        self.progress_bar["value"] = 0

        thread = threading.Thread(target=self.compress_pdfs, daemon=True)
        thread.start()

    def compress_pdfs(self):
        gui_handler = GUILogHandler(self.log)
        pdf_logger = logging.getLogger("pdf_compress")
        pdf_logger.addHandler(gui_handler)

        try:
            folder = Path(self.folder_path.get())
            image_quality = self.image_quality.get()
            max_dpi = self.max_dpi.get()

            self.log("Scanning for PDFs >5MB...")

            try:
                import pyvips

                self.log(
                    f"✓ Using pyvips {pyvips.__version__} for fast image processing",
                    "green",
                )
            except Exception as e:
                self.log(f"✗ pyvips not available: {e}", "red")

            self.log("")

            pdf_files = []
            for pdf_path in folder.rglob("*.pdf"):
                if pdf_path.is_file():
                    size = pdf_path.stat().st_size
                    if size > 5 * 1024 * 1024:
                        pdf_files.append((pdf_path, size))

            total_files = len(pdf_files)

            if total_files == 0:
                self.log("No PDF files >5MB found in the selected folder", "orange")
                return

            self.log(f"Found {total_files} PDFs to compress\n")
            self.log(f"Settings: Quality={image_quality}, Max DPI={max_dpi}\n")

            compressed_count = 0
            skipped_count = 0
            total_original_size = 0
            total_compressed_size = 0
            total_time = 0

            for idx, (pdf_path, original_size) in enumerate(pdf_files, 1):
                if self.cancel_requested:
                    self.log(
                        f"\nCancelled by user. Processed {idx - 1}/{total_files} files.",
                        "red",
                    )
                    break

                try:
                    self.log(f"[{idx}/{total_files}] Processing: {pdf_path.name}")
                    start_time = time.time()

                    temp_output = pdf_path.parent / f"_compressed_{pdf_path.name}"

                    compress_pdf_file(
                        str(pdf_path),
                        str(temp_output),
                        image_quality=image_quality,
                        max_dpi=max_dpi,
                    )

                    elapsed = time.time() - start_time
                    total_time += elapsed

                    if temp_output.exists():
                        compressed_size = temp_output.stat().st_size

                        if compressed_size < original_size:
                            temp_output.replace(pdf_path)
                            reduction = (1 - compressed_size / original_size) * 100
                            self.log(
                                f"  ✓ Compressed: {original_size / 1024 / 1024:.1f}MB → "
                                f"{compressed_size / 1024 / 1024:.1f}MB ({reduction:.1f}% reduction) "
                                f"in {elapsed:.1f}s",
                                "green",
                            )
                            compressed_count += 1
                            total_original_size += original_size
                            total_compressed_size += compressed_size
                        else:
                            temp_output.unlink()
                            self.log(f"  - Skipped: No size reduction ({elapsed:.1f}s)")
                            skipped_count += 1
                            total_original_size += original_size
                            total_compressed_size += original_size
                    else:
                        self.log("  ✗ Failed: Output file not created", "red")
                        skipped_count += 1
                        total_original_size += original_size
                        total_compressed_size += original_size

                except Exception as e:
                    self.log(f"  ✗ Error: {str(e)}", "red")
                    skipped_count += 1
                    total_original_size += original_size
                    total_compressed_size += original_size

                progress = (idx / total_files) * 100
                self.progress_bar["value"] = progress
                self.root.update()

            if not self.cancel_requested:
                self.progress_bar["value"] = 100

            total_reduction = 0
            if total_original_size > 0:
                total_reduction = (
                    1 - total_compressed_size / total_original_size
                ) * 100

            self.log("\n" + "=" * 70)
            status_title = (
                "COMPRESSION CANCELLED"
                if self.cancel_requested
                else "COMPRESSION COMPLETE"
            )
            self.log(status_title)
            self.log("=" * 70)
            self.log(
                f"Total files processed: {compressed_count + skipped_count}/{total_files}"
            )
            self.log(f"Compressed: {compressed_count} files")
            self.log(f"Skipped (no reduction): {skipped_count} files")
            if total_original_size > 0:
                self.log(
                    f"Total size: {total_original_size / 1024 / 1024:.1f}MB → "
                    f"{total_compressed_size / 1024 / 1024:.1f}MB ({total_reduction:.1f}% reduction)"
                )
            if total_time > 0 and (compressed_count + skipped_count) > 0:
                self.log(f"Total time: {total_time:.1f}s")
                self.log(
                    f"Average per file: {total_time / (compressed_count + skipped_count):.1f}s"
                )

            if not self.cancel_requested:
                messagebox.showinfo(
                    "Compression Complete",
                    f"Compressed {compressed_count} files\n"
                    f"{total_original_size / 1024 / 1024:.1f}MB → "
                    f"{total_compressed_size / 1024 / 1024:.1f}MB "
                    f"({total_reduction:.1f}% reduction)",
                )

        except Exception as e:
            self.log(f"\n✗ Fatal error: {str(e)}", "red")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")

        finally:
            pdf_logger.removeHandler(gui_handler)
            self.is_processing = False
            self.cancel_requested = False
            self.compress_button.configure(state=tk.NORMAL)
            self.cancel_button.configure(state=tk.DISABLED)


def main():
    root = tk.Tk()
    PDFCompressorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
