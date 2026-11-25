"""
core/contacts.py
Fetches contacts from macOS Contacts.app using pyobjc.
Falls back to a stub list if running outside macOS or permissions are denied.
Supports optional sorting by recently-texted order from chat.db.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import sys


@dataclass
class Contact:
    identifier: str
    first_name: str
    last_name: str
    phone_numbers: list[str] = field(default_factory=list)
    email_addresses: list[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.last_name]
        name = " ".join(p for p in parts if p).strip()
        return name if name else "Unknown"

    @property
    def display_handle(self) -> str:
        """Best handle to show in the UI (first phone, else first email)."""
        if self.phone_numbers:
            return self.phone_numbers[0]
        if self.email_addresses:
            return self.email_addresses[0]
        return ""

    @property
    def all_handles(self) -> list[str]:
        return self.phone_numbers + self.email_addresses


def _normalize_phone(raw: str) -> str:
    """Strip formatting so AppleScript handles look consistent."""
    import re
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return raw.strip()


def load_contacts() -> list[Contact]:
    """
    Load contacts from macOS Contacts.app.
    Returns a list sorted A→Z by last name.
    """
    if sys.platform != "darwin":
        return _stub_contacts()

    try:
        import Contacts  # pyobjc-framework-Contacts
        store = Contacts.CNContactStore.alloc().init()

        granted = [False]
        def handler(ok, err):
            granted[0] = ok
        store.requestAccessForEntityType_completionHandler_(
            Contacts.CNEntityTypeContacts, handler
        )

        keys = [
            Contacts.CNContactGivenNameKey,
            Contacts.CNContactFamilyNameKey,
            Contacts.CNContactPhoneNumbersKey,
            Contacts.CNContactEmailAddressesKey,
            Contacts.CNContactIdentifierKey,
        ]

        fetch_request = Contacts.CNContactFetchRequest.alloc().initWithKeysToFetch_(keys)
        fetch_request.setSortOrder_(Contacts.CNContactSortOrderFamilyName)

        contacts: list[Contact] = []

        def visitor(cn_contact, stop):
            phones = [
                _normalize_phone(str(lv.value().stringValue()))
                for lv in (cn_contact.phoneNumbers() or [])
            ]
            emails = [
                str(lv.value())
                for lv in (cn_contact.emailAddresses() or [])
            ]
            if not phones and not emails:
                return

            contacts.append(Contact(
                identifier=str(cn_contact.identifier()),
                first_name=str(cn_contact.givenName() or ""),
                last_name=str(cn_contact.familyName() or ""),
                phone_numbers=phones,
                email_addresses=emails,
            ))

        store.enumerateContactsWithFetchRequest_error_usingBlock_(
            fetch_request, None, visitor
        )

        contacts.sort(key=lambda c: (c.last_name.lower(), c.first_name.lower()))
        return contacts

    except Exception as exc:
        print(f"[contacts] Could not load from Contacts.app: {exc}")
        return _stub_contacts()


def sort_by_recent(contacts: list[Contact], recent_order: dict[str, int]) -> list[Contact]:
    """
    Re-sort contacts by most-recently-texted using handle rank from chat.db.
    Contacts with no message history are appended at the end (A→Z).
    """
    NO_RANK = len(recent_order) + 9999

    def best_rank(c: Contact) -> int:
        ranks = [recent_order.get(h, NO_RANK) for h in c.all_handles]
        return min(ranks) if ranks else NO_RANK

    recents  = [c for c in contacts if best_rank(c) < NO_RANK]
    no_hist  = [c for c in contacts if best_rank(c) >= NO_RANK]

    recents.sort(key=best_rank)
    no_hist.sort(key=lambda c: (c.last_name.lower(), c.first_name.lower()))
    return recents + no_hist


def _stub_contacts() -> list[Contact]:
    """Demo contacts for development / non-mac environments."""
    return [
        Contact("1", "Alice",  "Anderson", ["+15550001111"], ["alice@example.com"]),
        Contact("2", "Bob",    "Baker",    ["+15550002222"], []),
        Contact("3", "Carol",  "Chen",     ["+15550003333"], ["carol@example.com"]),
        Contact("4", "David",  "Diaz",     [], ["david@example.com"]),
        Contact("5", "Eve",    "Evans",    ["+15550005555"], ["eve@example.com"]),
        Contact("6", "Frank",  "Fisher",   ["+15550006666"], []),
        Contact("7", "Grace",  "Garcia",   ["+15550007777"], ["grace@example.com"]),
        Contact("8", "Henry",  "Hall",     ["+15550008888"], []),
    ]
