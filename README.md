# 🎬 CineMind — Intelligent Movie Recommendation System

> **An explainable, content-based movie recommendation platform built with Python, Flask, and scikit-learn.**

CineMind is a full-stack movie recommendation system designed to help users discover films based on their preferences, favorite movies, genres, moods, themes, and preferred release eras.

The system combines **TF-IDF text similarity, genre affinity, temporal similarity, automatic genre inference, flexible dataset ingestion, analytics, and an interactive web interface** into a single application.

It is designed as an **IBM-style capstone / portfolio project** demonstrating practical applications of Python, machine learning, data processing, REST APIs, web development, and software engineering.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Screenshots](#-screenshots)
- [How It Works](#-how-it-works)
- [Recommendation Algorithm](#-recommendation-algorithm)
- [Automatic Genre Classification](#-automatic-genre-classification)
- [Dataset Ingestion](#-dataset-ingestion)
- [Project Architecture](#-project-architecture)
- [Project Structure](#-project-structure)
- [Technology Stack](#-technology-stack)
- [Installation](#-installation)
- [Running the Application](#-running-the-application)
- [Using CineMind](#-using-cinemind)
- [REST API](#-rest-api)
- [Testing](#-testing)
- [Example Dataset](#-example-dataset)
- [Project Information](#-project-information)


---

# 🎯 Overview

Movie recommendation systems are widely used to help users discover content that matches their interests. CineMind approaches this problem using an **interpretable content-based recommendation architecture**.

Instead of relying on a black-box recommendation model, CineMind creates a user preference profile from several explicit signals:

- ⭐ Favorite movies
- 🎭 Preferred genres
- 📝 Natural-language mood or theme
- 📅 Preferred release era
- 🔎 Movie titles and descriptions

The recommendation engine then compares this profile against movies in the active catalogue and produces ranked recommendations.

Each recommendation can also provide an explanation describing why the movie was considered relevant.

---

# ✨ Features

## 🎬 Personalized Recommendations

Users can combine multiple preference signals:

- Favorite movies
- Genre preferences
- Natural-language mood/theme
- Release-year preferences

The system combines these signals to generate a ranked list of recommendations.

---

## 🧠 Content-Based Recommendation Engine

CineMind uses:

- TF-IDF vectorization
- Cosine similarity
- Multi-hot genre representations
- Temporal similarity
- Weighted score aggregation

The approach is lightweight, explainable, and does not require GPU-based deep learning.

---

## 📝 Natural-Language Mood Search

Users can describe what they want to watch using natural language.

Example:

> `psychological thriller with mind games`

or:

> `lonely astronaut stranded on a barren planet`

The query is converted into the same TF-IDF feature space used by the movie descriptions.

---

## 🎭 Automatic Genre Inference

Movies with missing genre information can be automatically categorized.

CineMind combines:

1. Nearest-centroid classification
2. TF-IDF text similarity
3. Word-stem evidence
4. Threshold-based genre assignment

Automatically inferred genres are explicitly marked in the interface.

---

## 📂 Flexible Dataset Upload

CineMind supports multiple dataset formats:

- CSV
- TSV
- TXT
- JSON
- XLSX

The ingestion pipeline can handle different encodings, delimiters, and column naming conventions.

For example, fields such as:

```text
title
movie_name
film
moviename
```

can be mapped into a common internal movie-title field.

---

## 📊 Dataset Analytics

The Insights section provides information such as:

- Total number of movies
- Number of genres
- Release-year range
- Automatically categorized movies
- Genre distribution
- Movies grouped by decade
- Dominant keywords/themes

---

## 🔍 Movie Library

The Library section allows users to:

- Search movies
- Filter by genre
- Sort alphabetically
- Sort by release year
- Browse the complete catalogue
- Paginate through large datasets

---

## 🌐 REST API

CineMind exposes JSON-based endpoints for external applications.

Available functionality includes:

- Health checks
- Dataset metadata
- Movie search
- Recommendations
- Dataset uploads
- Dataset reset

---

## 🛡️ Data Validation & Fault Tolerance

Uploaded datasets are validated before becoming the active dataset.

If an uploaded dataset is invalid, the existing working dataset remains available instead of being replaced by corrupted or unusable data.

---

---

# 📸 Screenshots

<img width="1599" height="899" alt="p1" src="https://github.com/user-attachments/assets/8f856547-d3e1-4ee8-81bc-8494a225c74f" />
<img width="1599" height="899" alt="p2" src="https://github.com/user-attachments/assets/9bc6e59c-6f5c-4615-9052-fab696b8996f" />
<img width="1599" height="899" alt="p3" src="https://github.com/user-attachments/assets/2e39cbe5-c423-4391-9b17-2846ee6544a1" />
<img width="1599" height="899" alt="p4" src="https://github.com/user-attachments/assets/482c415f-f6c8-4ea1-b8c8-983b8d854412" />
<img width="1599" height="899" alt="p5" src="https://github.com/user-attachments/assets/5eb234fb-837f-4e82-a651-45698bf73173" />



### Discover
<img width="1599" height="899" alt="WhatsApp Image 2026-10-29 at 12 45 35 PM" src="https://github.com/user-attachments/assets/654a3ddf-7755-4c96-935d-a7c77bb6a7a8" />


```text

```

### Library

<img width="1599" height="899" alt="p2" src="https://github.com/user-attachments/assets/acc6357b-3103-4c36-a569-ec0c1cbc74f8" />


```text

```

### Insights

<img width="1599" height="899" alt="p3" src="https://github.com/user-attachments/assets/4c3adc79-ac4b-4626-832d-4e4e97490a93" />


```text

```

### Dataset Upload

<img width="1599" height="899" alt="p4" src="https://github.com/user-attachments/assets/be14103a-893f-44f5-9a99-95c17ac8e3d4" />


```text

```

---

# ⚙️ How It Works

The overall workflow can be summarized as:

```text
                    ┌──────────────────────┐
                    │       User           │
                    │ Favorites / Genres   │
                    │ Mood / Era           │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Preference Profile   │
                    └──────────┬───────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │       Recommendation Engine    │
              │                                │
              │  TF-IDF Text Similarity        │
              │  Genre Similarity              │
              │  Temporal Similarity           │
              └───────────────┬────────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │ Candidate Ranking    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Top Recommendations  │
                    │ + Explanations       │
                    └──────────────────────┘
```

---

# 🧮 Recommendation Algorithm

CineMind builds a preference representation using several signals.

## 1. Text Similarity

Movie titles and descriptions are transformed into TF-IDF vectors.

The system then calculates similarity between the user's text preference and candidate movies.

---

## 2. Genre Similarity

Genres are converted into multi-hot vectors.

For example:

```text
Action     → 1
Comedy     → 0
Drama      → 1
Sci-Fi     → 1
Romance    → 0
```

This representation allows the system to compare genre preferences mathematically.

---

## 3. Temporal Similarity

The system can also consider the release year of movies.

The current temporal score uses an exponential decay function:

```text
YearScore = exp(-|Year - TargetYear| / τ)
```

where:

```text
τ = 20.0
```

---

## 4. Combined Recommendation Score

The current architecture combines the signals using:

```text
Score =
(
    0.60 × Text Similarity
    +
    0.30 × Genre Similarity
    +
    0.10 × Year Similarity
)
/
Sum of Active Weights
```

The weights are automatically re-normalized when some preference signals are not provided.

This allows the system to continue functioning when the user supplies only a subset of the available inputs.

---

# 🧠 Automatic Genre Classification

Some datasets may contain movies without genre information.

CineMind attempts to infer missing genres using a classification pipeline.

### Step 1 — Build Genre Centroids

For genres with enough labelled examples, the system creates a centroid from the TF-IDF representations of known movies.

### Step 2 — Compare Unlabelled Movies

The description of an unlabelled movie is compared against the available genre centroids.

### Step 3 — Word-Stem Evidence

The system also looks for textual evidence based on word stems.

Examples include:

```text
animated → Animation
space    → Science Fiction
scienc   → Science Fiction
```

### Step 4 — Threshold-Based Assignment

Only sufficiently strong matches are assigned automatically.

Automatically inferred genres are marked with an `✦ auto` indicator so that users can distinguish inferred information from original dataset information.

---

# 📂 Dataset Ingestion

CineMind is designed to tolerate common variations found in real-world movie datasets.

## Supported Formats

| Format | Supported |
|---|---|
| CSV | ✅ |
| TSV | ✅ |
| TXT | ✅ |
| JSON | ✅ |
| XLSX | ✅ |

## Supported Encodings

The loader supports common encodings including:

- UTF-8
- UTF-8 BOM
- CP1252
- Latin-1

## Delimiter Detection

The loader can detect common delimiters such as:

```text
,
;
\t
```

while preserving multi-value genre separators where applicable.

## Header Aliasing

Different column names can be mapped to canonical internal fields.

Examples:

| Dataset Column | Canonical Meaning |
|---|---|
| `film` | Title |
| `moviename` | Title |
| `movie name` | Title |
| `title` | Title |
| `overview` | Description |
| `plot` | Description |
| `desc` | Description |
| `category` | Genre |
| `release date` | Release Year |

---

# 🏗️ Project Architecture

```text
┌─────────────────────────────────────────────────────┐
│                    WEB BROWSER                      │
│                                                     │
│  Discover │ Library │ Insights │ Dataset            │
└───────────────────────┬─────────────────────────────┘
                        │
                        │ HTTP / REST JSON
                        ▼
┌─────────────────────────────────────────────────────┐
│                 FLASK APPLICATION                   │
│                                                     │
│  Page Controller          REST API Controller       │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                 DATA INGESTION                      │
│                                                     │
│  Data Loader            Genre Categorizer          │
│                                                     │
│  • Parsing              • Centroid classifier      │
│  • Validation           • Stem evidence            │
│  • Normalization        • Genre imputation         │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                CORE ENGINE & STORAGE                │
│                                                     │
│  Recommender            Dataset Store              │
│                                                     │
│  • TF-IDF               • Memory cache             │
│  • Genre similarity     • Persistence              │
│  • Year similarity      • Upload verification      │
│  • Explanations         • Dataset fallback         │
└─────────────────────────────────────────────────────┘
```

---

# 📁 Project Structure

```text
c:\anti-gr\
│
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── run.py
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── routes.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── data_loader.py
│   │   ├── categorizer.py
│   │   ├── recommender.py
│   │   └── store.py
│   │
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── app.js
│   │
│   └── templates/
│       └── index.html
│
├── data/
│   └── sample_movies.csv
│
├── instance/
│   └── data/
│
└── tests/
    ├── conftest.py
    ├── test_api.py
    ├── test_data_loader.py
    └── test_recommender.py
```

The project currently includes a bundled sample catalogue containing 75 movies and automated tests covering the API, data loader, and recommendation engine.

---

# 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend | Python | Application logic |
| Web Framework | Flask | Web server and REST API |
| Production Server | Waitress | WSGI production serving |
| Data Processing | pandas | Data manipulation |
| Scientific Computing | NumPy | Numerical operations |
| Scientific Computing | SciPy | Sparse matrix operations |
| Machine Learning | scikit-learn | TF-IDF and similarity |
| Excel Support | openpyxl | `.xlsx` ingestion |
| Frontend | HTML5 | Application structure |
| Styling | CSS3 | UI and animations |
| Frontend Logic | JavaScript ES2020 | Client-side interactions |
| Testing | pytest | Automated testing |

The project documentation specifies Python 3.10–3.12+, Flask 3.x, scikit-learn 1.4+, pandas 2.x–3.x, and pytest 8.x–9.x among its primary technology versions.

---

# 🚀 Installation

## Prerequisites

Install:

- Python 3.10 or newer
- pip
- Git

Verify your installation:

```cmd
python --version
pip --version
```

Python 3.12 is the recommended version for the current project configuration.

---

## 1. Clone the Repository

[GITHUB URL](https://github.com/whiteee1819/CineMind/tree/main)
```cmd
```

If the project already exists locally:

```cmd
cd /d c:\anti-gr
```

---

## 2. Create a Virtual Environment

### Windows CMD

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the environment again.

---

## 3. Install Dependencies

```cmd
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

# ▶️ Running the Application

## Development Server

Run:

```cmd
python run.py
```

The application will be available at:

```text
http://127.0.0.1:5000
```

---

## Development Mode with Debugging

Windows CMD:

```cmd
set CINEMIND_DEBUG=1
python run.py
```

---

## Production Server

CineMind also supports Waitress:

```cmd
python run.py --prod --port 5000
```

---

## Custom Host and Port

```cmd
python run.py --host 0.0.0.0 --port 8080
```

Then access:

```text
http://127.0.0.1:8080
```

---

# 🖥️ Using CineMind

## 1. Discover

The Discover section allows you to construct your preference profile.

### Add Favorite Movies

Search for a movie and add it to your favorites.

### Select Genres

Choose genres that should influence the recommendation results.

### Set Release Era

Optionally specify a release-year range.

Example:

```text
From: 1990
To: 2010
```

### Describe Your Mood

Enter a natural-language description.

Example:

```text
psychological thriller with mind games
```

### Generate Recommendations

Click **Recommend**.

The system generates a ranked list of movies with:

- Match percentage
- Movie poster
- Genres
- Explanation
- Release information

---

# 📚 Library

The Library allows users to explore the entire active dataset.

Available functionality includes:

- Full-text search
- Genre filtering
- Alphabetical sorting
- Newest-first sorting
- Oldest-first sorting
- Pagination

---

# 📊 Insights

The Insights section provides catalogue-level analytics.

It includes:

### Catalogue Metrics

- Total movies
- Number of genres
- Release-year range
- Automatically categorized percentage

### Genre Distribution

Visual representation of the number of movies belonging to each genre.

### Decade Timeline

Movies grouped by release decade.

### Theme / Keyword Analysis

Dominant terms extracted from the movie-description TF-IDF vocabulary.

---

# 📤 Dataset Upload

Users can upload their own movie dataset.

Supported formats:

```text
.csv
.tsv
.txt
.json
.xlsx
```

The upload process:

```text
Upload
   ↓
Format Detection
   ↓
Encoding Detection
   ↓
Column Mapping
   ↓
Data Cleaning
   ↓
Deduplication
   ↓
Genre Inference
   ↓
Recommendation Model
   ↓
Validation
   ↓
Activate Dataset
```

Users can also restore the default sample dataset.

---

# 🔌 REST API

The application exposes several REST endpoints.

## Health Check

```http
GET /api/health
```

Example:

```cmd
curl http://127.0.0.1:5000/api/health
```

---

## Dataset Metadata

```http
GET /api/dataset
```

Example:

```cmd
curl http://127.0.0.1:5000/api/dataset
```

---

## Movie Search

```http
GET /api/movies/search?q=matrix
```

Example:

```cmd
curl "http://127.0.0.1:5000/api/movies/search?q=matrix"
```

---

## Generate Recommendations

```http
POST /api/recommend
```

Example:

```cmd
curl -X POST http://127.0.0.1:5000/api/recommend ^
  -H "Content-Type: application/json" ^
  -d "{\"liked\":[2],\"genres\":[\"Crime\",\"Thriller\"],\"mood\":\"heist\",\"limit\":5}"
```

---

## Upload Dataset

```http
POST /api/upload
```

Example:

```cmd
curl -X POST http://127.0.0.1:5000/api/upload ^
  -F "file=@my_custom_movies.csv"
```

---

## Reset Dataset

```http
POST /api/dataset/reset
```

Example:

```cmd
curl -X POST http://127.0.0.1:5000/api/dataset/reset
```

---

# 🧪 Testing

CineMind includes an automated pytest test suite.

Run:

```cmd
python -m pytest -v
```

The current test suite contains **40 tests** covering:

- REST API functionality
- Security headers
- Dataset persistence
- Pagination
- Movie searching
- Recommendation edge cases
- File uploads
- Encoding handling
- Delimiter detection
- Column aliases
- JSON ingestion
- Deduplication
- Recommendation ranking
- Genre filtering
- Release-year filtering
- Natural-language mood input
- Automatic categorization
- Empty catalogue handling

The project documentation identifies 11 API tests, 14 data-loader tests, and 15 recommender tests.

---

# 📊 Example Dataset

The bundled dataset is:

```text
data/sample_movies.csv
```

It contains:

- 75 movies
- Multiple genres
- Movies spanning several decades
- Examples with missing genre information
- Data suitable for demonstrating automatic genre inference

The current project documentation specifically identifies movies such as **Heat, Shrek, and Cars** as examples containing missing genre fields for the auto-categorization demonstration.

---

---

---

# 🎓 Learning Outcomes

This project demonstrates practical experience with:

- Python programming
- Object-oriented programming
- Data preprocessing
- Data cleaning
- Feature engineering
- TF-IDF vectorization
- Cosine similarity
- Machine learning classification
- Recommendation systems
- Flask web development
- REST API development
- HTML/CSS/JavaScript
- File ingestion
- Dataset validation
- Automated testing
- Software architecture
- Error handling
- Data persistence
- Git/GitHub workflow

---
---

# ⭐ Acknowledgements

**MADE WITH THE EFFORTS OF FEW PEOPLE**
Mohd Fazal, Naved Iqbal, Mohd Zafar, Shariq Ahmad Khan.

---

<div align="center">

### 🎬 CineMind

**Intelligent • Explainable • Content-Aware Movie Recommendations**

Built with ❤️ using Python, Flask, scikit-learn, HTML, CSS & JavaScript.

</div>
