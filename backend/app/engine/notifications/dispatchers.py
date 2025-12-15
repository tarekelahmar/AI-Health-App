from __future__ import annotations

import json
from typing import Dict, Any

"""
MVP dispatchers:

- "inbox": already delivered via InboxItem (so this dispatcher is effectively a no-op)
- "console": prints payloads (useful for dev)

Later you can add:
- email (SES/SendGrid)
- push (FCM/APNs)
"""


def dispatch_console(payload_json: str) -> None:
    payload: Dict[str, Any] = {}
    try:
        payload = json.loads(payload_json or "{}")
    except Exception:
        payload = {"raw": payload_json}
    print(f"[NOTIFY][console] {payload}")


def dispatch_inbox(_payload_json: str) -> None:
    # Inbox delivery happens at creation time (InboxItem is the UI surface).
    # Keep as no-op for outbox compatibility.
    return


DISPATCHERS = {
    "console": dispatch_console,
    "inbox": dispatch_inbox,
}

