import tkinter as tk
from tkinter import ttk, messagebox
import requests
import time

API_URL = "http://127.0.0.1:5000"

class SQLClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SQL Client")
        self.root.geometry("900x600")
        self.root.configure(bg="#f9f9f9")
        self.page = 1
        self.total = 0

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Treeview", rowheight=28, font=('Segoe UI', 10))
        self.style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))
        self.style.configure("TButton", font=('Segoe UI', 10))
        self.style.configure("TLabel", font=('Segoe UI', 10))

        # Main frame
        main_frame = tk.Frame(root, bg="#f9f9f9")
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Left: query and results
        left_frame = tk.Frame(main_frame, bg="#f9f9f9")
        left_frame.pack(side='left', fill='both', expand=True)

        # Right: sidebar
        sidebar = tk.Frame(main_frame, width=200, bg="#f0f0f0")
        sidebar.pack(side='right', fill='y')
        tk.Label(sidebar, text="Tablas", bg="#f0f0f0", font=('Segoe UI', 11, 'bold')).pack(pady=5)
        self.table_list = tk.Listbox(sidebar, font=('Segoe UI', 10))
        self.table_list.pack(fill='y', expand=True, padx=5, pady=5)
        self.load_tables()

        # Query box
        query_label = tk.Label(left_frame, text="Consulta SQL", bg="#f9f9f9", font=('Segoe UI', 11, 'bold'))
        query_label.pack(anchor='w', padx=5)
        self.query_entry = tk.Text(left_frame, height=3, font=('Consolas', 10))
        self.query_entry.pack(fill='x', padx=5, pady=5)
        self.query_entry.bind("<Return>", self.run_query_event)

        # Results
        self.result_tree = ttk.Treeview(left_frame)
        self.result_tree.pack(fill='both', expand=True, padx=5, pady=5)

        # Navigation
        nav = tk.Frame(left_frame, bg="#f9f9f9")
        nav.pack(pady=5)
        self.prev_btn = ttk.Button(nav, text="⟨ Anterior", command=self.prev_page)
        self.prev_btn.pack(side='left', padx=5)
        self.page_label = ttk.Label(nav, text="Página 1")
        self.page_label.pack(side='left', padx=5)
        self.next_btn = ttk.Button(nav, text="Siguiente ⟩", command=self.next_page)
        self.next_btn.pack(side='left', padx=5)

        # Footer
        self.footer = ttk.Label(root, text="Tiempo de ejecución: 0s", anchor="center")
        self.footer.pack(fill='x', pady=5)

    def run_query_event(self, event):
        self.page = 1
        self.run_query()
        self.query_entry.delete("1.0", "end")  # Limpia la consulta tras ejecutar
        return "break"

    def run_query(self):
        sql = self.query_entry.get("1.0", "end-1c").strip()
        if not sql:
            return

        try:
            start = time.time()
            response = requests.post(f"{API_URL}/query", json={"query": sql, "page": self.page})
            duration = round(time.time() - start, 4)
            self.footer.config(text=f"Tiempo de ejecución: {duration} segundos")

            if response.status_code != 200:
                messagebox.showerror("Error", response.json().get("error", "Error desconocido"))
                return

            data = response.json()
            self.display_results(data)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def display_results(self, data):
        for col in self.result_tree.get_children():
            self.result_tree.delete(col)
        self.result_tree["columns"] = data["columns"]
        self.result_tree["show"] = "headings"

        for col in data["columns"]:
            self.result_tree.heading(col, text=col)
            self.result_tree.column(col, anchor="center")

        for row in data["rows"]:
            self.result_tree.insert("", "end", values=row)

        self.total = data.get("total", 0)
        total_pages = max(1, (self.total + 9) // 10)
        self.page_label.config(text=f"Página {self.page} de {total_pages}")

    def load_tables(self):
        try:
            response = requests.get(f"{API_URL}/tables")
            if response.status_code == 200:
                self.table_list.delete(0, tk.END)
                for table in response.json():
                    self.table_list.insert(tk.END, table)
        except Exception as e:
            self.table_list.insert(tk.END, f"Error: {e}")

    def next_page(self):
        if self.page * 10 < self.total:
            self.page += 1
            self.run_query()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.run_query()

if __name__ == "__main__":
    root = tk.Tk()
    app = SQLClientApp(root)
    root.mainloop()
