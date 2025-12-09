from typing import Iterator
from openai import OpenAI

from app.consult.application.port.ai_counselor_port import AICounselorPort
from app.consult.domain.consult_session import ConsultSession
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
        messages = [
            {
                "role": "system",
                "content": "당신은 10년 경력의 MBTI 전문 상담사입니다. 따뜻하고 공감적이며, 각 MBTI 유형의 특성을 깊이 이해하고 있습니다."
            }
        ]

        # 대화 히스토리 추가
        for msg in session.get_messages():
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        return messages