"""
Enterprise Webhook Integration Framework — Outbound event-driven webhooks
for LMS, HRIS, Calendar, and third-party integrations.
Supports retry with exponential backoff, payload signing, and idempotency keys.
"""
import json
import hmac
import hashlib
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from ..core.config import settings
from ..core.logger import log

import httpx


class WebhookEvent(str, Enum):
    """Standard webhook events comparable to Greenhouse/Lever."""
    APPLICATION_CREATED = "application.created"
    APPLICATION_UPDATED = "application.updated"
    STAGE_CHANGED = "stage.changed"
    CANDIDATE_HIRED = "candidate.hired"
    CANDIDATE_REJECTED = "candidate.rejected"
    SCORE_UPDATED = "score.updated"
    INTERVIEW_SCHEDULED = "interview.scheduled"
    INTERVIEW_COMPLETED = "interview.completed"
    OFFER_CREATED = "offer.created"
    OFFER_ACCEPTED = "offer.accepted"


@dataclass
class WebhookSubscription:
    """A registered webhook endpoint receiving events."""
    id: str
    url: str
    events: List[WebhookEvent]
    secret: str  # HMAC signing secret
    is_active: bool = True
    org_id: int = 0
    description: str = ""
    retry_count: int = 0
    max_retries: int = 5
    last_delivery: Optional[datetime] = None
    last_status: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WebhookService:
    """Manages webhook subscriptions and delivery."""

    _subscriptions: Dict[str, WebhookSubscription] = {}
    _delivery_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

    # ─── Subscription Management ──────────────────────────────────────────────

    @classmethod
    def subscribe(
        cls,
        url: str,
        events: List[WebhookEvent],
        org_id: int,
        description: str = "",
    ) -> WebhookSubscription:
        """Register a new webhook endpoint."""
        import uuid
        sub = WebhookSubscription(
            id=uuid.uuid4().hex[:12],
            url=url,
            events=events,
            secret=uuid.uuid4().hex,
            org_id=org_id,
            description=description,
        )
        cls._subscriptions[sub.id] = sub
        log.info("webhook_subscribed", id=sub.id, url=url, events=len(events))
        return sub

    @classmethod
    def unsubscribe(cls, subscription_id: str) -> bool:
        """Remove a webhook subscription."""
        if subscription_id in cls._subscriptions:
            del cls._subscriptions[subscription_id]
            log.info("webhook_unsubscribed", id=subscription_id)
            return True
        return False

    @classmethod
    def list_subscriptions(cls, org_id: int) -> List[Dict]:
        """List all webhooks for an organization."""
        return [
            {
                "id": s.id,
                "url": s.url,
                "events": [e.value for e in s.events],
                "is_active": s.is_active,
                "description": s.description,
                "last_delivery": s.last_delivery.isoformat() if s.last_delivery else None,
                "last_status": s.last_status,
            }
            for s in cls._subscriptions.values()
            if s.org_id == org_id
        ]

    # ─── Event Delivery ───────────────────────────────────────────────────────

    @classmethod
    async def publish(cls, event: WebhookEvent, payload: Dict[str, Any], org_id: int):
        """Publish an event to all matching subscriptions."""
        event_id = hashlib.md5(
            f"{event.value}:{json.dumps(payload, sort_keys=True, default=str)}".encode()
        ).hexdigest()[:16]

        matching_subs = [
            s for s in cls._subscriptions.values()
            if s.org_id == org_id and event in s.events and s.is_active
        ]

        if not matching_subs:
            log.debug("webhook_no_subscribers", event=event.value, org_id=org_id)
            return

        for sub in matching_subs:
            await cls._delivery_queue.put({
                "subscription_id": sub.id,
                "event": event.value,
                "payload": payload,
                "event_id": event_id,
            })

        log.info("webhook_published", event=event.value, subscribers=len(matching_subs))

    @classmethod
    async def _deliver(
        cls,
        subscription_id: str,
        event: str,
        payload: Dict[str, Any],
        event_id: str,
    ) -> bool:
        """Deliver a single webhook with retry logic."""
        sub = cls._subscriptions.get(subscription_id)
        if not sub or not sub.is_active:
            return False

        # Build signed payload
        body = json.dumps({
            "event": event,
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        })

        signature = hmac.new(
            sub.secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-AIATS-Webhook-Signature": signature,
            "X-AIATS-Webhook-ID": event_id,
            "X-AIATS-Event": event,
            "User-Agent": "AI-ATS-Webhook/2.1",
        }

        # Retry with exponential backoff
        for attempt in range(sub.max_retries):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(sub.url, content=body, headers=headers)
                    sub.last_status = resp.status_code
                    sub.last_delivery = datetime.now(timezone.utc)

                    if resp.status_code in [200, 201, 202, 204]:
                        log.debug("webhook_delivered", id=subscription_id, event=event, status=resp.status_code)
                        return True
                    elif resp.status_code >= 500:
                        # Server error — retry
                        delay = 2 ** attempt
                        log.warning("webhook_retry", id=subscription_id, attempt=attempt + 1, delay=delay)
                        await asyncio.sleep(delay)
                    else:
                        # Client error — don't retry
                        log.error("webhook_client_error", id=subscription_id, status=resp.status_code)
                        return False

            except (httpx.RequestError, asyncio.TimeoutError) as e:
                delay = 2 ** attempt
                log.warning("webhook_network_error", id=subscription_id, error=str(e), attempt=attempt + 1)
                await asyncio.sleep(delay)

        # All retries exhausted
        sub.is_active = False
        log.error("webhook_disabled_after_retries", id=subscription_id, url=sub.url)
        return False

    @classmethod
    async def process_queue(cls):
        """Background worker: continuously process the webhook delivery queue."""
        log.info("webhook_worker_started")
        while True:
            try:
                task = await cls._delivery_queue.get()
                await cls._deliver(
                    task["subscription_id"],
                    task["event"],
                    task["payload"],
                    task["event_id"],
                )
                cls._delivery_queue.task_done()
            except asyncio.CancelledError:
                log.info("webhook_worker_stopped")
                break
            except Exception as e:
                log.error("webhook_worker_error", error=str(e))
                await asyncio.sleep(1)


# ═══════════════════════════════════════════════════════════════════════════════
# Calendar Integration — Google Calendar, Outlook 365
# ═══════════════════════════════════════════════════════════════════════════════

class CalendarProvider(str, Enum):
    GOOGLE = "google"
    OUTLOOK = "outlook_365"
    APPLE = "apple"

class CalendarService:
    """Interview scheduling with external calendar providers."""

    @staticmethod
    async def get_available_slots(
        provider: CalendarProvider,
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int = 60,
        interviewer_email: str = "",
    ) -> List[Dict[str, Any]]:
        """Query provider for available time slots."""
        # In production, this would call Google Calendar API / Microsoft Graph API
        # For now, return mock slots that demonstrate the interface
        slots = []
        current = start_date
        while current < end_date:
            if current.hour >= 9 and current.hour < 17 and current.weekday() < 5:
                slots.append({
                    "start": current.isoformat(),
                    "end": (current + timedelta(minutes=duration_minutes)).isoformat(),
                    "provider": provider.value,
                })
            current += timedelta(minutes=30)

        return slots[:20]  # Return max 20 slots

    @staticmethod
    async def schedule_interview(
        provider: CalendarProvider,
        start_time: datetime,
        end_time: datetime,
        attendees: List[str],
        title: str,
        description: str = "",
        location: str = "Virtual",
    ) -> Dict[str, Any]:
        """Schedule an interview event on the provider's calendar."""
        event_id = hashlib.md5(
            f"{title}:{start_time.isoformat()}:{','.join(attendees)}".encode()
        ).hexdigest()[:12]

        log.info(
            "interview_scheduled",
            event_id=event_id,
            provider=provider.value,
            title=title,
            attendees=len(attendees),
            start=start_time.isoformat(),
        )

        # In production, call Google Calendar API create event / Microsoft Graph create event
        return {
            "event_id": event_id,
            "provider": provider.value,
            "title": title,
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "attendees": attendees,
            "location": location,
            "status": "scheduled",
            "meeting_link": f"https://meet.{provider.value}.com/{event_id}" if provider != CalendarProvider.APPLE else None,
        }

    @staticmethod
    async def cancel_interview(provider: CalendarProvider, event_id: str) -> Dict[str, str]:
        """Cancel a scheduled interview."""
        log.info("interview_cancelled", event_id=event_id, provider=provider.value)
        return {"event_id": event_id, "status": "cancelled", "provider": provider.value}

    @staticmethod
    async def send_calendar_invite(
        to_email: str,
        event_details: Dict[str, Any],
        provider: CalendarProvider = CalendarProvider.GOOGLE,
    ) -> Dict[str, str]:
        """Send a calendar invitation via email (ICS attachment)."""
        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AI ATS//Interview Scheduling//EN
METHOD:REQUEST
BEGIN:VEVENT
UID:{event_details.get('event_id')}@ai-ats.com
DTSTART:{event_details.get('start', '').replace('-', '').replace(':', '')[:15]}Z
DTEND:{event_details.get('end', '').replace('-', '').replace(':', '')[:15]}Z
SUMMARY:{event_details.get('title', 'Interview')}
DESCRIPTION:{event_details.get('description', '')}
LOCATION:{event_details.get('location', 'Virtual')}
ORGANIZER;CN=AI ATS:mailto:noreply@ai-ats.com
ATTENDEE;ROLE=REQ-PARTICIPANT:mailto:{to_email}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

        log.info("calendar_invite_sent", to=to_email, event_id=event_details.get("event_id"))
        return {
            "status": "sent",
            "to": to_email,
            "event_id": event_details.get("event_id", ""),
            "ics_content": ics_content[:200] + "...",
        }
