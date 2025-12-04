# Plan: MBTI 관계 솔루션 서비스 (Phase 1 MVP)

## 아키텍처 개요

핵사고날 아키텍처 (Hexagonal Architecture)

```
app/
├── consult/                    # 상담 도메인
│   ├── domain/
│   ├── application/
│   └── adapter/
├── converter/                  # 변환기 도메인
│   ├── domain/
│   ├── application/
│   └── adapter/
└── shared/                     # 공통 모듈 (MBTI, Gender)
```

---

## Backlog

> **개발 전략**: Walking Skeleton + 수직 슬라이스 (Vertical Slice)
> - 기초 빌딩 블록 먼저 구현 (의존성 높고 간단한 값 객체)
> - 이후 기능별로 도메인→유스케이스→API 완전히 구현
> - 각 Phase마다 작동하는 기능 완성

### Phase 0: 기초 빌딩 블록 (Shared Domain)

- [x] `HAIS-1` [Shared] MBTI 값 객체 생성 - "INTJ" 형식의 유효한 4글자 조합만 허용
- [x] `HAIS-2` [Shared] MBTI 유효성 검증 - "XXXX", "INXX" 등 유효하지 않은 값 거부
- [ ] `HAIS-3` [Shared] MBTI 차원별 조회 - `get_dimension(index)` 메서드로 E/I, S/N, T/F, J/P 개별 접근
- [ ] `HAIS-4` [Shared] Gender 값 객체 - MALE/FEMALE 생성 및 유효성 검증
- [ ] `HAIS-5` [Shared] UserProfile 값 객체 - Gender + MBTI 조합, 필수값 검증

### Phase 1: 병렬 개발 - Consult + Converter (동시 진행 가능 🔥)

> **팀 구성 제안**:
> - **Team Consult** (4명): HAIS-6,7,8 담당
> - **Team Converter** (2명): HAIS-9 담당
> - Phase 0 완료 후 두 팀이 동시에 작업 시작 가능!

#### Team Consult: 상담 기능 (수직 슬라이스 🎯💬📊)

- [ ] `HAIS-6` [Consult] 상담 시작 기능 (2명, 1-2일)
  - **Domain**: `ConsultSession` 생성, UUID, UserProfile 저장
  - **Port**: `AICounselorPort` 인터페이스 정의 (인사 메시지 생성 메서드)
  - **Adapter**: `OpenAICounselorAdapter` 구현 (인사 메시지 생성)
  - **UseCase**: `StartConsultUseCase` - 세션 생성 + AI 인사 포함
  - **Repository**: `ConsultRepositoryPort` + In-Memory 구현
  - **API**: `POST /consult/start` - 201 응답, session_id + greeting 반환

- [ ] `HAIS-7` [Consult] 메시지 전송 기능 (2명, 1-2일, HAIS-6 완료 후)
  - **Domain 확장**:
    - `Message` 도메인 모델 추가 (role: AI/USER, content, timestamp)
    - `ConsultSession.add_message()`, `get_messages()`, `get_user_turn_count()` 메서드 추가
  - **Port 확장**: `AICounselorPort`에 대화 응답 메서드 추가 (MBTI 맞춤 응답)
  - **Adapter 확장**: OpenAI 스트리밍 응답 구현
  - **UseCase**: `SendMessageUseCase` - 메시지 저장 + AI 응답 + 턴 관리 (3턴 제한)
  - **API**: `POST /consult/{session_id}/message` - SSE 스트리밍, 남은 턴 수 반환

- [ ] `HAIS-8` [Consult] 분석 조회 기능 (2명, 1-2일, HAIS-7 완료 후)
  - **Domain**: `Analysis` 도메인 모델 (상황 분석, 유형별 특성, 해결 방안, 주의사항)
  - **Port 확장**: `AICounselorPort`에 분석 생성 메서드 추가
  - **UseCase**: `GetAnalysisUseCase` - 3턴 완료 검증, 대화 기반 분석 생성
  - **API**: `GET /consult/{session_id}/analysis` - 200 응답 (완료 시), 404 (미완료 시)

#### Team Converter: 변환 기능 (수직 슬라이스 🔄)

- [ ] `HAIS-9` [Converter] 메시지 변환 기능 (2명, 2-3일, **Consult와 병렬 진행 가능**)
  - **Domain**: `ToneMessage` 도메인 (공손/캐주얼/간결 톤 + 해설)
  - **Port**: `MessageConverterPort` 인터페이스 정의
  - **Adapter**: OpenAI 기반 톤 변환 구현
  - **UseCase**: `ConvertMessageUseCase` - 발신자/수신자 MBTI 반영, 3가지 톤 동시 생성
  - **API**: `POST /converter/convert` - MBTI/길이 검증, 200 응답

### Phase 2: 통합 테스트 (E2E)

- [ ] `HAIS-10` [E2E] 상담 전체 플로우 검증 - 시작 → 3턴 대화 → 분석 조회까지 연결
- [ ] `HAIS-11` [E2E] 변환 전체 플로우 검증 - 변환 요청 → 3가지 톤 결과 반환