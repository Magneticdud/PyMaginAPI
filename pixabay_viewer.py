import os
import tkinter as tk
from tkinter import ttk, messagebox
from io import BytesIO
import requests
from PIL import Image, ImageTk
from dotenv import load_dotenv
import pyperclip
import threading
from urllib.parse import urlparse

class PixabayViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("PyMaginAPI: the Pixabay Image App")
        self.root.geometry("1200x900")  # Slightly taller to accommodate pagination
        
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv('PIXABAY_API_KEY')
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
        self.per_page = 21  # Number of images per page

    def setup_ui(self):
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Search frame
        search_frame = ttk.Frame(main_container, padding="10")
        search_frame.pack(fill=tk.X)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=50)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<Return>', lambda e: self.search_images())
        
        self.search_btn = ttk.Button(search_frame, text="Search", command=self.search_images)
        self.search_btn.pack(side=tk.LEFT, padx=5)
        
        # Stop button (initially hidden)
        self.stop_btn = ttk.Button(search_frame, text="Stop", command=self.stop_search, style='Accent.TButton')
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, length=100, mode='indeterminate')
        
        # Configure styles
        style = ttk.Style()
        style.configure('Accent.TButton', foreground='red')
        
        # Canvas with scrollbar
        self.canvas = tk.Canvas(main_container)
        self.scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Pagination frame (initially hidden)
        self.pagination_frame = ttk.Frame(main_container, padding="5")
        
        # Status bar (moved to bottom of window)
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def stop_search(self):
        self.stop_request = True
        self.search_btn['state'] = 'normal'
        self.stop_btn.pack_forget()
        self.progress.stop()
        self.progress.pack_forget()
        self.update_status("Search stopped")
    
    def search_images(self):
        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Please enter a search term")
            return
        
        # Reset stop flag
        self.stop_request = False
        
        # Update UI for search in progress
        self.search_btn['state'] = 'disabled'
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        self.progress.pack(fill=tk.X, padx=10, pady=5)
        self.progress.start(10)
        self.update_status(f"Searching for '{query}'...")
        
        # Clear previous results
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.photo_references.clear()
        self.root.update_idletasks()
        
        # Start search in a separate thread
        threading.Thread(target=self._perform_search, args=(query,), daemon=True).start()
    
    def _perform_search(self, query, page=1):
        try:
            if self.stop_request:
                return
                
            self.current_query = query
            self.current_page = page
            
            self.update_status(f"Contacting Pixabay API...")
            url = f"https://pixabay.com/api/?key={self.api_key}&q={query}&image_type=photo&per_page={self.per_page}&page={page}"
            
            # Make API request with timeout
            response = requests.get(url, timeout=10)
            
            if self.stop_request:
                return
                
            data = response.json()
            
            if 'hits' not in data or 'totalHits' not in data:
                self.root.after(0, lambda: messagebox.showerror("Error", "Invalid API response"))
                return
                
            self.images = data['hits']
            total_hits = data['totalHits']
            self.total_pages = max(1, (total_hits + self.per_page - 1) // self.per_page)
            
            if not self.images:
                self.root.after(0, lambda: self.update_status("No images found"))
            else:
                self.root.after(0, self.display_images)
                self.root.after(0, self.update_pagination_controls)
                
        except requests.exceptions.Timeout:
            self.root.after(0, lambda: messagebox.showerror("Error", "Request timed out. Please try again."))
        except requests.exceptions.RequestException as e:
            self.root.after(0, lambda: messagebox.showerror("Network Error", f"Failed to fetch images: {str(e)}"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}"))
        finally:
            # Reset UI
            self.root.after(0, self._reset_search_ui)
    
    def _reset_search_ui(self):
        """Reset UI elements after search is complete or stopped"""
        self.search_btn['state'] = 'normal'
        self.stop_btn.pack_forget()
        self.progress.stop()
        self.progress.pack_forget()
    
    def update_pagination_controls(self):
        # Clear existing controls
        for widget in self.pagination_frame.winfo_children():
            widget.destroy()
        
        if self.total_pages > 1:
            # Previous button
            prev_btn = ttk.Button(
                self.pagination_frame, 
                text="← Previous",
                command=lambda: self._perform_search(self.current_query, max(1, self.current_page - 1)),
                state="disabled" if self.current_page == 1 else "normal"
            )
            prev_btn.pack(side=tk.LEFT, padx=5)
            
            # Page info
            page_info = ttk.Label(
                self.pagination_frame,
                text=f"Page {self.current_page} of {self.total_pages}"
            )
            page_info.pack(side=tk.LEFT, padx=10)
            
            # Next button
            next_btn = ttk.Button(
                self.pagination_frame, 
                text="Next →",
                command=lambda: self._perform_search(self.current_query, min(self.total_pages, self.current_page + 1)),
                state="disabled" if self.current_page >= self.total_pages else "normal"
            )
            next_btn.pack(side=tk.LEFT, padx=5)
            
            # Show pagination frame
            self.pagination_frame.pack(fill=tk.X, pady=5)
    
    def display_images(self):
        if not self.images:
            ttk.Label(self.scrollable_frame, text="No images found").pack(pady=20)
            self.update_status("No images found")
            self.pagination_frame.pack_forget()  # Hide pagination if no results
            return
            
        self.update_status(f"Page {self.current_page} of {self.total_pages} - Loading {len(self.images)} images...")
            
        # Create a 3-column grid
        row = 0
        col = 0
        max_columns = 3
        
        for idx, img_data in enumerate(self.images):
            frame = ttk.Frame(self.scrollable_frame, padding=5, relief="groove", borderwidth=1)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            try:
                # Update status for current image
                if idx % 3 == 0:  # Update status every 3 images
                    self.root.after(0, self.update_status, f"Loading image {idx + 1} of {len(self.images)}...")
                    
                # Load and resize image
                try:
                    response = requests.get(img_data['webformatURL'], stream=True, timeout=10)
                    response.raise_for_status()
                    img = Image.open(BytesIO(response.content))
                    img.thumbnail((300, 200))  # Resize image
                    photo = ImageTk.PhotoImage(img)
                    self.photo_references.append(photo)  # Keep reference
                except Exception as e:
                    print(f"Error loading image {idx}: {str(e)}")
                    continue
                
                # Display image
                label = ttk.Label(frame, image=photo)
                label.pack(pady=5)
                
                # Display image info
                image_id = img_data.get('id', 'N/A')
                image_title = img_data.get('tags', 'Untitled').title()
                image_tags = img_data.get('tags', 'N/A')
                
                # Display image title (first few words of tags)
                title_text = ' '.join(image_title.split()[:5]) + ('...' if len(image_title.split()) > 5 else '')
                title_label = ttk.Label(frame, text=title_text, font=('Arial', 9, 'bold'), wraplength=280)
                title_label.pack(pady=(5, 2))
                
                # Make clickable ID that copies to clipboard
                id_frame = ttk.Frame(frame)
                id_frame.pack(fill=tk.X, pady=2)
                
                ttk.Label(id_frame, text="ID: ").pack(side=tk.LEFT)
                id_label = ttk.Label(id_frame, text=str(image_id), foreground="blue", cursor="hand2")
                id_label.pack(side=tk.LEFT)
                id_label.bind("<Button-1>", lambda e, id=image_id: self.copy_to_clipboard(id))
                
                # Display tags
                tags_label = ttk.Label(frame, text=f"Tags: {image_tags}", wraplength=280)
                tags_label.pack(pady=2)
                
                # Display user and likes
                user_label = ttk.Label(frame, text=f"By: {img_data.get('user', 'Unknown')}")
                user_label.pack(pady=2)
                
                likes_label = ttk.Label(frame, text=f"❤ {img_data.get('likes', 0)}")
                likes_label.pack(pady=2)
                
                # Update grid position
                col += 1
                if col >= max_columns:
                    col = 0
                    row += 1
                    
            except Exception as e:
                print(f"Error loading image {idx}: {str(e)}")
                continue
                
        # Configure grid weights
        for i in range(max_columns):
            self.scrollable_frame.columnconfigure(i, weight=1)
            
        # Bind mouse wheel events for scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)  # Linux scroll up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)  # Linux scroll down
        
        # Bind mouse enter/leave to ensure scroll events are captured properly
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        
        # Update scrollregion after all widgets are added
        self.canvas.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        # Scroll to top when new results are loaded
        self.canvas.yview_moveto(0.0)
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel/trackpad scrolling"""
        if event.num == 4:  # Linux scroll up
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:  # Linux scroll down
            self.canvas.yview_scroll(1, "units")
        else:  # Windows/MacOS
            self.canvas.yview_scroll(-1 * int(event.delta/120), "units")
    
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
            messagebox.showinfo("Copied!", f"Copied to clipboard: {text}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy to clipboard: {str(e)}")

def main():
    root = tk.Tk()
    app = PixabayViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
