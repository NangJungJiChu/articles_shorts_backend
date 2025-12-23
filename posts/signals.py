import re
import os
import requests
from io import BytesIO
from PIL import Image
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.conf import settings
from .models import Post, Comment, UserInteraction
from .utils import async_calculate_user_vector
from sentence_transformers import SentenceTransformer
from transformers import BlipProcessor, BlipForConditionalGeneration
from .opensearch_client import OpenSearchClient
from .bedrock_client import BedrockClient

import logging

logger = logging.getLogger(__name__)

# Load models globally
try:
    embed_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
except Exception as e:
    logger.error(f"Failed to load SentenceTransformer model: {e}")
    embed_model = None

try:
    # Load BLIP for image captioning
    caption_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
except Exception as e:
    logger.error(f"Failed to load BLIP model: {e}")
    caption_processor = None
    caption_model = None

def generate_image_caption(image_url):
    """
    Generate caption for an image URL (S3).
    """
    if not caption_model or not caption_processor:
        return ""
    
    try:
        # Download image from URL
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        raw_image = Image.open(BytesIO(response.content)).convert('RGB')
        
        inputs = caption_processor(raw_image, return_tensors="pt")
        out = caption_model.generate(**inputs)
        caption = caption_processor.decode(out[0], skip_special_tokens=True)
        return caption
    except Exception as e:
        logger.error(f"Error generating caption for {image_url}: {e}")
        return ""

@receiver(post_save, sender=Post)
def handle_post_embedding(sender, instance, created, **kwargs):
    """
    Generate embedding for the post content when saved.
    Includes image captions if images are present (S3 supported).
    """
    if not embed_model:
        logger.warning("Embedding model not loaded. Skipping embedding generation.")
        return

    # 1. Extract and caption images
    # Regex to find markdown images: ![](/media/...)
    content = instance.content or ""
    # Find all image paths starting with /media/
    # Pattern: ![alt](/media/filename)
    image_matches = re.findall(r'!\[.*?\]\((/media/(.*?))\)', content)
    
    captions = []
    for full_rel_path, filename in image_matches:
        # User confirmed structure: 
        # Content: /media/uuid.png
        # S3: https://{AWS_S3_CUSTOM_DOMAIN}/uuid.png
        if hasattr(settings, 'AWS_S3_CUSTOM_DOMAIN') and settings.AWS_S3_CUSTOM_DOMAIN:
            s3_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{filename}"
            caption = generate_image_caption(s3_url)
            if caption:
                captions.append(caption)

    # 2. Clean content (remove markdown images)
    pure_text = re.sub(r'!\[.*?\]\(.*?\)', '', content)
    
    # 3. Combine Title + Content + Captions
    caption_text = " ".join(captions)
    combined_text = f"{instance.title} {pure_text} {caption_text}".strip()

    if not combined_text:
        return

    try:
        # 4. Generate embedding
        vector = embed_model.encode(combined_text).tolist()

        # 5. Update without triggering signals again
        Post.objects.filter(pk=instance.pk).update(embedding=vector)
        logger.info(f"Generated embedding for Post {instance.pk} (with {len(captions)} captions)")
    except Exception as e:
        logger.error(f"Error generating embedding for Post {instance.pk}: {e}")

@receiver(m2m_changed, sender=Post.like_users.through)
def handle_like_interaction(sender, instance, action, pk_set, **kwargs):
    """
    Record an interaction when a user likes/unlikes a post.
    """
    if action == "post_add":
        for user_id in pk_set:
            UserInteraction.objects.create(
                user_id=user_id,
                post=instance,
                interaction_type='LIKE',
                score=5.0
            )
            async_calculate_user_vector(user_id)
    elif action == "post_remove":
        # Optional: update vector when like is removed? 
        # For now, interactions are historical, so we don't delete them.
        for user_id in pk_set:
            async_calculate_user_vector(user_id)

@receiver(post_save, sender=Comment)
def handle_comment_interaction(sender, instance, created, **kwargs):
    """
    Record an interaction when a user leaves a comment.
    """
    if created:
        UserInteraction.objects.create(
            user=instance.author,
            post=instance.post,
            interaction_type='COMMENT',
            score=3.0
        )
        async_calculate_user_vector(instance.author_id)

@receiver(post_save, sender=Post)
def sync_post_to_opensearch(sender, instance, created, **kwargs):
    """
    Sync post to OpenSearch when saved.
    Generates Bedrock embedding and indexes the document.
    Independent of DB embedding logic.
    """
    try:
        os_client = OpenSearchClient()
        os_client.create_index_if_not_exists() # Ensure index exists
        
        bedrock_client = BedrockClient()
        
        # 1. Prepare text
        content = instance.content or ""
        pure_text = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        combined_text = f"{instance.title} {pure_text}".strip()
        
        if not combined_text:
            return

        # 2. Generate Embedding
        vector = bedrock_client.get_embedding(combined_text)
        
        if not vector:
            logger.warning(f"Failed to generate Bedrock embedding for Post {instance.pk}")
            return

        # 3. Index to OpenSearch
        doc = {
            "id": str(instance.pk),
            "title": instance.title,
            "content": pure_text[:1000], 
            "author": instance.author.username,
            "created_at": instance.created_at.isoformat(),
            "embedding": vector
        }
        
        os_client.index_document('posts', str(instance.pk), doc)
        logger.info(f"Synced Post {instance.pk} to OpenSearch")
        
    except Exception as e:
        logger.error(f"Error syncing Post {instance.pk} to OpenSearch: {e}")

from django.db.models.signals import post_delete 
@receiver(post_delete, sender=Post)
def delete_post_from_opensearch(sender, instance, **kwargs):
    try:
        os_client = OpenSearchClient()
        if os_client.client:
            os_client.client.delete(index='posts', id=str(instance.pk), ignore=[404])
            logger.info(f"Deleted Post {instance.pk} from OpenSearch")
    except Exception as e:
        logger.error(f"Error deleting Post {instance.pk} from OpenSearch: {e}")

