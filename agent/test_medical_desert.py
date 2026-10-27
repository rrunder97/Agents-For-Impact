"""
test_medical_desert.py - Run the Medical Desert Test Case end-to-end.
"""

from schemas import CheckShelterReadinessInput, HazardType
from sentinel_agent import SentinelEvacuationAgent
from bigquery_service import BigQueryGroundingService
from maps_service import GoogleMapsGroundingService
from alert_service import EmergencyInterventionService


def run_test():
    print("=============================================================")
    print("RUNNING GOOGLE ADK TEST CASE: THE 'MEDICAL DESERT' SCENARIO")
    print("=============================================================")

    # Initialize services
    bq_svc = BigQueryGroundingService(use_mock=True)
    maps_svc = GoogleMapsGroundingService(use_mock=True)
    alert_svc = EmergencyInterventionService()

    agent = SentinelEvacuationAgent(
        bigquery_service=bq_svc,
        maps_service=maps_svc,
        alert_service=alert_svc
    )

    # Invocation parameters
    audit_input = CheckShelterReadinessInput(
        county_fips="12086",
        hazard_type=HazardType.HURRICANE,
        min_vulnerability_score=0.20
    )

    # Execute Audit
    reports = agent.run_audit(audit_input)

    print("\n" + "="*60)
    print("AUDIT EXECUTION RESULTS & GENERATED READINESS BRIEFS")
    print("="*60)

    for report in reports:
        print(f"\n{report.brief_markdown}")
        print("-" * 60)

    # Verification Assertions
    northside_report = next(r for r in reports if "Northside" in r.shelter_name)
    assert northside_report.physical_status == "CLOSED_PERMANENTLY", "Physical status should be CLOSED_PERMANENTLY"
    assert northside_report.last_mile_status == "FAIL", "Last mile status should be FAIL"
    assert northside_report.alert_dispatched is True, "Alert should have been dispatched"
    assert "East General" in northside_report.redirect_facility, "Redirect should point to East General"

    print("\n>>> ALL SKEPTIC TEST ASSERTIONS PASSED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    run_test()
