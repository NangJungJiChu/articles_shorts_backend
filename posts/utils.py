import numpy as np
from .models import UserInteraction
from django_q.tasks import async_task
from django.contrib.auth import get_user_model

def calculate_user_vector(user_id, limit=50):
    """
    Calculate the user's preference vector based on their recent interactions.
    Weight = interaction.score
    """
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None

    # Get recent interactions with scores
    interactions = UserInteraction.objects.filter(user=user).select_related('post').order_by('-created_at')[:limit]
    
    if not interactions:
        return None

    weighted_vectors = []
    total_weight = 0.0

    for interaction in interactions:
        post = interaction.post
        if post.embedding is None:
            continue
            
        weight = interaction.score
        # Ensure embedding is a numpy array
        embedding = np.array(post.embedding)
        
        weighted_vectors.append(embedding * weight)
        total_weight += weight

    if total_weight == 0:
        return None

    # Calculate weighted average
    user_vector = np.sum(weighted_vectors, axis=0) / total_weight
    
    # Save to User model
    user.preference_vector = user_vector.tolist()
    user.save(update_fields=['preference_vector'])
    
    return user.preference_vector

def async_calculate_user_vector(user_id):
    """
    Queue a background task to recalculate the user's preference vector.
    """
    async_task(calculate_user_vector, user_id)

def get_user_vector(user):
    """
    Get the user's preference vector. If not present, trigger calculation.
    """
    if user.preference_vector is not None:
        return user.preference_vector
    
    # If not present, calculate synchronously for immediate use if possible, 
    # or just return None if we want to wait for the background task.
    # In this case, we'll calculate it synchronously once for cold start.
    return calculate_user_vector(user.id)
