import os
import tkinter as tk
from tkinter import ttk, messagebox
from io import BytesIO
import requests
from PIL import Image, ImageTk
from dotenv import load_dotenv
import pyperclip

class PixabayViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("PyMaginAPI: the Pixabay Image App")
        self.root.geometry("1200x800")
        
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv('PIXABAY_API_KEY')
        if not self.api_key:
            messagebox.showerror("Error", "PIXABAY_API_KEY not found in .env file")
            return

        self.setup_ui()
        self.images = []
        self.photo_references = []  # To prevent garbage collection

    def setup_ui(self):
        # Search frame
        search_frame = ttk.Frame(self.root, padding="10")
        search_frame.pack(fill=tk.X)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=50)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<Return>', lambda e: self.search_images())
        
        search_btn = ttk.Button(search_frame, text="Search", command=self.search_images)
        search_btn.pack(side=tk.LEFT, padx=5)
        
        # Canvas with scrollbar
        self.canvas = tk.Canvas(self.root)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
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

    def search_images(self):
        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Please enter a search term")
            return
            
        # Clear previous results
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.photo_references.clear()
        
        # Make API request
        try:
            url = f"https://pixabay.com/api/?key={self.api_key}&q={query}&image_type=photo&per_page=21"
            response = requests.get(url)
            data = response.json()
            
            if 'hits' not in data:
                messagebox.showerror("Error", "Invalid API response")
                return
                
            self.images = data['hits']
            self.display_images()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch images: {str(e)}")
    
    def display_images(self):
        if not self.images:
            ttk.Label(self.scrollable_frame, text="No images found").pack(pady=20)
            return
            
        # Create a 3-column grid
        row = 0
        col = 0
        max_columns = 3
        
        for idx, img_data in enumerate(self.images):
            frame = ttk.Frame(self.scrollable_frame, padding=5, relief="groove", borderwidth=1)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            try:
                # Load and resize image
                response = requests.get(img_data['webformatURL'])
                img = Image.open(BytesIO(response.content))
                img.thumbnail((300, 200))  # Resize image
                photo = ImageTk.PhotoImage(img)
                self.photo_references.append(photo)  # Keep reference
                
                # Display image
                label = ttk.Label(frame, image=photo)
                label.pack(pady=5)
                
                # Display image info
                image_id = img_data.get('id', 'N/A')
                image_tags = img_data.get('tags', 'N/A')
                
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
