import json
from typing import Iterator
from openai import OpenAI

from app.consult.application.port.ai_counselor_port import AICounselorPort
from app.consult.domain.consult_session import ConsultSession
from app.consult.domain.analysis import Analysis
from app.shared.vo.mbti import MBTI
from app.shared.vo.gender import Gender


class OpenAICounselorAdapter(AICounselorPort):
    """OpenAI API를 사용하는 AI 상담사 구현체"""

    def __init__(self, api_key: str):
        self._client = OpenAI(api_key=api_key)

    def generate_greeting(self, mbti: MBTI, gender: Gender) -> str:
        """
        사용자의 MBTI와 성별에 맞는 인사말을 생성한다.

        MBTI 특성을 반영하여:
        - E/I: 외향적/내향적 톤 조절
        - S/N: 구체적/추상적 표현 선택
        - T/F: 논리적/감정적 접근
        - J/P: 체계적/유연한 대화 방식
        """
        prompt = self._build_greeting_prompt(mbti, gender)

        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 10년 경력의 MBTI 전문 상담사입니다. 따뜻하고 공감적이며, 각 MBTI 유형의 특성을 깊이 이해하고 있습니다."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=200
        )

        return response.choices[0].message.content.strip()

    def _build_greeting_prompt(self, mbti: MBTI, gender: Gender) -> str:
        """MBTI 특성을 반영한 인사말 생성 프롬프트"""

        # MBTI 차원별 특성 분석
        ei = mbti.energy        # E 또는 I
        sn = mbti.information   # S 또는 N
        tf = mbti.decision      # T 또는 F
        jp = mbti.lifestyle     # J 또는 P

        # 차원별 가이드라인
        ei_guide = {
            "E": "활발하고 친근하게, 에너지 넘치는 톤으로",
            "I": "차분하고 부드럽게, 편안한 분위기를 만드는 톤으로"
        }

        sn_guide = {
            "S": "구체적이고 실용적인 표현을 사용하여",
            "N": "개방적이고 가능성에 초점을 맞춘 표현을 사용하여"
        }

        tf_guide = {
            "T": "논리적이고 명확하게, 문제 해결 지향적으로",
            "F": "공감적이고 따뜻하게, 감정을 이해하는 태도로"
        }

        jp_guide = {
            "J": "체계적이고 목표 지향적인 대화를 시작하며",
            "P": "유연하고 탐색적인 대화를 시작하며"
        }

        return f"""사용자가 MBTI 관계 상담을 시작해.

사용자 정보:
- MBTI: {mbti.value}
- 성별: {gender.value}

첫 인사말을 생성해줘.

MBTI 특성 고려사항 (톤 조절용, 내용에 직접 언급하지 마):
- E/I ({ei}): {ei_guide[ei]}
- S/N ({sn}): {sn_guide[sn]}
- T/F ({tf}): {tf_guide[tf]}
- J/P ({jp}): {jp_guide[jp]}

요구사항:
1. 2-3문장으로 자연스럽게
2. MBTI 특성 칭찬 금지 (어색함)
3. 관계 고민 + 상대방 MBTI를 함께 물어보기
4. 이모지 사용 금지
5. 반말만 사용 (친구처럼 편하게)

좋은 예시:
- "안녕! 나는 MBTI 전문 상담사야. 무슨 관계 고민이 있어? 고민 상대의 MBTI도 알면 말해줘!"
- "반가워! 오늘 어떤 관계 이야기야? 상대방 MBTI 알아?"

나쁜 예시 (금지):
- "INTJ인 너의 논리적인 사고방식이 멋져!" (과한 칭찬, 어색함)
- "무슨 고민이야?" (상대방 MBTI 안 물어봄)

인사말:"""

    def generate_response(self, session: ConsultSession, user_message: str) -> str:
        """
        사용자 메시지에 대한 AI 응답을 생성한다.
        주의: session에 이미 user_message가 추가된 상태로 호출되어야 함
        """
        messages = self._build_messages(session)
        # session.get_messages()에 이미 user_message가 포함되어 있으므로 추가하지 않음

        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        return response.choices[0].message.content.strip()

    def generate_response_stream(self, session: ConsultSession, user_message: str) -> Iterator[str]:
        """
        사용자 메시지에 대한 AI 응답을 스트리밍 방식으로 생성한다.
        주의: session에 이미 user_message가 추가된 상태로 호출되어야 함
        """
        messages = self._build_messages(session)
        # session.get_messages()에 이미 user_message가 포함되어 있으므로 추가하지 않음

        stream = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    def _build_messages(self, session: ConsultSession) -> list[dict]:
        """대화 히스토리를 기반으로 OpenAI 메시지 형식을 생성한다"""
        turn_count = session.get_user_turn_count()

        # 턴 수에 따른 상담 전략
        strategy_guide = self._get_strategy_by_turn(turn_count)

        messages = [
            {
                "role": "system",
                "content": f"""당신은 10년 경력의 MBTI 전문 상담사입니다. 따뜻하고 공감적이며, 각 MBTI 유형의 특성을 깊이 이해하고 있습니다.

사용자 정보:
- MBTI: {session.mbti.value}
- 성별: {session.gender.value}

⚠️ 현재 {turn_count}턴 / 총 5턴 ({"마지막 턴 - 반드시 마무리만!" if turn_count >= 5 else f"남은 턴: {5 - turn_count}"})

상담 원칙:
1. 매번 다른 접근으로 질문하기 - 단순히 "더 자세히 말해줄래?" 같은 반복적 질문 금지
2. 사용자의 답변에서 구체적인 키워드를 찾아 깊이 파고들기
3. MBTI 특성을 활용하여 맞춤형 질문하기
4. 감정 공감과 구체적인 상황 파악을 균형있게
5. 2-3문장으로 간결하게 응답하기
6. 반말만 사용 (존댓말 금지)

{strategy_guide}

금지사항:
- "더 자세히 말해줄 수 있어?" 같은 일반적인 질문 반복
- 이전 턴과 동일한 질문 패턴 사용
- 너무 긴 응답 (2-3문장 준수)
"""
            }
        ]

        # 대화 히스토리 추가
        for msg in session.get_messages():
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        return messages

    def _get_strategy_by_turn(self, turn_count: int) -> str:
        """턴 수에 따른 상담 전략 가이드 (turn_count는 1부터 시작)"""
        strategies = {
            1: """[1턴 - 상황 & 상대방 파악]
🎯 목표: 고민의 핵심 인물, 관계, 상대방 MBTI 파악
📌 반드시 물어볼 것:
1. 관계 파악: "그 사람이랑은 어떤 관계야?"
2. 상대방 MBTI: "혹시 그 사람 MBTI 알아?"

💡 두 가지를 자연스럽게 한 번에 물어봐:
예시: "그 사람이랑 어떤 관계야? 혹시 그 사람 MBTI도 알아?"

❌ 금지: MBTI 모르면 넘어가지 말고, 성격이라도 물어봐
✅ 필수: 관계 유형 + 상대방 MBTI(또는 성격) 파악
""",
            2: """[2턴 - 상대방 탐색]
🎯 목표: 상대방의 행동/성격/반응 파악
📌 반드시 물어볼 것 (택1):
- "그 사람은 평소에 어떤 성격이야?"
- "그때 상대방 반응은 어땠어?"
- "상대방 입장에서는 왜 그랬을 것 같아?"
- "그 사람의 MBTI는 알아? 모르면 성격이라도?"

❌ 금지: 사용자 감정만 계속 묻기
✅ 필수: 상대방에 대한 정보 수집
""",
            3: """[3턴 - 패턴 분석]
🎯 목표: 반복되는 문제 패턴 발견
📌 반드시 물어볼 것 (택1):
- "비슷한 상황이 전에도 있었어?"
- "다른 사람들이랑도 이런 문제가 있어?"
- "이 문제가 생기면 보통 어떻게 대처해왔어?"
- "너는 이런 상황에서 주로 어떻게 행동하는 편이야?"

❌ 금지: 이미 들은 내용 다시 묻기
✅ 필수: 과거 경험이나 행동 패턴 탐색
""",
            4: """[4턴 - 욕구 파악]
🎯 목표: 사용자가 진짜 원하는 것 파악
📌 반드시 물어볼 것 (택1):
- "이 관계에서 가장 바라는 게 뭐야?"
- "이 상황이 어떻게 되면 좋겠어?"
- "상대방한테 가장 듣고 싶은 말이 뭐야?"
- "이 문제가 해결되면 뭐가 달라질 것 같아?"

❌ 금지: 해결책 바로 제시
✅ 필수: 사용자의 니즈/욕구 명확히 하기
""",
            5: """[5턴 - 마무리]
🎯 목표: 상담 마무리 및 프리미엄 안내
📌 필수 포함 내용:
1. 짧은 마무리 인사 (1문장: "오늘 상담은 여기까지야!")
2. 프리미엄 안내 (1문장: "더 깊은 상담을 원하면 프리미엄을 이용해봐!")
3. 분석 결과 안내 (1문장: "아래 분석 결과를 확인해봐")

❌ 절대 금지:
- 추가 질문하기
- 구체적인 조언이나 인사이트 제공 (분석 결과에서 제공됨)
- 대화 요약하기 (분석 결과에서 제공됨)

✅ 필수: 3문장 이내로 간결하게 마무리만
"""
        }
        return strategies.get(turn_count, strategies[5])

    def generate_analysis(self, session: ConsultSession) -> Analysis:
        """
        상담 세션을 기반으로 MBTI 관계 분석을 생성한다.
        """
        prompt = self._build_analysis_prompt(session)

        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 10년 경력의 MBTI 전문 상담사입니다. 대화 내용을 분석하여 MBTI 기반 관계 조언을 제공합니다. 반드시 JSON 형식으로만 응답하세요."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # OpenAI가 list로 반환할 경우 string으로 변환
        def to_string(value):
            if isinstance(value, list):
                return "\n".join(f"{i+1}. {item}" for i, item in enumerate(value))
            return value

        return Analysis(
            situation=to_string(result["situation"]),
            traits=to_string(result["traits"]),
            solutions=to_string(result["solutions"]),
            cautions=to_string(result["cautions"]),
            compatibility=to_string(result.get("compatibility", "")),
            scripts=to_string(result.get("scripts", "")),
        )

    def _build_analysis_prompt(self, session: ConsultSession) -> str:
        """분석을 위한 프롬프트 생성"""
        conversation = "\n".join([
            f"{'사용자' if msg.role == 'user' else 'AI'}: {msg.content}"
            for msg in session.get_messages()
        ])

        return f"""다음은 MBTI 관계 상담 대화입니다.

사용자 정보:
- MBTI: {session.mbti.value}
- 성별: {session.gender.value}

대화 내용:
{conversation}

위 대화를 깊이 있게 분석하여 6가지 섹션으로 정리해줘.

중요 원칙:
- 반말만 사용해 (존댓말 절대 금지, 친구처럼 편하게)
- 대화 내용을 구체적으로 인용하면서 분석해
- 일반적인 MBTI 설명이 아닌, 이 사용자의 상황에 맞춘 맞춤형 분석을 해
- 대화에서 상대방 MBTI가 언급되었다면 반드시 compatibility 섹션을 채워줘

반드시 아래 JSON 형식으로만 응답해:
{{
    "situation": "상황 정리 (3-4문장으로 사용자의 관계 고민을 구체적으로 요약. 대화에서 나온 핵심 내용을 포함해서 '네가 ~라고 했잖아' 같은 식으로)",
    "traits": "MBTI 특성 분석 (4-5문장으로 {session.mbti.value} 유형의 특성이 이 상황에서 어떻게 작용하는지 구체적으로 설명. 장점과 주의할 점 모두 언급)",
    "compatibility": "MBTI 궁합 분석 (대화에서 상대방 MBTI가 언급된 경우: {session.mbti.value}와 상대방 MBTI의 궁합을 3-4문장으로 분석. 잘 맞는 점, 충돌하기 쉬운 점, 이 관계에서 특히 주의할 점. 상대방 MBTI 모르면 빈 문자열)",
    "solutions": "관계 개선 솔루션 (구체적이고 실천 가능한 행동 조언 3가지. 각 조언은 2문장 이상으로 '이렇게 해봐', '~하는 게 좋겠어' 같은 친근한 톤으로)",
    "scripts": "대화 스크립트 (이 상황에서 상대방에게 실제로 할 수 있는 말 3가지. 각각 따옴표로 감싸서 실제 대화처럼. 예: '나 요즘 네가 연락 안 하면 좀 서운해. 바쁜 건 알지만...')",
    "cautions": "주의사항 ({session.mbti.value} 유형이 이 상황에서 특히 조심해야 할 점 2가지. 각 항목은 2문장 이상으로 구체적인 상황 예시와 함께)"
}}"""