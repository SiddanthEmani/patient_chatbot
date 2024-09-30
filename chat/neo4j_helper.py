from neo4j import GraphDatabase
from langchain_community.graphs import Neo4jGraph
import os
import logging
from django.conf import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Neo4j driver
neo4j_helper = Neo4jGraph(
    url=settings.NEO4J_URI,
    username=settings.NEO4J_USER,
    password=settings.NEO4J_PASSWORD,
)
logger.info("Neo4j driver connected successfully.")

def execute_cypher_query_helper(query, params=None):
    try:
        logger.info(f"Executing cypher query: {query} with parameters: {params}")
        results = neo4j_helper.query(query, params)
        logger.info(f"Query results: {results}")
        return results
    except Exception as e:
        logger.error(f"Failed to execute read query: {e}")
        return None

