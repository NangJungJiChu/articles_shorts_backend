import numpy as np
from .models import UserInteraction

def calculate_user_vector(user, limit=50):
    """
    Calculate the user's preference vector based on their recent interactions.
    Weight = interaction.score
    """
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

def get_user_vector(user):
    """
    Get the user's preference vector.
    """
    if user.preference_vector is not None:
        return user.preference_vector
    # If not present (legacy/new), try to calculate
    return calculate_user_vector(user)
