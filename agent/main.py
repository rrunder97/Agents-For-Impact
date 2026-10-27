"""
main.py - Main entrypoint for running the Sentinel Evacuation Readiness Agent.

Usage:
  python agent/main.py                     # Runs default interactive readiness check
  python agent/main.py --audit 12086       # Runs full Skeptic audit for Miami-Dade County
  python agent/main.py --query "Find medical shelters outside flood zones"
"""

import sys
import argparse
from agent import root_agent, query_emergency_shelters, audit_shelter_ground_truth, run_standalone_audit


def main():
    parser = argparse.ArgumentParser(description="Sentinel Evacuation Readiness Agent (Challenge 4)")
    parser.add_argument("--audit", type=str, default="12086", help="County FIPS code to audit (default: 12086)")
    parser.add_argument("--query", type=str, default=None, help="Natural language question to query BigQuery view")
    args = parser.parse_args()

    print("=====================================================================")
    print("      SENTINEL: ADAPTIVE EVACUATION READINESS & PLANNING AGENT      ")
    print("                      Agents for Impact 2026                         ")
    print("=====================================================================\n")

    if root_agent is not None:
        print(f"[ADK Loaded] Agent '{root_agent.name}' initialized on model '{root_agent.model}'.")
        print(f"[Tools Registered] {len(root_agent.tools)} tools attached: {[getattr(t, '__name__', type(t).__name__) for t in root_agent.tools]}\n")

    if args.query:
        print(f"Executing Natural Language Query: \"{args.query}\"")
        res = query_emergency_shelters(args.query)
        print(f"Status: {res.get('status')} | Rows returned: {res.get('row_count')}")
        print("\nResults Sample:")
        for row in res.get("data", [])[:5]:
            print(f"  - {row.get('shelter_name', 'Unknown')} ({row.get('city', 'N/A')}) | Cap: {row.get('evacuation_capacity')} | Gen: {row.get('generator_onsite')}")
        return

    print(f"Running Full Ground-Truth Audit for County FIPS: {args.audit}...")
    report = run_standalone_audit(county_fips=args.audit)
    print("\n" + report)


if __name__ == "__main__":
    main()
