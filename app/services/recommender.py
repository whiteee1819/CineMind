"""Hybrid content-based recommendation engine.

For every request a *taste profile* is assembled from up to four signals:

* **Liked movies** – their TF-IDF centroid, genre centroid and mean release year.
* **Preferred genres** – a hard filter (movie must have *any* of them) and a
  genre-vector boost.
* **Mood text** – free text such as "dark heist in space", vectorised with the
  same TF-IDF model as the catalogue.
* **Release window** – optional hard filter on the year.

Each candidate is scored with a weighted blend of three cosine-style signals::

    score = (0.60 * text + 0.30 * genre + 0.10 * year) / sum(active weights)

Weights of signals that are not available for a request (e.g. no liked movies,
hence no year target) are dropped and the rest are re-normalised, so a score is
always in ``[0, 1]``.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from .categorizer import infer_missing_genres
from .data_loader import parse_genres


class MovieRecommender:
    """In-memory recommender built from a normalised movie data frame."""

    TEXT_WEIGHT = 0.60
    GENRE_WEIGHT = 0.30
    YEAR_WEIGHT = 0.10
    #: Years between two releases after which the year score drops to ~37 %.
    YEAR_DECAY = 20.0
    #: How strongly mood text steers the profile relative to liked movies.
    MOOD_WEIGHT = 0.8
    #: Year score for movies without a release year (neutral).
    UNKNOWN_YEAR_SCORE = 0.5

    def __init__(self, frame: pd.DataFrame) -> None:
        if frame.empty:
            raise ValueError("Cannot build a recommender from an empty dataset.")

        self._titles: list[str] = frame["title"].tolist()
        self._descriptions: list[str] = frame["description"].tolist()
        self._years: np.ndarray = frame["year"].to_numpy(dtype=float)
        original_genres: list[list[str]] = [list(g) for g in frame["genres"]]
        self.size = len(self._titles)

        self._build_text_model()

        # Categorise movies that have no genre using their description.
        inferred = infer_missing_genres(self._text, original_genres, self._descriptions)
        self._genre_lists: list[list[str]] = [
            inferred.get(i, genres) for i, genres in enumerate(original_genres)
        ]
        self._inferred = np.zeros(self.size, dtype=bool)
        self._inferred[list(inferred)] = True
        self.genres_inferred = int(self._inferred.sum())

        self._build_genre_model()

        self._title_lower = np.array([t.lower() for t in self._titles])
        # Deterministic jitter breaks ties without an alphabetical bias.
        self._jitter = np.random.default_rng(42).random(self.size)
        self._decades = [self._decade_label(y) for y in self._years]
        self._stats = self._compute_stats()

    # ──────────────────────────────────────────────────────────────────
    # Model construction
    # ──────────────────────────────────────────────────────────────────
    def _build_text_model(self) -> None:
        """Fit TF-IDF on ``description + title``; degrade gracefully if empty."""
        documents = [f"{desc} {title}" for desc, title in zip(self._descriptions, self._titles)]
        self._vectorizer: TfidfVectorizer | None = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
            strip_accents="unicode",
            max_features=200_000,
        )
        try:
            self._text = self._vectorizer.fit_transform(documents).tocsr()
            self._terms = np.asarray(self._vectorizer.get_feature_names_out())
        except ValueError:  # "empty vocabulary" – e.g. only stop-words
            self._vectorizer = None
            self._text = sparse.csr_matrix((self.size, 0))
            self._terms = np.asarray([], dtype=str)

    def _build_genre_model(self) -> None:
        self.genres: list[str] = sorted({g for genres in self._genre_lists for g in genres})
        self._genre_index = {g: i for i, g in enumerate(self.genres)}
        self._genre_lookup = {g.lower(): g for g in self.genres}

        if not self.genres:
            self._genre = sparse.csr_matrix((self.size, 0))
            return

        rows, cols = [], []
        for i, genres in enumerate(self._genre_lists):
            for genre in genres:
                rows.append(i)
                cols.append(self._genre_index[genre])
        binary = sparse.csr_matrix(
            (np.ones(len(rows)), (rows, cols)), shape=(self.size, len(self.genres))
        )
        self._genre = normalize(binary).tocsr()

    @staticmethod
    def _decade_label(year: float) -> str | None:
        return None if math.isnan(year) else f"{int(year) // 10 * 10}s"

    # ──────────────────────────────────────────────────────────────────
    # Public read API
    # ──────────────────────────────────────────────────────────────────
    def movie(self, movie_id: int) -> dict[str, Any] | None:
        """Return one movie as a JSON-ready dict, or ``None`` if unknown."""
        if not 0 <= movie_id < self.size:
            return None
        year = self._years[movie_id]
        return {
            "id": int(movie_id),
            "title": self._titles[movie_id],
            "year": None if math.isnan(year) else int(year),
            "decade": self._decades[movie_id],
            "genres": list(self._genre_lists[movie_id]),
            "description": self._descriptions[movie_id],
            "genre_inferred": bool(self._inferred[movie_id]),
        }

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        """Title auto-complete: prefix matches first, then substring matches."""
        needle = query.strip().lower()
        if not needle:
            return []
        contains = np.char.find(self._title_lower, needle) >= 0
        indices = np.flatnonzero(contains)
        ranked = sorted(
            indices,
            key=lambda i: (not self._title_lower[i].startswith(needle), len(self._titles[i]), self._titles[i]),
        )
        return [self.movie(int(i)) for i in ranked[:limit]]

    def list_movies(
        self,
        query: str = "",
        genre: str = "",
        sort: str = "title",
        page: int = 1,
        per_page: int = 24,
    ) -> dict[str, Any]:
        """Paginated library view with optional text and genre filters."""
        mask = np.ones(self.size, dtype=bool)
        needle = query.strip().lower()
        if needle:
            in_desc = np.char.find(np.array([d.lower() for d in self._descriptions]), needle) >= 0
            mask &= (np.char.find(self._title_lower, needle) >= 0) | in_desc
        if genre:
            canonical = self._genre_lookup.get(genre.strip().lower())
            if canonical is None:
                mask &= False
            else:
                mask &= self._genre[:, self._genre_index[canonical]].toarray().ravel() > 0

        indices = np.flatnonzero(mask)
        if sort == "year_desc":
            order = sorted(indices, key=lambda i: (math.isnan(self._years[i]), -np.nan_to_num(self._years[i])))
        elif sort == "year_asc":
            order = sorted(indices, key=lambda i: (math.isnan(self._years[i]), np.nan_to_num(self._years[i])))
        else:
            order = sorted(indices, key=lambda i: self._title_lower[i])

        per_page = max(1, per_page)
        total = len(order)
        pages = max(1, math.ceil(total / per_page))
        page = min(max(1, page), pages)
        window = order[(page - 1) * per_page : page * per_page]
        return {
            "items": [self.movie(int(i)) for i in window],
            "total": total,
            "page": page,
            "pages": pages,
            "per_page": per_page,
        }

    def stats(self) -> dict[str, Any]:
        """Dataset analytics shown on the *Insights* tab."""
        return self._stats

    # ──────────────────────────────────────────────────────────────────
    # Recommendation
    # ──────────────────────────────────────────────────────────────────
    def recommend(
        self,
        liked_ids: list[int] | None = None,
        genres: list[str] | None = None,
        mood: str = "",
        year_min: int | None = None,
        year_max: int | None = None,
        limit: int = 12,
    ) -> dict[str, Any]:
        """Rank the catalogue for the given taste profile.

        Raises
        ------
        ValueError
            If the request contains no usable signal (no liked movie, genre or
            mood text).
        """
        liked = list(dict.fromkeys(i for i in (liked_ids or []) if 0 <= i < self.size))
        requested = [label for g in (genres or []) for label in parse_genres(g)]
        preferred = list(
            dict.fromkeys(
                self._genre_lookup[label.lower()] for label in requested if label.lower() in self._genre_lookup
            )
        )
        mood = (mood or "").strip()
        if not liked and not genres and not mood:
            raise ValueError("Pick at least one movie, a genre, or describe a mood.")

        # ── Signals ────────────────────────────────────────────────────
        text_query = self._text_query(liked, mood)
        text_scores = (
            np.asarray((self._text @ text_query.T).todense()).ravel() if text_query is not None else None
        )

        genre_query = self._genre_query(liked, preferred)
        genre_scores = self._genre @ genre_query if genre_query is not None else None

        year_scores = None
        liked_years = self._years[liked][~np.isnan(self._years[liked])] if liked else np.array([])
        if liked_years.size:
            target = float(liked_years.mean())
            year_scores = np.exp(-np.abs(np.nan_to_num(self._years, nan=1e6) - target) / self.YEAR_DECAY)
            year_scores[np.isnan(self._years)] = self.UNKNOWN_YEAR_SCORE

        # ── Blend ──────────────────────────────────────────────────────
        total_weight, blended = 0.0, np.zeros(self.size)
        for scores, weight in (
            (text_scores, self.TEXT_WEIGHT),
            (genre_scores, self.GENRE_WEIGHT),
            (year_scores, self.YEAR_WEIGHT),
        ):
            if scores is not None:
                blended += weight * scores
                total_weight += weight
        blended = blended / total_weight if total_weight else blended

        # ── Filters ────────────────────────────────────────────────────
        mask = np.ones(self.size, dtype=bool)
        if liked:
            mask[liked] = False
        if genres:
            if preferred:
                columns = [self._genre_index[g] for g in preferred]
                mask &= np.asarray(self._genre[:, columns].sum(axis=1)).ravel() > 0
            else:
                mask &= False  # none of the requested genres exists in this catalogue
        if year_min is not None:
            mask &= self._years >= year_min  # NaN compares False → excluded
        if year_max is not None:
            mask &= self._years <= year_max
        mask &= blended > 1e-9

        candidates = int(mask.sum())
        ranked = np.flatnonzero(mask)
        order = ranked[np.argsort(-(blended[ranked] + 1e-7 * self._jitter[ranked]), kind="stable")][:limit]

        results = self._explain(order, blended, text_query, liked, set(preferred))
        return {
            "results": results,
            "meta": {
                "candidates": candidates,
                "liked": [self._titles[i] for i in liked],
                "genres": preferred,
                "mood": mood,
                "signals": [
                    name
                    for name, active in (
                        ("text", text_scores is not None),
                        ("genre", genre_scores is not None),
                        ("year", year_scores is not None),
                    )
                    if active
                ],
            },
        }

    # -- query construction -------------------------------------------------
    def _text_query(self, liked: list[int], mood: str) -> sparse.csr_matrix | None:
        """Combine liked-movie centroid and mood text into one unit TF-IDF vector."""
        if self._vectorizer is None:
            return None
        query: sparse.csr_matrix | None = None
        if liked:
            centroid = sparse.csr_matrix(np.asarray(self._text[liked].mean(axis=0)))
            query = normalize(centroid)
        if mood:
            mood_vector = self._vectorizer.transform([mood])
            if mood_vector.nnz:
                query = mood_vector if query is None else normalize(query + self.MOOD_WEIGHT * mood_vector)
        return query if query is not None and query.nnz else None

    def _genre_query(self, liked: list[int], preferred: list[str]) -> np.ndarray | None:
        """Unit genre vector from liked movies' genres and explicit preferences."""
        if not self.genres:
            return None
        vector = np.zeros(len(self.genres))
        if liked:
            vector += np.asarray(self._genre[liked].mean(axis=0)).ravel()
        for genre in preferred:
            vector[self._genre_index[genre]] += 1.0
        norm = np.linalg.norm(vector)
        return vector / norm if norm else None

    # -- explanations -------------------------------------------------------
    def _explain(
        self,
        order: np.ndarray,
        scores: np.ndarray,
        text_query: sparse.csr_matrix | None,
        liked: list[int],
        preferred: set[str],
    ) -> list[dict[str, Any]]:
        """Attach score, shared genres, key themes and the closest liked movie."""
        if not len(order):
            return []

        profile_genres = set(preferred)
        for i in liked:
            profile_genres.update(self._genre_lists[i])

        closest: list[int | None] = [None] * len(order)
        if liked:
            similarity = 0.7 * (self._text[order] @ self._text[liked].T).toarray() + 0.3 * (
                self._genre[order] @ self._genre[liked].T
            ).toarray()
            closest = [liked[int(j)] for j in similarity.argmax(axis=1)]

        results = []
        for position, index in enumerate(order):
            item = self.movie(int(index))
            item["score"] = round(float(scores[index]), 4)
            # sqrt stretches the usually small cosine values into a readable 0-99 range.
            item["match"] = min(99, int(round(100 * math.sqrt(max(scores[index], 0.0)))))
            item["shared_genres"] = [g for g in item["genres"] if g in profile_genres]
            item["keywords"] = self._shared_terms(text_query, int(index))
            item["because"] = self._titles[closest[position]] if closest[position] is not None else None
            results.append(item)
        return results

    def _shared_terms(self, text_query: sparse.csr_matrix | None, index: int, top: int = 3) -> list[str]:
        """Terms that contributed most to the text similarity with the profile."""
        if text_query is None or self._text.shape[1] == 0:
            return []
        overlap = text_query.multiply(self._text[index]).tocoo()
        if overlap.nnz == 0:
            return []
        picked: list[str] = []
        for j in np.argsort(-overlap.data):
            term = str(self._terms[overlap.col[j]])
            # Skip n-grams whose words are already covered by a chosen term (and vice versa).
            if any(term in other or other in term for other in picked):
                continue
            picked.append(term)
            if len(picked) == top:
                break
        return picked

    # ──────────────────────────────────────────────────────────────────
    # Analytics
    # ──────────────────────────────────────────────────────────────────
    def _compute_stats(self) -> dict[str, Any]:
        genre_counts = np.asarray(self._genre.astype(bool).sum(axis=0)).ravel() if self.genres else []
        genre_table = sorted(
            ({"name": g, "count": int(c)} for g, c in zip(self.genres, genre_counts)),
            key=lambda row: (-row["count"], row["name"]),
        )

        decade_counts: dict[str, int] = {}
        for decade in self._decades:
            if decade:
                decade_counts[decade] = decade_counts.get(decade, 0) + 1
        decade_table = [{"name": d, "count": c} for d, c in sorted(decade_counts.items())]

        theme_table: list[dict[str, Any]] = []
        if self._text.shape[1]:
            weights = np.asarray(self._text.sum(axis=0)).ravel()
            for j in np.argsort(-weights):
                term = str(self._terms[j])
                if " " in term or len(term) < 4:
                    continue  # unigrams only: clearer to read
                theme_table.append({"name": term, "weight": round(float(weights[j]), 3)})
                if len(theme_table) == 14:
                    break

        known_years = self._years[~np.isnan(self._years)]
        return {
            "total": self.size,
            "year_min": int(known_years.min()) if known_years.size else None,
            "year_max": int(known_years.max()) if known_years.size else None,
            "genre_count": len(self.genres),
            "genres": genre_table,
            "decades": decade_table,
            "themes": theme_table,
            "with_description": int(sum(1 for d in self._descriptions if d)),
            "genres_inferred": self.genres_inferred,
            "avg_genres_per_movie": round(sum(len(g) for g in self._genre_lists) / self.size, 2),
        }
