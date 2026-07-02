FROM python:3.11-slim

# OS 패키지 업데이트 및 기본 도구 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# requirements.txt 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스코드 전체 복사
COPY . .

# Streamlit 포트 노출
EXPOSE 8503

# Streamlit 및 백그라운드 워커, 터널 실행 CMD 설정
CMD ["sh", "-c", "python start_tunnel.py & python worker.py & streamlit run app.py --server.port=8503 --server.address=0.0.0.0"]
