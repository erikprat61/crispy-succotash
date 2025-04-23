import os
import time
from pathlib import Path
from datetime import datetime, timedelta
import re
import argparse

# Directory where your Obsidian vault daily notes live
NOTES_DIR = Path.home() / "ObsidianVault" / "DailyNotes"

# Filename template: YYYY-MM-DD.md
DATE_FMT = "%Y-%m-%d"

# Regex to capture todo items in markdown: "- [ ] task"
TODO_PATTERN = re.compile(r"^- \[ \] (.+)")

# Configuration: first hour of the day to trigger note creation, and loop interval in seconds
START_HOUR = 6        # 6 AM local time
CHECK_INTERVAL = 60   # check every 60 seconds


def get_all_notes(directory: Path):
    """Return a list of (date, Path) tuples for all markdown files sorted by date."""
    print(f"[INFO] Scanning directory: {directory}")
    notes = []
    for md in directory.glob("*.md"):
        try:
            note_date = datetime.strptime(md.stem, DATE_FMT).date()
            notes.append((note_date, md))
            print(f"[INFO] Found note: {md.name} (date: {note_date})")
        except ValueError:
            print(f"[WARN] Skipping file with invalid date format: {md.name}")
            continue
    notes.sort()
    print(f"[INFO] Found {len(notes)} valid notes")
    return notes


def extract_undone_todos(note_path: Path):
    """Extract all unchecked todo descriptions from a note."""
    print(f"[INFO] Reading todos from: {note_path}")
    todos = []
    text = note_path.read_text(encoding='utf-8').splitlines()
    for line in text:
        match = TODO_PATTERN.match(line)
        if match:
            todos.append(match.group(1))
    print(f"[INFO] Found {len(todos)} undone todos in {note_path.name}")
    return todos


def aggregate_todos(past_notes):
    """Collect undone todos from a list of past (date, Path) tuples, deduped."""
    print("[INFO] Aggregating todos from past notes...")
    seen = set()
    todos = []
    for date, note in past_notes:
        print(f"[INFO] Processing todos from {date}")
        for todo in extract_undone_todos(note):
            if todo not in seen:
                seen.add(todo)
                todos.append(todo)
    print(f"[INFO] Found {len(todos)} unique undone todos across all notes")
    return todos


def create_daily_note(notes_dir: Path, note_date: datetime.date = None):
    """Generate a daily note for the given date (defaults to today)."""
    if note_date is None:
        note_date = datetime.now().date()
    
    fname = notes_dir / f"{note_date.strftime(DATE_FMT)}.md"
    print(f"[INFO] Checking if note exists: {fname}")
    
    if fname.exists():
        print(f"[INFO] Note already exists: {fname}")
        return

    # Gather notes from the last 7 days
    one_week_ago = note_date - timedelta(days=7)
    print(f"[INFO] Gathering notes from the past week (since {one_week_ago})")
    all_notes = get_all_notes(notes_dir)
    recent_notes = [(d,p) for d,p in all_notes if one_week_ago <= d < note_date]
    print(f"[INFO] Found {len(recent_notes)} notes from the past week")

    todos = aggregate_todos(recent_notes)

    # Build file content
    body = f"# {note_date.strftime(DATE_FMT)}\n\n"

    # Tasks section
    body += "## Tasks\n"
    if todos:
        for t in todos:
            body += f"- [ ] {t}\n"
    else:
        body += "- [ ] \n"
    body += "\n"

    # Notes section placeholder
    body += "## Notes\n- \n"

    # Ensure directory exists
    print(f"[INFO] Ensuring directory exists: {notes_dir}")
    notes_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[INFO] Writing new note to: {fname}")
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(body)
    print(f"[INFO] Successfully created daily note: {fname}")


def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Daily Notes Generator for Obsidian')
    parser.add_argument('--create-now', action='store_true', 
                       help='Manually trigger note creation for today')
    parser.add_argument('--date', type=str, 
                       help='Create note for specific date (YYYY-MM-DD format)')
    args = parser.parse_args()

    print(f"[INFO] Notes directory: {NOTES_DIR}")
    
    # Handle manual creation requests
    if args.create_now:
        print("[INFO] Manual creation triggered for today")
        create_daily_note(NOTES_DIR)
        return
    elif args.date:
        try:
            note_date = datetime.strptime(args.date, DATE_FMT).date()
            print(f"[INFO] Manual creation triggered for date: {note_date}")
            create_daily_note(NOTES_DIR, note_date=note_date)
            return
        except ValueError:
            print(f"[ERROR] Invalid date format. Please use YYYY-MM-DD format.")
            return

    print("[INFO] Starting automatic monitoring mode...")
    # Original automatic monitoring logic
    last_run_date = None
    while True:
        now = datetime.now()
        # Reset flag at start of a new day
        if last_run_date != now.date():
            last_run_date = now.date()
            print(f"[INFO] New day detected: {now.date()}")
        # If it's past START_HOUR and today's note isn't created yet, make it
        if now.hour >= START_HOUR:
            note_path = NOTES_DIR / f"{now.strftime(DATE_FMT)}.md"
            if not note_path.exists():
                print(f"[INFO] Creating note for {now.date()} (current hour: {now.hour})")
                create_daily_note(NOTES_DIR, note_date=now.date())
        # Sleep until next check or until resume from sleep wakes us
        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    print("[INFO] Daily Notes Generator started...")
    main()
