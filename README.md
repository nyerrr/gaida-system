# GAIDA
### A Web-based (PWA) Guidance System with Multimodal Anxiety Detection and Virtual Agent

> Undergraduate thesis project — University of the East

---

## Overview

GAIDA is a Progressive Web App (PWA) designed to support student mental health through multimodal anxiety detection and an AI-powered virtual agent. Users can express themselves via text or voice, and the system analyzes both linguistic and acoustic signals to assess anxiety levels and respond empathetically in real time.

The platform also includes a **Counselor Dashboard** where licensed counselors can monitor ongoing sessions, view anxiety detection scores, and intervene directly when crisis levels are detected.

---

## Features

- **Multimodal Input** — accepts both text and voice input for anxiety detection
- **Speech-to-Text** — powered by OpenAI Whisper (medium/large-v2) with auto-detection of Filipino languages (Tagalog, Taglish, Bisaya, Ilocano)
- **Voice Emotion Analysis** — extracts acoustic features (pitch, energy, jitter) for emotion classification
- **Anxiety Detection Ensemble** — Logistic Regression, Random Forest, and Neural Network with majority voting for higher accuracy
- **Virtual Agent** — fine-tuned OpenAI GPT-3.5 Turbo for empathetic, context-aware responses
- **Crisis Detection** — fuzzy matching via SequenceMatcher to flag high-risk messages
- **Venting Mode** — dedicated mode with custom intent handling and adjusted GPT prompting
- **Counselor Dashboard** — real-time session monitoring with REST-based typing indicators and direct intervention capability
- **Informed Consent Gate** — privacy consent flow before any session begins
- **PWA Support** — installable, works offline via Service Worker + Background Sync
- **Multilingual** — supports Tagalog, Taglish, Bisaya, and Ilocano

---

## Tech Stack

### Frontend
| Layer | Technology |
|---|---|
| UI Framework | React 18 |
| Build Tool | Vite 7 |
| Routing | React Router v6 |
| Styling | Tailwind CSS |
| Markdown | ReactMarkdown |
| Charts | Recharts |
| PWA | vite-plugin-pwa + Service Worker + Manifest |
| Client Storage | localStorage + IndexedDB |

### Backend
| Layer | Technology |
|---|---|
| API Framework | FastAPI |
| Language | Python |
| Web Server | Uvicorn |
| AI Response | OpenAI GPT-3.5 Turbo (fine-tuned) |
| Intent Classification | Scikit-learn (LR + RF + NN ensemble) |
| Text Vectorization | TF-IDF |
| Ensemble Method | Majority Voting |
| Crisis Detection | Fuzzy Matching (SequenceMatcher) |
| Speech-to-Text | OpenAI Whisper (medium/large-v2) |
| Text-to-Speech | tts.py |
| Voice Emotion | Acoustic Features (pitch, energy, jitter) |
| Session Storage | In-memory Python dict (RAM) |
| Model Persistence | Pickle (.pkl) |
| Training Data | JSONL |

### Database & Auth
| Layer | Technology |
|---|---|
| Cloud Database | Supabase (PostgreSQL) |
| Auth | Session tokens + localStorage |
| Privacy Gate | has_consent() + InformedConsent.jsx |

---

## ML Architecture

The anxiety detection pipeline uses an ensemble of three classifiers trained on 1,000+ labeled data points:

```
Input (text)
    └── TF-IDF Vectorization
            ├── Logistic Regression
            ├── Random Forest
            └── Neural Network
                    └── Majority Voting → Final Prediction
```

Voice input is processed separately through acoustic feature extraction (pitch, energy, jitter) before being merged with the text classification result.

---

## Counselor Dashboard

Counselors have a separate authenticated interface where they can:

- Monitor all active user sessions in real time
- View anxiety detection scores per message
- See typing indicators via REST polling
- Intervene directly into a session when crisis detection is triggered

---

## PWA

GAIDA is fully installable as a PWA on mobile and desktop. It supports:

- Offline access via Service Worker caching
- Background Sync for queued messages
- App manifest for home screen installation

---

## Team

Developed by a team of 6 CS students at the University of the East as part of our undergraduate thesis.

---

## Status

> 🎓 This is an academic thesis project. The live demo is not publicly available. Source code is available in this repository.
