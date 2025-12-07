# Plan: MBTI 관계 솔루션 서비스 (Phase 1 MVP)

## 아키텍처 개요

핵사고날 아키텍처 (Hexagonal Architecture) - 4 레이어

```
app/
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
├── converter/                  # 변환기 도메인 (동일 구조)
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── adapter/
└── shared/                     # 공통 모듈 (MBTI, Gender, UserProfile)
    └── domain/                # 공통 값 객체
```

**핵사고날 의존성 흐름**:
```
Adapter (Web) → Application (UseCase) → Domain ← Infrastructure (DB, API)
   [Inbound]        [Port]              [Core]      [Outbound]
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

#### Auth Domain (인증 시스템 🔐)

> **중요**: 모든 AI 세션은 로그인 필수. 대화 내용은 user_id와 연결하여 저장.

- [x] `HAIS-6` [Auth] User 도메인 - id, email (핵심 유저 정보)
- [x] `HAIS-7` [Auth] UserIdentity 도메인 - user_id, provider, provider_user_id (OAuth 연결, 여러 provider 지원)
- [ ] `HAIS-8` [Auth] UserInfo 도메인 - user_id, mbti, gender (프로필 정보)
- [ ] `HAIS-9` [Auth] Repository Port - UserRepositoryPort, UserIdentityRepositoryPort, UserInfoRepositoryPort 인터페이스 + In-Memory 구현
- [ ] `HAIS-10` [Auth] OAuth 콜백 처리 + JWT 발급 - Google/Kakao OAuth 로그인, 신규 회원 자동 생성
- [ ] `HAIS-11` [Auth] 인증 미들웨어 - JWT 검증, 요청에 user_id 주입

### Phase 1: 병렬 개발 - Consult + Converter (동시 진행 가능 🔥)

> **팀 구성 제안**:
> - **Team Consult** (4명, 페어 2팀): HAIS-12~17 담당
> - **Team Converter** (2명, 페어 1팀): HAIS-18~20 담당
> - Phase 0 완료 후 두 팀이 동시에 작업 시작 가능!
> - **각 항목은 2-3시간 단위**로 작게 쪼개져 있어 관리 용이

#### Team Consult: 상담 기능 (Thin Slice 방식 🎯)

- [ ] `HAIS-12` [Consult] 상담 세션 생성 (2-3시간) **🔐 인증 필수**
  - **📖 유저 스토리**: "로그인한 사용자로서, 상담 세션을 시작하고 싶다"
  - **Domain**: `ConsultSession` (id, user_id, profile, created_at)
  - **Repository**: `ConsultRepositoryPort` + In-Memory 구현
  - **API**: `POST /consult/start` (Header: Authorization) → `{"session_id": "uuid"}`
  - **✅ 인수 조건**: UUID 세션 생성, user_id 연결, JWT 검증, 프로필 저장, curl 테스트 가능

- [ ] `HAIS-13` [Consult] AI 인사 메시지 추가 (2시간)
  - **📖 유저 스토리**: "사용자로서, 세션을 시작하면 내 MBTI에 맞는 AI 인사말을 받고 싶다"
  - **Port**: `AICounselorPort` 인터페이스 정의 (generate_greeting 메서드)
  - **Adapter**: `OpenAICounselorAdapter` 구현 (OpenAI API 연동)
  - **UseCase**: `StartConsultUseCase` 생성
  - **API 확장**: 응답에 `greeting` 필드 추가
  - **✅ 인수 조건**: AI 인사말 포함, MBTI 특성 반영

- [ ] `HAIS-14` [Consult] 메시지 전송 기본 (3시간) **🔐 인증 필수**
  - **📖 유저 스토리**: "로그인한 사용자로서, 질문을 보내고 AI의 답변을 받고 싶다"
  - **Domain 확장**: `Message` 도메인 (role, content, timestamp)
  - **Domain 확장**: `ConsultSession.add_message()`, `get_messages()`
  - **Port 확장**: `AICounselorPort.generate_response()` 추가
  - **UseCase**: `SendMessageUseCase` 생성 (세션 소유자 검증 포함)
  - **API**: `POST /consult/{session_id}/message` (Header: Authorization) → 일반 JSON 응답
  - **✅ 인수 조건**: 메시지 저장, user_id 검증 (세션 소유자만 접근), AI 응답 생성, 대화 히스토리 조회 가능

- [ ] `HAIS-15` [Consult] SSE 스트리밍 추가 (1-2시간)
  - **📖 유저 스토리**: "사용자로서, AI 응답이 한 글자씩 실시간으로 나타나길 원한다"
  - **Adapter 확장**: OpenAI 스트리밍 모드
  - **API 확장**: SSE (Server-Sent Events) 응답 형식
  - **✅ 인수 조건**: 스트리밍 응답, EventSource로 수신 가능

- [ ] `HAIS-16` [Consult] 턴 관리 및 제한 (1-2시간)
  - **📖 유저 스토리**: "사용자로서, 3턴 대화 후 자동으로 분석 단계로 전환되길 원한다"
  - **Domain 확장**: `ConsultSession.get_user_turn_count()`, `is_completed()`
  - **UseCase 확장**: 3턴 체크, 초과 시 에러
  - **API 확장**: 응답에 `remaining_turns` 필드 추가
  - **✅ 인수 조건**: 턴 카운트 정확, 3턴 초과 시 400 에러

- [ ] `HAIS-17` [Consult] 분석 결과 생성 (3시간)
  - **📖 유저 스토리**: "사용자로서, 3턴 완료 후 MBTI 기반 관계 분석을 받고 싶다"
  - **Domain**: `Analysis` (situation, traits, solutions, cautions)
  - **Port 확장**: `AICounselorPort.generate_analysis()`
  - **UseCase**: `GetAnalysisUseCase` 생성
  - **API**: `GET /consult/{session_id}/analysis` → 200 (완료) / 404 (미완료)
  - **✅ 인수 조건**: 3턴 완료 검증, 4개 섹션 포함, 대화 기반 분석

#### Team Converter: 변환 기능 (Thin Slice 방식 🔄)

- [ ] `HAIS-18` [Converter] 메시지 변환 기본 (2시간, **Consult와 병렬 가능**)
  - **📖 유저 스토리**: "사용자로서, 내 메시지를 다른 톤으로 변환하고 싶다"
  - **Domain**: `ToneMessage` (tone, content, explanation)
  - **Port**: `MessageConverterPort` 인터페이스 정의
  - **Adapter**: OpenAI 기반 변환 (1가지 톤만)
  - **API**: `POST /converter/convert` → 1가지 톤 반환
  - **✅ 인수 조건**: 톤 변환 작동, 해설 포함

- [ ] `HAIS-19` [Converter] 3가지 톤 동시 생성 (2시간)
  - **📖 유저 스토리**: "사용자로서, 공손/캐주얼/간결 3가지 버전을 한 번에 받고 싶다"
  - **UseCase**: `ConvertMessageUseCase` - 3가지 톤 병렬 생성
  - **API 확장**: 응답에 3가지 톤 배열
  - **✅ 인수 조건**: 3가지 톤 모두 포함, 각각 해설 있음

- [ ] `HAIS-20` [Converter] MBTI 맞춤 변환 (2시간)
  - **📖 유저 스토리**: "사용자로서, 발신자/수신자 MBTI를 고려한 최적의 표현을 원한다"
  - **UseCase 확장**: 발신자/수신자 MBTI 파라미터 추가
  - **Adapter 확장**: 프롬프트에 MBTI 특성 반영
  - **API 확장**: MBTI 검증, 400 에러 핸들링
  - **✅ 인수 조건**: MBTI 특성 반영된 변환, 잘못된 MBTI는 400

### Phase 2: 통합 테스트 (E2E)

- [ ] `HAIS-21` [E2E] 상담 전체 플로우 검증 - 시작 → 3턴 대화 → 분석 조회까지 연결
- [ ] `HAIS-22` [E2E] 변환 전체 플로우 검증 - 변환 요청 → 3가지 톤 결과 반환