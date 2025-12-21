import re
import os
import requests
from io import BytesIO
from PIL import Image
from django.core.management.base import BaseCommand
from django.conf import settings
from posts.models import Post
from sentence_transformers import SentenceTransformer
from transformers import BlipProcessor, BlipForConditionalGeneration

class Command(BaseCommand):
    help = 'Backfill embeddings for posts that are missing them, including image captions from S3.'

    def handle(self, *args, **options):
        self.stdout.write("Loading embedding model...")
        embed_model = SentenceTransformer('jhgan/ko-sroberta-multitask')

        self.stdout.write("Loading image captioning model (BLIP)...")
        try:
            caption_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to load BLIP model: {e}"))
            caption_processor = None
            caption_model = None

        posts_to_update = Post.objects.filter(embedding__isnull=True)
        count = posts_to_update.count()
        self.stdout.write(f"Found {count} posts to update.")

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No posts needed updating."))
            return

        processed = 0
        for post in posts_to_update.iterator():
            try:
                # 1. Image Captioning
                content = post.content or ""
                # Find all image paths starting with /media/
                # Pattern: ![alt](/media/filename)
                image_matches = re.findall(r'!\[.*?\]\((/media/(.*?))\)', content)
                captions = []
                
                if caption_model and caption_processor and hasattr(settings, 'AWS_S3_CUSTOM_DOMAIN') and settings.AWS_S3_CUSTOM_DOMAIN:
                    for full_rel_path, filename in image_matches:
                        s3_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{filename}"
                        try:
                            response = requests.get(s3_url, timeout=5)
                            if response.status_code == 200:
                                raw_image = Image.open(BytesIO(response.content)).convert('RGB')
                                inputs = caption_processor(raw_image, return_tensors="pt")
                                out = caption_model.generate(**inputs)
                                cap = caption_processor.decode(out[0], skip_special_tokens=True)
                                captions.append(cap)
                        except Exception as img_e:
                            # self.stdout.write(self.style.WARNING(f"Failed to caption {s3_url}: {img_e}"))
                            pass

                # 2. Prepare Text
                # Remove all markdown images from text
                pure_text = re.sub(r'!\[.*?\]\(.*?\)', '', content)
                caption_text = " ".join(captions)
                combined_text = f"{post.title} {pure_text} {caption_text}".strip()
                
                if not combined_text:
                    continue

                # 3. Generate Embedding
                vector = embed_model.encode(combined_text).tolist()
                
                # 4. Update
                Post.objects.filter(pk=post.pk).update(embedding=vector)
                
                processed += 1
                if processed % 10 == 0:
                     self.stdout.write(f"Processed {processed}/{count} posts...")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing post {post.pk}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully backfilled embeddings for {processed} posts."))
