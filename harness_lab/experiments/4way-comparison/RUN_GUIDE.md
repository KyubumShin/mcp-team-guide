# 4-System A/B 비교 실험 실행 가이드

## 사전 요구사항

- Python 3.11+
- Node.js 16+
- Claude Code CLI (`claude` 명령어 사용 가능)
- OMC 플러그인 설치 완료
- hoyeon 플러그인 설치 완료
- UAM 플러그인 설치 완료 (`/tmp/uam-repo`)

## 1단계: 환경 설정

```bash
cd experiments/4way-comparison
python harness/setup_env.py
```

- 24개 실행 디렉토리 생성 확인
- 각 디렉토리에 scaffold + git init 확인

## 2단계: 수동 실행 (24회)

### Tier 1 (TaskFlow)

```bash
# OMC
cd runs/omc-t1-run1 && claude "autopilot: $(cat ../../tasks/tier1-taskflow/prompt.md)"
cd runs/omc-t1-run2 && claude "autopilot: $(cat ../../tasks/tier1-taskflow/prompt.md)"
cd runs/omc-t1-run3 && claude "autopilot: $(cat ../../tasks/tier1-taskflow/prompt.md)"

# hoyeon
cd runs/hoyeon-t1-run1 && claude "/specify $(cat ../../tasks/tier1-taskflow/prompt.md)"
cd runs/hoyeon-t1-run2 && claude "/specify $(cat ../../tasks/tier1-taskflow/prompt.md)"
cd runs/hoyeon-t1-run3 && claude "/specify $(cat ../../tasks/tier1-taskflow/prompt.md)"

# UAM Standard
cd runs/uam-t1-run1 && claude "uam $(cat ../../tasks/tier1-taskflow/prompt.md)"
cd runs/uam-t1-run2 && claude "uam $(cat ../../tasks/tier1-taskflow/prompt.md)"
cd runs/uam-t1-run3 && claude "uam $(cat ../../tasks/tier1-taskflow/prompt.md)"

# UAM-MPL
cd runs/uam-mpl-t1-run1 && claude "uam mpl $(cat ../../tasks/tier1-taskflow/prompt.md)"
cd runs/uam-mpl-t1-run2 && claude "uam mpl $(cat ../../tasks/tier1-taskflow/prompt.md)"
cd runs/uam-mpl-t1-run3 && claude "uam mpl $(cat ../../tasks/tier1-taskflow/prompt.md)"
```

### Tier 2 (Bookshelf API)

```bash
# OMC
cd runs/omc-t2-run1 && claude "autopilot: $(cat ../../tasks/tier2-bookshelf-api/prompt.md)"
cd runs/omc-t2-run2 && claude "autopilot: $(cat ../../tasks/tier2-bookshelf-api/prompt.md)"
cd runs/omc-t2-run3 && claude "autopilot: $(cat ../../tasks/tier2-bookshelf-api/prompt.md)"

# hoyeon
cd runs/hoyeon-t2-run1 && claude "/specify $(cat ../../tasks/tier2-bookshelf-api/prompt.md)"
cd runs/hoyeon-t2-run2 && claude "/specify $(cat ../../tasks/tier2-bookshelf-api/prompt.md)"
cd runs/hoyeon-t2-run3 && claude "/specify $(cat ../../tasks/tier2-bookshelf-api/prompt.md)"

# UAM Standard
cd runs/uam-t2-run1 && claude "uam $(cat ../../tasks/tier2-bookshelf-api/prompt.md)"
cd runs/uam-t2-run2 && claude "uam $(cat ../../tasks/tier2-bookshelf-api/prompt.md)"
cd runs/uam-t2-run3 && claude "uam $(cat ../../tasks/tier2-bookshelf-api/prompt.md)"

# UAM-MPL
cd runs/uam-mpl-t2-run1 && claude "uam mpl $(cat ../../tasks/tier2-bookshelf-api/prompt.md)"
cd runs/uam-mpl-t2-run2 && claude "uam mpl $(cat ../../tasks/tier2-bookshelf-api/prompt.md)"
cd runs/uam-mpl-t2-run3 && claude "uam mpl $(cat ../../tasks/tier2-bookshelf-api/prompt.md)"
```

### 실행 체크리스트

- [ ] 각 실행 전 `git status`로 깨끗한 상태 확인
- [ ] 실행 시작/종료 시간 기록 (자동 수집되지만 수동 백업)
- [ ] 각 실행이 완전히 끝난 후 다음 실행 시작
- [ ] 같은 시스템의 3회 반복은 연속 실행 권장
- [ ] **각 실행 완료 후 `run_manifest.json`에서 해당 실행의 status를 `"complete"`로 변경**

### 실행 완료 기록

각 실행이 끝나면 `runs/run_manifest.json`에서 해당 항목의 `"status"`를 `"ready"` → `"complete"`로 변경해야 합니다.
`collect_metrics.py`는 `"complete"` 상태인 실행만 처리합니다.

```bash
# 예시: omc-t1-run1 완료 후
# runs/run_manifest.json에서 해당 항목을 찾아 수정:
#   "status": "ready"  →  "status": "complete"

# 또는 jq로 일괄 변경 (모든 실행 완료 후):
cd runs && jq '(.runs[] | .status) = "complete"' run_manifest.json > tmp.json && mv tmp.json run_manifest.json
```

## 3단계: 메트릭 수집

```bash
python harness/collect_metrics.py
```

- `results/` 디렉토리에 완료된 실행 수만큼 JSON 파일 생성
- 누락된 메트릭이 있으면 null로 표시됨
- `status`가 `"complete"`가 아닌 실행은 건너뜀

## 4단계: 비교 리포트 생성

```bash
python harness/compare_report.py
```

- `results/REPORT.md` 생성 확인
- 가설 검증 결과 확인

## 문제 해결

### 실행이 중간에 멈춘 경우

- `git log`로 마지막 커밋 확인
- 해당 실행은 부분 완료로 기록 (`collect_metrics.py`가 처리)

### 테스트가 실행되지 않는 경우

- `pip install -e .` 확인
- `conftest.py`의 fixture 확인

### HITL 응답이 필요한 경우

- `hitl_responses.yaml` 참조하여 동일한 응답 입력
- OMC는 자율 모드이므로 HITL 불필요
