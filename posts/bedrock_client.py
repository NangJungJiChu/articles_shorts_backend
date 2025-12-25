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
            region = getattr(settings, 'BEDROCK_REGION', 'ap-northeast-2')
            self.client = boto3.client(
                'bedrock-runtime',
                region_name=region,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            self.client = None

    def get_embedding(self, text):
        if not self.client:
            return None
        
        import time
        max_retries = 5
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Amazon Titan Text Embeddings v2
                model_id = "amazon.titan-embed-text-v2:0"
                body = json.dumps({
                    "inputText": text,
                    "dimensions": 1024,
                    "normalize": True
                })
                
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
                # Check for throttling (429 or ThrottlingException)
                error_str = str(e)
                if "ThrottlingException" in error_str or "Too many requests" in error_str:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Bedrock throttled (attempt {attempt+1}/{max_retries}). Retrying in {delay}s...")
                    time.sleep(delay)
                elif "ValidationException" in error_str and "Too many input tokens" in error_str:
                    logger.error(f"Bedrock validation error: {e}. Text too long.")
                    break
                else:
                    logger.error(f"Bedrock embedding generation failed: {e}")
                    # For other transient errors, still try next attempt
                    time.sleep(base_delay)
                    
        return None
