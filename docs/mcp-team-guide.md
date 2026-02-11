# MCP 팀 설정 가이드

## 1. 소개

### MCP란?

MCP(Model Context Protocol)는 AI 코딩 도구(Cursor, Claude Code 등)가 외부 서비스(GitHub, Jira, Confluence)와 연동할 수 있게 해주는 프로토콜입니다. MCP 서버를 설정하면 AI가 직접 이슈를 조회하고, PR을 생성하고, 문서를 검색하는 등의 작업을 수행할 수 있습니다.

### 팀에서 MCP를 사용하는 이유

- **생산성 향상**: AI가 GitHub 이슈, Jira 티켓, Confluence 문서에 직접 접근
- **컨텍스트 공유**: 프로젝트 설정 파일을 커밋하여 팀 전체가 동일한 MCP 구성 사용
- **보안 유지**: 환경 변수를 통해 개인 토큰을 분리하여 설정 파일에 시크릿 노출 방지

### 다루는 범위

| 항목 | 설명 |
|------|------|
| **MCP 서버** | GitHub, Jira, Confluence |
| **클라이언트** | Cursor (주), Claude Code (부) |

---

## 2. 사전 요구사항

### 필수 소프트웨어

- **Node.js** (v18 이상): MCP 서버 실행에 필요 (`npx` 사용)
  - 설치 확인: `node --version`

### 필요한 토큰

| 서비스 | 토큰 종류 | 필요 권한 |
|--------|-----------|-----------|
| GitHub | Personal Access Token (PAT) | `repo`, `read:org`, `read:user` |
| Jira / Confluence | Atlassian API Token | Jira 및 Confluence 프로젝트 접근 권한 |

### 토큰 생성 가이드 링크

- **GitHub PAT**: https://github.com/settings/tokens
- **Atlassian API Token**: https://id.atlassian.com/manage-profile/security/api-tokens

---

## 3. 개인 토큰 설정

각 팀원이 자신의 로컬 환경에서 수행해야 하는 단계입니다.

### 3.1 GitHub Personal Access Token 생성

1. GitHub에 로그인
2. **Settings** > **Developer settings** > **Personal access tokens** > **Tokens (classic)** 이동
3. **Generate new token (classic)** 클릭
4. 토큰 이름 입력 (예: `mcp-cursor`)
5. 필요한 권한 선택:
   - `repo` (전체)
   - `read:org`
   - `read:user`
6. **Generate token** 클릭 후 토큰 복사 (다시 볼 수 없음)

### 3.2 Atlassian API Token 생성

1. https://id.atlassian.com/manage-profile/security/api-tokens 접속
2. **API 토큰 만들기** 클릭
3. 레이블 입력 (예: `mcp-cursor`)
4. **만들기** 클릭 후 토큰 복사

### 3.3 환경 변수 설정

쉘 프로필 파일(`~/.zshrc` 또는 `~/.bashrc`)에 다음을 추가합니다:

```bash
# === MCP 토큰 설정 ===

# GitHub
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_여기에_토큰_입력"

# Atlassian (Jira + Confluence)
export ATLASSIAN_URL="https://회사이름.atlassian.net"
export ATLASSIAN_EMAIL="본인이메일@회사.com"
export ATLASSIAN_API_TOKEN="ATATT3x여기에_토큰_입력"
```

설정 후 터미널을 재시작하거나 다음 명령 실행:

```bash
source ~/.zshrc  # 또는 source ~/.bashrc
```

환경 변수 설정 확인:

```bash
echo $GITHUB_PERSONAL_ACCESS_TOKEN
echo $ATLASSIAN_URL
echo $ATLASSIAN_EMAIL
echo $ATLASSIAN_API_TOKEN
```

각 값이 올바르게 출력되면 설정 완료입니다.

---

## 4. Cursor 설정 (주 클라이언트)

### 설정 파일 위치

프로젝트 루트의 `.cursor/mcp.json`에 설정합니다. 이 파일은 **환경 변수 참조만 포함**하므로 Git에 안전하게 커밋할 수 있습니다.

### 전체 설정 예시

`.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    },
    "atlassian": {
      "command": "npx",
      "args": ["-y", "@xuandev/atlassian-mcp"],
      "env": {
        "ATLASSIAN_URL": "${ATLASSIAN_URL}",
        "ATLASSIAN_EMAIL": "${ATLASSIAN_EMAIL}",
        "ATLASSIAN_API_TOKEN": "${ATLASSIAN_API_TOKEN}"
      }
    }
  }
}
```

### 설정 확인 방법

1. Cursor를 재시작합니다
2. **Settings** > **MCP** 메뉴에서 서버 목록 확인
3. 각 서버 옆에 초록색 상태 표시가 나타나면 정상 연결

---

## 5. Claude Code 설정 (부 클라이언트)

### 설정 파일 위치

프로젝트 루트의 `.mcp.json`에 설정합니다.

### 전체 설정 예시

`.mcp.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    },
    "atlassian": {
      "command": "npx",
      "args": ["-y", "@xuandev/atlassian-mcp"],
      "env": {
        "ATLASSIAN_URL": "${ATLASSIAN_URL}",
        "ATLASSIAN_EMAIL": "${ATLASSIAN_EMAIL}",
        "ATLASSIAN_API_TOKEN": "${ATLASSIAN_API_TOKEN}"
      }
    }
  }
}
```

### 설정 확인 방법

Claude Code에서 다음 명령으로 MCP 서버 상태를 확인합니다:

```
/mcp
```

각 서버가 `connected` 상태로 표시되면 정상입니다.

---

## 6. 컨테이너 환경에서 MCP 서버 운영

로컬 `npx`로 MCP 서버를 실행하는 대신, Docker/Kubernetes를 사용하여 팀 공용 MCP 서버를 중앙에서 운영할 수 있습니다.

### 왜 컨테이너로 운영하는가?

- **환경 통일**: 팀원 로컬에 Node.js 설치 불필요
- **중앙 관리**: 토큰을 Kubernetes Secret으로 일괄 관리
- **가용성**: 항상 실행 중인 서버로 클라이언트 재시작 시에도 즉시 연결
- **보안 강화**: 토큰이 개인 로컬 환경에 저장되지 않음

### 6.1 Docker로 MCP 서버 실행

#### Dockerfile 예시 (GitHub MCP 서버)

```dockerfile
FROM node:20-slim

RUN npm install -g @modelcontextprotocol/server-github

EXPOSE 3000

CMD ["npx", "-y", "supergateway", "--stdio", "npx -y @modelcontextprotocol/server-github", "--port", "3000"]
```

> **참고**: MCP 서버는 기본적으로 stdio 통신을 사용합니다. 원격 접근을 위해 [supergateway](https://github.com/supercorp-ai/supergateway) 같은 브릿지를 사용하여 stdio를 SSE(Server-Sent Events) HTTP 엔드포인트로 변환합니다.

#### 로컬 Docker 실행

```bash
docker build -t mcp-github-server .

docker run -d \
  --name mcp-github \
  -p 3000:3000 \
  -e GITHUB_PERSONAL_ACCESS_TOKEN="ghp_여기에_토큰" \
  mcp-github-server
```

### 6.2 Kubernetes 배포

#### Secret 생성

토큰을 Kubernetes Secret으로 관리합니다:

```bash
# GitHub 토큰 Secret
kubectl create secret generic mcp-github-secret \
  --from-literal=GITHUB_PERSONAL_ACCESS_TOKEN="ghp_여기에_토큰"

# Atlassian 토큰 Secret
kubectl create secret generic mcp-atlassian-secret \
  --from-literal=ATLASSIAN_URL="https://회사이름.atlassian.net" \
  --from-literal=ATLASSIAN_EMAIL="본인이메일@회사.com" \
  --from-literal=ATLASSIAN_API_TOKEN="ATATT3x여기에_토큰"
```

#### Deployment + Service 예시 (GitHub MCP 서버)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-github-server
  labels:
    app: mcp-github-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mcp-github-server
  template:
    metadata:
      labels:
        app: mcp-github-server
    spec:
      containers:
        - name: mcp-github
          image: mcp-github-server:latest
          ports:
            - containerPort: 3000
          envFrom:
            - secretRef:
                name: mcp-github-secret
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "250m"
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-github-server
spec:
  selector:
    app: mcp-github-server
  ports:
    - port: 3000
      targetPort: 3000
  type: ClusterIP
```

#### 배포

```bash
kubectl apply -f mcp-github-server.yaml
```

### 6.3 로컬에서 클러스터 MCP 서버에 접근

#### 방법 A: kubectl port-forward (개발용)

```bash
kubectl port-forward svc/mcp-github-server 3000:3000
```

#### 방법 B: Ingress 설정 (팀 공용)

클러스터에 Ingress를 구성하여 `mcp-github.internal.company.com` 같은 내부 도메인으로 노출합니다.

### 6.4 클라이언트에서 원격 MCP 서버 연결

컨테이너로 운영하는 MCP 서버는 `command` 대신 `url`을 사용하여 SSE로 연결합니다.

#### Cursor 설정 (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "github": {
      "url": "http://localhost:3000/sse"
    },
    "atlassian": {
      "url": "http://localhost:3001/sse"
    }
  }
}
```

#### Claude Code 설정 (`.mcp.json`)

```json
{
  "mcpServers": {
    "github": {
      "url": "http://localhost:3000/sse"
    },
    "atlassian": {
      "url": "http://localhost:3001/sse"
    }
  }
}
```

> **팁**: Ingress를 사용하는 경우 `localhost:3000` 대신 내부 도메인 URL을 사용합니다:
> ```json
> "url": "https://mcp-github.internal.company.com/sse"
> ```

### 6.5 개인 토큰 vs 공용 토큰 선택

| 방식 | 장점 | 단점 | 적합한 경우 |
|------|------|------|-------------|
| **개인 토큰 (로컬 npx)** | 권한 추적 용이, 개인별 권한 설정 | 로컬 환경 설정 필요 | 감사 로그가 중요한 경우 |
| **공용 서비스 토큰 (K8s)** | 설정 간편, 중앙 관리 | 개인별 행위 추적 어려움 | 팀 공용 읽기 위주 작업 |
| **개인 토큰 + K8s** | 보안과 편의성 모두 확보 | 구현 복잡도 증가 | 기업 환경 권장 |

> **권장**: 읽기 전용 작업(이슈 조회, 문서 검색)은 공용 서비스 토큰으로, 쓰기 작업(PR 생성, 이슈 수정)은 개인 토큰으로 분리하는 것이 이상적입니다.

---

## 7. 보안 규칙

### 절대 하지 말아야 할 것

- 설정 파일(`.mcp.json`, `.cursor/mcp.json`)에 토큰을 직접 입력하지 마세요
- 토큰이 포함된 파일을 Git에 커밋하지 마세요
- 토큰을 Slack, 이메일 등으로 공유하지 마세요

### 반드시 지켜야 할 것

- 설정 파일에서는 `${ENV_VAR}` 구문만 사용하세요
- `.env` 파일을 사용하는 경우 반드시 `.gitignore`에 추가하세요
- 토큰은 쉘 프로필(`~/.zshrc`)에만 저장하세요

### 토큰 갱신

- **GitHub PAT**: 만료 기간을 설정한 경우, 만료 전에 새 토큰을 생성하고 `~/.zshrc`의 값을 교체하세요
- **Atlassian API Token**: 보안 정책에 따라 주기적으로(예: 90일) 갱신을 권장합니다

### .gitignore 확인

프로젝트의 `.gitignore`에 다음이 포함되어 있는지 확인하세요:

```
.env
.env.local
.env.*.local
```

---

## 8. 트러블슈팅

### 자주 발생하는 문제

| 증상 | 원인 | 해결 방법 |
|------|------|-----------|
| MCP 서버가 `disconnected` 표시 | 환경 변수 미설정 | `echo $GITHUB_PERSONAL_ACCESS_TOKEN`으로 확인 후 `~/.zshrc` 수정 |
| `npx` 명령 실패 | Node.js 미설치 | `node --version` 확인, 없으면 Node.js 설치 |
| GitHub 서버 권한 오류 | PAT 권한 부족 | GitHub에서 토큰 권한에 `repo`, `read:org` 추가 |
| Atlassian 인증 실패 | URL 형식 오류 | `ATLASSIAN_URL`이 `https://xxx.atlassian.net` 형식인지 확인 |
| 터미널 재시작 후 동작 안 함 | 환경 변수 미적용 | `source ~/.zshrc` 실행 또는 새 터미널 열기 |
| Cursor에서 서버 안 보임 | 설정 파일 위치 오류 | `.cursor/mcp.json`이 프로젝트 루트에 있는지 확인 |

### MCP 연결 테스트

**Cursor에서:**
1. Settings > MCP에서 서버 상태 확인
2. AI 채팅에서 "List my GitHub repositories" 같은 명령 시도

**Claude Code에서:**
1. `/mcp` 명령으로 서버 목록 및 상태 확인
2. GitHub 관련 질문을 하여 MCP 도구가 호출되는지 확인

---

## MCP 서버 패키지 요약

| 서비스 | 패키지 | 환경 변수 |
|--------|--------|-----------|
| GitHub | `@modelcontextprotocol/server-github` | `GITHUB_PERSONAL_ACCESS_TOKEN` |
| Jira + Confluence | `@xuandev/atlassian-mcp` | `ATLASSIAN_URL`, `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN` |
