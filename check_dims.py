import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'njjc.settings')
django.setup()

from posts.models import Post

def check_post(post_id):
    try:
        post = Post.objects.get(pk=post_id)
        print(f"Post {post_id}:")
        if post.embedding is not None:
            # pgvector field usually returns a list/array
            print(f"  Embedding dimensions: {len(post.embedding)}")
        else:
            print("  Embedding is None")
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    check_post(6148)
    check_post(8842)
