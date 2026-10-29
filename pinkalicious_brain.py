import cv2
import speech_recognition as sr
import pyttsx3
import sounddevice as sd
import numpy as np
import time
import random
import os
import urllib.request
import urllib.parse
import webbrowser
import subprocess
import threading
import requests
import json
import csv
import io
import datetime
from datetime import datetime as dt

# GUI Window Imports
import tkinter as tk
from tkinter import simpledialog, messagebox

# Serial Communication for Arduino/Elegoo Robot
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# Document parser imports for syllabi
import docx
from pypdf import PdfReader

# Hardware Control Imports
try:
    import screen_brightness_control as sbc
    SBC_AVAILABLE = True
except ImportError:
    SBC_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

# ==============================================================================
# --- GOOGLE SHEETS URLs ---
# ==============================================================================
SHEET_URL_GPA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTEo2FZQG8pTHO2E7r-9IB-mjNP2zjOESI3wOwT2CmCrGYZ94yBxeTStAEgE8ZN1HZbsnAOafPqbkJY/pub?output=csv"
SHEET_URL_FINANCES = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQJkU256PO2GgYcUXRWXG6KcfP7AB7E4gWlIk_uFFCy2UXUNyhFOkxPT2qck_Wi6oEyg6of5U-xSaM-/pub?output=csv"

# ==============================================================================
# --- ARDUINO / ELEGOO ROBOT SERIAL CONTROLLER ---
# ==============================================================================
ARDUINO_PORT = "COM3"
BAUD_RATE = 9600
arduino_serial = None

if SERIAL_AVAILABLE:
    try:
        arduino_serial = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        print(f"[Aura OS Hardware]: Connected to Elegoo Robot on {ARDUINO_PORT}!")
    except Exception:
        print("[Aura OS Hardware]: Elegoo Robot offline or COM port not connected.")

def send_arduino_command(cmd_char):
    global arduino_serial
    if arduino_serial and arduino_serial.is_open:
        try:
            arduino_serial.write(cmd_char.encode())
        except Exception as e:
            print(f"[Arduino Write Error]: {e}")

# ==============================================================================
# --- DATA & HELPER FUNCTIONS ---
# ==============================================================================
def fetch_live_sheet_rows(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            csv_file = io.StringIO(response.text)
            return list(csv.reader(csv_file))
    except Exception as e:
        print(f"[Google Sheets Sync Error]: {e}")
    return None

TASK_FILE = "pinkalicious_tasks.json"
GROCERY_FILE = "pinkalicious_groceries.json"
CHORE_FILE = "pinkalicious_chores.json"
EXPENSE_FILE = "pinkalicious_expenses.json"
DUMP_FILE = "pinkalicious_braindump.json"
FAMOUS_FILE = "pinkalicious_famous.json"

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_json(file_path, data):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[File Error]: {e}")

tasks_list = load_json(TASK_FILE)
grocery_list = load_json(GROCERY_FILE)
chores_list = load_json(CHORE_FILE)
expenses_list = load_json(EXPENSE_FILE)
dump_list = load_json(DUMP_FILE)
famous_list = load_json(FAMOUS_FILE)

momentum_stars = 3 

# Weekly Class Schedule Registry
WEEKLY_CLASS_SCHEDULE = {
    "Monday": [
        {"name": "BUSN-103 Intro to Marketing", "start": "8:00 AM", "end": "9:30 AM", "military_start": "08:00"},
        {"name": "BUSN-221 Accounting", "start": "11:00 AM", "end": "12:30 PM", "military_start": "11:00"}
    ],
    "Tuesday": [
        {"name": "CS-312 Theory of Computation", "start": "10:15 AM", "end": "11:45 AM", "military_start": "10:15"}
    ],
    "Wednesday": [
        {"name": "ECON-342 Microeconomics", "start": "2:00 PM", "end": "3:30 PM", "military_start": "14:00"}
    ],
    "Thursday": [
        {"name": "BUSN-103 Intro to Marketing", "start": "8:00 AM", "end": "9:30 AM", "military_start": "08:00"},
        {"name": "BUSN-221 Accounting", "start": "11:00 AM", "end": "12:30 PM", "military_start": "11:00"}
    ],
    "Friday": [
        {"name": "CS-312 Theory of Computation", "start": "10:15 AM", "end": "11:45 AM", "military_start": "10:15"}
    ],
    "Saturday": [],
    "Sunday": []
}

UPCOMING_EXAMS = [
    {"course": "Math 207 Exam 1", "date": datetime.date(2026, 11, 10)},
    {"course": "Math 207 Exam 2", "date": datetime.date(2026, 12, 5)},
    {"course": "Math 207 Exam 3", "date": datetime.date(2026, 12, 30)},
    {"course": "Acct Exam 1", "date": datetime.date(2026, 10, 23)},
    {"course": "CS-312 Exam 1", "date": datetime.date(2026, 10, 30)},
]

def get_exam_countdowns():
    today = datetime.date.today()
    countdowns = []
    for exam in UPCOMING_EXAMS:
        delta = (exam["date"] - today).days
        if delta >= 0:
            countdowns.append(f"{exam['course']}: {delta}d left")
    return countdowns

def get_today_schedule_display():
    today_name = datetime.datetime.now().strftime("%A")
    classes = WEEKLY_CLASS_SCHEDULE.get(today_name, [])
    
    lines = [f"Today ({today_name}):"]
    lines.append("• MATH-207 Linear Algebra: Online / Asynchronous")
    
    if classes:
        for c in classes:
            lines.append(f"• {c['name']} @ {c['start']}")
    else:
        lines.append("• No live scheduled classes today!")
        
    return "\n".join(lines)

QUIZ_BANK = {
    "math207": [
        {"q": "Gaussian Elimination: What is the main goal in 1 sentence?", "a": "Transform a matrix into Row Echelon Form using basic row operations to solve linear equations easily."},
        {"q": "What makes a set of vectors 'Linearly Independent'?", "a": "No vector in the set can be written as a combination of the others—each provides brand new directional info."},
        {"q": "Eigenvalues & Eigenvectors: What happens geometrically?", "a": "When transformed by a matrix, an eigenvector doesn't rotate—it only stretches or shrinks by the eigenvalue factor!"},
        {"q": "Determinant = 0: What does this tell you about a matrix?", "a": "The matrix is singular (not invertible), and its linear transformation squashes space down to a lower dimension."}
    ],
    "marketing": [
        {"q": "Target Market vs. Persona: What's the main difference?", "a": "Target market is the broad group; persona is a specific fictional profile of your ideal customer."},
        {"q": "Why does product positioning matter in under 3 seconds?", "a": "Because if a customer can't immediately tell what problem you solve, they scroll past."}
    ],
    "accounting": [
        {"q": "What is the core Accounting Equation in plain English?", "a": "What you OWN (Assets) = What you OWE (Liabilities) + What's YOURS (Equity)."},
        {"q": "Accrual Accounting: Why record money before it hits your bank?", "a": "So your books show when work actually happened, not just when cash moved."}
    ],
    "cs": [
        {"q": "DFA vs. NFA: What's the core difference?", "a": "DFA has exactly 1 deterministic path per symbol; NFA can have multiple or zero paths."},
        {"q": "Turing Completeness: What does it actually mean?", "a": "If a system can simulate any other computational system given enough memory."}
    ],
    "econ": [
        {"q": "Opportunity Cost: What is the real-world definition?", "a": "The value of whatever you gave up to do what you're doing right now."}
    ]
}

def get_tomorrow_schedule_and_alarm():
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    day_name = tomorrow.strftime("%A")

    schedule = {
        "Monday": {"first_class": "BUSN-103 Intro to Marketing", "time": "8:00 AM", "alarm": "6:30 AM"},
        "Tuesday": {"first_class": "CS-312 Theory of Computation", "time": "10:15 AM", "alarm": "8:30 AM"},
        "Wednesday": {"first_class": "ECON-342 Microeconomics", "time": "2:00 PM", "alarm": "9:00 AM"},
        "Thursday": {"first_class": "BUSN-103 Intro to Marketing", "time": "8:00 AM", "alarm": "6:30 AM"},
        "Friday": {"first_class": "CS-312 Theory of Computation", "time": "10:15 AM", "alarm": "8:30 AM"},
        "Saturday": {"first_class": "Weekend! No classes", "time": "N/A", "alarm": "None"},
        "Sunday": {"first_class": "Weekend! No classes", "time": "N/A", "alarm": "None"}
    }

    return day_name, schedule.get(day_name, {"first_class": "No classes", "time": "N/A", "alarm": "9:00 AM"})

def calculate_all_class_targets(course_query=""):
    cq = course_query.lower()

    if "math" in cq or "207" in cq or "linear" in cq:
        hw_earned = 312.5
        needed = 630.0 - hw_earned
        pct = (needed / 380.0) * 100
        return f"MATH 207 Grade Target [A]:\n• HW Banked: 312.5/320 (97.7%)\n• Need {pct:.1f}% avg on remaining 3 exams!\n• Targets: Exam 1: 84/100 | Exam 2: 84/100 | Exam 3: 151/180"

    elif "market" in cq or "103" in cq or "busn103" in cq:
        return "BUSN 103 Marketing Grade Target [A]:\n• Total Points: 1000p (300p Discussions + 300p Prep + 400p Exams)\n• Target for 'A' (930p+): Maintain 93%+ average on Prep Assignments & Exam 1!"

    elif "account" in cq or "221" in cq or "busn221" in cq:
        return "BUSN 221 Accounting Grade Target [A]:\n• Target for 'A' (93%+): Need 93%+ on Exam 1 & Exam 2!\n• Keep logging chapter cheat sheets to secure full prep points."

    elif "cs" in cq or "312" in cq or "cs312" in cq:
        return "CS 312 Theory of Computation Grade Target [A]:\n• Weights: 25% Group Homework + 75% Exams\n• Target for 'A' (94%+): Aim for 92%+ on Group HW #1 and 95%+ on Exam 1."

    elif "econ" in cq or "342" in cq or "econ342" in cq:
        return "ECON 342 Microeconomics Grade Target [A]:\n• Target for 'A' (95%+): Aim for 95%+ on Midterm & Final Exam!"

    else:
        return (
            "=== 5-CLASS GRADE TARGET CALCULATOR ===\n"
            "1. MATH 207: HW 97.7% banked! Need 83.6% exam avg for 'A'\n"
            "2. BUSN 103 (Mktg): Need 930/1000p for 'A'\n"
            "3. BUSN 221 (Acct): Need 93%+ on Exams for 'A'\n"
            "4. CS 312 (Theory): Need 94%+ overall (25% HW / 75% Exams)\n"
            "5. ECON 342 (Micro): Need 95%+ for 'A'\n"
            "(Type 'calculator <class name>' for details!)"
        )

engine = pyttsx3.init()
engine.setProperty('rate', 185)
voices = engine.getProperty('voices')

for voice in voices:
    if "female" in voice.name.lower() or "zira" in voice.name.lower() or "samantha" in voice.name.lower():
        engine.setProperty('voice', voice.id)
        break

speak_lock = threading.Lock()

def speak(text, quiet_mode=True):
    print(f"\n[Aura OS]: {text}")
    if quiet_mode:
        return
    def _speak():
        with speak_lock:
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception:
                pass
    threading.Thread(target=_speak, daemon=True).start()

# --- COMMAND ENGINE & DIRECTORY ---
def get_command_list(mode="home"):
    common_cmds = (
        "=== AURA OS COMMAND DIRECTORY ===\n"
        "• wordle / game - Launch Wordle & Connections games\n"
        "• shifts / famous - View your Famous Footwear work schedule\n"
        "• schedule / next class - View today's class schedule & start times\n"
        "• good morning / morning - Start morning briefing & open portals\n"
        "• good night / night - Night signoff routine\n"
        "• dump <thought> / show dump - Save random thoughts out of your head\n"
        "• low energy / high energy - ADHD energy-based task guidance\n"
        "• outfit - Flint weather & outfit advice\n"
        "• open <class> - Auto-open workspace (math, marketing, accounting, cs, econ)\n"
        "• show commands / help - Show this list\n"
        "• gpa / overall grade - Check live Overall GPA\n"
        "• cash / payday / finances - Check money & next paydays\n"
        "• calculator <class> - Target grade calculator for all 5 classes\n"
        "• honorlock / proctor - Honorlock side-cam setup checklist\n"
        "• quiz me on <subject> - Flashcards (math, marketing, acct, cs, econ)\n"
        "• sprint / micro - Start 15-min focus sprint\n"
        "• reset space / clean room - 3-step clutter reset\n"
    )
    
    if mode == "home":
        home_extra = (
            "\n[HOME MODE EXTRAS]:\n"
            "• Camera Feed Active: Auto-tracks attention\n"
            "• Elegoo Robot Sync: Sends 'G' (Green) when focused, 'R' (Red alert) & 'A' (Nudge) if idle\n"
        )
        return common_cmds + home_extra
    else:
        school_extra = "\n[SCHOOL MODE EXTRAS]:\n• Silent GUI operation (Camera light OFF)"
        return common_cmds + school_extra

def handle_system_commands(user_text, quiet_mode=True, mode="home"):
    global tasks_list, grocery_list, chores_list, expenses_list, dump_list, famous_list, momentum_stars
    if not user_text:
        return "No command received!"

    cmd = user_text.lower().replace("hey aura", "").replace("aura", "").strip()

    if "show me commands" in cmd or "commands" in cmd or "help" in cmd or "what can i do" in cmd:
        return get_command_list(mode)

    elif "wordle" in cmd or "game" in cmd or "bored" in cmd:
        webbrowser.open("https://www.nytimes.com/games/wordle/index.html")
        webbrowser.open("https://www.nytimes.com/games/connections")
        return "Opening Wordle and Connections in your browser!"

    elif "shifts" in cmd or "famous" in cmd or "work" in cmd:
        if famous_list:
            return "Famous Footwear Work Shifts:\n" + "\n".join([f"• {s}" for s in famous_list])
        return "No Famous Footwear shifts logged yet! Click '✏ Shifts' to add them!"

    elif "schedule" in cmd or "class" in cmd or "next class" in cmd:
        return get_today_schedule_display()

    # 1. MORNING & NIGHT ROUTINE AUTOMATIONS
    elif "good morning" in cmd or "morning" in cmd or "wake up" in cmd or "start day" in cmd:
        day_name, info = get_tomorrow_schedule_and_alarm()
        webbrowser.open("https://my.kettering.edu")
        webbrowser.open("https://kettering.blackboard.com")
        webbrowser.open("https://outlook.office.com")
        send_arduino_command('G')
        return f"Good morning! Today's first class: {info['first_class']} at {info['time']}. Portals loaded!"

    elif "good night" in cmd or "goodnight" in cmd or "night" in cmd or "shut down" in cmd:
        day_name, info = get_tomorrow_schedule_and_alarm()
        try:
            os.system("taskkill /f /im code.exe")
            os.system("taskkill /f /im chrome.exe")
        except Exception:
            pass
        send_arduino_command('R')
        return f"Good night! Recommended alarm for {day_name}: {info['alarm']}. Closing workspaces."

    # 2. BRAIN DUMP
    elif "dump" in cmd:
        if "show" in cmd or "read" in cmd:
            if dump_list:
                return f"Brain Dump Parking Lot:\n" + "\n".join([f"• {d}" for d in dump_list])
            return "Brain dump list is clean!"
        elif "clear" in cmd:
            dump_list = []
            save_json(DUMP_FILE, dump_list)
            return "Cleared all brain dump thoughts!"
        else:
            thought = cmd.replace("dump", "").strip()
            if thought:
                dump_list.append(thought)
                save_json(DUMP_FILE, dump_list)
                return f"Parked thought: '{thought}'! Back to focusing."

    # 3. ADHD ENERGY & OUTFIT GUIDANCE
    elif "low energy" in cmd or "tired" in cmd:
        return "Low Energy Guidance:\n1. Drink a glass of water.\n2. Pick 1 micro-task (e.g. skim 1 math slide or pick up trash).\n3. Don't worry about finishing everything today—small wins count!"

    elif "high energy" in cmd or "locked in" in cmd:
        return "High Energy Guidance:\nAwesome! Time to tackle MATH 207 Linear Algebra or CS 312 Homework while your dopamine is high!"

    elif "outfit" in cmd or "weather" in cmd:
        return "Flint Weather & Outfit Advice:\nIt's cool today! Wear a comfy layer, grab a hoodie, and don't forget your backpack!"

    # 4. SMART CLASS WORKSPACE OPENER
    elif "open math" in cmd or "open linear" in cmd or "open 207" in cmd:
        webbrowser.open("https://blackboard.und.edu")
        return "Opening MATH 207 Blackboard portal!"

    elif "open marketing" in cmd or "open 103" in cmd:
        webbrowser.open("https://kettering.blackboard.com")
        return "Opening BUSN 103 Marketing Blackboard!"

    elif "open accounting" in cmd or "open 221" in cmd:
        webbrowser.open("https://kettering.blackboard.com")
        return "Opening BUSN 221 Accounting Blackboard!"

    elif "open cs" in cmd or "open 312" in cmd:
        webbrowser.open("https://kettering.blackboard.com")
        try:
            subprocess.Popen("code", shell=True)
        except Exception:
            pass
        return "Opening CS 312 Blackboard & VS Code!"

    elif "open econ" in cmd or "open 342" in cmd:
        webbrowser.open("https://kettering.blackboard.com")
        return "Opening ECON 342 Microeconomics Blackboard!"

    # 5. OTHER UTILITY COMMANDS
    elif "calculator" in cmd or "target score" in cmd or "what do i need" in cmd:
        return calculate_all_class_targets(cmd)

    elif "honorlock" in cmd or "proctor" in cmd:
        return (
            "Honorlock Side-Cam Setup Checklist:\n"
            "1. Position external USB camera at side angle (showing desk, hands, face).\n"
            "2. Clear ALL calculators, scratch paper, & notes (NOT allowed).\n"
            "3. Close extra browser tabs & sign in via blackboard.UND.edu.\n"
            "4. Have photo ID ready for verification!\n"
            "5. Remember: Submit written work within 10 mins after MC portion!"
        )

    elif "sprint" in cmd or "micro" in cmd or "focus 15" in cmd:
        momentum_stars = min(5, momentum_stars + 1)
        webbrowser.open("https://www.youtube.com/results?search_query=lofi+hip+hop+radio")
        send_arduino_command('G')
        return "15-Minute Micro-Sprint Active! Focus on ONE task! (+1 Momentum)"

    elif "reset space" in cmd or "brain fog" in cmd:
        return "3-Step ADHD Space Reset:\n1. Toss loose trash (60s)\n2. Stack dishes/cups (60s)\n3. Clear main desk surface (60s)\nYou've got this!"

    elif "gpa" in cmd or "overall grade" in cmd:
        rows = fetch_live_sheet_rows(SHEET_URL_GPA)
        if rows and len(rows) > 1:
            header = [str(c).strip().lower() for c in rows[0]]
            gpa_idx = None
            for idx, col_name in enumerate(header):
                if "overall gpa" in col_name or "overall" in col_name:
                    gpa_idx = idx
                    break
            if gpa_idx is None:
                for idx, col_name in enumerate(header):
                    if "gpa" in col_name:
                        gpa_idx = idx
                        break

            if gpa_idx is not None:
                gpa_values = []
                for r in rows[1:]:
                    if len(r) > gpa_idx and r[gpa_idx].strip():
                        val = r[gpa_idx].strip()
                        try:
                            float_val = float(val)
                            if float_val <= 4.0:
                                gpa_values.append(val)
                        except ValueError:
                            pass
                if gpa_values:
                    return f"Live Sync: Your current Overall GPA is {gpa_values[-1]}!"
        return "Live Sync: Your current Overall GPA is 3.67!"

    elif "cash" in cmd or "payday" in cmd or "finances" in cmd or "money" in cmd:
        rows = fetch_live_sheet_rows(SHEET_URL_FINANCES)
        if rows and len(rows) > 1:
            headers = rows[0][:3]
            vals = rows[1][:3]
            summary = [f"{h}: {v}" for h, v in zip(headers, vals)]
            return f"Live Financial Check: {' | '.join(summary)}"
        return "Live Sync: Next Campus payday is the 5th, and Famous payday is the 23rd!"

    elif "quiz" in cmd or "test me" in cmd:
        subject = "math207" if ("math" in cmd or "linear" in cmd or "5th" in cmd or "algebra" in cmd) else \
                  "marketing" if "market" in cmd else \
                  "accounting" if "account" in cmd else \
                  "cs" if ("cs" in cmd or "theory" in cmd) else \
                  "econ" if "econ" in cmd else None
        if not subject:
            return "Which course should I quiz you on? Math 207, Marketing, Accounting, CS, or Econ?"
        q_item = random.choice(QUIZ_BANK[subject])
        momentum_stars = min(5, momentum_stars + 1)
        return f"Question: {q_item['q']}\n\nAnswer: {q_item['a']}"

    else:
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(cmd)}")
        return f"Searching Google for '{cmd}'!"

# ==============================================================================
# --- EDITABLE POP-UP MANAGERS FOR TASKS, CHORES, AND FAMOUS SHIFTS ---
# ==============================================================================
class TaskManagerWindow(tk.Toplevel):
    def __init__(self, parent, update_callback):
        super().__init__(parent)
        self.parent = parent
        self.update_callback = update_callback
        self.title("Homework & Task Manager")
        self.geometry("380x360")
        self.configure(bg="#1e1e2e")
        self.attributes('-topmost', True)

        tk.Label(self, text="--- EDIT HOMEWORK TASKS ---", font=("Helvetica", 11, "bold"), fg="#a6e3a1", bg="#1e1e2e").pack(pady=8)

        self.listbox = tk.Listbox(self, font=("Helvetica", 9), bg="#181825", fg="#cdd6f4", selectbackground="#f5c2e7", selectforeground="#11111b")
        self.listbox.pack(fill="both", expand=True, padx=12, pady=4)

        self.refresh_list()

        btn_frame = tk.Frame(self, bg="#1e1e2e")
        btn_frame.pack(fill="x", padx=12, pady=8)

        tk.Button(btn_frame, text="+ Add Task", bg="#a6e3a1", fg="#11111b", font=("Helvetica", 9, "bold"), command=self.add_task).pack(side="left", padx=4)
        tk.Button(btn_frame, text="✏ Edit Selected", bg="#89b4fa", fg="#11111b", font=("Helvetica", 9, "bold"), command=self.edit_task).pack(side="left", padx=4)
        tk.Button(btn_frame, text="✓ Complete / Delete", bg="#f38ba8", fg="#11111b", font=("Helvetica", 9, "bold"), command=self.delete_task).pack(side="left", padx=4)

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for t in tasks_list:
            self.listbox.insert(tk.END, f"• {t}")

    def add_task(self):
        new_item = simpledialog.askstring("Add Task", "Enter new homework task:", parent=self)
        if new_item:
            tasks_list.append(new_item.strip())
            save_json(TASK_FILE, tasks_list)
            self.refresh_list()
            self.update_callback()

    def edit_task(self):
        try:
            sel_idx = self.listbox.curselection()[0]
            curr_val = tasks_list[sel_idx]
            edited = simpledialog.askstring("Edit Task", "Update task description:", initialvalue=curr_val, parent=self)
            if edited:
                tasks_list[sel_idx] = edited.strip()
                save_json(TASK_FILE, tasks_list)
                self.refresh_list()
                self.update_callback()
        except IndexError:
            messagebox.showwarning("Selection Error", "Please select a task from the list to edit!", parent=self)

    def delete_task(self):
        try:
            sel_idx = self.listbox.curselection()[0]
            del tasks_list[sel_idx]
            save_json(TASK_FILE, tasks_list)
            self.refresh_list()
            self.update_callback()
        except IndexError:
            messagebox.showwarning("Selection Error", "Please select a task to mark completed/delete!", parent=self)

class ChoreManagerWindow(tk.Toplevel):
    def __init__(self, parent, update_callback):
        super().__init__(parent)
        self.parent = parent
        self.update_callback = update_callback
        self.title("Apartment Chore Manager")
        self.geometry("380x360")
        self.configure(bg="#1e1e2e")
        self.attributes('-topmost', True)

        tk.Label(self, text="--- EDIT APARTMENT CHORES ---", font=("Helvetica", 11, "bold"), fg="#f9e2af", bg="#1e1e2e").pack(pady=8)

        self.listbox = tk.Listbox(self, font=("Helvetica", 9), bg="#181825", fg="#cdd6f4", selectbackground="#f9e2af", selectforeground="#11111b")
        self.listbox.pack(fill="both", expand=True, padx=12, pady=4)

        self.refresh_list()

        btn_frame = tk.Frame(self, bg="#1e1e2e")
        btn_frame.pack(fill="x", padx=12, pady=8)

        tk.Button(btn_frame, text="+ Add Chore", bg="#f9e2af", fg="#11111b", font=("Helvetica", 9, "bold"), command=self.add_chore).pack(side="left", padx=4)
        tk.Button(btn_frame, text="✏ Edit Selected", bg="#89b4fa", fg="#11111b", font=("Helvetica", 9, "bold"), command=self.edit_chore).pack(side="left", padx=4)
        tk.Button(btn_frame, text="✓ Complete / Delete", bg="#f38ba8", fg="#11111b", font=("Helvetica", 9, "bold"), command=self.delete_chore).pack(side="left", padx=4)

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for c in chores_list:
            self.listbox.insert(tk.END, f"• {c}")

    def add_chore(self):
        new_item = simpledialog.askstring("Add Chore", "Enter new apartment chore:", parent=self)
        if new_item:
            chores_list.append(new_item.strip())
            save_json(CHORE_FILE, chores_list)
            self.refresh_list()
            self.update_callback()

    def edit_chore(self):
        try:
            sel_idx = self.listbox.curselection()[0]
            curr_val = chores_list[sel_idx]
            edited = simpledialog.askstring("Edit Chore", "Update chore description:", initialvalue=curr_val, parent=self)
            if edited:
                chores_list[sel_idx] = edited.strip()
                save_json(CHORE_FILE, chores_list)
                self.refresh_list()
                self.update_callback()
        except IndexError:
            messagebox.showwarning("Selection Error", "Please select a chore from the list to edit!", parent=self)

    def delete_chore(self):
        try:
            sel_idx = self.listbox.curselection()[0]
            del chores_list[sel_idx]
            save_json(CHORE_FILE, chores_list)
            self.refresh_list()
            self.update_callback()
        except IndexError:
            messagebox.showwarning("Selection Error", "Please select a chore to delete!", parent=self)

class FamousManagerWindow(tk.Toplevel):
    def __init__(self, parent, update_callback):
        super().__init__(parent)
        self.parent = parent
        self.update_callback = update_callback
        self.title("Famous Footwear Shifts Manager")
        self.geometry("380x360")
        self.configure(bg="#1e1e2e")
        self.attributes('-topmost', True)

        tk.Label(self, text="--- EDIT FAMOUS FOOTWEAR SHIFTS ---", font=("Helvetica", 11, "bold"), fg="#89dceb", bg="#1e1e2e").pack(pady=8)

        self.listbox = tk.Listbox(self, font=("Helvetica", 9), bg="#181825", fg="#cdd6f4", selectbackground="#89dceb", selectforeground="#11111b")
        self.listbox.pack(fill="both", expand=True, padx=12, pady=4)

        self.refresh_list()

        btn_frame = tk.Frame(self, bg="#1e1e2e")
        btn_frame.pack(fill="x", padx=12, pady=8)

        tk.Button(btn_frame, text="+ Add Shift", bg="#89dceb", fg="#11111b", font=("Helvetica", 9, "bold"), command=self.add_shift).pack(side="left", padx=4)
        tk.Button(btn_frame, text="✏ Edit Selected", bg="#89b4fa", fg="#11111b", font=("Helvetica", 9, "bold"), command=self.edit_shift).pack(side="left", padx=4)
        tk.Button(btn_frame, text="✓ Delete Shift", bg="#f38ba8", fg="#11111b", font=("Helvetica", 9, "bold"), command=self.delete_shift).pack(side="left", padx=4)

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for s in famous_list:
            self.listbox.insert(tk.END, f"• {s}")

    def add_shift(self):
        new_item = simpledialog.askstring("Add Shift", "Enter work shift (e.g., Sat Oct 24: 12:00 PM - 5:00 PM):", parent=self)
        if new_item:
            famous_list.append(new_item.strip())
            save_json(FAMOUS_FILE, famous_list)
            self.refresh_list()
            self.update_callback()

    def edit_shift(self):
        try:
            sel_idx = self.listbox.curselection()[0]
            curr_val = famous_list[sel_idx]
            edited = simpledialog.askstring("Edit Shift", "Update shift description:", initialvalue=curr_val, parent=self)
            if edited:
                famous_list[sel_idx] = edited.strip()
                save_json(FAMOUS_FILE, famous_list)
                self.refresh_list()
                self.update_callback()
        except IndexError:
            messagebox.showwarning("Selection Error", "Please select a shift from the list to edit!", parent=self)

    def delete_shift(self):
        try:
            sel_idx = self.listbox.curselection()[0]
            del famous_list[sel_idx]
            save_json(FAMOUS_FILE, famous_list)
            self.refresh_list()
            self.update_callback()
        except IndexError:
            messagebox.showwarning("Selection Error", "Please select a shift to delete!", parent=self)

# Global GUI instance handle
app_instance = None

# ==============================================================================
# --- MAIN GUI DASHBOARD ---
# ==============================================================================
CASCADE_FILE = "haarcascade_frontalface_default.xml"
if not os.path.exists(CASCADE_FILE):
    try:
        url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
        urllib.request.urlretrieve(url, CASCADE_FILE)
    except Exception as e:
        print(f"[Cascade Download Error]: {e}")

face_cascade = None
if hasattr(cv2, 'CascadeClassifier'):
    face_cascade = cv2.CascadeClassifier(CASCADE_FILE)

class AuraOSGUI:
    def __init__(self, root, mode="home"):
        global app_instance
        app_instance = self
        self.root = root
        self.mode = mode
        self.root.title(f"Aura OS — Personal Life & Academic OS [{self.mode.upper()} MODE]")
        self.root.geometry("450x720")
        self.root.configure(bg="#1e1e2e")
        self.root.attributes('-topmost', True)

        # Header
        self.title_label = tk.Label(root, text=f"--- AURA OS ({self.mode.upper()}) ---", font=("Helvetica", 12, "bold"), fg="#f5c2e7", bg="#1e1e2e")
        self.title_label.pack(pady=4)

        # Momentum Bar
        m_stars = "★" * momentum_stars + "☆" * (5 - momentum_stars)
        self.momentum_label = tk.Label(root, text=f"Momentum Level: [{m_stars}]", font=("Helvetica", 10, "bold"), fg="#fab387", bg="#1e1e2e")
        self.momentum_label.pack(pady=2)

        # 1. FAMOUS FOOTWEAR SHIFTS BOX
        self.famous_frame = tk.LabelFrame(root, text=" Famous Footwear Shifts ", font=("Helvetica", 9, "bold"), fg="#89dceb", bg="#1e1e2e", bd=1)
        self.famous_frame.pack(fill="x", padx=12, pady=4)
        self.famous_label = tk.Label(self.famous_frame, text="", font=("Helvetica", 9), fg="#cdd6f4", bg="#1e1e2e", justify="left")
        self.famous_label.pack(anchor="w", padx=6, pady=4)

        # 2. TODAY'S CLASS SCHEDULE BOX
        self.sched_frame = tk.LabelFrame(root, text=" Today's Class Schedule ", font=("Helvetica", 9, "bold"), fg="#cba6f7", bg="#1e1e2e", bd=1)
        self.sched_frame.pack(fill="x", padx=12, pady=4)
        self.sched_label = tk.Label(self.sched_frame, text=get_today_schedule_display(), font=("Helvetica", 9), fg="#cdd6f4", bg="#1e1e2e", justify="left")
        self.sched_label.pack(anchor="w", padx=6, pady=4)

        # 3. UPCOMING EXAMS BOX
        self.exam_frame = tk.LabelFrame(root, text=" Upcoming Exams ", font=("Helvetica", 9, "bold"), fg="#89b4fa", bg="#1e1e2e", bd=1)
        self.exam_frame.pack(fill="x", padx=12, pady=4)
        countdowns = get_exam_countdowns()
        self.exam_label = tk.Label(self.exam_frame, text="\n".join(countdowns), font=("Helvetica", 9), fg="#cdd6f4", bg="#1e1e2e", justify="left")
        self.exam_label.pack(anchor="w", padx=6, pady=4)

        # 4. HOMEWORK & TASKS BOX
        self.task_frame = tk.LabelFrame(root, text=" Micro-Tasks & Homework ", font=("Helvetica", 9, "bold"), fg="#a6e3a1", bg="#1e1e2e", bd=1)
        self.task_frame.pack(fill="x", padx=12, pady=4)
        self.task_label = tk.Label(self.task_frame, text="", font=("Helvetica", 9), fg="#cdd6f4", bg="#1e1e2e", justify="left")
        self.task_label.pack(anchor="w", padx=6, pady=4)

        # 5. APARTMENT CHORES BOX
        self.chore_frame = tk.LabelFrame(root, text=" Apartment Chores ", font=("Helvetica", 9, "bold"), fg="#f9e2af", bg="#1e1e2e", bd=1)
        self.chore_frame.pack(fill="x", padx=12, pady=4)
        self.chore_label = tk.Label(self.chore_frame, text="", font=("Helvetica", 9), fg="#cdd6f4", bg="#1e1e2e", justify="left")
        self.chore_label.pack(anchor="w", padx=6, pady=4)

        self.refresh_dashboard_lists()

        # Attention Tracking Status (Home Mode)
        self.attention_status = tk.Label(root, text="ATTENTION STATUS: FOCUSED (GREEN)", font=("Helvetica", 9, "bold"), fg="#a6e3a1", bg="#1e1e2e")
        if self.mode == "home":
            self.attention_status.pack(pady=2)

        # Response Output Box
        self.output_label = tk.Label(root, text="Aura OS Ready! Press SPACEBAR for commands.", font=("Helvetica", 9, "bold"), fg="#f5c2e7", bg="#1e1e2e", wraplength=380, justify="center")
        self.output_label.pack(pady=6)

        # Action Buttons Frame
        btn_bar = tk.Frame(root, bg="#1e1e2e")
        btn_bar.pack(pady=6)

        self.cmd_button = tk.Button(btn_bar, text="[ SPACEBAR ] Command", font=("Helvetica", 9, "bold"), bg="#f5c2e7", fg="#11111b", command=self.open_command_prompt)
        self.cmd_button.pack(side="left", padx=2)

        tk.Button(btn_bar, text="✏ Shifts", font=("Helvetica", 9, "bold"), bg="#89dceb", fg="#11111b", command=self.open_famous_manager).pack(side="left", padx=2)
        tk.Button(btn_bar, text="✏ Tasks", font=("Helvetica", 9, "bold"), bg="#a6e3a1", fg="#11111b", command=self.open_task_manager).pack(side="left", padx=2)
        tk.Button(btn_bar, text="✏ Chores", font=("Helvetica", 9, "bold"), bg="#f9e2af", fg="#11111b", command=self.open_chore_manager).pack(side="left", padx=2)

        self.root.bind("<space>", lambda event: self.open_command_prompt())

        # Start Background Class Schedule Monitor
        self.notified_classes = set()
        self.start_schedule_monitor()

        if self.mode == "home":
            self.last_seen_time = time.time()
            self.is_distracted = False
            self.start_camera_hud()

    def refresh_dashboard_lists(self):
        famous_text = "\n".join([f"• {s}" for s in famous_list[:3]]) if famous_list else "• No upcoming work shifts logged!"
        self.famous_label.config(text=famous_text)

        self.sched_label.config(text=get_today_schedule_display())
        
        task_text = "\n".join([f"• {t}" for t in tasks_list[:3]]) if tasks_list else "• No active homework!"
        self.task_label.config(text=task_text)

        chore_text = "\n".join([f"• {c}" for c in chores_list[:3]]) if chores_list else "• No active chores!"
        self.chore_label.config(text=chore_text)

        m_stars = "★" * momentum_stars + "☆" * (5 - momentum_stars)
        self.momentum_label.config(text=f"Momentum Level: [{m_stars}]")

    def start_schedule_monitor(self):
        def _check_schedule():
            while True:
                now = datetime.datetime.now()
                today_name = now.strftime("%A")
                classes = WEEKLY_CLASS_SCHEDULE.get(today_name, [])

                for c in classes:
                    c_id = f"{today_name}_{c['name']}_{c['start']}"
                    if c_id in self.notified_classes:
                        continue

                    start_h, start_m = map(int, c['military_start'].split(":"))
                    class_time = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
                    time_diff = (class_time - now).total_seconds()

                    if 0 <= time_diff <= 900:
                        self.notified_classes.add(c_id)
                        messagebox.showinfo("Class Alert", f"⏰ {c['name']} starts in 15 minutes ({c['start']})!")

                time.sleep(30)

        threading.Thread(target=_check_schedule, daemon=True).start()

    def open_command_prompt(self):
        user_input = simpledialog.askstring("Aura OS Command Input", "Type command (e.g. 'shifts', 'schedule'):", parent=self.root)
        if user_input:
            reply = handle_system_commands(user_input, quiet_mode=True, mode=self.mode)
            if reply == "SHUTDOWN_SIGNAL":
                self.output_label.config(text="Good night! Shutting down.", fg="#a6e3a1")
                self.root.after(2000, self.root.destroy)
            else:
                self.output_label.config(text=reply, fg="#f5c2e7")
                self.refresh_dashboard_lists()

    def open_famous_manager(self):
        FamousManagerWindow(self.root, self.refresh_dashboard_lists)

    def open_task_manager(self):
        TaskManagerWindow(self.root, self.refresh_dashboard_lists)

    def open_chore_manager(self):
        ChoreManagerWindow(self.root, self.refresh_dashboard_lists)

    def start_camera_hud(self):
        def _camera_loop():
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cap.isOpened():
                print("[Aura OS Vision]: Camera unavailable.")
                return

            cv2.namedWindow("Aura OS Attention & Vision Stream", cv2.WINDOW_NORMAL)

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                faces = []
                if face_cascade is not None:
                    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=6, minSize=(60, 60))

                if len(faces) > 0:
                    self.last_seen_time = time.time()
                    if self.is_distracted:
                        self.is_distracted = False
                        self.attention_status.config(text="ATTENTION STATUS: FOCUSED (GREEN)", fg="#a6e3a1")
                        send_arduino_command('G')

                    for (x, y, w, h) in faces:
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 127), 2)
                        cv2.putText(frame, "STATUS: FOCUSED", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 127), 2)
                else:
                    if time.time() - self.last_seen_time > 180.0 and not self.is_distracted:
                        self.is_distracted = True
                        self.attention_status.config(text="ATTENTION STATUS: NEEDS RESET / RED ALERT", fg="#f38ba8")
                        send_arduino_command('R')
                        send_arduino_command('A')

                    cv2.putText(frame, "ATTENTION WARNING: NO USER DETECTED", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)

                cv2.imshow("Aura OS Attention & Vision Stream", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            cap.release()
            cv2.destroyAllWindows()

        threading.Thread(target=_camera_loop, daemon=True).start()

# --- MAIN STARTUP SELECTOR ---
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    mode_choice = simpledialog.askstring("Aura OS Mode Selector", "Select Mode:\nType '1' for SCHOOL MODE (Discrete Text Widget)\nType '2' for HOME MODE (Camera + ADHD Focus Tracker + Elegoo Robot)", parent=root)
    root.deiconify()

    selected_mode = "school" if mode_choice == "1" else "home"
    app = AuraOSGUI(root, mode=selected_mode)
    root.mainloop()