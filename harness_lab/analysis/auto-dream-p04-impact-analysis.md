# Auto-Dream이 P-04 (Skill Filtering & Memory Cleansing)에 미치는 영향 분석

> **작성일**: 2026-03-25
> **관련 기능**: P-04 (Skill Audit CLI, deferred v0.9.0)
> **트리거**: Claude Code auto-dream 기능 발견 (미출시, feature flag `tengu_onyx_plover`)

---

## 1. Auto-Dream 개요

Auto-dream은 Claude Code의 **메모리 자동 정리(consolidation) 기능**으로, 세션 간 축적된 메모리 파일의 노후화 문제를 해결한다. Anthropic의 Sleep-time Compute 논문(arXiv:2504.13171)에 기반하며, 유휴 시간에 사전 계산하여 테스트 타임 컴퓨트를 ~5배 절감하는 개념을 메모리 정리에 적용했다.

### 시스템 프롬프트 구조 (v2.1.78)

```
변수 6개:
  MEMORY_DIR          — 메모리 파일 경로
  MEMORY_DIR_CONTEXT  — 추가 디렉토리 설명
  TRANSCRIPTS_DIR     — 세션 트랜스크립트 경로 (JSONL)
  INDEX_FILE          — MEMORY.md 경로
  INDEX_MAX_LINES     — 인덱스 최대 줄 수 (200)
  ADDITIONAL_CONTEXT  — 선택적 추가 컨텍스트
```

### 4-Phase 구조

| Phase | 이름 | 동작 |
|-------|------|------|
| 1 | **Orient** | 메모리 디렉토리 ls, INDEX_FILE 읽기, 기존 토픽 파일 스킴 |
| 2 | **Gather Signal** | 일일 로그 확인, drift된 메모리 탐지, 트랜스크립트 narrow grep |
| 3 | **Consolidate** | 토픽 파일에 병합, 상대→절대 날짜 변환, 모순 사실 삭제 |
| 4 | **Prune & Index** | INDEX_FILE을 MAX_LINES 이하 유지, stale 포인터 제거, 관련성 재정렬 |

### 실행 조건 (dual-gate)

| 파라미터 | 값 | 목적 |
|---------|---|------|
| `enabled` | `false` (서버 flag) | 점진적 롤아웃 제어 |
| `minHours` | `24` | 최소 24시간 간격 |
| `minSessions` | `5` | 최소 5개 세션 누적 |

### 안전장치

- **메모리 파일만 read-write**, 프로젝트 소스코드 read-only
- Lock file로 동시 실행 방지
- 백그라운드 실행 (활성 세션 비차단)

### 설계 특이점

1. **grep-only 정책**: 트랜스크립트를 통째로 읽지 않고 narrow grep만 수행 → 913 세션도 8-9분 내 처리
2. **source-of-truth 위임**: auto-memory 시스템 프롬프트의 포맷/규칙을 재사용, 중복 정의 없음
3. **조건부 렌더링**: `${ADDITIONAL_CONTEXT?...:""}` — 불필요한 섹션 자체를 제거하여 토큰 절약

### 현재 상태 (2026-03-25)

- Feature flag `tengu_onyx_plover` 뒤에서 점진적 롤아웃 중
- `/memory` 메뉴에서 "Auto-dream: on/off" 표시
- 수동 트리거: "dream", "auto dream", "consolidate my memory files"

---

## 2. Auto-Dream vs P-04 비교

### 범위 비교

| 차원 | Auto-Dream | P-04 |
|------|-----------|------|
| **대상** | `~/.claude/projects/*/memory/` (사용자 메모리) | `.mpl/memory/` (플러그인 메모리) + skills + hooks + agents |
| **트리거** | 24h + 5 sessions (서버 flag) | N runs (passive) + model upgrade (active) |
| **정리 방식** | Rule-based: 날짜 변환, 모순 제거, 중복 병합, index pruning | Confidence decay, usage stats, false positive rate, model dependency audit |
| **실행 주체** | Background subagent | Compound run 후처리 + CLI audit |
| **이론 배경** | Sleep-time Compute paper | Bounded Retries 확장 + OpenViking 역방향 + DeerFlow confidence |

### 겹치는 영역

P-04의 "Memory Cleansing" 부분만 겹침:
- 상대 날짜 → 절대 날짜 변환 (동일)
- 모순 항목 제거 (동일)
- 중복 병합 (동일)
- Stale 항목 정리 (auto-dream: rule-based, P-04: decay function)

### P-04 고유 영역 (auto-dream이 다루지 않음)

- **Layer 1**: Hook/skill 발동 통계 수집 (usage-stats.jsonl)
- **Layer 1**: False positive rate 기반 pruning candidate 탐지
- **Layer 2**: 모델 업그레이드 시 skill-metadata 검증
- **Confidence decay**: `confidence(t) = initial × decay^(days/half_life)`

### 관계 정의

**경쟁이 아니라 계층 분리**:
- Auto-dream = 사용자 수준 메모리 (프로젝트 컨텍스트, 선호도, 피드백)
- P-04 = 플러그인 수준 메모리 (학습, 라우팅 패턴, 스킬 효과성)

---

## 3. P-04 보류 근거에 대한 영향 평가

### 원래 보류 근거 (debate 합의, 2026-03-24)

| # | 보류 근거 | 원문 | Auto-Dream 영향 |
|---|----------|------|----------------|
| 1 | **입력 데이터 부재** | "P-03 로그 데이터 최소 10회 축적 후 설계" | ❌ 변화 없음 — auto-dream은 usage tracking 미수행 |
| 2 | **Premature optimization** | "decay 함수 파라미터를 정하려면 충분한 사용 데이터 필요" | ✅ **부분 완화** — rule-based consolidation으로 대체 가능 |
| 3 | **수동이 충분** | "critic 흡수 등 수동으로 잘 해왔음" | ⚠️ Anthropic 판단은 반론이 되나 MPL 규모에 직접 적용은 논리 비약 |

### P-04 구성요소별 변경

| 구성요소 | 원안 | Auto-Dream 반영 후 | 변경 근거 |
|----------|------|-------------------|----------|
| ① Memory Cleansing | Confidence decay function | **Auto-dream 4-phase consolidation 채택** | 프로덕션 검증 패턴 존재, 데이터 없는 수식 설계 불필요 |
| ② Usage Statistics (Layer 1) | Hook/skill 발동 통계 수집 | 변화 없음 — P-03 데이터 필요 | Auto-dream은 usage tracking 미수행 |
| ③ Model Audit (Layer 2) | 모델 업그레이드 시 검증 | 변화 없음 — auto-dream 범위 밖 | Plugin lifecycle은 Anthropic 관할 밖 |

### 일정 변경 근거 평가

| 앞당김 요인 | 가능 여부 | 이유 |
|------------|:--------:|------|
| P-03 의존성 해소 | ❌ | Auto-dream과 무관 |
| Decay function 제거 | ✅ | Rule-based로 대체 → 구현 난이도 ↓ |
| 검증된 패턴 차용 | ✅ | 4-phase 구조 그대로 적용 → 설계 리스크 ↓ |
| 수동 충분론 약화 | ⚠️ | 간접 근거일 뿐 직접 증거 아님 |

### 최종 판정

**일정 유지, 범위 조정**:

```
v0.8.0: P-03 + P-01 (변경 없음)
v0.9.0: P-04 (범위 변경)
  ① Memory Cleansing → auto-dream 4-phase 패턴 채택 (decay function 폐기)
  ② Usage Statistics → P-03 데이터 기반 (원안 유지)
  ③ Model Audit → 원안 유지
```

**핵심 변화**: P-04 ①이 "데이터 기반 수식 설계" → "검증된 패턴 적용"으로 바뀌면서, v0.9.0 도달 시 **구현 속도 향상 + 설계 위험 감소**. 단, ②③이 P-03 데이터에 의존하므로 일정 앞당김은 정당화되지 않음.

---

## 4. Skill-Level 적용 설계: mpl-dream (미래 참조)

Auto-dream의 4-phase를 `.mpl/memory/`에 적용하는 `mpl-dream` skill 구상:

| Phase | Auto-Dream 원본 | mpl-dream 적용 |
|-------|----------------|----------------|
| Orient | memory dir ls + INDEX_FILE | `.mpl/memory/` 스캔 + learnings.md, routing-patterns.jsonl 상태 파악 |
| Gather Signal | 트랜스크립트 narrow grep | 최근 N회 `.mpl/plans/*.md`에서 실패/재시도 패턴 추출 |
| Consolidate | 날짜 변환, 모순 제거, 병합 | learnings.md 모순 제거 + routing-patterns confidence 갱신 |
| Prune & Index | INDEX_FILE max lines 유지 | 200줄 초과 시 archive 이동 + pruning-candidates.md 생성 |

이 설계는 P-04 ① 구현 시 직접 활용 가능.

---

## 5. 참고 소스

- [시스템 프롬프트 (GitHub, Piebald-AI)](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/agent-prompt-dream-memory-consolidation.md) — v2.1.78
- [DEV Community 분석](https://dev.to/akari_iku/does-claude-code-need-sleep-inside-the-unreleased-auto-dream-feature-2n7m) — Sleep-time Compute 연결 분석
- [claudefa.st 가이드](https://claudefa.st/blog/guide/mechanics/auto-dream) — 4-Phase 상세 설명
- [Sleep-time Compute 논문](https://arxiv.org/abs/2504.13171) — arXiv:2504.13171 (Kevin Lin, Charlie Snell et al.)
- P-04 debate transcript: `analysis/p01-p05-debate-transcript.md`
