"""
Simple tkinter UI for YouTube Channel Info Fetcher
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from googleapiclient.errors import HttpError

from youtube import fetch_channel_info, handle_api_error


def create_ui():
   """Create a simple tkinter UI for the YouTube Channel Info Fetcher."""
   root = tk.Tk()
   root.title("YouTube Channel Info Fetcher")
   root.geometry("900x700")
   root.configure(bg="#f0f0f0")
   
   # Header
   header_frame = tk.Frame(root, bg="#2c3e50")
   header_frame.pack(fill=tk.X, padx=0, pady=0)
   header_label = tk.Label(
       header_frame, 
       text="YouTube Channel Information Fetcher",
       font=("Arial", 16, "bold"),
       bg="#2c3e50",
       fg="white",
       pady=10
   )
   header_label.pack()
   
   # Input frame
   input_frame = tk.Frame(root, bg="#f0f0f0")
   input_frame.pack(fill=tk.X, padx=15, pady=15)
   
   label = tk.Label(input_frame, text="Enter YouTube Channel Name or Handle:", bg="#f0f0f0", font=("Arial", 11))
   label.pack(anchor=tk.W, pady=(0, 5))
   
   input_var = tk.StringVar(value="codebasics")
   entry = tk.Entry(input_frame, textvariable=input_var, font=("Arial", 12), width=50)
   entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
   
   # Search button
   def on_search():
       channel_name = input_var.get().strip()
       if not channel_name:
           messagebox.showwarning("Input Error", "Please enter a channel name.")
           return
       
       search_btn.config(state=tk.DISABLED)
       search_btn.config(text="Loading...")
       root.update()
       
       try:
           result = fetch_channel_info(channel_name)
           display_results(result)
       except ValueError as e:
           messagebox.showerror("Error", f"Error: {e}")
       except HttpError as e:
           messagebox.showerror("API Error", handle_api_error(e))
       finally:
           search_btn.config(state=tk.NORMAL)
           search_btn.config(text="Search")
   
   search_btn = tk.Button(
       input_frame,
       text="Search",
       command=on_search,
       bg="#3498db",
       fg="white",
       font=("Arial", 11, "bold"),
       padx=20,
       pady=8
   )
   search_btn.pack(side=tk.LEFT, padx=(10, 0))
   
   # Results frame
   results_frame = tk.Frame(root, bg="white")
   results_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
   
   results_label = tk.Label(results_frame, text="Results:", bg="white", font=("Arial", 11, "bold"))
   results_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
   
   # Text widget for results
   text_widget = scrolledtext.ScrolledText(
       results_frame,
       height=20,
       width=100,
       font=("Courier", 10),
       bg="#fafafa",
       fg="#333333",
       padx=10,
       pady=10
   )
   text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
   
   def display_results(result):
       text_widget.config(state=tk.NORMAL)
       text_widget.delete(1.0, tk.END)
       formatted_result = json.dumps(result, indent=2, ensure_ascii=False)
       text_widget.insert(tk.END, formatted_result)
       text_widget.config(state=tk.DISABLED)
   
   # Bind Enter key to search
   entry.bind("<Return>", lambda e: on_search())
   
   root.mainloop()
