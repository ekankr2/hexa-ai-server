# Plan: MBTI 관계 솔루션 서비스 (Phase 1 MVP)

## 아키텍처 개요

핵사고날 아키텍처 (Hexagonal Architecture) - 4 레이어

```
app/
├── user/                       # 사용자 도메인
│   └── domain/                # User 엔티티 (id, email, mbti, gender)
│
├── auth/                       # 인증 도메인 (OAuth 전용)
│   └── domain/                # OAuthIdentity (provider, provider_user_id, email)
│
├── consult/                    # 상담 도메인
│   ├── domain/                 # 비즈니스 로직 (엔티티, 값 객체)
│   ├── application/            # 유스케이스 레이어
│   │   ├── port/              # 포트 인터페이스 (의존성 역전)
│   │   └── use_case/          # 비즈니스 흐름 (유스케이스)
│   ├── infrastructure/         # Secondary Adapter (Outbound)
│   │   ├── repository/        # DB 구현체
│   │   └── service/           # 외부 API 구현체 (OpenAI 등)
│   └── adapter/               # Primary Adapter (Inbound)
│       └── input/web/         # 웹 컨트롤러 (FastAPI)
│           ├── request/       # 요청 DTO
│           └── response/      # 응답 DTO
│
├── converter/                  # 변환기 도메인 (동일 구조)
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── adapter/
│
└── shared/                     # 공통 값 객체
    └── vo/                    # MBTI, Gender VO
```

**핵사고날 의존성 흐름**:
```
Adapter (Web) → Application (UseCase) → Domain ← Infrastructure (DB, API)
   [Inbound]        [Port]              [Core]      [Outbound]
```

---

## 설계 원칙 (Anti Over-Engineering)

> **YAGNI + KISS 우선**

### ❌ 하지 말 것
- **추상 포트가 구현체 1개일 때**: `OAuthProviderPort` → `GoogleOAuthProvider` 같은 불필요한 추상화
- **복잡한 DI 셋업**: `register_provider()`, `set_use_case()` 같은 초기화 함수
- **파라미터 릴레이**: 설정값을 계속 전달하는 대신 필요한 곳에서 직접 읽기

### ✅ 해야 할 것
- **Service 직접 사용**: `GoogleOAuthService`처럼 구체적인 서비스 클래스
- **Router에서 직접 인스턴스화**: 필요한 곳에서 바로 생성
- **설정은 config에서**: `get_settings()`로 필요할 때 읽기 (os.getenv 금지)
- **추상화는 구현체가 2개 이상일 때만**: 실제 교체 가능성이 있을 때

### 참고 패턴
```python
# Router에서 직접 생성
service = GoogleOAuthService()

# Service는 config에서 읽기
from config.settings import get_settings
settings = get_settings()
client_id = settings.GOOGLE_CLIENT_ID
```

---

## Backlog

> **개발 전략**: Walking Skeleton + 수직 슬라이스 (Vertical Slice)
> - 기초 빌딩 블록 먼저 구현 (의존성 높고 간단한 값 객체)
> - 이후 기능별로 도메인→유스케이스→API 완전히 구현
> - 각 Phase마다 작동하는 기능 완성

### Phase 0: 기초 빌딩 블록 (Shared Domain + Auth)

#### Shared Domain (공통 값 객체)

- [x] `HAIS-1` [Shared] MBTI 값 객체 생성 - "INTJ" 형식의 유효한 4글자 조합만 허용
- [x] `HAIS-2` [Shared] MBTI 유효성 검증 - "XXXX", "INXX" 등 유효하지 않은 값 거부
- [x] `HAIS-3` [Shared] MBTI 차원별 조회 - `get_dimension(index)` 메서드로 E/I, S/N, T/F, J/P 개별 접근
- [x] `HAIS-4` [Shared] Gender 값 객체 - MALE/FEMALE 생성 및 유효성 검증
- [x] `HAIS-5` [Shared] UserProfile 값 객체 - Gender + MBTI 조합, 필수값 검증

#### User Domain (사용자 정보)

- [x] `HAIS-6` [User] User 도메인 - id, email (핵심 유저 정보)

#### Auth Domain (인증 시스템 🔐)

> **중요**: 모든 AI 세션은 로그인 필수. 대화 내용은 user_id와 연결하여 저장.
> Auth 도메인은 순수 OAuth 인증만 담당, User 도메인과 분리됨.

- [x] `HAIS-7` [Auth] UserIdentity 도메인 - OAuth 연결 (여러 provider 지원)

#### Refactoring (도메인 구조 개선 - YAGNI 적용)

- [x] `HAIS-8` [Refactor] User 도메인 이동 및 확장
  - auth/domain/user.py → user/domain/user.py 이동
  - mbti: Optional[MBTI], gender: Optional[Gender] 추가
  - UserProfile 삭제 (YAGNI - 불필요한 추상화 제거)

- [x] `HAIS-9` [Refactor] OAuthIdentity 분리
  - UserIdentity → OAuthIdentity 리네임
  - user_id 제거 (auth는 user를 모름)
  - email 추가 (OAuth provider에서 받은 이메일)
  - 순수 OAuth 정보만 담당

- [x] `HAIS-10` [Auth] Google OAuth 로그인 + Redis 세션
  - GoogleOAuthService: Google API 연동 (인증 URL, 토큰 교환, 프로필 조회)
  - RedisSessionRepository: 세션 저장/조회/삭제 (TTL 지원)
  - google_oauth_router: /auth/google, /auth/google/callback, /auth/status, /auth/logout
  - auth_dependency: 세션 검증, user_id 주입

### Phase 1: 병렬 개발 - Consult + Converter (동시 진행 가능 🔥)

> **팀 구성 제안**:
> - **Team Consult** (4명, 페어 2팀): HAIS-11~16 담당
> - **Team Converter** (2명, 페어 1팀): HAIS-17~19 담당
> - Phase 0 완료 후 두 팀이 동시에 작업 시작 가능!
> - **각 항목은 2-3시간 단위**로 작게 쪼개져 있어 관리 용이

#### Team Consult: 상담 기능 (Thin Slice 방식 🎯)

- [x] `HAIS-11` [Consult] 상담 세션 생성 **🔐 인증 필수**
  - **📖 유저 스토리**: "로그인한 사용자로서, 상담 세션을 시작하고 싶다"
  - **Domain**: `ConsultSession` (id, user_id, profile, created_at)
  - **Repository**: `ConsultRepositoryPort` + In-Memory 구현
  - **API**: `POST /consult/start` (Header: Authorization) → `{"session_id": "uuid"}`
  - **✅ 인수 조건**: UUID 세션 생성, user_id 연결, 세션 검증, 프로필 저장, curl 테스트 가능

- [x] `HAIS-11-DB` [Consult] 상담 세션 DB 마이그레이션 **[STRUCTURAL]**
  - **📖 목적**: In-Memory 구현체를 실제 DB로 교체 (영속성 확보)
  - **작업 내용**:
    - `ConsultRepositoryPort` 구현체를 In-Memory → DB(PostgreSQL/MySQL/기타)로 교체
    - DB 테이블 스키마 설계 및 마이그레이션 스크립트 작성
    - 기존 테스트는 **모두 통과**해야 함 (동작 변경 없음)
    - 테스트용 Fake Repository는 유지 (통합 테스트에서 활용)
  - **✅ 인수 조건**:
    - 모든 기존 API 테스트 통과
    - 세션 재시작 후에도 데이터 유지 (영속성 검증)
    - DB 연결 실패 시 적절한 에러 핸들링
  - **⚠️ 주의**: 이 작업은 Structural Change이므로 별도 커밋으로 분리

- [x] `HAIS-12` [Consult] AI 인사 메시지 추가
  - **📖 유저 스토리**: "사용자로서, 세션을 시작하면 내 MBTI에 맞는 AI 인사말을 받고 싶다"
  - **Port**: `AICounselorPort` 인터페이스 정의 (generate_greeting 메서드)
  - **Adapter 구현**:
    - `FakeAICounselor`: 테스트용 구현체 (고정 인사말)
    - `OpenAICounselorAdapter`: 프로덕션 구현체 (OpenAI API 연동)
      - MBTI 4차원 특성 프롬프트 (E/I, S/N, T/F, J/P)
      - 차원별 톤 가이드라인 (활발함/차분함, 구체적/추상적, 논리적/감정적, 체계적/유연함)
      - gpt-4o-mini 모델 사용
  - **UseCase**: `StartConsultUseCase` 확장 (ai_counselor 주입)
  - **API 확장**: 응답에 `greeting` 필드 추가
  - **테스트 스크립트**: OpenAI API 실제 테스트 스크립트 작성
  - **✅ 인수 조건**: AI 인사말 포함, MBTI 4차원 특성 반영, OpenAI API 연동 성공

- [x] `HAIS-13` [Consult] 메시지 전송 기본 **🔐 인증 필수**
  - **📖 유저 스토리**: "로그인한 사용자로서, 질문을 보내고 AI의 답변을 받고 싶다"
  - **Domain 확장**: `Message` 도메인 (role, content, timestamp)
  - **Domain 확장**: `ConsultSession.add_message()`, `get_messages()`
  - **Port 확장**: `AICounselorPort.generate_response()` 추가
  - **UseCase**: `SendMessageUseCase` 생성 (세션 소유자 검증 포함)
  - **API**: `POST /consult/{session_id}/message` (Header: Authorization) → 일반 JSON 응답
  - **✅ 인수 조건**: 메시지 저장, user_id 검증 (세션 소유자만 접근), AI 응답 생성, 대화 히스토리 조회 가능

- [x] `HAIS-14` [Consult] SSE 스트리밍 추가
  - **📖 유저 스토리**: "사용자로서, AI 응답이 한 글자씩 실시간으로 나타나길 원한다"
  - **Adapter 확장**: OpenAI 스트리밍 모드
  - **API 확장**: SSE (Server-Sent Events) 응답 형식
  - **✅ 인수 조건**: 스트리밍 응답, EventSource로 수신 가능

- [x] `HAIS-15` [Consult] 턴 관리 및 제한
  - **📖 유저 스토리**: "사용자로서, 5턴 대화 후 자동으로 분석 단계로 전환되길 원한다"
  - **Domain 확장**: `ConsultSession.get_user_turn_count()`, `is_completed()`
  - **UseCase 확장**: 5턴 체크, 초과 시 에러
  - **API 확장**: 응답에 `remaining_turns` 필드 추가
  - **✅ 인수 조건**: 턴 카운트 정확, 5턴 초과 시 400 에러

- [x] `HAIS-16` [Consult] 5턴 완료 시 자동 분석
  - **📖 유저 스토리**: "사용자로서, 5턴 완료 후 종료 안내와 함께 자동으로 분석 결과를 받고 싶다"
  - **Domain**: `Analysis` (situation, traits, solutions, cautions)
  - **Port 확장**: `AICounselorPort.generate_analysis()`
  - **UseCase 확장**: `SendMessageUseCase` - 5턴째 메시지 시 분석 자동 생성
  - **API 확장**: 5턴째 응답에 `is_completed: true`, `analysis` 필드 포함
  - **응답 메시지**: "무료 상담이 종료되었습니다. 프로 결제 시 추가 상담 가능합니다. 지금까지 대화를 바탕으로 분석해드릴게요!"
  - **✅ 인수 조건**: 5턴 완료 시 자동 분석, 4개 섹션 포함, 종료 안내 메시지

#### Team Converter: 변환 기능 (Thin Slice 방식 🔄)

- [x] `HAIS-17` [Converter] 메시지 변환 기본 (**Consult와 병렬 가능**) ✅
  - **📖 유저 스토리**: "사용자로서, 내 메시지를 다른 톤으로 변환하고 싶다"
  - **Domain**: `ToneMessage` (tone, content, explanation)
  - **Port**: `MessageConverterPort` 인터페이스 정의
  - **Adapter**: OpenAI 기반 변환 (1가지 톤만)
  - **API**: `POST /converter/convert` → 1가지 톤 반환
  - **✅ 인수 조건**: 톤 변환 작동, 해설 포함

- [x] `HAIS-18` [Converter] 3가지 톤 동시 생성 ✅
  - **📖 유저 스토리**: "사용자로서, 공손/캐주얼/간결 3가지 버전을 한 번에 받고 싶다"
  - **UseCase**: `ConvertMessageUseCase` - 3가지 톤 병렬 생성
  - **API 확장**: 응답에 3가지 톤 배열
  - **✅ 인수 조건**: 3가지 톤 모두 포함, 각각 해설 있음

- [x] `HAIS-19` [Converter] MBTI 맞춤 변환 ✅
  - **📖 유저 스토리**: "사용자로서, 발신자/수신자 MBTI를 고려한 최적의 표현을 원한다"
  - **UseCase 확장**: 발신자/수신자 MBTI 파라미터 추가
  - **Adapter 확장**: 프롬프트에 MBTI 특성 반영
  - **API 확장**: MBTI 검증, 400 에러 핸들링
  - **✅ 인수 조건**: MBTI 특성 반영된 변환, 잘못된 MBTI는 400

### Phase 2: 통합 테스트 (E2E)

- [ ] `HAIS-20` [E2E] 상담 전체 플로우 검증 - 시작 → 3턴 대화 → 분석 조회까지 연결
- [ ] `HAIS-21` [E2E] 변환 전체 플로우 검증 - 변환 요청 → 3가지 톤 결과 반환