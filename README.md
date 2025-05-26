## ADK Agent

This sample creates a simple "weather_time_agent" agent hosted by an A2A server using the Agent Development Kit (ADK).

## Prerequisites

1. Development Environment
- backend
    - Python 3.13 or higher
    - [UV](https://docs.astral.sh/uv/) installed
- frontend
    - node v22 or higher
    - npm installed
2. GCP Account
- Account with LLM access and Vertex AI permissions
```bash
gcloud auth application-default login
```
- When deploying to GCP CloudRun, connect using a service account.

## Sample Installation
1. Download
```bash
curl -L -o a2adk-template.zip https://github.com/didim365/a2adk-template/archive/main.zip
unzip a2adk-template.zip
```
2. Backend Installation
```bash
uv sync
```
3. Frontend Installation
```bash
cd frontend
npm install
```

## How to Run the Sample
1. Run the ADK agent. (Does not use the A2A server.)
```bash
cd a2adk
adk run agent
# or adk web
```
2. Run the A2A server:
```bash
a2adk
# or a2adk --agent root_agent
# or a2adk --host localhost --port 10008
```
3. Run the frontend.
- Start the development server.
```bash
cd frontend
npm run dev
```
- Open http://localhost:5173 in your web browser.

## How to Debug the Sample
Use the VSCode debugger.
1. Debug ADK Agent
Debug the ADK agent (code under ./a2adk/agents).
2. Debug A2A Agent
Debug the A2A server.
3. Debug frontend
Debug the A2A web client (run `npm run dev` first).

## How to Build Sample Docker Images
1. Backend
```bash
docker buildx build --platform=linux/amd64 -t a2adk-backend .
```
2. Frontend
```bash
cd frontend
docker buildx build --platform=linux/amd64 -t a2adk-frontend .
```
When deploying, use the values from `.env` as environment variables.
