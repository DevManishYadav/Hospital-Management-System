import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

# ================= DATABASE =================
con = sqlite3.connect("hospital.db")
cur = con.cursor()
cur.execute("PRAGMA foreign_keys = ON")

cur.execute("""
CREATE TABLE IF NOT EXISTS patient(
    pid INTEGER PRIMARY KEY,
    name TEXT,
    age TEXT,
    gender TEXT,
    disease TEXT,
    contact TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS doctor(
    did INTEGER PRIMARY KEY,
    name TEXT,
    specialization TEXT,
    contact TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS appointment(
    aid INTEGER PRIMARY KEY,
    pid INTEGER,
    did INTEGER,
    appointment_date TEXT,
    FOREIGN KEY(pid) REFERENCES patient(pid),
    FOREIGN KEY(did) REFERENCES doctor(did)
)
""")
con.commit()

# ================= PLACEHOLDER =================
def add_placeholder(entry, text):
    entry.insert(0, text)
    entry.config(fg="gray")
    def focus_in(e):
        if entry.get() == text:
            entry.delete(0, tk.END)
            entry.config(fg="black")
    def focus_out(e):
        if entry.get() == "":
            entry.insert(0, text)
            entry.config(fg="gray")
    entry.bind("<FocusIn>", focus_in)
    entry.bind("<FocusOut>", focus_out)

def val(entry, text):
    return "" if entry.get() == text else entry.get()

# ================= ID MANAGEMENT =================
def next_id(table, col):
    cur.execute(f"SELECT MAX({col}) FROM {table}")
    x = cur.fetchone()[0]
    return 1 if x is None else x + 1

def fix_ids(table, col):
    cur.execute(f"SELECT {col} FROM {table} ORDER BY {col}")
    rows = cur.fetchall()
    for i, row in enumerate(rows, start=1):
        if row[0] != i:
            cur.execute(f"UPDATE {table} SET {col}=? WHERE {col}=?", (i, row[0]))
    con.commit()

# ================= PATIENT =================
def load_patients():
    patient_table.delete(*patient_table.get_children())
    cur.execute("SELECT * FROM patient ORDER BY pid")
    for r in cur.fetchall():
        patient_table.insert("", tk.END, values=r)

def add_patient():
    cur.execute("INSERT INTO patient VALUES(?,?,?,?,?,?)",
                (next_id("patient","pid"), val(pname,"Patient Name"), val(page,"Age"),
                 val(pgender,"Gender"), val(pdisease,"Disease"), val(pcontact,"Contact")))
    con.commit()
    load_patients()

def select_patient(e):
    d = patient_table.item(patient_table.focus())["values"]
    if d:
        for ent in (pid,pname,page,pgender,pdisease,pcontact):
            ent.delete(0, tk.END)
            ent.config(fg="black")
        pid.insert(0,d[0]); pname.insert(0,d[1]); page.insert(0,d[2])
        pgender.insert(0,d[3]); pdisease.insert(0,d[4]); pcontact.insert(0,d[5])

def update_patient():
    cur.execute("UPDATE patient SET name=?,age=?,gender=?,disease=?,contact=? WHERE pid=?",
                (val(pname,"Patient Name"), val(page,"Age"), val(pgender,"Gender"),
                 val(pdisease,"Disease"), val(pcontact,"Contact"), pid.get()))
    con.commit()
    load_patients()

def delete_patient():
    cur.execute("DELETE FROM patient WHERE pid=?", (pid.get(),))
    fix_ids("patient","pid")
    con.commit()
    load_patients()

# ================= DOCTOR =================
def load_doctors():
    doctor_table.delete(*doctor_table.get_children())
    cur.execute("SELECT * FROM doctor ORDER BY did")
    for r in cur.fetchall():
        doctor_table.insert("", tk.END, values=r)

def add_doctor():
    cur.execute("INSERT INTO doctor VALUES(?,?,?,?)",
                (next_id("doctor","did"), val(dname,"Doctor Name"),
                 val(dspec,"Specialization"), val(dcontact,"Contact")))
    con.commit()
    load_doctors()

def select_doctor(e):
    d = doctor_table.item(doctor_table.focus())["values"]
    if d:
        for ent in (did,dname,dspec,dcontact):
            ent.delete(0, tk.END)
            ent.config(fg="black")
        did.insert(0,d[0]); dname.insert(0,d[1]); dspec.insert(0,d[2]); dcontact.insert(0,d[3])

def update_doctor():
    cur.execute("UPDATE doctor SET name=?,specialization=?,contact=? WHERE did=?",
                (val(dname,"Doctor Name"), val(dspec,"Specialization"), val(dcontact,"Contact"), did.get()))
    con.commit()
    load_doctors()

def delete_doctor():
    cur.execute("DELETE FROM doctor WHERE did=?", (did.get(),))
    fix_ids("doctor","did")
    con.commit()
    load_doctors()

# ================= APPOINTMENT =================
def load_appointments():
    app_table.delete(*app_table.get_children())
    cur.execute("""
    SELECT a.aid, p.name, d.name, a.appointment_date
    FROM appointment a
    JOIN patient p ON a.pid=p.pid
    JOIN doctor d ON a.did=d.did
    ORDER BY a.aid
    """)
    for r in cur.fetchall():
        app_table.insert("", tk.END, values=r)

def add_appointment():
    cur.execute("INSERT INTO appointment VALUES(?,?,?,?)",
                (next_id("appointment","aid"), val(apid,"Patient ID"), val(adid,"Doctor ID"), val(adate,"Date (DD-MM-YYYY)")))
    con.commit()
    load_appointments()

def select_appointment(e):
    d = app_table.item(app_table.focus())["values"]
    if d:
        aid.delete(0, tk.END); adate.delete(0, tk.END)
        aid.insert(0,d[0]); adate.insert(0,d[3])

def update_appointment():
    cur.execute("UPDATE appointment SET appointment_date=? WHERE aid=?",
                (val(adate,"Date (DD-MM-YYYY)"), aid.get()))
    con.commit()
    load_appointments()

def delete_appointment():
    cur.execute("DELETE FROM appointment WHERE aid=?", (aid.get(),))
    fix_ids("appointment","aid")
    con.commit()
    load_appointments()

# ================= GUI =================
root = tk.Tk()
root.title("Hospital Management System")
root.state("zoomed")

tk.Label(root,text="🏥 Hospital Management System", font=("Arial",22,"bold"), bg="#0b5ed7", fg="white").pack(fill="x")

tabs = ttk.Notebook(root)
tabs.pack(fill="both", expand=True)

# --- PATIENT TAB ---
pt=tk.Frame(tabs); tabs.add(pt,text="Patient")
pid=tk.Entry(pt); pname=tk.Entry(pt); page=tk.Entry(pt)
pgender=tk.Entry(pt); pdisease=tk.Entry(pt); pcontact=tk.Entry(pt)
for e in (pid,pname,page,pgender,pdisease,pcontact): e.pack(pady=3)
for e,t in zip((pid,pname,page,pgender,pdisease,pcontact), ("ID","Name","Age","Gender","Disease","Contact")):
    add_placeholder(e,t)
tk.Button(pt,text="Add",command=add_patient).pack()
tk.Button(pt,text="Update",command=update_patient).pack()
tk.Button(pt,text="Delete",command=delete_patient).pack()
patient_table=ttk.Treeview(pt,columns=("ID","Name","Age","Gender","Disease","Contact"),show="headings")
for c in patient_table["columns"]: patient_table.heading(c,text=c)
patient_table.pack(fill="both",expand=True)
patient_table.bind("<ButtonRelease-1>",select_patient)
load_patients()

# --- DOCTOR TAB ---
dt=tk.Frame(tabs); tabs.add(dt,text="Doctor")
did=tk.Entry(dt); dname=tk.Entry(dt); dspec=tk.Entry(dt); dcontact=tk.Entry(dt)
for e in (did,dname,dspec,dcontact): e.pack(pady=3)
for e,t in zip((did,dname,dspec,dcontact), ("ID","Name","Specialization","Contact")):
    add_placeholder(e,t)
tk.Button(dt,text="Add",command=add_doctor).pack()
tk.Button(dt,text="Update",command=update_doctor).pack()
tk.Button(dt,text="Delete",command=delete_doctor).pack()
doctor_table=ttk.Treeview(dt,columns=("ID","Name","Specialization","Contact"),show="headings")
for c in doctor_table["columns"]: doctor_table.heading(c,text=c)
doctor_table.pack(fill="both",expand=True)
doctor_table.bind("<ButtonRelease-1>",select_doctor)
load_doctors()

# --- APPOINTMENT TAB ---
at=tk.Frame(tabs); tabs.add(at,text="Appointment")
aid=tk.Entry(at); apid=tk.Entry(at); adid=tk.Entry(at); adate=tk.Entry(at)
for e in (aid,apid,adid,adate): e.pack(pady=4)
for e,t in zip((aid,apid,adid,adate), ("Appointment ID","Patient ID","Doctor ID","Date")):
    add_placeholder(e,t)
tk.Button(at,text="Add",command=add_appointment).pack()
tk.Button(at,text="Update",command=update_appointment).pack()
tk.Button(at,text="Delete",command=delete_appointment).pack()
app_table=ttk.Treeview(at,columns=("AppointmentID","Patient","Doctor","Date"),show="headings")
for c in app_table["columns"]: app_table.heading(c,text=c)
app_table.pack(fill="both",expand=True)
app_table.bind("<ButtonRelease-1>",select_appointment)
load_appointments()

root.mainloop()
