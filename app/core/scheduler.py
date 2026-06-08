"""Campaign scheduling and anti-spam logic."""

from datetime import datetime, timedelta, time
from typing import Protocol


def should_send_to_contact(
    contact_status: str,
    last_sent_at: datetime | None,
    follow_up_delay_hours: int,
    now: datetime,
) -> bool:
    """Return True if a message may be sent to the contact now.

    *contact_status* is the campaign-contact status (e.g. ``pending``,
    ``sent``, ``follow_up_sent``).
    *last_sent_at* is the timestamp of the most recent outbound message.
    """
    if contact_status == "pending":
        return True

    if contact_status in ("sent", "follow_up_sent"):
        if last_sent_at is None:
            return True
        delay = timedelta(hours=follow_up_delay_hours)
        return now >= last_sent_at + delay

    return False


def is_within_working_hours(
    timezone_str: str,
    working_start: time,
    working_end: time,
    now: datetime,
) -> bool:
    """Return True if *now* falls within working hours in the given timezone.

    The timezone string is currently accepted for API compatibility but
    the comparison is performed on the *localised* ``now`` value passed
    by the caller.
    """
    current_time = now.time()
    if working_start <= working_end:
        return working_start <= current_time <= working_end
    # Handles overnight shifts (not expected for 9-18 but kept robust)
    return current_time >= working_start or current_time <= working_end


class _HasContactAttrs(Protocol):
    status: str
    initial_sent_at: datetime | None
    follow_up_sent_at: datetime | None
    message_count: int


class _HasScriptAttrs(Protocol):
    max_messages: int
    follow_up_delay_hours: int
    working_hours_start: time
    working_hours_end: time
    timezone: str


def next_contact_to_process(
    campaign_contacts: list[_HasContactAttrs],
    script: _HasScriptAttrs,
    now: datetime,
) -> list[_HasContactAttrs]:
    """Return contacts that are ready to receive a message right now.

    Filters apply anti-spam rules:
    - max *script.max_messages* messages per contact,
    - only during working hours,
    - follow-ups respect *follow_up_delay_hours*.
    """
    if not is_within_working_hours(
        script.timezone,
        script.working_hours_start,
        script.working_hours_end,
        now,
    ):
        return []

    ready: list[_HasContactAttrs] = []
    for contact in campaign_contacts:
        if contact.message_count >= script.max_messages:
            continue

        last_sent = contact.follow_up_sent_at or contact.initial_sent_at
        if should_send_to_contact(
            contact.status,
            last_sent,
            script.follow_up_delay_hours,
            now,
        ):
            ready.append(contact)

    return ready
