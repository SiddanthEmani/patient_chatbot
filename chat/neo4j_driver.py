from neo4j import GraphDatabase
import os
import logging
from django.conf import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jDriver:
    def __init__(self):
        # Initialize Neo4j driver
        self.driver = GraphDatabase.driver(
            uri=settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        # Verify driver connection
        try:
            self.driver.verify_connectivity()
            logger.info("Neo4j driver connected successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")

    # Close the driver connection
    def close(self):
        self.driver.close()
        logger.info("Neo4j driver connection closed.")

    # Execute a read query
    def execute_read_query(self, query, parameters=None):
        logger.info(f"Executing read query: {query} with parameters: {parameters}")
        with self.driver.session() as session:
            result = session.read_transaction(lambda tx: tx.run(query, parameters).data())
            logger.info(f"Read query result: {result}")
            return result
        
    # Execute a write query
    def execute_write_query(self, query, parameters=None):
        logger.info(f"Executing write query: {query} with parameters: {parameters}")
        with self.driver.session() as session:
            result = session.write_transaction(lambda tx: tx.run(query, parameters).data())
            logger.info(f"Write query result: {result}")
            return result
