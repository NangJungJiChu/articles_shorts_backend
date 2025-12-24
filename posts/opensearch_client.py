import logging
from opensearchpy import OpenSearch, RequestsHttpConnection
from django.conf import settings
import os

logger = logging.getLogger(__name__)

class OpenSearchClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OpenSearchClient, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'localhost')
        OPENSEARCH_PORT = int(os.environ.get('OPENSEARCH_PORT', 9200))
        OPENSEARCH_USER = os.environ.get('OPENSEARCH_USER', '')
        OPENSEARCH_PASSWORD = os.environ.get('OPENSEARCH_PASSWORD', '')

        try:
            self.client = OpenSearch(
                hosts=[{'host': host, 'port': port}],
                http_auth=auth,
                use_ssl=True,
                verify_certs=False, # For local dev with self-signed certs
                ssl_assert_hostname=False,
                ssl_show_warn=False,
                connection_class=RequestsHttpConnection
            )
            logger.info("OpenSearch client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch client: {e}")
            self.client = None

    def get_client(self):
        return self.client

    def create_index_if_not_exists(self, index_name='posts'):
        if not self.client:
            return
        
        if not self.client.indices.exists(index=index_name):
            # Define k-NN index mapping matching Lambda
            body = {
                "settings": {
                    "index": {
                        "knn": True,
                         "knn.algo_param.ef_search": 100
                    }
                },
                "mappings": {
                    "properties": {
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 1024, 
                            "method": {
                                "name": "hnsw",
                                "engine": "nmslib",
                                "space_type": "cosinesimil"
                            }
                        },
                        "title": {"type": "text"},
                        "content": {"type": "text"},
                        "id": {"type": "keyword"},
                    }
                }
            }
            self.client.indices.create(index=index_name, body=body)
            logger.info(f"Created OpenSearch index: {index_name}")

    def index_document(self, index_name, doc_id, body):
        if not self.client:
            return
        try:
            self.client.index(index=index_name, id=doc_id, body=body, refresh=True)
            logger.info(f"Indexed document {doc_id} to {index_name}")
        except Exception as e:
            logger.error(f"Error indexing to OpenSearch: {e}")

    def search(self, index_name, query_vector, k=5):
        if not self.client:
            return []
        
        query = {
            "size": k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_vector,
                        "k": k
                    }
                }
            }
        }
        
        try:
            response = self.client.search(index=index_name, body=query)
            hits = response['hits']['hits']
            return hits
        except Exception as e:
            logger.error(f"OpenSearch search failed: {e}")
            return []
