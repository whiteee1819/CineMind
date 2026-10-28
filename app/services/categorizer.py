"""Automatic genre categorisation for movies that arrive without a genre.

Approach (a *nearest-centroid text classifier*):

1. Every genre that has at least ``min_examples`` labelled movies becomes a
   class; its centroid is the mean TF-IDF vector of those movies.
2. Each unlabelled movie is compared to every centroid by cosine similarity.
3. The best matching genres (above an absolute and a relative threshold) are
   assigned.

It is intentionally lightweight – no training step, deterministic, and it works
on catalogues of any size.  The recommender flags inferred genres so the UI can
show them as "AI-suggested".
"""

from __future__ import annotations

import re
from collections import Counter

import numpy as np
from scipy import sparse
from sklearn.preprocessing import normalize


def infer_missing_genres(
    text_matrix: sparse.csr_matrix,
    genre_lists: list[list[str]],
    descriptions: list[str],
    *,
    min_examples: int = 2,
    top_n: int = 2,
    min_similarity: float = 0.04,
    relative_threshold: float = 0.6,
) -> dict[int, list[str]]:
    """Suggest genres for rows whose genre list is empty.

    Besides centroid similarity, a genre whose *name* occurs in the description
    (``"animated"`` → Animation) receives a fixed bonus.  This keeps the
    classifier useful on small catalogues where centroids are still noisy.

    Parameters
    ----------
    text_matrix:
        L2-normalised TF-IDF matrix (one row per movie).
    genre_lists:
        Known genres per movie (empty list = unknown).
    descriptions:
        Raw description per movie (same order as ``genre_lists``).
    min_examples:
        Minimum number of labelled movies a genre needs to be predictable.
    top_n:
        Maximum number of genres assigned per movie.
    min_similarity:
        Absolute similarity floor for a prediction.
    relative_threshold:
        A runner-up genre must reach this fraction of the best similarity.

    Returns
    -------
    dict
        ``{row index: [genre, ...]}`` – only rows that received a prediction.
    """
    unlabeled = [i for i, genres in enumerate(genre_lists) if not genres]
    if not unlabeled or text_matrix.shape[1] == 0:
        return {}

    counts = Counter(genre for genres in genre_lists for genre in genres)
    classes = sorted(genre for genre, count in counts.items() if count >= min_examples)
    if not classes:
        return {}
    class_index = {genre: j for j, genre in enumerate(classes)}

    # Sparse (movies x classes) membership matrix, then centroids via one product.
    rows, cols = [], []
    for i, genres in enumerate(genre_lists):
        for genre in genres:
            if genre in class_index:
                rows.append(i)
                cols.append(class_index[genre])
    membership = sparse.csr_matrix(
        (np.ones(len(rows)), (rows, cols)), shape=(len(genre_lists), len(classes))
    )
    centroids = normalize(membership.T @ text_matrix)  # (classes x vocabulary)

    similarities = (text_matrix[unlabeled] @ centroids.T).toarray()
    similarities += _name_evidence(classes, [descriptions[i] for i in unlabeled])
    predictions: dict[int, list[str]] = {}
    for row, movie_index in enumerate(unlabeled):
        scores = similarities[row]
        best = float(scores.max()) if scores.size else 0.0
        if best < min_similarity:
            continue
        floor = max(min_similarity, relative_threshold * best)
        ranked = np.argsort(-scores)[:top_n]
        picked = [classes[j] for j in ranked if scores[j] >= floor]
        if picked:
            predictions[movie_index] = picked
    return predictions


_WORD_RE = re.compile(r"[a-z]+")
_NAME_BONUS = 0.25


def _name_evidence(classes: list[str], descriptions: list[str]) -> np.ndarray:
    """Return a (descriptions x classes) matrix of genre-name match bonuses.

    A genre matches when every word of its name is found, by a 6-letter stem,
    among the description's words – so "animated" matches "Animation" and
    "Science Fiction" needs both a "scienc…" and a "fictio…" word.
    """
    stems = [
        [word[:6] for word in _WORD_RE.findall(genre.lower())] or [genre.lower()[:6]]
        for genre in classes
    ]
    bonus = np.zeros((len(descriptions), len(classes)))
    for row, description in enumerate(descriptions):
        words = {word[:6] for word in _WORD_RE.findall(description.lower())}
        for column, genre_stems in enumerate(stems):
            if all(stem in words for stem in genre_stems):
                bonus[row, column] = _NAME_BONUS
    return bonus
