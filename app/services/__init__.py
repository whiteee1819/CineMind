"""Services layer: data ingestion, categorisation and recommendation logic."""

from .data_loader import DatasetError
from .recommender import MovieRecommender
from .store import DatasetStore

__all__ = ["DatasetError", "DatasetStore", "MovieRecommender"]
