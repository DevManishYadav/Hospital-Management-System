import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import hashlib
import csv
from datetime import datetime

# ================= DATABASE MANAGER =================
class Database:
    def __init__(self, db_name="hospital.db"):
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self.cur.execute("PRAGMA foreign_keys = ON")
        self.create_tables()
        self.create_default_admin()

    def create_tables(self):
        # Users
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                uid INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'staff',
                full_name TEXT
            )
        """)
        # Patients
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                pid INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER,
                gender TEXT,
                blood_group TEXT,
                contact TEXT,
                address TEXT,
                registration_date TEXT DEFAULT CURRENT_DATE
            )
        """)
        # Doctors
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS doctors (
                did INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                specialization TEXT,
                contact TEXT,
                email TEXT,
                consultation_fee REAL DEFAULT 0
            )
        """)
        # Rooms
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                rid INTEGER PRIMARY KEY,
                room_number TEXT UNIQUE NOT NULL,
                room_type TEXT,
                capacity INTEGER DEFAULT 1,
                daily_charge REAL DEFAULT 0,
                status TEXT DEFAULT 'Available'
            )
        """)
        # Admissions
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS admissions (
                admission_id INTEGER PRIMARY KEY,
                pid INTEGER NOT NULL,
                rid INTEGER NOT NULL,
                admission_date TEXT NOT NULL,
                discharge_date TEXT,
                FOREIGN KEY(pid) REFERENCES patients(pid),
                FOREIGN KEY(rid) REFERENCES rooms(rid)
            )
        """)
        # Appointments
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                aid INTEGER PRIMARY KEY,
                pid INTEGER NOT NULL,
                did INTEGER NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT,
                status TEXT DEFAULT 'Scheduled',
                notes TEXT,
                FOREIGN KEY(pid) REFERENCES patients(pid),
                FOREIGN KEY(did) REFERENCES doctors(did)
            )
        """)
        # Billing
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS billing (
                bid INTEGER PRIMARY KEY,
                pid INTEGER NOT NULL,
                admission_id INTEGER,
                amount REAL NOT NULL,
                description TEXT,
                payment_date TEXT,
                payment_method TEXT,
                status TEXT DEFAULT 'Pending',
                FOREIGN KEY(pid) REFERENCES patients(pid),
                FOREIGN KEY(admission_id) REFERENCES admissions(admission_id)
            )
        """)
        self.conn.commit()

    def create_default_admin(self):
        self.cur.execute("SELECT * FROM users WHERE username='Neharu'")
        if not self.cur.fetchone():
            hashed = hashlib.sha256("Neharu123".encode()).hexdigest()
            self.cur.execute("INSERT INTO users (username, password, role, full_name) VALUES (?,?,?,?)",
                             ("Neharu", hashed, "Neharu", "System Administrator"))
            self.conn.commit()

    def next_id(self, table, col):
        self.cur.execute(f"SELECT MAX({col}) FROM {table}")
        x = self.cur.fetchone()[0]
        return 1 if x is None else x + 1

    def reorder_ids(self, table, col):
        self.cur.execute(f"SELECT {col} FROM {table} ORDER BY {col}")
        rows = self.cur.fetchall()
        for i, row in enumerate(rows, start=1):
            if row[0] != i:
                self.cur.execute(f"UPDATE {table} SET {col}=? WHERE {col}=?", (i, row[0]))
        self.conn.commit()

    def execute_query(self, query, params=()):
        self.cur.execute(query, params)
        self.conn.commit()
        return self.cur

    def fetch_all(self, query, params=()):
        self.cur.execute(query, params)
        return self.cur.fetchall()

    def fetch_one(self, query, params=()):
        self.cur.execute(query, params)
        return self.cur.fetchone()

# ================= LOGIN WINDOW =================
class LoginWindow:
    def __init__(self, db):
        self.db = db
        self.root = tk.Tk()
        self.root.title("Hospital Management System - Login")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        self.center_window()
        self.setup_ui()

    def center_window(self):
        self.root.update_idletasks()
        w, h = 400, 300
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", font=("Segoe UI", 11))
        style.configure("TButton", font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", font=("Segoe UI", 11))

        main_frame = ttk.Frame(self.root, padding="30 20")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="🏥 HOSPITAL MANAGEMENT", font=("Segoe UI", 16, "bold")).pack(pady=(0,20))
        ttk.Label(main_frame, text="Username").pack(anchor="w")
        self.username = ttk.Entry(main_frame, width=30)
        self.username.pack(fill="x", pady=(0,10))
        self.username.focus()

        ttk.Label(main_frame, text="Password").pack(anchor="w")
        self.password = ttk.Entry(main_frame, width=30, show="•")
        self.password.pack(fill="x", pady=(0,20))
        self.password.bind("<Return>", lambda e: self.login())

        ttk.Button(main_frame, text="Login", command=self.login).pack(pady=5)

    def login(self):
        username = self.username.get().strip()
        password = self.password.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password")
            return
        hashed = hashlib.sha256(password.encode()).hexdigest()
        user = self.db.fetch_one("SELECT * FROM users WHERE username=? AND password=?", (username, hashed))
        if user:
            self.root.destroy()
            app = MainApplication(self.db, user)
            app.run()
        else:
            messagebox.showerror("Login Failed", "Invalid credentials")

    def run(self):
        self.root.mainloop()

# ================= MAIN APPLICATION =================
class MainApplication:
    def __init__(self, db, user):
        self.db = db
        self.current_user = user
        self.root = tk.Tk()
        self.root.title("Hospital Management System v2.0")
        self.root.state("zoomed")
        self.setup_styles()
        self.create_menu()
        self.create_notebook()
        self.load_dashboard()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=25)
        style.map("Treeview", background=[("selected", "#347ab3")])

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Patients (CSV)", command=self.export_patients)
        file_menu.add_separator()
        file_menu.add_command(label="Logout", command=self.logout)
        file_menu.add_command(label="Exit", command=self.root.quit)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def create_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.dash_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dash_frame, text="📊 Dashboard")

        self.patient_frame = PatientFrame(self.notebook, self.db)
        self.notebook.add(self.patient_frame, text="🧑‍⚕️ Patients")

        self.doctor_frame = DoctorFrame(self.notebook, self.db)
        self.notebook.add(self.doctor_frame, text="👨‍⚕️ Doctors")

        self.appt_frame = AppointmentFrame(self.notebook, self.db)
        self.notebook.add(self.appt_frame, text="📅 Appointments")

        self.room_frame = RoomFrame(self.notebook, self.db)
        self.notebook.add(self.room_frame, text="🏨 Rooms")

        self.billing_frame = BillingFrame(self.notebook, self.db)
        self.notebook.add(self.billing_frame, text="💰 Billing")

        self.report_frame = ReportFrame(self.notebook, self.db)
        self.notebook.add(self.report_frame, text="📈 Reports")

        self.status_var = tk.StringVar()
        self.status_var.set(f"Logged in as: {self.current_user['full_name']} ({self.current_user['role']})")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(side="bottom", fill="x")

        # === TAB CHANGE EVENT — AUTO REFRESH ===
        def on_tab_changed(event):
            selected_tab = event.widget.tab(event.widget.select(), "text")
            if "Dashboard" in selected_tab:
                self.load_dashboard()
            elif "Appointments" in selected_tab:
                self.appt_frame.refresh()
            elif "Patients" in selected_tab:
                self.patient_frame.refresh()
            elif "Doctors" in selected_tab:
                self.doctor_frame.refresh()
            elif "Rooms" in selected_tab:
                self.room_frame.refresh()
            elif "Billing" in selected_tab:
                self.billing_frame.refresh()

        self.notebook.bind("<<NotebookTabChanged>>", on_tab_changed)

    def load_dashboard(self):
        # Clear existing content
        for widget in self.dash_frame.winfo_children():
            widget.destroy()

        # Fetch live statistics
        patient_count = self.db.fetch_one("SELECT COUNT(*) FROM patients")[0]
        doctor_count = self.db.fetch_one("SELECT COUNT(*) FROM doctors")[0]
        appt_today = self.db.fetch_one("SELECT COUNT(*) FROM appointments WHERE appointment_date = date('now')")[0]
        revenue = self.db.fetch_one("SELECT SUM(amount) FROM billing WHERE status='Paid'")[0] or 0

        # Header
        ttk.Label(self.dash_frame, text="🏥 Hospital Dashboard", font=("Segoe UI", 18, "bold")).pack(pady=20)

        # Manual refresh button
        refresh_btn = ttk.Button(self.dash_frame, text="🔄 Refresh Now", command=self.load_dashboard)
        refresh_btn.pack(pady=(0, 10))

        # Statistics Cards
        stats_frame = ttk.Frame(self.dash_frame)
        stats_frame.pack(pady=20)

        cards = [
            ("Total Patients", patient_count, "#2ecc71"),
            ("Total Doctors", doctor_count, "#3498db"),
            ("Today's Appointments", appt_today, "#f39c12"),
            ("Total Revenue", f"${revenue:,.2f}", "#9b59b6")
        ]

        for i, (title, value, color) in enumerate(cards):
            card = tk.Frame(stats_frame, bg=color, width=200, height=100)
            card.grid(row=0, column=i, padx=10, pady=10)
            card.pack_propagate(False)
            tk.Label(card, text=title, font=("Segoe UI", 12), bg=color, fg="white").pack(pady=(20, 0))
            tk.Label(card, text=str(value), font=("Segoe UI", 24, "bold"), bg=color, fg="white").pack()

        # Upcoming Appointments
        ttk.Label(self.dash_frame, text="📋 Upcoming Appointments", font=("Segoe UI", 14, "bold")).pack(pady=(20, 10))

        tree = ttk.Treeview(self.dash_frame, columns=("Patient", "Date", "Time"), show="headings", height=5)
        tree.heading("Patient", text="Patient")
        tree.heading("Date", text="Date")
        tree.heading("Time", text="Time")
        tree.column("Patient", width=200)
        tree.column("Date", width=120)
        tree.column("Time", width=100)
        tree.pack(padx=20, fill="x")

        recent = self.db.fetch_all("""
            SELECT p.name, a.appointment_date, a.appointment_time
            FROM appointments a
            JOIN patients p ON a.pid = p.pid
            WHERE a.appointment_date >= date('now')
            ORDER BY a.appointment_date, a.appointment_time
            LIMIT 5
        """)

        if recent:
            for row in recent:
                patient_name = row[0] or "Unknown"
                date_str = row[1] or "—"
                time_str = row[2] or "—"
                tree.insert("", "end", values=(patient_name, date_str, time_str))
        else:
            tree.insert("", "end", values=("No upcoming appointments", "", ""))

        ttk.Separator(self.dash_frame, orient="horizontal").pack(fill="x", padx=20, pady=10)

        # Quick Stats Row
        quick_frame = ttk.Frame(self.dash_frame)
        quick_frame.pack(pady=5)
        pending_bills = self.db.fetch_one("SELECT COUNT(*) FROM billing WHERE status='Pending'")[0]
        occupied_rooms = self.db.fetch_one("SELECT COUNT(*) FROM rooms WHERE status='Occupied'")[0]
        ttk.Label(quick_frame, text=f"Pending Bills: {pending_bills}").pack(side="left", padx=15)
        ttk.Label(quick_frame, text=f"Occupied Rooms: {occupied_rooms}").pack(side="left", padx=15)

    def export_patients(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return
        data = self.db.fetch_all("SELECT * FROM patients")
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Age", "Gender", "Blood Group", "Contact", "Address", "Reg Date"])
            writer.writerows(data)
        messagebox.showinfo("Export", "Patients exported successfully.")

    def logout(self):
        self.root.destroy()
        LoginWindow(self.db).run()

    def show_about(self):
        messagebox.showinfo("About", "Hospital Management System v2.0\n\nDeveloped for educational purposes.\n© 2025")

    def run(self):
        self.root.mainloop()

# ================= BASE FRAME (WITH FORM FIX) =================
class BaseFrame(ttk.Frame):
    def __init__(self, parent, db, table_name, columns, id_col):
        super().__init__(parent)
        self.db = db
        self.table_name = table_name
        self.columns = columns
        self.id_col = id_col
        self.form_mode = None
        self.form_frame = None
        self.setup_ui()

    def setup_ui(self):
        control_frame = ttk.Frame(self)
        control_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(control_frame, text="➕ Add", command=self.add_record).pack(side="left", padx=2)
        ttk.Button(control_frame, text="✏️ Edit", command=self.edit_record).pack(side="left", padx=2)
        ttk.Button(control_frame, text="🗑️ Delete", command=self.delete_record).pack(side="left", padx=2)
        ttk.Button(control_frame, text="🔄 Refresh", command=self.refresh).pack(side="left", padx=2)

        ttk.Label(control_frame, text="Search:").pack(side="left", padx=(20,5))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.filter_tree())
        ttk.Entry(control_frame, textvariable=self.search_var, width=20).pack(side="left")

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        cols_display = [c[1] for c in self.columns]
        self.tree = ttk.Treeview(tree_frame, columns=cols_display, show="headings", selectmode="browse")
        for col, display, width in self.columns:
            self.tree.heading(display, text=display)
            self.tree.column(display, width=width, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self.edit_record())
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        data = self.db.fetch_all(f"SELECT * FROM {self.table_name} ORDER BY {self.id_col}")
        for row in data:
            values = [row[c[0]] for c in self.columns]
            self.tree.insert("", "end", values=values)

    def filter_tree(self):
        query = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        data = self.db.fetch_all(f"SELECT * FROM {self.table_name} ORDER BY {self.id_col}")
        for row in data:
            if query in str(row).lower():
                values = [row[c[0]] for c in self.columns]
                self.tree.insert("", "end", values=values)

    def get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Please select a record.")
            return None
        item = self.tree.item(sel[0])
        return item['values'][0]

    def _destroy_form(self):
        if self.form_frame is not None:
            self.form_frame.destroy()
            self.form_frame = None

    def _create_form_frame(self, title):
        self._destroy_form()
        self.form_frame = ttk.LabelFrame(self, text=title, padding=10)

    def add_record(self):
        try:
            self._create_form_frame("Add New Record")
            self.form_mode = "add"
            empty_record = {c[0]: "" for c in self.columns if c[0] != self.id_col}
            self.populate_form(empty_record)
            self.form_frame.pack(fill="x", padx=10, pady=10)
            self.form_frame.update_idletasks()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open add form: {e}")
            self._destroy_form()

    def edit_record(self):
        id_val = self.get_selected_id()
        if id_val is None:
            return
        record = self.db.fetch_one(f"SELECT * FROM {self.table_name} WHERE {self.id_col}=?", (id_val,))
        if not record:
            messagebox.showerror("Error", "Record not found.")
            return
        try:
            self._create_form_frame(f"Edit Record (ID: {id_val})")
            self.form_mode = "edit"
            self.populate_form(dict(record))
            self.form_frame.pack(fill="x", padx=10, pady=10)
            self.form_frame.update_idletasks()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open edit form: {e}")
            self._destroy_form()

    def delete_record(self):
        id_val = self.get_selected_id()
        if id_val is None:
            return
        if messagebox.askyesno("Confirm", "Delete this record?"):
            try:
                self.db.execute_query(f"DELETE FROM {self.table_name} WHERE {self.id_col}=?", (id_val,))
                self.db.reorder_ids(self.table_name, self.id_col)
                self.refresh()
                messagebox.showinfo("Success", "Record deleted successfully.")
            except sqlite3.IntegrityError as e:
                messagebox.showerror("Error", f"Cannot delete: record is referenced elsewhere.\n{e}")

    def populate_form(self, record):
        raise NotImplementedError("Subclasses must implement populate_form")

    def save_record(self):
        raise NotImplementedError("Subclasses must implement save_record")

# ================= PATIENT FRAME =================
class PatientFrame(BaseFrame):
    def __init__(self, parent, db):
        columns = [
            ("pid", "ID", 50),
            ("name", "Name", 150),
            ("age", "Age", 50),
            ("gender", "Gender", 80),
            ("blood_group", "Blood Grp", 80),
            ("contact", "Contact", 120),
            ("address", "Address", 200)
        ]
        super().__init__(parent, db, "patients", columns, "pid")

    def populate_form(self, record):
        fields = ["name", "age", "gender", "blood_group", "contact", "address"]
        self.form_entries = {}
        row = 0
        for field in fields:
            ttk.Label(self.form_frame, text=field.replace("_"," ").title()+":").grid(row=row, column=0, sticky="e", padx=5, pady=3)
            if field == "gender":
                combo = ttk.Combobox(self.form_frame, values=["Male","Female","Other"], state="readonly")
                combo.grid(row=row, column=1, sticky="w", padx=5, pady=3)
                combo.set(record.get(field, ""))
                self.form_entries[field] = combo
            elif field == "blood_group":
                combo = ttk.Combobox(self.form_frame, values=["A+","A-","B+","B-","AB+","AB-","O+","O-"], state="readonly")
                combo.grid(row=row, column=1, sticky="w")
                combo.set(record.get(field, ""))
                self.form_entries[field] = combo
            else:
                entry = ttk.Entry(self.form_frame, width=30)
                entry.grid(row=row, column=1, sticky="w", padx=5, pady=3)
                entry.insert(0, record.get(field, ""))
                self.form_entries[field] = entry
            row += 1

        btn_frame = ttk.Frame(self.form_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=self.save_record).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self._destroy_form).pack(side="left")

        if self.form_mode == "edit":
            self.form_entries['pid'] = record['pid']

    def save_record(self):
        data = {field: (entry.get() if isinstance(entry, ttk.Entry) else entry.get()) 
                for field, entry in self.form_entries.items() if field != 'pid'}
        if not data.get('name'):
            messagebox.showerror("Error", "Name is required.")
            return
        try:
            age = int(data['age']) if data['age'] else None
        except ValueError:
            messagebox.showerror("Error", "Age must be a number.")
            return
        if self.form_mode == "add":
            self.db.execute_query(
                "INSERT INTO patients (name, age, gender, blood_group, contact, address) VALUES (?,?,?,?,?,?)",
                (data['name'], age, data['gender'], data['blood_group'], data['contact'], data['address'])
            )
            messagebox.showinfo("Success", "Patient added successfully.")
        else:
            pid = self.form_entries.get('pid')
            self.db.execute_query(
                "UPDATE patients SET name=?, age=?, gender=?, blood_group=?, contact=?, address=? WHERE pid=?",
                (data['name'], age, data['gender'], data['blood_group'], data['contact'], data['address'], pid)
            )
            messagebox.showinfo("Success", "Patient updated successfully.")
        self._destroy_form()
        self.refresh()

# ================= DOCTOR FRAME =================
class DoctorFrame(BaseFrame):
    def __init__(self, parent, db):
        columns = [
            ("did", "ID", 50),
            ("name", "Name", 150),
            ("specialization", "Specialization", 150),
            ("contact", "Contact", 120),
            ("email", "Email", 150),
            ("consultation_fee", "Fee", 80)
        ]
        super().__init__(parent, db, "doctors", columns, "did")

    def populate_form(self, record):
        fields = ["name", "specialization", "contact", "email", "consultation_fee"]
        self.form_entries = {}
        row = 0
        for field in fields:
            ttk.Label(self.form_frame, text=field.replace("_"," ").title()+":").grid(row=row, column=0, sticky="e", padx=5, pady=3)
            entry = ttk.Entry(self.form_frame, width=30)
            entry.grid(row=row, column=1, sticky="w", padx=5, pady=3)
            entry.insert(0, str(record.get(field, "")))
            self.form_entries[field] = entry
            row += 1
        btn_frame = ttk.Frame(self.form_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=self.save_record).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self._destroy_form).pack(side="left")
        if self.form_mode == "edit":
            self.form_entries['did'] = record['did']

    def save_record(self):
        data = {f: e.get() for f, e in self.form_entries.items() if f != 'did'}
        if not data['name']:
            messagebox.showerror("Error", "Name required.")
            return
        try:
            fee = float(data['consultation_fee']) if data['consultation_fee'] else 0.0
        except ValueError:
            messagebox.showerror("Error", "Fee must be a number.")
            return
        if self.form_mode == "add":
            self.db.execute_query(
                "INSERT INTO doctors (name, specialization, contact, email, consultation_fee) VALUES (?,?,?,?,?)",
                (data['name'], data['specialization'], data['contact'], data['email'], fee)
            )
            messagebox.showinfo("Success", "Doctor added successfully.")
        else:
            did = self.form_entries.get('did')
            self.db.execute_query(
                "UPDATE doctors SET name=?, specialization=?, contact=?, email=?, consultation_fee=? WHERE did=?",
                (data['name'], data['specialization'], data['contact'], data['email'], fee, did)
            )
            messagebox.showinfo("Success", "Doctor updated successfully.")
        self._destroy_form()
        self.refresh()

# ================= APPOINTMENT FRAME (FIXED) =================
class AppointmentFrame(BaseFrame):
    def __init__(self, parent, db):
        columns = [
            ("aid", "ID", 50),
            ("patient_name", "Patient", 150),
            ("doctor_name", "Doctor", 150),
            ("appointment_date", "Date", 100),
            ("appointment_time", "Time", 80),
            ("status", "Status", 100),
            ("notes", "Notes", 200)
        ]
        super().__init__(parent, db, "appointments", columns, "aid")
        self.patients = {}
        self.doctors = {}
        self.load_dropdown_data()

    def load_dropdown_data(self):
        self.patients = {row['pid']: row['name'] for row in self.db.fetch_all("SELECT pid, name FROM patients")}
        self.doctors = {row['did']: row['name'] for row in self.db.fetch_all("SELECT did, name FROM doctors")}

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        query = """
            SELECT a.aid, p.name, d.name, a.appointment_date, a.appointment_time, a.status, a.notes
            FROM appointments a
            JOIN patients p ON a.pid = p.pid
            JOIN doctors d ON a.did = d.did
            ORDER BY a.appointment_date DESC, a.appointment_time
        """
        data = self.db.fetch_all(query)
        for row in data:
            self.tree.insert("", "end", values=tuple(row))
        self.load_dropdown_data()

    def filter_tree(self):
        query = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        data = self.db.fetch_all("""
            SELECT a.aid, p.name, d.name, a.appointment_date, a.appointment_time, a.status, a.notes
            FROM appointments a
            JOIN patients p ON a.pid = p.pid
            JOIN doctors d ON a.did = d.did
            ORDER BY a.appointment_date DESC, a.appointment_time
        """)
        for row in data:
            if query in str(row).lower():
                self.tree.insert("", "end", values=tuple(row))

    def add_record(self):
        self.load_dropdown_data()
        super().add_record()

    def edit_record(self):
        self.load_dropdown_data()
        super().edit_record()

    def populate_form(self, record):
        self.form_entries = {}
        if not self.patients:
            ttk.Label(self.form_frame, text="⚠ No patients found. Please add a patient first.", 
                      foreground="red").grid(row=0, column=0, columnspan=2, pady=10)
            btn_frame = ttk.Frame(self.form_frame)
            btn_frame.grid(row=1, column=0, columnspan=2, pady=10)
            ttk.Button(btn_frame, text="Cancel", command=self._destroy_form).pack()
            return
        if not self.doctors:
            ttk.Label(self.form_frame, text="⚠ No doctors found. Please add a doctor first.", 
                      foreground="red").grid(row=0, column=0, columnspan=2, pady=10)
            btn_frame = ttk.Frame(self.form_frame)
            btn_frame.grid(row=1, column=0, columnspan=2, pady=10)
            ttk.Button(btn_frame, text="Cancel", command=self._destroy_form).pack()
            return

        ttk.Label(self.form_frame, text="Patient:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        self.patient_cb = ttk.Combobox(self.form_frame, values=list(self.patients.values()), state="readonly", width=30)
        self.patient_cb.grid(row=0, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(self.form_frame, text="Doctor:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        self.doctor_cb = ttk.Combobox(self.form_frame, values=list(self.doctors.values()), state="readonly", width=30)
        self.doctor_cb.grid(row=1, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(self.form_frame, text="Date (YYYY-MM-DD):").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        self.date_entry = ttk.Entry(self.form_frame, width=30)
        self.date_entry.grid(row=2, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(self.form_frame, text="Time (HH:MM):").grid(row=3, column=0, sticky="e", padx=5, pady=3)
        self.time_entry = ttk.Entry(self.form_frame, width=30)
        self.time_entry.grid(row=3, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(self.form_frame, text="Status:").grid(row=4, column=0, sticky="e", padx=5, pady=3)
        self.status_cb = ttk.Combobox(self.form_frame, values=["Scheduled","Completed","Cancelled"], state="readonly", width=30)
        self.status_cb.grid(row=4, column=1, sticky="w", padx=5, pady=3)
        self.status_cb.set("Scheduled")

        ttk.Label(self.form_frame, text="Notes:").grid(row=5, column=0, sticky="e", padx=5, pady=3)
        self.notes_entry = ttk.Entry(self.form_frame, width=30)
        self.notes_entry.grid(row=5, column=1, sticky="w", padx=5, pady=3)

        if self.form_mode == "edit":
            self.form_entries['aid'] = record['aid']
            self.patient_cb.set(record.get('patient_name', ''))
            self.doctor_cb.set(record.get('doctor_name', ''))
            self.date_entry.insert(0, record.get('appointment_date', ''))
            self.time_entry.insert(0, record.get('appointment_time', ''))
            self.status_cb.set(record.get('status', 'Scheduled'))
            self.notes_entry.insert(0, record.get('notes', ''))

        btn_frame = ttk.Frame(self.form_frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=self.save_record).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self._destroy_form).pack(side="left")

    def save_record(self):
        patient_name = self.patient_cb.get()
        doctor_name = self.doctor_cb.get()
        date = self.date_entry.get().strip()
        time = self.time_entry.get().strip()
        status = self.status_cb.get()
        notes = self.notes_entry.get().strip()

        if not patient_name or not doctor_name or not date:
            messagebox.showerror("Error", "Patient, Doctor, and Date are required.")
            return

        pid = next((k for k, v in self.patients.items() if v == patient_name), None)
        did = next((k for k, v in self.doctors.items() if v == doctor_name), None)
        if not pid or not did:
            messagebox.showerror("Error", "Invalid patient or doctor selection.")
            return

        if self.form_mode == "add":
            self.db.execute_query(
                "INSERT INTO appointments (pid, did, appointment_date, appointment_time, status, notes) VALUES (?,?,?,?,?,?)",
                (pid, did, date, time, status, notes)
            )
            messagebox.showinfo("Success", "Appointment scheduled successfully.")
        else:
            aid = self.form_entries.get('aid')
            self.db.execute_query(
                "UPDATE appointments SET pid=?, did=?, appointment_date=?, appointment_time=?, status=?, notes=? WHERE aid=?",
                (pid, did, date, time, status, notes, aid)
            )
            messagebox.showinfo("Success", "Appointment updated successfully.")
        self._destroy_form()
        self.refresh()

# ================= ROOM FRAME =================
class RoomFrame(BaseFrame):
    def __init__(self, parent, db):
        columns = [
            ("rid", "ID", 50),
            ("room_number", "Room No.", 100),
            ("room_type", "Type", 120),
            ("capacity", "Capacity", 60),
            ("daily_charge", "Daily Charge", 100),
            ("status", "Status", 100)
        ]
        super().__init__(parent, db, "rooms", columns, "rid")

    def populate_form(self, record):
        fields = ["room_number", "room_type", "capacity", "daily_charge", "status"]
        self.form_entries = {}
        row = 0
        for field in fields:
            ttk.Label(self.form_frame, text=field.replace("_"," ").title()+":").grid(row=row, column=0, sticky="e", padx=5, pady=3)
            if field == "status":
                combo = ttk.Combobox(self.form_frame, values=["Available","Occupied","Maintenance"], state="readonly")
                combo.grid(row=row, column=1, sticky="w", padx=5, pady=3)
                combo.set(record.get(field, "Available"))
                self.form_entries[field] = combo
            else:
                entry = ttk.Entry(self.form_frame, width=30)
                entry.grid(row=row, column=1, sticky="w", padx=5, pady=3)
                entry.insert(0, str(record.get(field, "")))
                self.form_entries[field] = entry
            row += 1
        btn_frame = ttk.Frame(self.form_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=self.save_record).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self._destroy_form).pack(side="left")
        if self.form_mode == "edit":
            self.form_entries['rid'] = record['rid']

    def save_record(self):
        data = {f: (e.get() if isinstance(e, ttk.Entry) else e.get()) 
                for f, e in self.form_entries.items() if f != 'rid'}
        if not data['room_number']:
            messagebox.showerror("Error", "Room number required.")
            return
        try:
            capacity = int(data['capacity']) if data['capacity'] else 1
            charge = float(data['daily_charge']) if data['daily_charge'] else 0.0
        except ValueError:
            messagebox.showerror("Error", "Capacity and charge must be numbers.")
            return
        if self.form_mode == "add":
            try:
                self.db.execute_query(
                    "INSERT INTO rooms (room_number, room_type, capacity, daily_charge, status) VALUES (?,?,?,?,?)",
                    (data['room_number'], data['room_type'], capacity, charge, data['status'])
                )
                messagebox.showinfo("Success", "Room added successfully.")
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Room number already exists.")
        else:
            rid = self.form_entries.get('rid')
            self.db.execute_query(
                "UPDATE rooms SET room_number=?, room_type=?, capacity=?, daily_charge=?, status=? WHERE rid=?",
                (data['room_number'], data['room_type'], capacity, charge, data['status'], rid)
            )
            messagebox.showinfo("Success", "Room updated successfully.")
        self._destroy_form()
        self.refresh()

# ================= BILLING FRAME =================
class BillingFrame(BaseFrame):
    def __init__(self, parent, db):
        columns = [
            ("bid", "Bill ID", 60),
            ("patient_name", "Patient", 150),
            ("amount", "Amount", 100),
            ("description", "Description", 200),
            ("payment_date", "Date", 100),
            ("status", "Status", 80)
        ]
        super().__init__(parent, db, "billing", columns, "bid")
        self.patients = {}
        self.load_patients()

    def load_patients(self):
        self.patients = {row['pid']: row['name'] for row in self.db.fetch_all("SELECT pid, name FROM patients")}

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        query = """
            SELECT b.bid, p.name, b.amount, b.description, b.payment_date, b.status
            FROM billing b
            JOIN patients p ON b.pid = p.pid
            ORDER BY b.bid DESC
        """
        data = self.db.fetch_all(query)
        for row in data:
            self.tree.insert("", "end", values=tuple(row))
        self.load_patients()

    def filter_tree(self):
        query = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        data = self.db.fetch_all("""
            SELECT b.bid, p.name, b.amount, b.description, b.payment_date, b.status
            FROM billing b
            JOIN patients p ON b.pid = p.pid
            ORDER BY b.bid DESC
        """)
        for row in data:
            if query in str(row).lower():
                self.tree.insert("", "end", values=tuple(row))

    def add_record(self):
        self.load_patients()
        super().add_record()

    def edit_record(self):
        self.load_patients()
        super().edit_record()

    def populate_form(self, record):
        self.form_entries = {}
        if not self.patients:
            ttk.Label(self.form_frame, text="⚠ No patients found. Please add a patient first.", 
                      foreground="red").grid(row=0, column=0, columnspan=2, pady=10)
            btn_frame = ttk.Frame(self.form_frame)
            btn_frame.grid(row=1, column=0, columnspan=2, pady=10)
            ttk.Button(btn_frame, text="Cancel", command=self._destroy_form).pack()
            return

        ttk.Label(self.form_frame, text="Patient:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        self.patient_cb = ttk.Combobox(self.form_frame, values=list(self.patients.values()), state="readonly", width=30)
        self.patient_cb.grid(row=0, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(self.form_frame, text="Amount ($):").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        self.amount_entry = ttk.Entry(self.form_frame, width=30)
        self.amount_entry.grid(row=1, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(self.form_frame, text="Description:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        self.desc_entry = ttk.Entry(self.form_frame, width=30)
        self.desc_entry.grid(row=2, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(self.form_frame, text="Payment Date (YYYY-MM-DD):").grid(row=3, column=0, sticky="e", padx=5, pady=3)
        self.date_entry = ttk.Entry(self.form_frame, width=30)
        self.date_entry.grid(row=3, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(self.form_frame, text="Status:").grid(row=4, column=0, sticky="e", padx=5, pady=3)
        self.status_cb = ttk.Combobox(self.form_frame, values=["Pending","Paid","Cancelled"], state="readonly", width=30)
        self.status_cb.grid(row=4, column=1, sticky="w", padx=5, pady=3)
        self.status_cb.set("Pending")

        if self.form_mode == "edit":
            self.form_entries['bid'] = record['bid']
            self.patient_cb.set(record.get('patient_name', ''))
            self.amount_entry.insert(0, str(record.get('amount', '')))
            self.desc_entry.insert(0, record.get('description', ''))
            self.date_entry.insert(0, record.get('payment_date', ''))
            self.status_cb.set(record.get('status', 'Pending'))

        btn_frame = ttk.Frame(self.form_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=self.save_record).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self._destroy_form).pack(side="left")

    def save_record(self):
        patient_name = self.patient_cb.get()
        amount_str = self.amount_entry.get().strip()
        desc = self.desc_entry.get().strip()
        date = self.date_entry.get().strip()
        status = self.status_cb.get()

        if not patient_name or not amount_str:
            messagebox.showerror("Error", "Patient and amount are required.")
            return
        try:
            amount = float(amount_str)
        except ValueError:
            messagebox.showerror("Error", "Amount must be a number.")
            return

        pid = next((k for k, v in self.patients.items() if v == patient_name), None)
        if not pid:
            messagebox.showerror("Error", "Invalid patient selection.")
            return

        if self.form_mode == "add":
            self.db.execute_query(
                "INSERT INTO billing (pid, amount, description, payment_date, status) VALUES (?,?,?,?,?)",
                (pid, amount, desc, date, status)
            )
            messagebox.showinfo("Success", "Bill added successfully.")
        else:
            bid = self.form_entries.get('bid')
            self.db.execute_query(
                "UPDATE billing SET pid=?, amount=?, description=?, payment_date=?, status=? WHERE bid=?",
                (pid, amount, desc, date, status, bid)
            )
            messagebox.showinfo("Success", "Bill updated successfully.")
        self._destroy_form()
        self.refresh()

# ================= REPORT FRAME =================
class ReportFrame(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        ttk.Label(self, text="Reports Module", font=("Segoe UI", 14)).pack(pady=20)
        ttk.Button(self, text="Generate Patient List (CSV)", command=self.export_patients).pack(pady=5)
        ttk.Button(self, text="Revenue Report", command=self.revenue_report).pack(pady=5)
        ttk.Button(self, text="Appointments Summary", command=self.appointments_summary).pack(pady=5)

    def export_patients(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return
        data = self.db.fetch_all("SELECT * FROM patients")
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID","Name","Age","Gender","Blood Group","Contact","Address","Reg Date"])
            writer.writerows(data)
        messagebox.showinfo("Export", "Patients exported successfully.")

    def revenue_report(self):
        total = self.db.fetch_one("SELECT SUM(amount) FROM billing WHERE status='Paid'")[0] or 0
        pending = self.db.fetch_one("SELECT SUM(amount) FROM billing WHERE status='Pending'")[0] or 0
        messagebox.showinfo("Revenue Report", f"Total Paid: ${total:,.2f}\nTotal Pending: ${pending:,.2f}")

    def appointments_summary(self):
        today = datetime.now().strftime("%Y-%m-%d")
        count = self.db.fetch_one("SELECT COUNT(*) FROM appointments WHERE appointment_date=?", (today,))[0]
        messagebox.showinfo("Appointments Summary", f"Appointments today: {count}")

# ================= ENTRY POINT =================
if __name__ == "__main__":
    db = Database()
    LoginWindow(db).run()