import boto3
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class BedrockClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BedrockClient, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        try:
            self.client = boto3.client(
                'bedrock-runtime',
                region_name=settings.AWS_S3_REGION_NAME if hasattr(settings, 'AWS_S3_REGION_NAME') else 'ap-northeast-2',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            self.client = None

    def get_embedding(self, text):
        if not self.client:
            return None
            
        # Amazon Titan Text Embeddings v2
        model_id = "amazon.titan-embed-text-v2:0"
        
        body = json.dumps({
            "inputText": text,
            "dimensions": 1024,
            "normalize": True
        })

        try:
            response = self.client.invoke_model(
                body=body,
                modelId=model_id,
                accept="application/json",
                contentType="application/json"
            )
            response_body = json.loads(response.get("body").read())
            embedding = response_body.get("embedding")
            return embedding
        except Exception as e:
            logger.error(f"Bedrock embedding generation failed: {e}")
            return None
