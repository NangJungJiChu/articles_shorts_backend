# Articles Shorts Backend - Server Setup Script

이 저장소는 `Articles Shorts Backend` 프로젝트를 Ubuntu 서버에 자동으로 배포하고 설정하기 위한 쉘 스크립트를 포함하고 있습니다.

이 스크립트는 **EC2 User Data** 또는 초기 서버 설정 시 실행하도록 설계되었습니다.

## 📋 주요 기능

이 스크립트(`setup.sh`)는 다음과 같은 작업을 순차적으로 수행합니다:

1.  **시스템 패키지 업데이트 및 설치**: `git`, `python3-pip`, `curl` 등 필수 패키지 설치.
2.  **프로젝트 클론**: 지정된 Git 리포지토리에서 소스 코드를 가져옵니다.
3.  **환경 변수 설정 (`.env`)**: AWS, DB, OpenSearch 연결 정보를 설정합니다.
4.  **Python 환경 설정 (`uv`)**:
    * 최신 Python 패키지 매니저인 `uv`를 설치합니다.
    * `uv sync`를 통해 의존성을 고속으로 설치합니다.
5.  **Crontab 등록**: 30분마다 추천 시스템 학습(`run_recsys_training`)을 수행하는 스케줄러를 등록합니다.
6.  **Systemd 서비스 등록 및 실행**:
    * `njjc-qcluster`: Django Q 클러스터 (비동기 작업 큐)
    * `njjc-runserver`: Django 개발 서버 (0.0.0.0:8000)
    * 두 서비스 모두 자동 재시작(Restart=always) 및 부팅 시 자동 실행 설정.

## 🚀 사용 방법

### 1. 스크립트 수정 (필수)
`setup.sh` 파일을 열어 아래의 **민감한 정보들을 실제 사용 환경에 맞게 수정**해주세요.

```bash
# setup.sh 내부 수정 필요 부분
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY       # <-- 실제 키로 변경
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY   # <-- 실제 키로 변경
DB_PASSWORD=YOUR_DB_PASSWORD            # <-- 실제 비밀번호로 변경
# ... 기타 DB 및 OpenSearch 정보 수정
```

### 2. 실행 권한 부여 및 실행
서버 접속 후 스크립트에 실행 권한을 부여하고 실행합니다.

```bash
chmod +x setup.sh
sudo ./setup.sh
```

## 🛠 서비스 관리

스크립트 실행 후 `systemctl` 명령어를 통해 서비스를 관리할 수 있습니다.

```bash
# 상태 확인
sudo systemctl status njjc-runserver
sudo systemctl status njjc-qcluster

# 로그 확인
journalctl -u njjc-runserver -f
```

## ⚠️ 주의 사항
* 이 스크립트는 `Ubuntu` 환경을 기준으로 작성되었습니다.
* 보안을 위해 실제 운영 환경에서는 `.env` 생성 로직을 제거하고, AWS Parameter Store나 Secrets Manager를 사용하는 것을 권장합니다.