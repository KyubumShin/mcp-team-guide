# 테스트 실행 가이드

4-System A/B 비교 실험의 테스트 실행 및 채점 절차를 상세히 설명합니다.

## 개요

### 테스트 구조

4-System A/B 비교 실험에서는 2개 Tier의 작업에 대해 에이전트 성능을 평가합니다.

#### Tier 1 (TaskFlow)
- 기본 테스트: 59개
- 히든 테스트: 30개
- 합계: 89개

#### Tier 2 (Bookshelf API)
- 기본 테스트: 60개
- 히든 테스트: 30개
- 합계: 90개

**핵심 원칙:** 테스트는 에이전트에게 제공되지 않습니다. 에이전트는 prompt와 scaffold만 받고, 평가는 블라인드 채점 방식으로 진행됩니다.

### 테스트 파일 위치 및 자동 복사

#### Tier 1 (TaskFlow)
Tier 1 테스트는 외부 저장소(v3_eval_store)에서 관리됩니다:
- `setup_env.py` 실행 시 자동으로 복사됨
- 복사 대상: `tasks/tier1-taskflow/tests/`, `tasks/tier1-taskflow/tests_hidden/`
- 이후 각 실행 디렉토리의 conftest.py에 의해 로드됨

#### Tier 2 (Bookshelf API)
Tier 2 테스트는 저장소 내에 관리됩니다.

**기본 테스트 (60개):**
| 파일 | 테스트 수 | 주요 영역 |
|------|----------|----------|
| `test_auth.py` | 12개 | 회원가입, 로그인, JWT 검증 |
| `test_books.py` | 12개 | 책 CRUD, 소유권 검사 |
| `test_bookshelves.py` | 12개 | 서재 관리, 소유권 검사 |
| `test_search.py` | 12개 | 검색, 필터링, 페이지네이션 |
| `test_validation.py` | 12개 | 입력 유효성, 에러 형식 |

**히든 테스트 (30개):**
| 파일 | 테스트 수 | 주요 영역 |
|------|----------|----------|
| `test_auth_hidden.py` | 8개 | 만료 토큰, 변조 토큰, 동시 세션, 대소문자 무시, 빈 헤더 |
| `test_edge_hidden.py` | 8개 | 빈 문자열, 초장문 입력, 특수문자, SQL 인젝션 |
| `test_integration_hidden.py` | 14개 | 크로스 유저 권한 검사, 삭제 cascade, 대량 데이터 페이지네이션 |

### 테스트 파일 위치 요약

```
experiments/4way-comparison/
├── tasks/
│   ├── tier1-taskflow/
│   │   ├── tests/           (59개 기본 테스트)
│   │   └── tests_hidden/    (30개 히든 테스트)
│   └── tier2-bookshelf-api/
│       ├── tests/           (60개 기본 테스트)
│       └── tests_hidden/    (30개 히든 테스트)
└── runs/
    ├── omc-t1-run1/
    ├── hoyeon-t1-run1/
    ├── uam-t1-run1/
    ├── uam-mpl-t1-run1/
    └── ... (총 24개 실행 디렉토리)
```

## 사전 요구사항

### Python 환경 설정

#### Python 버전
- Python 3.11 이상 필수
- `python3 --version` 또는 `python --version`으로 확인

#### 가상 환경 생성 (권장)
각 실행 디렉토리별로 독립적인 Python 환경을 유지하는 것을 권장합니다:

```bash
cd experiments/4way-comparison/runs/uam-mpl-t2-run1
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate     # Windows
```

### 필수 패키지 설치

#### 방법 1: pyproject.toml 사용 (권장)
각 실행 디렉토리에는 scaffold의 `pyproject.toml`이 포함됩니다:

```bash
cd experiments/4way-comparison/runs/uam-mpl-t2-run1
pip install -e ".[dev]"
```

이 명령어는 다음을 자동으로 설치합니다:
- **핵심 의존성**: fastapi, uvicorn, aiosqlite, pyjwt, bcrypt, pydantic
- **개발 의존성**: pytest, pytest-asyncio, httpx

#### 방법 2: 수동 설치
```bash
pip install pytest>=7.4.0
pip install pytest-asyncio>=0.23.0
pip install httpx>=0.25.0
pip install fastapi>=0.104.0
pip install uvicorn>=0.24.0
pip install aiosqlite>=0.19.0
pip install pyjwt>=2.8.0
pip install bcrypt>=4.1.0
pip install pydantic>=2.5.0
```

### 의존성 확인
설치 후 다음 명령어로 확인:

```bash
python -c "import pytest; print(f'pytest {pytest.__version__}')"
python -c "import pytest_asyncio; print('pytest-asyncio OK')"
python -c "import httpx; print('httpx OK')"
```

## conftest.py 동작 방식

Bookshelf API 테스트는 `tests/conftest.py`와 `tests_hidden/conftest.py`에 정의된 fixture에 의존합니다.

### conftest.py 파일 구조

#### 기본 테스트의 conftest.py (`tests/conftest.py`)
- 완전히 자체포함된 정의
- 세션 스코프의 event_loop 생성
- 테스트별 격리된 임시 DB 생성

#### 히든 테스트의 conftest.py (`tests_hidden/conftest.py`)
```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tests'))
from conftest import *  # noqa: F401,F403
```
- 기본 테스트의 fixture를 재사용
- 같은 fixture 정의를 중복하지 않음

### 핵심 Fixture 상세 설명

#### 1. `event_loop` Fixture (세션 스코프)
```python
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

**역할**: 세션 전체에서 사용할 단일 asyncio 이벤트 루프를 생성합니다.

**동작 방식**:
- pytest-asyncio와 함께 작동
- 테스트 시작 전 생성, 종료 후 정리
- 모든 비동기 테스트가 이 루프를 사용

#### 2. `client` Fixture (비인증 클라이언트)
```python
@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Unauthenticated async HTTP client with isolated temp database."""
    db_path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_URL"] = db_path

    app = _import_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
```

**역할**: 각 테스트마다 격리된 환경에서 HTTP 클라이언트를 제공합니다.

**동작 방식**:
- 테스트 시작 시: 새로운 임시 SQLite DB 파일 생성
- `DATABASE_URL` 환경변수를 임시 DB 경로로 설정
- FastAPI 앱 인스턴스 로드 (아래 설명 참고)
- `AsyncClient` 생성 (HTTP 요청을 위한 비동기 클라이언트)
- 테스트 실행
- 테스트 종료 시: 임시 DB 파일 자동 삭제

**테스트 간 격리**:
- 각 테스트는 완전히 새로운 DB를 받음
- 이전 테스트의 데이터가 다음 테스트에 영향을 주지 않음
- 병렬 실행 시에도 안전함

#### 3. `_import_app()` 헬퍼 함수
```python
def _import_app():
    """Import the FastAPI app — agents may place it in different locations."""
    try:
        from bookshelf.main import app
        return app
    except ImportError:
        from bookshelf import app  # fallback
        return app
```

**역할**: 에이전트가 만든 앱을 다양한 패키지 구조에서 찾습니다.

**동작 방식**:
- 첫 번째 시도: `bookshelf.main` 모듈에서 `app` 임포트
- 실패 시 두 번째 시도: `bookshelf` 패키지 직접 임포트
- 이렇게 하면 에이전트가 `bookshelf/main.py` 또는 `bookshelf/__init__.py`에 앱을 만들어도 모두 작동

**일반적인 디렉토리 구조**:
```
scaffold/
├── bookshelf/
│   ├── __init__.py        (여기에 app이 있을 수 있음)
│   └── main.py            (또는 여기에 app이 있을 수 있음)
├── pyproject.toml
└── ...
```

#### 4. `auth_client` Fixture (인증된 클라이언트)
```python
@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    """Authenticated client for test@example.com / TestPass123!"""
    await client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "TestPass123!",
        "username": "testuser",
    })
    resp = await client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "TestPass123!",
    })
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
```

**역할**: 인증된 요청을 할 수 있는 클라이언트를 제공합니다.

**동작 방식**:
- `client` fixture에 의존 (같은 DB 사용)
- test@example.com / TestPass123! 계정으로 자동 등록
- 자동으로 로그인하여 access_token 획득
- 모든 HTTP 요청에 `Authorization: Bearer {token}` 헤더 자동 추가

**사용 예시**:
```python
@pytest.mark.asyncio
async def test_get_my_books(auth_client):
    # Authorization 헤더가 자동으로 포함됨
    resp = await auth_client.get("/books")
    assert resp.status_code == 200
```

#### 5. `second_auth_client` Fixture (두 번째 사용자)
```python
@pytest_asyncio.fixture
async def second_auth_client(client: AsyncClient) -> AsyncGenerator[AsyncClient, None]:
    """A second authenticated user for permission tests.

    Uses the same app/DB as `client` so both users coexist.
    Returns a separate AsyncClient with the second user's token.
    """
    # Register second user via shared client (same DB)
    await client.post("/auth/register", json={
        "email": "other@example.com",
        "password": "OtherPass123!",
        "username": "otheruser",
    })
    resp = await client.post("/auth/login", json={
        "email": "other@example.com",
        "password": "OtherPass123!",
    })
    token = resp.json()["access_token"]

    app = _import_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c
```

**역할**: 권한 검사 테스트를 위한 두 번째 사용자 클라이언트를 제공합니다.

**동작 방식**:
- `client` fixture와 **같은 DB**를 공유
- other@example.com / OtherPass123! 계정으로 등록 및 로그인
- 독립적인 AsyncClient 생성 (auth_client와는 다르게 client 기반이 아님)
- 이를 통해 두 사용자가 같은 DB에서 공존

**권한 테스트 예시**:
```python
@pytest.mark.asyncio
async def test_user_cannot_access_another_users_book(auth_client, second_auth_client):
    # auth_client의 소유 책 생성
    book_resp = await auth_client.post("/books", json={
        "title": "Secret Book",
        "author": "Author",
        "genre": "Fiction",
    })
    book_id = book_resp.json()["id"]

    # second_auth_client가 접근 시도 → 403 Forbidden
    resp = await second_auth_client.get(f"/books/{book_id}")
    assert resp.status_code == 403
```

### DB 격리 메커니즘

```
테스트 1 시작
  → 임시 DB 1 생성
  → DATABASE_URL=/tmp/xxx1.db
  → 테스트 실행
  → 테스트 종료
  → DB 1 삭제

테스트 2 시작
  → 임시 DB 2 생성 (다른 파일)
  → DATABASE_URL=/tmp/xxx2.db
  → 테스트 실행
  → 테스트 종료
  → DB 2 삭제

...
```

**장점**:
- 테스트 간 상태 누출 없음 (완전히 격리됨)
- 병렬 테스트 실행 시에도 안전
- 테스트 실패 시에도 임시 파일 자동 삭제
- 각 테스트가 깨끗한 상태에서 시작

## 수동 테스트 실행

### Tier 2 (Bookshelf API) 테스트 실행

#### 1단계: 실행 디렉토리로 이동

```bash
cd /Users/kbshin/project/harness_lab/experiments/4way-comparison/runs/uam-mpl-t2-run1
```

#### 2단계: 의존성 설치

```bash
pip install -e ".[dev]"
```

**출력 예시**:
```
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 aiosqlite-0.19.0 pyjwt-2.8.1 bcrypt-4.1.2 pydantic-2.5.0 pytest-7.4.3 pytest-asyncio-0.23.1 httpx-0.25.1
```

#### 3단계: 기본 테스트 실행 (60개)

```bash
python -m pytest ../../tasks/tier2-bookshelf-api/tests/ -v
```

**출력 예시**:
```
tests/test_auth.py::test_register_success PASSED                           [  1%]
tests/test_auth.py::test_register_duplicate_email PASSED                   [  1%]
...
tests/test_validation.py::test_error_response_format PASSED               [100%]

============================== 60 passed in 12.34s ===============================
```

#### 4단계: 히든 테스트 실행 (30개)

```bash
python -m pytest ../../tasks/tier2-bookshelf-api/tests_hidden/ -v
```

**출력 예시**:
```
tests_hidden/test_auth_hidden.py::test_expired_token PASSED                [  1%]
tests_hidden/test_auth_hidden.py::test_tampered_token PASSED               [  3%]
...
tests_hidden/test_integration_hidden.py::test_large_page_pagination PASSED [100%]

============================== 30 passed in 8.56s ===============================
```

#### 5단계: 전체 테스트 (90개, 최종 점수 확인)

```bash
python -m pytest ../../tasks/tier2-bookshelf-api/tests/ ../../tasks/tier2-bookshelf-api/tests_hidden/ --tb=short -q
```

**출력 예시**:
```
......................................................................... 60 passed in 12.34s
..............................                                             30 passed in 8.56s

============================= 90 passed in 20.90s ============================
```

### Tier 1 (TaskFlow) 테스트 실행

#### 1단계: 실행 디렉토리로 이동

```bash
cd /Users/kbshin/project/harness_lab/experiments/4way-comparison/runs/uam-mpl-t1-run1
```

#### 2단계: 의존성 설치

```bash
pip install -e ".[dev]"
```

#### 3단계: 기본 테스트 실행 (59개)

```bash
python -m pytest ../../tasks/tier1-taskflow/tests/ -v
```

#### 4단계: 히든 테스트 실행 (30개)

```bash
python -m pytest ../../tasks/tier1-taskflow/tests_hidden/ -v
```

#### 5단계: 전체 테스트 (89개)

```bash
python -m pytest ../../tasks/tier1-taskflow/tests/ ../../tasks/tier1-taskflow/tests_hidden/ --tb=short -q
```

### pytest 주요 옵션 및 활용

#### 기본 실행 옵션

| 옵션 | 설명 | 예시 |
|------|------|------|
| `-v` 또는 `--verbose` | 각 테스트 결과를 자세히 표시 | `pytest tests/ -v` |
| `-q` 또는 `--quiet` | 요약 정보만 표시 (최소 출력) | `pytest tests/ -q` |
| `-x` | 첫 번째 실패에서 멈춤 | `pytest tests/ -x` |
| `--tb=short` | 짧은 traceback 출력 | `pytest tests/ --tb=short` |
| `--tb=long` | 전체 traceback 출력 | `pytest tests/ --tb=long` |
| `--tb=no` | traceback 없음 (채점용) | `pytest tests/ --tb=no` |

#### 실패 테스트만 자세히 보기

```bash
python -m pytest ../../tasks/tier2-bookshelf-api/tests/ --tb=long -x
```

**동작**:
- 첫 번째 실패한 테스트에서 멈춤 (`-x`)
- 전체 traceback 표시 (`--tb=long`)
- 실패 원인을 깊이 있게 분석할 수 있음

#### 특정 테스트 파일만 실행

```bash
python -m pytest ../../tasks/tier2-bookshelf-api/tests/test_auth.py -v
```

**출력**:
```
tests/test_auth.py::test_register_success PASSED                           [  8%]
tests/test_auth.py::test_register_duplicate_email PASSED                   [16%]
...
tests/test_auth.py::test_register_returns_no_password PASSED              [100%]

============================== 12 passed in 3.21s ================================
```

#### 특정 테스트 함수만 실행

```bash
python -m pytest ../../tasks/tier2-bookshelf-api/tests/test_auth.py::test_register_success -v
```

**출력**:
```
tests/test_auth.py::test_register_success PASSED                          [100%]

============================== 1 passed in 0.42s ==================================
```

#### 키워드로 테스트 필터링

```bash
# "auth"를 포함한 모든 테스트 실행
python -m pytest ../../tasks/tier2-bookshelf-api/tests/ -k "auth" -v

# "search"를 포함한 모든 테스트 실행
python -m pytest ../../tasks/tier2-bookshelf-api/tests/ -k "search" -v

# "not" 을 사용한 제외
python -m pytest ../../tasks/tier2-bookshelf-api/tests/ -k "not auth" -v
```

#### 요약 형식 (채점 결과 확인용)

```bash
python -m pytest ../../tasks/tier2-bookshelf-api/tests/ --tb=no -q
```

**출력**:
```
60 passed in 12.34s
```

#### 컬러 비활성화 (로그 기록용)

```bash
python -m pytest ../../tasks/tier2-bookshelf-api/tests/ --color=no -v
```

### 테스트 실행 체크리스트

테스트를 수동으로 실행할 때 확인하세요:

- [ ] 올바른 디렉토리에 있는가? (`pwd` 확인)
- [ ] Python 버전이 3.11+인가? (`python --version` 확인)
- [ ] 의존성이 설치되었는가? (`pip list | grep pytest` 확인)
- [ ] `tests/` 디렉토리가 존재하는가? (`ls ../../tasks/tier2-bookshelf-api/tests/`)
- [ ] conftest.py가 있는가? (`ls ../../tasks/tier2-bookshelf-api/tests/conftest.py`)
- [ ] 에이전트가 패키지를 만들었는가? (`ls bookshelf/` 또는 구조 확인)

## 자동 메트릭 수집

### collect_metrics.py 개요

`harness/collect_metrics.py`는 모든 완료된 실행에서 자동으로 테스트 점수, 토큰 사용, 시간, 계획 메트릭을 수집합니다.

### collect_metrics.py 동작 방식

#### 1단계: Manifest 로드
```python
manifest_path = RUNS_DIR / "run_manifest.json"
with open(manifest_path) as f:
    manifest = json.load(f)
```

`runs/run_manifest.json`에서 실행 정보 로드:
- `system`: OMC, hoyeon, UAM, UAM-MPL
- `tier`: t1 또는 t2
- `run`: 1, 2, 3
- `status`: "ready", "complete", 기타

#### 2단계: 완료 상태 필터링
```python
if status != "complete":
    print(f"Skipping {run_name} (status: {status})")
    continue
```

`status`가 `"complete"`인 실행만 처리합니다.

#### 3단계: 각 실행의 메트릭 수집

**실행 디렉토리별 처리**:

```
runs/uam-mpl-t2-run1/
  ├── bookshelf/               (에이전트가 만든 구현)
  ├── .uam/
  │   ├── PLAN.md             → Plan metrics 추출
  │   └── metrics.json        → Token metrics 추출
  ├── .git/
  │   └── logs                → Timing metrics 추출
  └── tests/
      ├── tests/              → 기본 테스트 실행
      └── tests_hidden/       → 히든 테스트 실행
```

#### 4단계: pytest 실행 및 파싱
```python
result = subprocess.run(
    ["python", "-m", "pytest", str(temp_tests), "--tb=short", "-q", "--no-header"],
    cwd=run_dir,
    capture_output=True,
    text=True,
    timeout=120,
)
output = result.stdout + result.stderr

# Parse "X passed, Y failed, Z errors"
passed = int(re.search(r"(\d+) passed", output).group(1))
failed = int(re.search(r"(\d+) failed", output).group(1))
errors = int(re.search(r"(\d+) error", output).group(1))
```

각 실행에서:
- 기본 테스트 디렉토리 복사 (임시 위치)
- pytest 실행 (타임아웃 120초)
- 결과 파싱: 통과, 실패, 에러 수
- 임시 디렉토리 삭제

#### 5단계: 메트릭 추출

**점수 계산 (task_success)**:
```python
basic_score = (basic_passed / basic_total * 70) if basic_total > 0 else 0
hidden_score = (hidden_passed / hidden_total * 30) if hidden_total > 0 else 0
total_score = round(basic_score + hidden_score, 1)

grade = "S" if total_score >= 95 else "A" if total_score >= 85 else ...
```

**토큰 메트릭 (token_efficiency)**:
- UAM/UAM-MPL: `.uam/metrics.json` 읽음
- OMC: `.omc/state/` 디렉토리에서 찾음
- hoyeon: `.hoyeon/state.json` 읽음

**타이밍 메트릭 (timing)**:
- `git log` 첫 커밋 (scaffold)
- `git log` 마지막 커밋 (완료)
- 커밋 수 (scaffold 제외)
- 총 소요 시간 (초)

**계획 메트릭 (plan_metrics)**:
- PLAN.md에서 체크박스 카운트
- `- [x]` → 완료
- `- [ ]` → 미완료
- `- [!]` 또는 `- [F]` → 실패

### 실행 방법

#### 1단계: 실행 상태 업데이트

모든 실행이 완료된 후, `runs/run_manifest.json`에서 `status`를 `"complete"`으로 변경합니다.

**방법 A: 수동 편집**
```bash
# 1. JSON 파일 열기
nano runs/run_manifest.json  # 또는 텍스트 에디터

# 2. 각 실행의 status를 "ready" → "complete"로 변경
# 예시:
# "status": "ready"   →   "status": "complete"

# 3. 저장
```

**방법 B: jq로 일괄 변경**
```bash
cd /Users/kbshin/project/harness_lab/experiments/4way-comparison

# 모든 실행을 complete로 변경
jq '(.runs[] | .status) = "complete"' runs/run_manifest.json > runs/tmp.json
mv runs/tmp.json runs/run_manifest.json
```

**방법 C: Python으로 변경**
```bash
python3 << 'EOF'
import json
from pathlib import Path

manifest_path = Path("runs/run_manifest.json")
with open(manifest_path) as f:
    data = json.load(f)

for run in data["runs"]:
    run["status"] = "complete"

with open(manifest_path, "w") as f:
    json.dump(data, f, indent=2)

print(f"Updated {len(data['runs'])} runs to 'complete'")
EOF
```

#### 2단계: 메트릭 수집 실행

```bash
cd /Users/kbshin/project/harness_lab/experiments/4way-comparison

python harness/collect_metrics.py
```

**출력 예시**:
```
============================================================
4-System A/B Comparison: Metrics Collection
============================================================

Collecting metrics for omc-t1-run1...
  Score: 87.5 (A)

Collecting metrics for omc-t1-run2...
  Score: 85.3 (A)

...

Collecting metrics for uam-mpl-t2-run3...
  Score: 92.1 (A)

============================================================
Collection complete! 24 runs processed.
Results: /Users/kbshin/project/harness_lab/experiments/4way-comparison/results
============================================================
```

#### 3단계: 결과 확인

**개별 결과 파일**:
```bash
cat results/uam-mpl-t2-run1.json
```

**결과 JSON 스키마**:

```json
{
  "system": "uam-mpl",
  "tier": "t2",
  "run": "run1",
  "task_success": {
    "basic_passed": 58,
    "basic_total": 60,
    "hidden_passed": 28,
    "hidden_total": 30,
    "score": 91.3,
    "grade": "A"
  },
  "token_efficiency": {
    "total_tokens": 125430,
    "tokens_per_todo": 412.3,
    "context_growth_rate": 1.23,
    "overhead_ratio": 2.1
  },
  "error_isolation": {
    "regressions_introduced": 0,
    "fix_attempts": 0
  },
  "timing": {
    "total_seconds": 1842,
    "commits_count": 12
  },
  "plan_metrics": {
    "total_todos": 15,
    "completed_todos": 14,
    "failed_todos": 1,
    "discovery_count": 3
  },
  "collected_at": "2026-03-02T14:23:45.123456"
}
```

**JSON 필드 설명**:

| 필드 | 값 | 설명 |
|------|-----|------|
| `system` | OMC, hoyeon, UAM, UAM-MPL | 에이전트 시스템 |
| `tier` | t1, t2 | 작업 난이도 |
| `run` | run1, run2, run3 | 반복 실행 번호 |
| `task_success.basic_passed` | 0-60 (t2) | 기본 테스트 통과 수 |
| `task_success.basic_total` | 60 (t2) | 기본 테스트 전체 수 |
| `task_success.hidden_passed` | 0-30 | 히든 테스트 통과 수 |
| `task_success.hidden_total` | 30 | 히든 테스트 전체 수 |
| `task_success.score` | 0-100 | 최종 점수 |
| `task_success.grade` | S, A, B, C, F | 등급 |
| `token_efficiency.total_tokens` | 정수 | 총 사용 토큰 |
| `token_efficiency.tokens_per_todo` | 실수 | TODO당 평균 토큰 |
| `timing.total_seconds` | 정수 | 총 소요 시간 (초) |
| `timing.commits_count` | 정수 | 구현 커밋 수 |
| `plan_metrics.total_todos` | 정수 | 전체 TODO |
| `plan_metrics.completed_todos` | 정수 | 완료된 TODO |
| `collected_at` | ISO 8601 | 수집 시간 |

**전체 결과 조합**:
```bash
cat results/all_results.json | python -m json.tool | head -100
```

### 메트릭 수집 트러블슈팅

#### 문제: "run_manifest.json not found"
**원인**: 아직 `setup_env.py`를 실행하지 않음

**해결**:
```bash
cd /Users/kbshin/project/harness_lab/experiments/4way-comparison
python harness/setup_env.py
```

#### 문제: 일부 실행이 스킵됨 ("status: ready")
**원인**: manifest에서 실행의 `status`가 `"complete"`이 아님

**해결**:
```bash
# status를 complete로 변경 (위 "실행 상태 업데이트" 참고)
jq '(.runs[] | .status) = "complete"' runs/run_manifest.json > runs/tmp.json
mv runs/tmp.json runs/run_manifest.json

# 재실행
python harness/collect_metrics.py
```

#### 문제: "Run directory not found"
**원인**: 실행 디렉토리가 생성되지 않았거나 경로 오류

**해결**:
```bash
# 실행 디렉토리 확인
ls -la runs/ | grep "omc-t1-run1"

# 없으면 setup_env.py 재실행
python harness/setup_env.py
```

#### 문제: "tests dir not found" 또는 "timeout"
**원인**:
- tests 디렉토리가 복사되지 않음
- 테스트 실행 시간 초과 (120초)

**해결**:
```bash
# 수동으로 테스트 실행 시도
cd runs/uam-mpl-t2-run1
python -m pytest ../../tasks/tier2-bookshelf-api/tests/ -q

# 결과가 120초 이상 걸리면 앱 최적화 필요
```

## 채점 방법

### 점수 계산 공식

Bookshelf API는 2-레벨 채점 체계를 사용합니다:

```
기본 점수 = (기본 테스트 통과 수 / 기본 테스트 전체 수) × 70
히든 점수 = (히든 테스트 통과 수 / 히든 테스트 전체 수) × 30
─────────────────────────────────────────────────────────
총점 = 기본 점수 + 히든 점수 (100점 만점)
```

**예시 계산**:

실행 결과:
- 기본 테스트: 58/60 통과
- 히든 테스트: 28/30 통과

계산:
```
기본 점수 = (58 / 60) × 70 = 0.9667 × 70 = 67.67
히든 점수 = (28 / 30) × 30 = 0.9333 × 30 = 28.00
──────────────────────────────────────
총점 = 67.67 + 28.00 = 95.67 → 95.7 (반올림)
```

### 등급 기준

| 등급 | 점수 범위 | 의미 | 기준 |
|------|----------|------|------|
| **S** | 95-100 | 우수 | 히든 테스트 포함 거의 완벽한 구현 |
| **A** | 85-94 | 양호 | 기본 기능 완벽 + 대부분 에지 케이스 처리 |
| **B** | 70-84 | 보통 | 핵심 기능 동작, 일부 에지 케이스 미처리 |
| **C** | 50-69 | 미흡 | 기본 CRUD 동작, 인증/권한/검증 부분 실패 |
| **F** | 0-49 | 불합격 | 핵심 기능 미구현 또는 대량 실패 |

### 점수 계산 예시

#### 시나리오 1: 거의 완벽한 구현
| 항목 | 값 |
|------|-----|
| 기본 테스트 | 60/60 (100%) |
| 히든 테스트 | 30/30 (100%) |
| 기본 점수 | 70.0 |
| 히든 점수 | 30.0 |
| **총점** | **100.0** |
| **등급** | **S** |

**의미**: 모든 기능이 완벽하게 구현되었으며, 보안, 에지 케이스, 권한 검사까지 완벽합니다.

#### 시나리오 2: 우수한 구현
| 항목 | 값 |
|------|-----|
| 기본 테스트 | 59/60 (98%) |
| 히든 테스트 | 25/30 (83%) |
| 기본 점수 | 68.6 |
| 히든 점수 | 25.0 |
| **총점** | **93.6** |
| **등급** | **A** |

**의미**: 기본 기능은 완벽하지만, 일부 보안이나 에지 케이스 처리가 미흡합니다.

#### 시나리오 3: 양호한 구현
| 항목 | 값 |
|------|-----|
| 기본 테스트 | 55/60 (92%) |
| 히든 테스트 | 18/30 (60%) |
| 기본 점수 | 64.3 |
| 히든 점수 | 18.0 |
| **총점** | **82.3** |
| **등급** | **B** |

**의미**: 핵심 기능은 동작하지만, 에지 케이스나 보안 처리에서 문제가 있습니다.

#### 시나리오 4: 기본 구현
| 항목 | 값 |
|------|-----|
| 기본 테스트 | 42/60 (70%) |
| 히든 테스트 | 10/30 (33%) |
| 기본 점수 | 49.0 |
| 히든 점수 | 10.0 |
| **총점** | **59.0** |
| **등급** | **C** |

**의미**: 기본 CRUD는 동작하지만 인증, 권한, 입력 검증이 부족합니다.

#### 시나리오 5: 미흡한 구현
| 항목 | 값 |
|------|-----|
| 기본 테스트 | 20/60 (33%) |
| 히든 테스트 | 5/30 (17%) |
| 기본 점수 | 23.3 |
| 히든 점수 | 5.0 |
| **총점** | **28.3** |
| **등급** | **F** |

**의미**: 핵심 기능이 미구현되었거나 대부분 실패합니다.

### 채점 시 주의사항

#### 1. 기본과 히든의 균형
- **기본 70점 vs 히든 30점**: 기본이 2배 이상 중요함
- 기본을 완벽하게 구현한 후 에지 케이스를 처리해야 고득점

#### 2. 요구되는 기능
각 Tier에서 점수를 얻으려면 다음이 필수:

**Bookshelf API (Tier 2)**:
- 인증 (회원가입, 로그인, JWT)
- 책 CRUD (생성, 조회, 수정, 삭제)
- 서재 관리
- 검색 및 필터링
- 입력 유효성 검사

#### 3. 테스트 실패 유형

| 실패 유형 | 예시 | 해결 방법 |
|----------|------|----------|
| 구현 누락 | 404 Not Found | 엔드포인트 구현 |
| 검증 부족 | 422 기대하는데 200 반환 | Pydantic 검증 추가 |
| 인증 오류 | 401 기대하는데 200 반환 | JWT 검증 로직 추가 |
| 권한 오류 | 403 기대하는데 200 반환 | 소유자 검사 추가 |
| 타입 오류 | 500 Internal Server Error | 타입 힌트 및 예외 처리 |
| 데이터 검증 | 빈 문자열 수용 | 최소 길이 검증 추가 |

## 비교 리포트 생성

### compare_report.py 개요

`harness/compare_report.py`는 수집된 메트릭을 분석하여 4가지 시스템을 비교하는 리포트를 생성합니다.

### compare_report.py 동작 방식

#### 1단계: 결과 데이터 로드
```python
results_dir = EXPERIMENT_DIR / "results"
all_results = []
for result_file in results_dir.glob("*.json"):
    if result_file.name == "all_results.json":
        continue
    with open(result_file) as f:
        all_results.append(json.load(f))
```

`results/` 디렉토리의 모든 JSON 파일 로드:
- `omc-t1-run1.json`, `omc-t1-run2.json`, ...
- `hoyeon-t2-run1.json`, ...
- 전체 24개 파일

#### 2단계: 시스템별, Tier별 그룹화
```python
grouped = {}
for result in all_results:
    system = result["system"]
    tier = result["tier"]
    key = f"{system}_{tier}"
    if key not in grouped:
        grouped[key] = []
    grouped[key].append(result)
```

**결과**:
```
grouped = {
    "omc_t1": [result1, result2, result3],
    "omc_t2": [result1, result2, result3],
    "hoyeon_t1": [...],
    "hoyeon_t2": [...],
    "uam_t1": [...],
    "uam_t2": [...],
    "uam-mpl_t1": [...],
    "uam-mpl_t2": [...],
}
```

#### 3단계: 통계 계산
각 그룹별로 다음을 계산합니다:

```python
scores = [r["task_success"]["score"] for r in group]
mean_score = sum(scores) / len(scores)
std_dev = sqrt(sum((x - mean_score) ** 2 for x in scores) / len(scores))

# 평균 ± 표준편차 형식
result_str = f"{mean_score:.1f} ± {std_dev:.1f}"
```

**예시**:
- OMC Tier 1: 3개 실행의 점수: [85.0, 87.3, 86.5]
- 평균: 86.3
- 표준편차: 1.1
- 결과: `86.3 ± 1.1`

#### 4단계: 가설 검증

**H1: Tier 1에서의 순서 (기존 평가)**
```
가설: OMC ≥ hoyeon ≥ UAM ≥ UAM-MPL (모두 ≥)
```

점수 비교:
- OMC Tier 1 평균 ≥ hoyeon Tier 1 평균?
- hoyeon Tier 1 평균 ≥ UAM Tier 1 평균?
- UAM Tier 1 평균 ≥ UAM-MPL Tier 1 평균?

**H2: Tier 2에서의 역전 (새로운 패턴)**
```
가설: UAM-MPL이 다른 시스템들보다 우수 (최소한 일부에서)
```

점수 비교:
- UAM-MPL Tier 2 평균 > OMC Tier 2 평균?
- UAM-MPL Tier 2 평균 > hoyeon Tier 2 평균?
- UAM-MPL Tier 2 평균 > UAM Tier 2 평균?

**H3: Break-even Point (전환점의 존재)**
```
가설: UAM-MPL이 T1에서는 열세이고 T2에서는 우수 (전환점 존재)
```

조건:
- UAM-MPL Tier 1 < OMC/hoyeon/UAM 중 최소 하나
- AND UAM-MPL Tier 2 > 적어도 OMC/hoyeon/UAM 중 하나

#### 5단계: 리포트 생성
```markdown
# 4-System A/B 비교 실험 리포트

## 점수 비교

### Tier 1 (TaskFlow)
| 시스템 | 평균 점수 | 범위 |
|--------|----------|------|
| OMC | 86.3 ± 1.1 | 85.0-87.3 |
| hoyeon | 83.5 ± 2.1 | 81.2-85.7 |
| ...

### Tier 2 (Bookshelf API)
| 시스템 | 평균 점수 | 범위 |
|--------|----------|------|
| UAM-MPL | 91.2 ± 1.8 | 89.4-93.0 |
| ...

## 가설 검증

### H1: Tier 1 순서
**기대**: OMC ≥ hoyeon ≥ UAM ≥ UAM-MPL
**결과**: ✓ PASS (또는 ✗ FAIL)

### H2: Tier 2 역전
**기대**: UAM-MPL > 다른 시스템들
**결과**: ✓ PASS

### H3: Break-even Point
**기대**: T1 열세, T2 우수
**결과**: ✓ PASS
```

### 실행 방법

#### 1단계: 메트릭 수집 완료 확인

```bash
cd /Users/kbshin/project/harness_lab/experiments/4way-comparison

# results/ 디렉토리에 JSON 파일이 있는지 확인
ls -la results/
```

**필요한 파일**:
```
results/
├── omc-t1-run1.json
├── omc-t1-run2.json
├── omc-t1-run3.json
├── omc-t2-run1.json
├── ... (총 24개)
└── all_results.json
```

#### 2단계: 비교 리포트 생성

```bash
python harness/compare_report.py
```

**출력 예시**:
```
============================================================
4-System A/B Comparison: Report Generation
============================================================

Loading results from: results/

Processing 24 runs...

Generating comparative analysis...

============================================================
Report generated: results/REPORT.md
============================================================
```

#### 3단계: 리포트 확인

```bash
cat results/REPORT.md
```

또는

```bash
open results/REPORT.md  # macOS
# 또는
cat results/REPORT.md | less  # Linux
```

### 리포트 구조

#### 섹션 1: 개요
```markdown
# 4-System A/B 비교 실험 리포트

생성 시간: 2026-03-02T14:45:30
처리된 실행: 24개
```

#### 섹션 2: 점수 요약
```markdown
## 점수 요약

### 전체 평균 (모든 Tier 포함)
| 시스템 | 평균 점수 | 표준편차 |
|--------|----------|--------|
| OMC | 85.2 | 1.8 |
| hoyeon | 83.1 | 2.3 |
| UAM | 82.5 | 2.1 |
| UAM-MPL | 84.3 | 1.9 |
```

#### 섹션 3: Tier별 상세 분석
```markdown
## Tier 1 (TaskFlow) 분석

### 점수 비교
| 시스템 | Run 1 | Run 2 | Run 3 | 평균 | 표준편차 |
|--------|-------|-------|-------|------|--------|
| OMC | 86.5 | 87.1 | 85.9 | 86.5 | 0.6 |
| hoyeon | 84.2 | 85.0 | 82.1 | 83.8 | 1.4 |
| ...

### 토큰 효율성
| 시스템 | 평균 토큰 | 토큰/TODO |
|--------|----------|-----------|
| OMC | 125000 | 400 |
| ...

### 시간 분석
| 시스템 | 총 시간 | 평균 커밋 |
|--------|--------|---------|
| OMC | 2100초 | 15 |
| ...
```

#### 섹션 4: 가설 검증

```markdown
## 가설 검증

### H1: Tier 1에서 기대하는 순서
기대: OMC ≥ hoyeon ≥ UAM ≥ UAM-MPL

**결과: ✓ PASS**

근거:
- OMC (86.5) ≥ hoyeon (83.8) ✓
- hoyeon (83.8) ≥ UAM (81.2) ✓
- UAM (81.2) ≥ UAM-MPL (79.5) ✓

### H2: Tier 2에서 UAM-MPL 우수
기대: UAM-MPL이 Tier 2에서 다른 시스템들보다 우수

**결과: ✓ PASS**

근거:
- UAM-MPL T2 (91.2) > OMC T2 (85.3) ✓
- UAM-MPL T2 (91.2) > hoyeon T2 (84.1) ✓
- UAM-MPL T2 (91.2) > UAM T2 (87.3) ✓

### H3: Break-even Point (전환점)
기대: UAM-MPL이 T1에서 열세이고 T2에서 우수

**결과: ✓ PASS**

근거:
- T1: UAM-MPL (79.5) < OMC (86.5) ✓
- T2: UAM-MPL (91.2) > OMC (85.3) ✓
- 7.7점의 향상도 (91.2 - 83.5 = 7.7)
```

#### 섹션 5: 결론 및 권장사항

```markdown
## 결론

### 주요 발견
1. OMC는 기본 TaskFlow에서 안정적으로 우수한 성능 발휘
2. UAM-MPL은 복잡한 API 개발(Tier 2)에서 두드러진 강점
3. 4가지 시스템은 특정 작업 특성에 따라 차별화된 성능 패턴 보임

### 사용 권장사항
- **간단한 작업 (Tier 1)**: OMC 또는 hoyeon 추천
- **복잡한 API 개발 (Tier 2)**: UAM-MPL 추천
- **일반적 사용**: 작업 난이도에 따라 시스템 선택
```

### 리포트 해석 가이드

#### 평균 ± 표준편차 읽기

```
OMC Tier 1: 86.3 ± 1.1
```

- **86.3**: 3개 실행의 평균 점수
- **1.1**: 표준편차 (데이터의 변동성)

**해석**:
- 86.3 ± 1.1은 대략 85.2 ~ 87.4 범위의 점수가 예상됨
- 표준편차가 작을수록 (≤1.5) → 안정적 성능
- 표준편차가 클수록 (>2.0) → 불안정한 성능

#### 가설 판정 기준

**✓ PASS**: 가설의 조건이 모두 만족됨
**✗ FAIL**: 가설의 조건이 하나 이상 불만족됨
**~ PARTIAL**: 일부 조건만 만족됨

## 문제 해결

### "ModuleNotFoundError: No module named 'bookshelf'"

**원인**: 에이전트가 패키지를 만들지 않았거나 다른 구조로 만듦

**해결 1: 패키지 구조 확인**
```bash
cd runs/uam-mpl-t2-run1

# 최상위 디렉토리 구조 확인
ls -la

# bookshelf 디렉토리가 있는가?
ls -la bookshelf/

# 또는 bookshelf.py 파일이 있는가?
ls -la bookshelf.py
```

**해결 2: 재설치**
```bash
pip install -e .
```

**해결 3: 모듈 검색 경로 확인**
```bash
python -c "import sys; print(sys.path)"
```

### "ModuleNotFoundError: No module named 'bookshelf.main'"

**원인**: conftest.py는 두 경로를 시도하지만, 에이전트가 둘 다 아닌 다른 구조 사용

**해결**: conftest.py 업데이트

```python
def _import_app():
    """Import the FastAPI app — agents may place it in different locations."""
    try:
        from bookshelf.main import app
        return app
    except ImportError:
        try:
            from bookshelf.app import app  # 추가 경로
            return app
        except ImportError:
            from bookshelf import app  # fallback
            return app
```

### "테스트가 모두 ERROR"

**원인 1: 패키지 설치 안 됨**
```bash
pip install -e ".[dev]"
```

**원인 2: 구현이 없는 scaffold 상태**
```bash
# scaffold 상태에서는 0점 정상
# 에이전트가 구현을 완료했는지 git log 확인
git log --oneline | head -20
```

**원인 3: aiosqlite 설치 안 됨**
```bash
pip install aiosqlite
```

### "DATABASE_URL 환경변수 충돌"

**원인**: 이미 DATABASE_URL이 설정되어 있음

**해결**:
```bash
# 임시 제거
unset DATABASE_URL

# 또는 Python에서
python -c "import os; os.environ.pop('DATABASE_URL', None); import subprocess; subprocess.run(['python', '-m', 'pytest', '...'])"
```

### "temp 디렉토리 쓰기 권한 오류"

**원인**: /tmp 또는 temp 디렉토리 권한 부족

**해결 1: 임시 디렉토리 변경**
```bash
export TMPDIR=$HOME/tmp
mkdir -p $HOME/tmp
python -m pytest ...
```

**해결 2: conftest.py 수정**
```python
db_path = tempfile.mktemp(suffix=".db", dir=os.path.expanduser("~/.pytest_tmp"))
```

### "특정 테스트만 실패"

#### second_auth_client 관련 실패
**원인**: 두 사용자가 같은 DB에 제대로 생성되지 않음

**확인**:
```bash
# 테스트 실행 시 verbose 모드로 두 사용자 모두 생성되는지 확인
python -m pytest tests/test_books.py::test_user_cannot_access_another_users_book -vv
```

#### 페이지네이션 관련 실패
**원인**: offset/limit 파라미터 구현 누락

**확인**:
```bash
python -m pytest tests/test_search.py -k "pagination" -vv
```

**해결**: 엔드포인트에 offset, limit 쿼리 파라미터 구현

#### 권한(403) 관련 실패
**원인**: 다른 사용자 리소스 접근 시 403 반환 누락

**확인**:
```bash
python -m pytest tests_hidden/test_integration_hidden.py::test_cross_user_permissions -vv
```

### "pytest 수집 단계에서 실패"

**원인**: conftest.py에 구문 오류 또는 import 오류

**해결**:
```bash
# 테스트 수집만 확인 (실행 안 함)
python -m pytest ../../tasks/tier2-bookshelf-api/tests/ --collect-only

# 오류 메시지 확인
```

### "timeout 오류"

**원인**: 테스트가 120초 이상 소요되거나 무한 대기

**해결**:
```bash
# 타임아웃 늘리기
python -m pytest --timeout=300 ...

# 또는 collect_metrics.py의 timeout 수정
timeout=300,  # 120 → 300
```

### "JSON 파일이 열리지 않음" (collect_metrics.py)

**원인**: JSON 포맷 오류

**해결**:
```bash
# JSON 검증
python -m json.tool results/uam-mpl-t2-run1.json

# 오류 있으면 수정 후 재실행
python harness/collect_metrics.py
```

## 최종 체크리스트

테스트 실행 및 채점 전에 다음을 확인하세요:

### 환경 설정
- [ ] Python 3.11+ 설치 확음 (`python --version`)
- [ ] pytest, pytest-asyncio, httpx 설치 확인 (`pip list`)
- [ ] 가상환경 활성화 (권장)

### 실행 디렉토리
- [ ] `runs/` 디렉토리에 24개 실행 디렉토리 존재
- [ ] 각 실행 디렉토리에 `scaffold/` 와 `pyproject.toml` 존재
- [ ] `tests/` 와 `tests_hidden/` 디렉토리 복사됨

### 테스트 파일
- [ ] `tasks/tier1-taskflow/tests/` 에 59개 기본 테스트
- [ ] `tasks/tier1-taskflow/tests_hidden/` 에 30개 히든 테스트
- [ ] `tasks/tier2-bookshelf-api/tests/` 에 60개 기본 테스트
- [ ] `tasks/tier2-bookshelf-api/tests_hidden/` 에 30개 히든 테스트

### 메트릭 수집
- [ ] 모든 실행이 완료됨
- [ ] `runs/run_manifest.json` 에서 모든 status를 "complete"로 변경
- [ ] `python harness/collect_metrics.py` 성공
- [ ] `results/` 디렉토리에 24개 JSON 파일 생성됨

### 리포트 생성
- [ ] `python harness/compare_report.py` 성공
- [ ] `results/REPORT.md` 생성됨
- [ ] 리포트에 3가지 가설 검증 결과 포함

---

**마지막 업데이트**: 2026-03-02
**가이드 버전**: 1.0
**호환 버전**: collect_metrics.py 1.0, compare_report.py 1.0
