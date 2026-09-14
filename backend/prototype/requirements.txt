from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict

class CodeEmbedder:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)  # Realistic embeddings

    def embed_texts(self, texts: List[str]):
        return self.model.encode(texts)

def cluster_procedural_patterns(paragraph_texts: List[str], n_clusters=3):
    """Mock unsupervised clustering of procedural patterns into 'classes'."""
    if len(paragraph_texts) < 2:
        return [0] * len(paragraph_texts)
    
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(paragraph_texts)
    kmeans = KMeans(n_clusters=min(n_clusters, len(paragraph_texts)), random_state=42)
    clusters = kmeans.fit_predict(X)
    return clusters.tolist()