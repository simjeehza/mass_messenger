# Mass Messenger for Mac

Send iMessages and SMS individually to multiple contacts — each gets their own 1-on-1 thread, never a group chat.

## Features

- **Contact picker** — search and select individual contacts or select all
- **Groups** — save named groups for quick reuse
- **Message sequences** — queue multiple messages to send back-to-back
- **Send now** — fires immediately via Messages.app
- **Scheduled sends** — pick a future date/time; runs in the background
- **Dark UI** — native macOS dark theme

---

## Requirements

- macOS 12+
- Python 3.11+
- Messages.app signed in to iMessage

---

## Setup

```bash
# 1. Clone / copy the project folder
cd mass_messenger

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python main.py
```

---

## macOS Permissions

On first launch, macOS will ask for two permissions:

| Permission | Where to grant |
|---|---|
| **Contacts** | System Settings → Privacy & Security → Contacts → enable for Terminal (or your app) |
| **Automation** (control Messages.app) | System Settings → Privacy & Security → Automation → enable Messages for Terminal |

If you skip these, the app runs in **dev / simulation mode** — sends are printed to the console instead of going through Messages.

---

## How sending works

Each recipient gets a completely separate 1-on-1 iMessage/SMS thread. The app uses AppleScript to tell Messages.app to send to each handle individually — no group chats are ever created.

For sequences, each message in the list is sent in order with a short delay between them.

---

## Project layout

```
mass_messenger/
├── main.py              Entry point
├── requirements.txt
├── core/
│   ├── contacts.py      Reads contacts from macOS Contacts.app via pyobjc
│   ├── groups.py        SQLite-backed group storage
│   ├── messenger.py     AppleScript → Messages.app sending
│   └── scheduler.py     APScheduler wrapper for timed sends
└── ui/
    ├── styles.py         Dark theme stylesheet
    ├── main_window.py    Top-level window + tab bar
    ├── compose_tab.py    Contact picker + message editor + send/schedule
    ├── groups_tab.py     Create/edit/delete contact groups
    ├── contact_picker.py Reusable searchable checkable contact list
    └── schedule_tab.py   View and cancel scheduled sends
```

---

## Data storage

Groups and scheduled messages are stored in:
```
~/Library/Application Support/MassMessenger/data.db
```

---

## Tips

- **Load a group** in the Compose tab using the "Load group" dropdown to instantly check all members.
- **Message sequences** — click "+ Add message" to queue multiple messages; they send in order.
- **Scheduling** — the app must be running at send time for scheduled messages to fire. A future version can use a launchd agent for background operation.
- To **bundle as a standalone .app**, use `py2app` or `PyInstaller`.
