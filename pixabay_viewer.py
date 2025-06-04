import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
from io import BytesIO
import requests
from PIL import Image, ImageTk
from dotenv import load_dotenv
import pyperclip
import threading
from pathlib import Path
from typing import Dict, Any


class Translator:
    def __init__(self, language: str = "en"):
        self.language = language
        self.translations: Dict[str, Any] = {}
        self.load_translations()

    def load_translations(self):
        """Load translations from JSON files in the translations directory"""
        try:
            trans_file = (
                Path(__file__).parent / "translations" / f"{self.language}.json"
            )
            with open(trans_file, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
        except Exception as e:
            print(f"Error loading translations: {e}")
            # Fallback to English if there's an error
            if self.language != "en":
                self.language = "en"
                self.load_translations()

    def get(self, key: str, **kwargs) -> str:
        """Get a translated string with optional formatting"""
        try:
            # Handle nested keys (e.g., 'error.api_error')
            keys = key.split(".")
            value = self.translations
            for k in keys:
                value = value[k]

            if isinstance(value, str) and kwargs:
                return value.format(**kwargs)
            return str(value)
        except (KeyError, AttributeError):
            return key  # Return the key if translation not found


class PixabayViewer:
    def __init__(self, root):
        self.root = root
        # Initialize translator with default language (English)
        self.translator = Translator("en")
        self.root.title(self.translator.get("app_title"))

        # Set window to fullscreen
        self.root.state("zoomed")  # Maximize window
        self.root.minsize(1200, 800)  # Minimum size

        # Set window icon if available
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass

        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv("PIXABAY_API_KEY")
        if not self.api_key:
            messagebox.showerror("Error", "PIXABAY_API_KEY not found in .env file")
            return

        self.setup_ui()
        self.images = []
        self.photo_references = []  # To prevent garbage collection
        self.stop_request = False  # Flag to stop ongoing requests
        self.current_page = 1
        self.total_pages = 1
        self.current_query = ""
        self.per_page = (
            24  # Number of images per page (divisible by 4 for 4-column layout)
        )
        self.columns = 4  # Number of columns in the grid

    def setup_ui(self):
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Create menu bar
        self.menubar = tk.Menu(self.root)

        # Language menu
        language_menu = tk.Menu(self.menubar, tearoff=0)
        language_menu.add_command(
            label=self.translator.get("menu.english"),
            command=lambda: self.change_language("en"),
        )
        language_menu.add_command(
            label=self.translator.get("menu.italian"),
            command=lambda: self.change_language("it"),
        )
        self.menubar.add_cascade(
            label=self.translator.get("menu.language"), menu=language_menu
        )
        self.root.config(menu=self.menubar)

        # Search frame
        search_frame = ttk.Frame(main_container, padding="10")
        search_frame.pack(fill=tk.X)

        self.search_label = ttk.Label(
            search_frame, text=self.translator.get("search_label")
        )
        self.search_label.pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            search_frame, textvariable=self.search_var, width=50
        )
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<Return>", lambda e: self.search_images())

        self.search_btn = ttk.Button(
            search_frame,
            text=self.translator.get("search_button"),
            command=self.search_images,
        )
        self.search_btn.pack(side=tk.LEFT, padx=5)

        # Stop button (initially hidden)
        self.stop_btn = ttk.Button(
            search_frame,
            text=self.translator.get("stop_button"),
            command=self.stop_search,
            style="Accent.TButton",
        )

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Progress bar
        self.progress = ttk.Progressbar(
            self.root, orient=tk.HORIZONTAL, length=100, mode="indeterminate"
        )

        # Configure styles
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="red")

        # Canvas with scrollbar
        self.canvas = tk.Canvas(main_container)
        self.scrollbar = ttk.Scrollbar(
            main_container, orient="vertical", command=self.canvas.yview
        )
        self.scrollable_frame = ttk.Frame(self.canvas)

        # Pagination frame (initially hidden)
        self.pagination_frame = ttk.Frame(main_container, padding="5")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def update_status(self, message_key, **kwargs):
        """Update status bar with translated message"""
        try:
            if isinstance(message_key, str):
                # Handle loading image status with current/total
                if message_key.startswith("loading_image_"):
                    try:
                        _, current, total = message_key.split("_")
                        message = self.translator.get("loading_image").format(
                            current=current, total=total
                        )
                    except (ValueError, KeyError):
                        message = self.translator.get("loading_image_default")
                # Handle fetching page status
                elif message_key == "fetching_page" and "page" in kwargs:
                    message = self.translator.get("fetching_page").format(
                        page=kwargs["page"]
                    )
                # Default case
                else:
                    message = self.translator.get(message_key, **kwargs)
            else:
                message = str(message_key)
            self.status_var.set(message)
            self.root.update_idletasks()
        except Exception as e:
            print(f"Error updating status: {e}")

    def change_language(self, lang_code):
        """Change application language"""
        if self.translator.language != lang_code:
            self.translator = Translator(lang_code)
            self.root.title(self.translator.get("app_title"))
            self.search_btn.config(text=self.translator.get("search_button"))
            self.stop_btn.config(text=self.translator.get("stop_button"))
            self.retranslate_ui()

    def update_pagination_controls(self):
        """Update pagination controls with current page and language"""
        if not hasattr(self, "pagination_frame"):
            return

        # Clear existing controls
        for widget in self.pagination_frame.winfo_children():
            widget.destroy()

        if self.total_pages <= 1:
            return

        # Previous button
        prev_btn = ttk.Button(
            self.pagination_frame,
            text=self.translator.get("previous_button"),
            command=lambda: self._perform_search(
                self.current_query, max(1, self.current_page - 1)
            ),
            state="disabled" if self.current_page == 1 else "normal",
        )
        prev_btn.pack(side=tk.LEFT, padx=5)

        # Page info
        page_info = ttk.Label(
            self.pagination_frame,
            text=self.translator.get(
                "page_info", current=self.current_page, total=self.total_pages
            ),
        )
        page_info.pack(side=tk.LEFT, padx=10)

        # Next button
        next_btn = ttk.Button(
            self.pagination_frame,
            text=self.translator.get("next_button"),
            command=lambda: self._perform_search(
                self.current_query, min(self.total_pages, self.current_page + 1)
            ),
            state="disabled" if self.current_page >= self.total_pages else "normal",
        )
        next_btn.pack(side=tk.LEFT, padx=5)

        self.pagination_frame.pack(fill=tk.X, pady=5)

    def retranslate_ui(self):
        """Retranslate all UI elements"""
        # Update window title
        self.root.title(self.translator.get("app_title"))

        # Update search UI
        if hasattr(self, "search_btn"):
            self.search_btn.config(text=self.translator.get("search_button"))
        if hasattr(self, "stop_btn"):
            self.stop_btn.config(text=self.translator.get("stop_button"))
        if hasattr(self, "search_label"):
            self.search_label.config(text=self.translator.get("search_label"))
        if hasattr(self, "search_entry"):
            self.search_entry.update()

        # Update pagination
        if hasattr(self, "pagination_frame"):
            self.update_pagination_controls()

        # Update status
        if hasattr(self, "images") and self.images:
            self.update_status("ready")
        else:
            self.update_status("no_images")

        # Force a UI update
        self.root.update_idletasks()

    def stop_search(self):
        self.stop_request = True
        self.search_btn["state"] = "normal"
        self.stop_btn.pack_forget()
        self.progress.stop()
        self.progress.pack_forget()
        self.update_status("Search stopped")

    def search_images(self):
        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning(
                self.translator.get("error.api_error"),
                self.translator.get("error.empty_query"),
            )
            return

        # Reset stop flag
        self.stop_request = False

        # Update UI for search in progress
        self.search_btn["state"] = "disabled"
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        self.progress.pack(fill=tk.X, padx=10, pady=5)
        self.progress.start(10)
        self.update_status("searching_for", query=query)

        # Clear previous results
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.photo_references.clear()
        self.root.update_idletasks()

        # Start search in a separate thread
        threading.Thread(
            target=self._perform_search, args=(query,), daemon=True
        ).start()

    def _perform_search(self, query, page=1):
        try:
            if self.stop_request:
                return

            # Update UI for search in progress
            self.root.after(0, self.update_status, "contacting_api")
            self.stop_btn.pack(side=tk.LEFT, padx=5)
            self.progress.pack(fill=tk.X, padx=10, pady=5)
            self.progress.start(10)

            # Store search state
            self.current_query = query
            self.current_page = page

            # Start search in a separate thread
            threading.Thread(
                target=self._fetch_images, args=(query, page), daemon=True
            ).start()

        except Exception as e:
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Error", f"Failed to start search: {str(e)}"
                ),
            )
            self._reset_search_ui()

    def _fetch_images(self, query, page):
        """Fetch images in a background thread"""
        try:
            if self.stop_request:
                return

            self.root.after(0, self.update_status, "contacting_api")
            url = f"https://pixabay.com/api/?key={self.api_key}&q={query}&image_type=photo&per_page={self.per_page}&page={page}"

            # Make API request with timeout
            self.root.after(0, lambda: self.update_status("fetching_page", page=page))
            response = requests.get(url, timeout=15)

            if self.stop_request:
                return

            self.root.after(0, self.progress.step, 25)  # Update progress
            data = response.json()

            if "hits" not in data or "totalHits" not in data:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        self.translator.get("error.api_error"),
                        self.translator.get("error.invalid_response"),
                    ),
                )
                return

            self.images = data["hits"]
            total_hits = data["totalHits"]
            self.total_pages = max(1, (total_hits + self.per_page - 1) // self.per_page)

            self.root.after(0, self.progress.step, 75)  # Update progress

            if not self.images:
                self.root.after(0, lambda: self.update_status("no_images"))
            else:
                self.root.after(0, self.display_images)
                self.root.after(0, self.update_pagination_controls)
                self.root.after(0, self.progress.step, 100)  # Complete progress

        except requests.exceptions.Timeout:
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    self.translator.get("error.api_error"),
                    self.translator.get("error.timeout"),
                ),
            )
        except requests.exceptions.RequestException as e:
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    self.translator.get("error.network_error"),
                    self.translator.get("error.network_error_detail", error=str(e)),
                ),
            )
        except Exception as e:
            error_msg = str(e)  # Capture the error message in the outer scope
            self.root.after(
                0,
                lambda msg=error_msg: messagebox.showerror(
                    self.translator.get("error.api_error"),
                    self.translator.get("error.unexpected_error", error=msg),
                ),
            )
        finally:
            # Reset UI in all cases
            self.root.after(0, self._reset_search_ui)

    def _reset_search_ui(self):
        """Reset UI elements after search is complete or stopped"""
        self.search_btn["state"] = "normal"
        self.stop_btn.pack_forget()
        self.progress.stop()
        self.progress.pack_forget()

    def display_images(self):
        """Display images in a grid layout"""
        # Clear existing images and reset photo references
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.photo_references = []

        if not self.images:
            ttk.Label(
                self.scrollable_frame, text=self.translator.get("no_images")
            ).pack(pady=20)
            if hasattr(self, "pagination_frame"):
                self.pagination_frame.pack_forget()  # Hide pagination if no results
            return

        self.update_status(
            "loading_images",
            current=self.current_page,
            total=self.total_pages,
            count=len(self.images),
        )

        # Configure grid for 4 columns
        for i in range(self.columns):
            self.scrollable_frame.columnconfigure(i, weight=1, uniform="column")

        # Create image grid
        row = 0
        col = 0
        for idx, img_data in enumerate(self.images):
            # Skip if we've already processed this image (prevents duplication)
            if idx > 0 and idx % self.per_page == 0:
                break

            frame = ttk.Frame(
                self.scrollable_frame, padding=5, relief="groove", borderwidth=1
            )
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            try:
                # Update status for current image
                current = idx + 1
                total = len(self.images)
                self.root.after(
                    0,
                    lambda c=current, t=total: self.update_status(
                        f"loading_image_{c}_{t}"  # Combine into a single string
                    ),
                )

                # Load and resize image
                try:
                    response = requests.get(
                        img_data["webformatURL"], stream=True, timeout=10
                    )
                    response.raise_for_status()
                    img = Image.open(BytesIO(response.content))
                    img.thumbnail((300, 200))  # Resize image
                    photo = ImageTk.PhotoImage(img)
                    self.photo_references.append(
                        photo
                    )  # Keep reference to prevent garbage collection
                except Exception as e:
                    print(f"Error loading image {idx}: {str(e)}")
                    continue

                # Display image
                label = ttk.Label(frame, image=photo)
                label.pack(pady=5)

                # Display image info
                image_id = img_data.get("id", "N/A")
                image_title = img_data.get("tags", "Untitled").title()
                image_tags = img_data.get("tags", "N/A")

                # Display image title (first few words of tags)
                title_text = " ".join(image_title.split()[:5]) + (
                    "..." if len(image_title.split()) > 5 else ""
                )
                title_label = ttk.Label(
                    frame, text=title_text, font=("Arial", 9, "bold"), wraplength=280
                )
                title_label.pack(pady=(5, 2))

                # Make clickable ID that copies to clipboard
                id_frame = ttk.Frame(frame)
                id_frame.pack(fill=tk.X, pady=2)

                ttk.Label(id_frame, text=self.translator.get("image_id")).pack(
                    side=tk.LEFT
                )
                id_label = ttk.Label(
                    id_frame, text=str(image_id), foreground="blue", cursor="hand2"
                )
                id_label.pack(side=tk.LEFT)
                id_label.bind(
                    "<Button-1>", lambda e, id=image_id: self.copy_to_clipboard(id)
                )

                # Display tags
                tags_text = self.translator.get("tags", tags=image_tags)
                tags_label = ttk.Label(frame, text=tags_text, wraplength=280)
                tags_label.pack(pady=2)

                # Display user and likes
                user_text = self.translator.get(
                    "by", user=img_data.get("user", "Unknown")
                )
                user_label = ttk.Label(frame, text=user_text)
                user_label.pack(pady=2)

                likes_label = ttk.Label(frame, text=f"❤ {img_data.get('likes', 0)}")
                likes_label.pack(pady=2)

                # Update grid position
                col += 1
                if col >= self.columns:
                    col = 0
                    row += 1

            except Exception as e:
                print(f"Error processing image {idx}: {str(e)}")
                continue

        # Bind mouse enter/leave to ensure scroll events are captured properly
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        # Update scrollregion after all widgets are added
        self.canvas.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        # Scroll to top when new results are loaded
        self.canvas.yview_moveto(0.0)

        # Update status to show loading is complete
        self.root.after(0, self.update_status, "ready")
        self.progress.stop()
        self.progress.pack_forget()

    def _on_mousewheel(self, event):
        """Handle mouse wheel/trackpad scrolling"""
        if event.num == 4:  # Linux scroll up
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:  # Linux scroll down
            self.canvas.yview_scroll(1, "units")
        else:  # Windows/MacOS
            self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")

    def _bind_mousewheel(self, event):
        """Bind mouse wheel events when mouse enters canvas"""
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        """Unbind mouse wheel events when mouse leaves canvas"""
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def copy_to_clipboard(self, text):
        try:
            pyperclip.copy(str(text))
            self.update_status("copied_to_clipboard", text=text)
        except Exception as e:
            messagebox.showerror(
                self.translator.get("error.api_error"),
                self.translator.get("error.copy_failed", error=str(e)),
            )


def main():
    root = tk.Tk()
    app = PixabayViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
