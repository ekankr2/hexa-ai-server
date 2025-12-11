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

        return f"""사용자가 MBTI 관계 상담을 시작합니다.

사용자 정보:
- MBTI: {mbti.value}
- 성별: {gender.value}

이 사용자의 MBTI 특성에 맞춰 첫 인사말을 생성해주세요.

MBTI 특성 고려사항:
- E/I ({ei}): {ei_guide[ei]}
- S/N ({sn}): {sn_guide[sn]}
- T/F ({tf}): {tf_guide[tf]}
- J/P ({jp}): {jp_guide[jp]}

요구사항:
1. 2-3문장으로 간결하게
2. 사용자의 MBTI 유형을 언급하며 공감 표현
3. "어떤 관계 고민이 있으세요?" 같은 자연스러운 질문으로 마무리
4. 이모지는 최대 1-2개만 사용 (과하지 않게)
5. 반말 사용 (친근하고 편안한 분위기)

인사말을 생성해주세요:"""

    def generate_response(self, session: ConsultSession, user_message: str) -> str:
        """
        사용자 메시지에 대한 AI 응답을 생성한다.
        """
        messages = self._build_messages(session)
        messages.append({"role": "user", "content": user_message})

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
        """
        messages = self._build_messages(session)
        messages.append({"role": "user", "content": user_message})

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

상담 원칙:
1. 매번 다른 접근으로 질문하기 - 단순히 "더 자세히 말해줄래?" 같은 반복적 질문 금지
2. 사용자의 답변에서 구체적인 키워드를 찾아 깊이 파고들기
3. MBTI 특성을 활용하여 맞춤형 질문하기
4. 감정 공감과 구체적인 상황 파악을 균형있게
5. 2-3문장으로 간결하게 응답하기

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
        """턴 수에 따른 상담 전략 가이드"""
        strategies = {
            0: """[1턴 전략]
- 첫 응답이므로 사용자의 고민을 들었다는 공감 표현
- 고민의 핵심 키워드(인물, 상황, 감정)에 대해 구체적으로 물어보기
- 예: "그 친구와는 얼마나 오래 알고 지냈어?" / "그때 어떤 감정이 들었어?"
""",
            1: """[2턴 전략]
- 사용자가 말한 구체적 상황이나 감정에 대해 MBTI 관점으로 해석
- 관계의 다른 측면(상대방의 입장, 배경 등)을 탐색하는 질문
- 예: "상대방은 어떻게 반응했어?" / "비슷한 일이 전에도 있었어?"
""",
            2: """[3턴 전략]
- 문제의 패턴이나 근본 원인 파악하기
- MBTI 특성과 연결하여 왜 이런 상황이 발생했는지 통찰 제공
- 예: "{MBTI}라서 이런 부분이 힘들었을 것 같아" + 추가 질문
""",
            3: """[4턴 전략]
- 해결 방향성에 대한 사용자의 생각 물어보기
- 실제로 시도해본 방법이 있는지 확인
- 예: "이 상황을 어떻게 해결하고 싶어?" / "뭘 시도해봤어?"
""",
            4: """[5턴 전략]
- 마지막 턴이므로 핵심 조언과 함께 응답
- 구체적인 행동 제안 1-2가지 포함
- 공감과 격려로 마무리
"""
        }
        return strategies.get(turn_count, strategies[4])

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
            max_tokens=1000,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        return Analysis(
            situation=result["situation"],
            traits=result["traits"],
            solutions=result["solutions"],
            cautions=result["cautions"],
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

위 대화를 분석하여 다음 4가지 섹션으로 정리해주세요.

반드시 아래 JSON 형식으로만 응답하세요:
{{
    "situation": "상황 정리 (2-3문장으로 사용자의 관계 고민을 요약)",
    "traits": "MBTI 특성 분석 (사용자의 MBTI 특성이 이 상황에 어떻게 영향을 미치는지 설명)",
    "solutions": "관계 개선 솔루션 (구체적인 행동 조언 3가지를 번호 매겨서)",
    "cautions": "주의사항 (이 MBTI 유형이 조심해야 할 점 2가지)"
}}"""