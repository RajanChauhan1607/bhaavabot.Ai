# Bhavabot — Empathy Companion Backend (FastAPI + Supabase + Gemini)

This is the completed backend for **Bhavabot**, an empathetic emotional-support companion designed in alignment with the *Toronto Empathy Questionnaire (TEQ)* research framework and clinical safety safeguards.

---

## Architecture Overview

```
Next.js Frontend (bhaavabot.Ai)
      ↓ (HTTP / REST)
FastAPI Backend (Port 8000)
      ├── 1. Safety Engine (Deterministic CRISIS & Self-Harm Interception)
      ├── 2. Emotion Analysis (Emotion Lexicon + Intensity & Confidence)
      ├── 3. Empathy Profile Engine (25-item TEQ + Dispersion + 4 Profiles)
      ├── 4. LLM Service (Gemini 2.5 Flash-Lite with Empathetic Fallback)
      ├── 5. Recommendation Engine (Curated Public Domain Books & CC Audio)
      └── 6. Supabase Persistence (PostgreSQL + RLS + In-Memory Fallback)
```

---

## 1. Prerequisites & Installation

### Python Environment
Ensure Python 3.10+ is installed:
```powershell
cd c:\Users\HP\OneDrive\Documents\Bhavabot\backend
python -m pip install -r requirements.txt
```

### Environment Variables
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Fill in:
* `SUPABASE_URL`: Your Supabase Project URL.
* `SUPABASE_KEY`: Your Supabase Anon or Service Role key.
* `GEMINI_API_KEY`: Your Google AI Studio Gemini key (backend only — never exposed to the frontend).
* `GEMINI_MODEL`: `gemini-2.5-flash-lite` (default).

*(Note: The server operates in full resilient fallback mode even if keys are not provided yet).*

---

## 2. Supabase Database Setup

1. Open your project on [supabase.com](https://supabase.com).
2. Go to **SQL Editor**.
3. Open `backend/supabase_schema.sql`, copy all contents, and click **Run**.
4. This initializes:
   - `profiles`: user profiles linked to `auth.users`.
   - `empathy_profiles`: stores TEQ scores, dispersion, and communication profiles (A/B/C/D).
   - `conversations` & `messages`: conversation history with emotion and safety metadata.
   - `user_preferences`: focus themes and content preferences.
   - `reflections`: inner weather check-ins.
   - `favorites`: user saved books and audio.
   - `books`: public-domain curated book catalogue.

---

## 3. Running the Backend

```powershell
cd c:\Users\HP\OneDrive\Documents\Bhavabot\backend
uvicorn app.main:app --reload --port 8000
```
Interactive Swagger documentation will be live at:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 4. Running the Frontend

```powershell
cd c:\Users\HP\OneDrive\Documents\Bhavabot\bhaavabot.Ai
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 5. Running the Test Suite

```powershell
cd c:\Users\HP\OneDrive\Documents\Bhavabot\backend
python -m pytest -v tests
```
The test suite validates:
- Deterministic 25-item TEQ assessment scoring and reverse-scoring.
- Dispersion calculation and 4 profile classifications.
- Safety engine crisis detection and pre-LLM intervention.
- Empathetic chat flow and fallback generation.
- Curated public-domain licensing and recommendation logic.
