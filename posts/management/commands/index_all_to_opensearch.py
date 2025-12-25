from django.core.management.base import BaseCommand
from posts.models import Post
from posts.opensearch_client import OpenSearchClient
from posts.bedrock_client import BedrockClient
import logging
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync all posts to OpenSearch index for semantic search'

    def handle(self, *args, **options):
        self.stdout.write("Initializing clients...")
        os_client = OpenSearchClient()
        bedrock_client = BedrockClient()

        self.stdout.write("Ensuring index exists...")
        os_client.create_index_if_not_exists('posts')

        posts = Post.objects.all()
        count = posts.count()
        self.stdout.write(f"Found {count} posts to index.")

        indexed_count = 0
        for post in posts:
            try:
                # We use Bedrock for OpenSearch embeddings (1024 dim)
                # The user want Bedrock/OpenSearch separate from local SentenceTransformer
                combined_text = f"{post.title} {post.content}"
                # Truncate to avoid Bedrock token limit (8192 tokens)
                # 15000 chars is a safe approximation for ~8000 tokens
                combined_text = combined_text[:15000] 
                
                embedding = bedrock_client.get_embedding(combined_text)
                
                if not embedding:
                    self.stdout.write(self.style.WARNING(f"Failed to get embedding for post {post.id}"))
                    continue

                doc = {
                    'id': str(post.id),
                    'title': post.title,
                    'content': post.content,
                    'author': post.author.username if post.author else 'unknown',
                    'embedding': embedding
                }
                
                os_client.index_document('posts', str(post.id), doc)
                indexed_count += 1
                
                # Rate limit for Bedrock
                time.sleep(1.0)
                
                if indexed_count % 10 == 0:
                    self.stdout.write(f"Indexed {indexed_count}/{count}...")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error indexing post {post.id}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully indexed {indexed_count} posts to OpenSearch."))
