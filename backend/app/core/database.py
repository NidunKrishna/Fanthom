"""Run parameterized Neo4j queries with verified TLS and bounded connections."""
import sys
from contextlib import contextmanager

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable


class GraphDatabaseClient:
    """Open and close a driver per operation; credentials never leave the backend."""

    def __init__(self, settings):
        """Retain connection settings without connecting during application import."""
        self.settings = settings

    @contextmanager
    def session(self):
        """Yield a database session and close all associated sockets afterwards."""
        if not self.settings.neo4j_uri:
            raise ServiceUnavailable('Neo4j is not configured.')
        if sys.platform == 'win32':
            import truststore
            truststore.inject_into_ssl()
        with GraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_username, self.settings.neo4j_password),
            connection_timeout=5, max_transaction_retry_time=0,
        ) as driver:
            with driver.session(database=self.settings.neo4j_database) as session:
                yield session

    def read(self, query, **parameters):
        """Execute a read transaction and return ordinary dictionaries."""
        with self.session() as session:
            return session.execute_read(lambda tx: tx.run(query, **parameters).data())

    def write(self, query, **parameters):
        """Commit one parameterized write transaction and return its records."""
        with self.session() as session:
            return session.execute_write(lambda tx: tx.run(query, **parameters).data())
