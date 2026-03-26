"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import sqlite3
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

DB_PATH = current_dir / "activities.db"

seed_activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS activities (
            name TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            schedule TEXT NOT NULL,
            max_participants INTEGER NOT NULL
        )"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_name TEXT NOT NULL,
            email TEXT NOT NULL,
            UNIQUE(activity_name, email),
            FOREIGN KEY (activity_name) REFERENCES activities(name) ON DELETE CASCADE
        )"""
    )
    conn.commit()

    # Seed early data if empty
    cursor.execute("SELECT COUNT(*) as count FROM activities")
    if cursor.fetchone()[0] == 0:
        for name, info in seed_activities.items():
            cursor.execute(
                "INSERT INTO activities (name, description, schedule, max_participants) VALUES (?,?,?,?)",
                (name, info["description"], info["schedule"], info["max_participants"])
            )
            for email in info.get("participants", []):
                cursor.execute(
                    "INSERT OR IGNORE INTO participants (activity_name, email) VALUES (?,?)",
                    (name, email)
                )
        conn.commit()

    conn.close()


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


def load_all_activities(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM activities")
    activities_data = {}
    for row in cursor.fetchall():
        name = row["name"]
        cursor.execute("SELECT email FROM participants WHERE activity_name = ?", (name,))
        participants = [r["email"] for r in cursor.fetchall()]
        activities_data[name] = {
            "description": row["description"],
            "schedule": row["schedule"],
            "max_participants": row["max_participants"],
            "participants": participants,
        }
    return activities_data


@app.get("/activities")
def get_activities(db=Depends(get_db)):
    return load_all_activities(db)


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM activities WHERE name = ?", (activity_name,))
    activity = cursor.fetchone()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    cursor.execute("SELECT COUNT(*) FROM participants WHERE activity_name = ?", (activity_name,))
    count = cursor.fetchone()[0]
    max_participants = activity["max_participants"]
    if count >= max_participants:
        raise HTTPException(status_code=400, detail="Activity is full")

    cursor.execute(
        "SELECT 1 FROM participants WHERE activity_name = ? AND email = ?",
        (activity_name, email)
    )
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Student is already signed up")

    cursor.execute(
        "INSERT INTO participants (activity_name, email) VALUES (?,?)",
        (activity_name, email)
    )
    db.commit()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM activities WHERE name = ?", (activity_name,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Activity not found")

    cursor.execute(
        "SELECT 1 FROM participants WHERE activity_name = ? AND email = ?",
        (activity_name, email)
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    cursor.execute(
        "DELETE FROM participants WHERE activity_name = ? AND email = ?",
        (activity_name, email)
    )
    db.commit()
    return {"message": f"Unregistered {email} from {activity_name}"}
