# Sports Analytics RAG System

Production-grade RAG system for sports Q&A — Football, NBA, Tennis, Cricket.

## Quick Start (VSCode)

### 1. Clone / open in VSCode
```bash
git clone <your-repo>
cd sports-rag
code .
```

### 2. Create virtual environment
```bash
python -m venv venv

# Activate:
# Windows:  venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
```

VSCode will detect the venv automatically. Press `Ctrl+Shift+P` →
"Python: Select Interpreter" → choose `./venv`.

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
cp .env.example .env
# Edit .env — add your keys:
#   GEMINI_API_KEY  → https://aistudio.google.com/apikey  (free)
#   RAPIDAPI_KEY    → https://rapidapi.com/hub (SofaScore API)
```

### 4b. Test Gemini works before anything else
```bash
python scripts/test_gemini.py
# Should print: "All tests passed. Gemini is ready!"
```

### 5. Copy your Kaggle data
```
data/raw/
├── Full_Dataset.csv
├── NBA_GAMES.csv
├── NBA_PLAYERS.csv
├── NBA_PLAYER_GAMES.csv
├── ATP Dataset_2012-01 to 2017-07_Int_V4.csv
├── matches.csv
├── deliveries.csv
├── FIFA - World Cup Summary.csv
└── FIFA - [year].csv  (all years)
```

### 6. Run the full pipeline
```bash
python scripts/run_pipeline.py --data-dir data/raw
```

This runs all 3 steps in order:
- Step 1: CSV → natural language text documents
- Step 2: Documents → chunks (data/chunks/)
- Step 3: Chunks → embeddings + FAISS index (data/embeddings/)

---

## Week-by-Week Commands

### Week 1 — Data
```bash
# Process Kaggle data only (no API key needed)
python scripts/run_pipeline.py --data-dir data/raw --skip-api

# Add live data from SofaScore (needs RAPIDAPI_KEY in .env)
python -m src.ingestion.sofascore_collector --sport football --days 30
python -m src.ingestion.sofascore_collector --sport tennis --days 30
```

### Week 2 — RAG Pipeline
```bash
# Test retrieval
python -m src.retrieval.retriever "Who won the 2022 Champions League?"

# Interactive test in notebook
jupyter notebook notebooks/02_rag_pipeline.ipynb
```

### Week 3 — API + UI
```bash
# Start FastAPI backend
uvicorn src.api.main:app --reload --port 8000

# Start Streamlit frontend (new terminal)
streamlit run src/frontend/app.py
```

### Week 4 — Evaluation
```bash
python -m src.evaluation.ragas_eval
```

---

## Project Structure

```
sports-rag/
├── src/
│   ├── config.py              # all settings, reads from .env
│   ├── ingestion/
│   │   ├── text_builder.py    # CSV row → natural language
│   │   ├── data_processor.py  # orchestrates Kaggle processing
│   │   ├── sofascore_collector.py  # live API data
│   │   └── chunker.py         # text → RAG chunks
│   ├── embeddings/
│   │   └── embedder.py        # chunks → FAISS index
│   ├── retrieval/             # (Week 2)
│   ├── api/                   # (Week 3)
│   └── frontend/              # (Week 3)
├── data/
│   ├── raw/       → your Kaggle CSVs go here
│   ├── processed/ → auto-generated JSONL files
│   ├── chunks/    → auto-generated chunk files
│   └── embeddings/→ FAISS index lives here
├── notebooks/
├── tests/
├── scripts/
│   └── run_pipeline.py
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## Data Flow

```
Kaggle CSVs (data/raw/)
        ↓  data_processor.py
Processed JSONL (data/processed/)
        ↓  chunker.py
Chunks JSONL (data/chunks/)
        ↓  embedder.py
FAISS Index + Metadata (data/embeddings/)
        ↓  retriever.py  [Week 2]
RAG Query → Answer
```
"# Sports-Rag" 
