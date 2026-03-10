# Bookshelf API

온라인 서재 관리 REST API를 구현해주세요.

## 핵심 기능
1. 사용자 인증 (회원가입, 로그인, JWT 토큰)
2. 책 CRUD (등록, 조회, 수정, 삭제)
3. 서재(Bookshelf) 관리 (생성, 조회, 책 추가/제거)
4. 검색 및 필터링 (제목, 저자, 장르별)
5. 페이지네이션 (offset/limit)
6. 권한 관리 (본인 서재만 수정 가능)

## 기술 요구사항
- Python 3.11+, FastAPI, SQLite (aiosqlite)
- Pydantic v2 모델, 비동기 처리
- JWT 인증 (PyJWT)
- 비밀번호 해싱 (bcrypt)

## 비기능 요구사항
- 적절한 HTTP 상태 코드
- 입력 유효성 검사
- 에러 응답 일관성 ({"detail": "message"} 형식)
