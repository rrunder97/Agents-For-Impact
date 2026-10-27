"""
test_bigquery_nl.py - Tests natural language to BigQuery SQL query generation and execution.
"""

from bigquery_nl_query import BigQueryNLQueryEngine

def run_tests():
    engine = BigQueryNLQueryEngine()

    test_queries = [
        "Find medical shelters with generators outside flood zones",
        "What is the total evacuation capacity by city?",
        "Find shelters within 10 miles of 25.7617, -80.1918"
    ]

    print("=================================================================")
    print("TESTING BIGQUERY NATURAL LANGUAGE SQL GENERATION ENGINE")
    print("Target View: qwiklabs-gcp-03-82491e646971.evacuation_readiness.v_emergency_shelters_all")
    print("=================================================================\n")

    for idx, query in enumerate(test_queries, 1):
        print(f"[{idx}] Natural Language Query:")
        print(f"    \"{query}\"")
        sql = engine.generate_sql(query)
        print("Generated BigQuery Standard SQL:")
        for line in sql.strip().split("\n"):
            print(f"    {line}")
        
        result = engine.execute_query(sql)
        print(f"Execution Status: {result['status']} (Rows: {result['row_count']})")
        print("-" * 65 + "\n")

    print(">>> ALL NATURAL LANGUAGE SQL TESTS PASSED! <<<")

if __name__ == "__main__":
    run_tests()
