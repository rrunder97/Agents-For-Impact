"""
alert_service.py - Implements Step 4: External Intervention (send_fips_alert).
Dispatches high-urgency notifications to county emergency managers.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from schemas import FipsAlertPayload, GroundingPriority


class EmergencyInterventionService:
    """Handles external alerting when critical shelter vulnerabilities are verified."""

    def __init__(self, eoc_registry: Optional[Dict[str, str]] = None):
        # Default registry mapping county FIPS to emergency manager ops email
        self.eoc_registry = eoc_registry or {
            "12086": "eoc-ops@miamidade.gov",
            "12011": "eoc-operations@broward.org",
            "48201": "emergency-mgmt@harriscountytx.gov"
        }
        self.dispatched_alerts: List[FipsAlertPayload] = []

    def dispatch_fips_alert(
        self,
        county_fips: str,
        county_name: str,
        shelter_name: str,
        grounding_priority: GroundingPriority,
        failure_reasons: List[str],
        suggested_redirect: Optional[str] = None,
    ) -> FipsAlertPayload:
        """Dispatches an alert payload to the emergency manager."""
        eoc_email = self.eoc_registry.get(county_fips, f"em-ops-{county_fips}@state-eoc.gov")
        
        alert = FipsAlertPayload(
            county_fips=county_fips,
            county_name=county_name,
            emergency_manager_email=eoc_email,
            shelter_name=shelter_name,
            grounding_priority=grounding_priority,
            failure_reasons=failure_reasons,
            suggested_redirect=suggested_redirect,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self.dispatched_alerts.append(alert)
        self._send_notification(alert)
        return alert

    def _send_notification(self, alert: FipsAlertPayload) -> None:
        """Simulates or performs the outbound delivery (e.g. SMTP, Webhook, SMS)."""
        print(f"\n[SENTINEL ALERT DISPATCHED] -> {alert.emergency_manager_email}")
        print(f"Priority: {alert.grounding_priority.value}")
        print(f"Shelter: {alert.shelter_name} (FIPS {alert.county_fips} - {alert.county_name})")
        print(f"Failures: {', '.join(alert.failure_reasons)}")
        if alert.suggested_redirect:
            print(f"Reroute: {alert.suggested_redirect}")
        print("-" * 60)
