# Hugging Face Spaces (Docker) template

Build and run locally:

```bash
docker build -f deploy/hf-space/Dockerfile -t copilot-hf .
docker run --rm -p 7860:7860 copilot-hf
```

Then open `http://localhost:7860/ui/`.

In Hugging Face Space settings, add secrets like:

- `ADMIN_BOOTSTRAP_TOKEN`
- `JWT_SECRET_KEY`
- optional connector keys / model endpoints
# Hugging Face Space (Docker) template

This template runs the FastAPI app in a Docker Space.

## Build locally

Run from repository root:

```bash
docker build -f deploy/hf-space/Dockerfile -t saas-copilot-hf .
docker run --rm -p 7860:7860 saas-copilot-hf
```

Open `http://localhost:7860/ui/`.

## Space settings

- SDK: `Docker`
- Exposed port: `7860`
- Add env vars in Space secrets:
  - `ADMIN_BOOTSTRAP_TOKEN`
  - `JWT_SECRET_KEY`
  - optional: `OLLAMA_BASE_URL`, `QDRANT_URL`, connector tokens
