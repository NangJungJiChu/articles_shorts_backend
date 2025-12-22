import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from django.conf import settings
from .models import UserInteraction, Post
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

def train_matrix_factorization(n_components=64):
    """
    Train Matrix Factorization model using SVD on User-Item Interaction Matrix.
    Updates User.cf_latent_vector and Post.cf_latent_vector.
    
    Score Mapping:
    - LIKE: 5
    - COMMENT: 3
    - VIEW: 1 (or calculated score)
    """
    logger.info("Starting Matrix Factorization Training...")
    
    # 1. Load Data
    interactions = UserInteraction.objects.all().values('user_id', 'post_id', 'score')
    df = pd.DataFrame(list(interactions))
    
    if df.empty:
        logger.warning("No interactions found. Skipping training.")
        return
        
    # 2. Create Pivot Table (User x Item)
    # Fill NaN with 0 (Implicit Feedback assumption: 0 = unknown/uninterested)
    user_item_matrix = df.pivot_table(index='user_id', columns='post_id', values='score', fill_value=0)
    
    # 3. Matrix Factorization (SVD)
    # Using TruncatedSVD (efficient for sparse matrices)
    # n_components = latent dimension (64)
    # If interactions are few, reduce components
    n_users, n_items = user_item_matrix.shape
    actual_components = min(n_components, n_users - 1, n_items - 1)
    if actual_components < 2:
        actual_components = 2 # Minimum dim
        
    svd = TruncatedSVD(n_components=actual_components, random_state=42)
    user_factors = svd.fit_transform(user_item_matrix) # U * Sigma
    item_factors = svd.components_.T # V
    
    # 4. Save Latent Vectors
    
    # A. Save User Vectors
    user_ids = user_item_matrix.index
    users_to_update = []
    
    for idx, user_id in enumerate(user_ids):
        vector = user_factors[idx].tolist()
        # Pad if dimensions reduced (e.g. if SVD reduced dim due to small data)
        # We need fixed 64 dim for DB
        if len(vector) < n_components:
            vector = vector + [0.0] * (n_components - len(vector))
            
        u = User(id=user_id)
        u.cf_latent_vector = vector
        users_to_update.append(u)
    
    User.objects.bulk_update(users_to_update, ['cf_latent_vector'])
    logger.info(f"Updated {len(users_to_update)} User vectors.")
    
    # B. Save Item Vectors
    post_ids = user_item_matrix.columns
    posts_to_update = []
    
    for idx, post_id in enumerate(post_ids):
        vector = item_factors[idx].tolist()
        if len(vector) < n_components:
            vector = vector + [0.0] * (n_components - len(vector))
            
        p = Post(id=post_id)
        p.cf_latent_vector = vector
        posts_to_update.append(p)
        
    Post.objects.bulk_update(posts_to_update, ['cf_latent_vector'])
    logger.info(f"Updated {len(posts_to_update)} Post vectors.")
    
    logger.info("Matrix Factorization Training Completed.")
