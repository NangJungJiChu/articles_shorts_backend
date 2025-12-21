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
    return user_vector.tolist()
