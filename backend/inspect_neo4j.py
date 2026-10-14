"""Read-only schema inventory; credentials are loaded from backend/.env."""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase


def main():
    """Print graph shape and sample records without changing stored data."""
    if sys.platform == 'win32':
        import truststore
        truststore.inject_into_ssl()
    load_dotenv(Path(__file__).with_name('.env'))
    queries = {
        'labels': 'MATCH (n) RETURN labels(n) AS labels, count(*) AS count ORDER BY count DESC',
        'relationships': 'MATCH (a)-[r]->(b) RETURN labels(a) AS source, type(r) AS relationship, labels(b) AS target, count(*) AS count ORDER BY count DESC LIMIT 30',
        'properties': 'MATCH (n) UNWIND keys(n) AS property RETURN labels(n) AS labels, property, count(*) AS count ORDER BY labels, property',
        'samples': 'MATCH (n) RETURN labels(n) AS labels, properties(n) AS properties LIMIT 3',
    }
    with GraphDatabase.driver(os.environ['NEO4J_URI'],
                              auth=(os.environ['NEO4J_USERNAME'], os.environ['NEO4J_PASSWORD']),
                              connection_timeout=15, max_transaction_retry_time=10) as driver:
        for name, query in queries.items():
            records, _, _ = driver.execute_query(query, database_=os.environ['NEO4J_DATABASE'], routing_='r')
            print(json.dumps({name: [record.data() for record in records]}, default=str))


if __name__ == '__main__':
    main()
