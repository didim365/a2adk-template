## ADK 에이전트

이 샘플은 에이전트 개발 키트(ADK)를 사용하여 A2A 서버로 호스팅되는 간단한 "weather_time_agent" 에이전트를 만듭니다.

## 사전 준비 사항

1. 개발 환경
- backend
    - Python 3.13 이상
    - [UV](https://docs.astral.sh/uv/)
- frontend
    - node v22 이상
    - npm
2. GCP 계정
- LLM 액세스 및 Vertex AI 권한이 있는 계정
```bash
gcloud auth application-default login
```

## 샘플 설치
1. 다운로드
```bash
curl -L -o a2adk-template.zip https://github.com/didim365/a2adk-template/archive/main.zip
unzip a2adk-template.zip
```
2. backend 설치
```bash
uv sync
```
3. frontend 설치
```bash
cd frontend
npm install
```

## 샘플 실행 방법
1. adk 에이전트를 실행합니다. (A2A 서버를 사용하지 않는다.)
```bash
cd a2adk
adk run agent
# or adk web
```
2. A2A 서버를 실행합니다:
```bash
a2adk
# or a2adk --agent root_agent
# or a2adk --host localhost --port 10008
```
3. frontend를 실행합니다.
- 개발 서버를 실행 합니다.
```bash
cd frontend
npm run dev
```
- 웹 브라우저로 http://localhost:5173을 연다

### 샘플 Debug 방밥
vscode의 디버그를 사용한다.
1. Debug ADK Agent
ADK 에이전트를 (./a2adk/agents 아래 코드) debug한다. 
2. Debug A2A Agent
A2A 서버를 debug한다.
3. Debug frontend
A2A web client를 debug한다. (npm run dev 먼저 수행한다.)
