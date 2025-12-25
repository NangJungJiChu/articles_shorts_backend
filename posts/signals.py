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

# Models will be lazy-loaded to prevent blocking startup
_embed_model = None
_caption_processor = None
_caption_model = None

def get_embed_model():
    global _embed_model
    if _embed_model is None:
        try:
            logger.info("Loading SentenceTransformer model...")
            from sentence_transformers import SentenceTransformer
            _embed_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer model: {e}")
    return _embed_model

def get_caption_models():
    global _caption_processor, _caption_model
    if _caption_model is None or _caption_processor is None:
        try:
            logger.info("Loading BLIP models...")
            from transformers import BlipProcessor, BlipForConditionalGeneration
            _caption_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            _caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        except Exception as e:
            logger.error(f"Failed to load BLIP model: {e}")
    return _caption_processor, _caption_model

def generate_image_caption(image_url):
    caption_processor, caption_model = get_caption_models()
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
    embed_model = get_embed_model()
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
        # 4. Generate embedding for pgvector (SentenceTransformer)
        vector = embed_model.encode(combined_text).tolist()

        # 5. Update without triggering signals again
        Post.objects.filter(pk=instance.pk).update(embedding=vector)
        logger.info(f"Generated pgvector embedding for Post {instance.pk}")

        # 6. Index to OpenSearch (using Bedrock)
        bedrock_client = BedrockClient()
        os_embedding = bedrock_client.get_embedding(combined_text)
        if os_embedding:
            os_client = OpenSearchClient()
            doc = {
                'id': str(instance.id),
                'title': instance.title,
                'content': instance.content,
                'author': instance.author.username if instance.author else 'unknown',
                'embedding': os_embedding
            }
            os_client.index_document('posts', str(instance.id), doc)
            logger.info(f"Indexed Post {instance.pk} to OpenSearch")
        else:
            logger.error(f"Failed to generate Bedrock embedding for Post {instance.pk}")

    except Exception as e:
        logger.error(f"Error handling embedding for Post {instance.pk}: {e}")

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
        # Remove interaction if user unlikes
        for user_id in pk_set:
            UserInteraction.objects.filter(
                user_id=user_id,
                post=instance,
                interaction_type='LIKE'
            ).delete()
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


@receiver(post_delete, sender=Comment)
def handle_comment_deletion(sender, instance, **kwargs):
    """
    Remove interaction when a comment is deleted.
    Tries to find the interaction created around the same time.
    """
    try:
        # Define a time window to match the interaction (e.g., +/- 2 seconds)
        from datetime import timedelta
        # Ensure instance.created_at is not null
        if not instance.created_at:
            return

        time_threshold = timedelta(seconds=5) 
        min_time = instance.created_at - time_threshold
        max_time = instance.created_at + time_threshold

        # Find matching interaction
        # We order by created_at to find the closest one
        interactions = UserInteraction.objects.filter(
            user=instance.author,
            post=instance.post,
            interaction_type='COMMENT',
            created_at__range=(min_time, max_time)
        )
        
        # If multiple found, pick the one closest in time
        closest_interaction = None
        min_diff = None

        for interaction in interactions:
            diff = abs((interaction.created_at - instance.created_at).total_seconds())
            if min_diff is None or diff < min_diff:
                min_diff = diff
                closest_interaction = interaction

        if closest_interaction:
            closest_interaction.delete()
            async_calculate_user_vector(instance.author.id)
            logger.info(f"Deleted interaction for Comment {instance.id}")
            
    except Exception as e:
        logger.error(f"Error handling comment deletion for Comment {instance.id}: {e}")
