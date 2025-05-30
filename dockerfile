# --- 빌드 스테이지 ---
# uv와 애플리케이션 의존성을 설치하는 데 사용됩니다.
FROM python:3.13-slim-bookworm AS builder

# Git 설치 (uv가 Git 저장소에서 의존성을 가져올 수 있도록)
# RUN apt-get update && apt-get install -y git --no-install-recommends && rm -rf /var/lib/apt/lists/*

# uv 바이너리 복사 (ghcr.io/astral-sh/uv 에서 사용 가능한 최신 안정 버전을 확인하세요.)
# 예시: COPY --from=ghcr.io/astral-sh/uv:0.2.10 /uv /bin/uv (실제 최신 버전으로 변경)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 작업 디렉토리 설정
WORKDIR /app

# uv 캐시를 위한 마운트 설정 (빌드 속도 향상)
# UV_COMPILE_BYTECODE=1: Python 파일을 .pyc 바이트코드 파일로 컴파일
# UV_LINK_MODE=copy: uv가 하드 링크를 사용하지 못할 때 복사 모드 사용
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# 애플리케이션 코드 복사
# .dockerignore 파일을 사용하여 불필요한 파일을 제외하는 것이 좋습니다.
COPY . /app

# uv sync를 사용하여 의존성 설치
# --frozen: lock 파일과 일치하는지 확인
# --no-install-project: 현재 프로젝트 자체는 설치하지 않음
# --no-dev: 개발 의존성은 설치하지 않음
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# --- 최종 실행 스테이지 ---
# 빌드된 가상 환경과 애플리케이션 코드를 포함하는 최종 이미지입니다.
FROM python:3.13-slim-bookworm AS base

# 빌드 스테이지에서 설치된 가상 환경 복사
COPY --from=builder /app /app

# 가상 환경의 bin 디렉토리를 PATH에 추가하여 애플리케이션 실행 시 사용
ENV PATH="/app/.venv/bin:$PATH"

# 작업 디렉토리 설정
WORKDIR /app

# 애플리케이션이 수신할 포트 노출 (예: Uvicorn 사용 시 8000번 포트)
EXPOSE 8000

# 애플리케이션 실행 명령어
# FastAPI 애플리케이션 예시:
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["a2adk", "--agent", "root_agent", "--host", "0.0.0.0", "--port", "8000"]
# CMD ["sh", "-c", "sleep infinity"]
