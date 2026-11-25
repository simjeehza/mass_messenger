"""
core/messenger.py
Sends iMessages / SMS individually via AppleScript -> Messages.app.
Each recipient (contact or group chat) gets their own send call.
"""

from __future__ import annotations
import subprocess
import time
import sys
from typing import Callable


def _applescript(script: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, result.stdout.strip()
    return False, result.stderr.strip()


def send_message(handle: str, message: str) -> tuple[bool, str]:
    """Send a single iMessage/SMS to one handle (phone or email). 1-on-1 thread."""
    if sys.platform != "darwin":
        print(f"[DEV] Would send to {handle}: {message}")
        return True, ""

    safe_msg    = message.replace("\\", "\\\\").replace('"', '\\"')
    safe_handle = handle.replace('"', '\\"')

    script = f'''
tell application "Messages"
    set targetService to 1st service whose service type = iMessage
    set targetBuddy to buddy "{safe_handle}" of targetService
    send "{safe_msg}" to targetBuddy
end tell
'''
    return _applescript(script)


def send_to_group_chat(chat_id: str, message: str) -> tuple[bool, str]:
    """Send a message to an existing group chat by its chat identifier."""
    if sys.platform != "darwin":
        print(f"[DEV] Would send to group chat {chat_id}: {message}")
        return True, ""

    safe_msg     = message.replace("\\", "\\\\").replace('"', '\\"')
    safe_chat_id = chat_id.replace('"', '\\"')

    script = f'''
tell application "Messages"
    set targetChat to chat id "{safe_chat_id}"
    send "{safe_msg}" to targetChat
end tell
'''
    return _applescript(script)


def send_bulk(
    handles: list[str],
    messages: list[str],
    group_chat_ids: list[str] | None = None,
    delay_between_recipients: float = 0.5,
    delay_between_messages: float = 1.0,
    progress_cb: Callable[[str, int, int, bool, str], None] | None = None,
) -> dict[str, list[tuple[bool, str]]]:
    """
    Send `messages` to each individual handle AND each group chat separately.
    progress_cb(recipient_label, msg_index, total_msgs, success, error)
    Returns {recipient_label: [(success, error), ...]}
    """
    results: dict[str, list[tuple[bool, str]]] = {}
    all_recipients: list[tuple[str, str]] = (
        [("handle", h) for h in handles] +
        [("group",  g) for g in (group_chat_ids or [])]
    )

    for idx, (kind, recipient) in enumerate(all_recipients):
        handle_results = []
        for msg_i, msg in enumerate(messages):
            if kind == "group":
                ok, err = send_to_group_chat(recipient, msg)
            else:
                ok, err = send_message(recipient, msg)

            handle_results.append((ok, err))
            if progress_cb:
                progress_cb(recipient, msg_i + 1, len(messages), ok, err)
            if msg_i < len(messages) - 1:
                time.sleep(delay_between_messages)

        results[recipient] = handle_results

        if idx < len(all_recipients) - 1:
            time.sleep(delay_between_recipients)

    return results


def check_messages_running() -> bool:
    if sys.platform != "darwin":
        return True
    ok, _ = _applescript('tell application "Messages" to get name')
    return ok
