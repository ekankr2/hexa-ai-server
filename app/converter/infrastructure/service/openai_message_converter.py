"""OpenAI 기반 메시지 변환 어댑터"""

import json
from openai import OpenAI

from app.converter.application.port.message_converter_port import MessageConverterPort
from app.converter.domain.tone_message import ToneMessage
from app.shared.vo.mbti import MBTI
from config.settings import get_settings


class OpenAIMessageConverter(MessageConverterPort):
    """OpenAI API를 사용한 메시지 변환 구현체"""

    def __init__(self):
        """OpenAI 클라이언트 초기화"""
        settings = get_settings()
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def convert(
        self,
        original_message: str,
        sender_mbti: MBTI,
        receiver_mbti: MBTI,
        tone: str,
    ) -> ToneMessage:
        """메시지를 특정 톤으로 변환

        Args:
            original_message: 원본 메시지
            sender_mbti: 발신자 MBTI
            receiver_mbti: 수신자 MBTI
            tone: 변환할 톤

        Returns:
            ToneMessage: 변환된 메시지
        """
        prompt = self._build_prompt(original_message, sender_mbti, receiver_mbti, tone)

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 MBTI 기반 커뮤니케이션 전문가입니다. 메시지를 지정된 톤으로 변환하고 JSON 형식으로만 응답하세요.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        # JSON 응답 파싱
        content = response.choices[0].message.content.strip()
        # markdown 코드 블록 제거
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        result = json.loads(content)

        return ToneMessage(
            tone=tone, content=result["content"], explanation=result["explanation"]
        )

    def _build_prompt(
        self, original_message: str, sender_mbti: MBTI, receiver_mbti: MBTI, tone: str
    ) -> str:
        """프롬프트 생성

        Args:
            original_message: 원본 메시지
            sender_mbti: 발신자 MBTI
            receiver_mbti: 수신자 MBTI
            tone: 변환할 톤

        Returns:
            str: 생성된 프롬프트
        """
        # MBTI 차원별 특성 추출
        receiver_characteristics = self._get_mbti_characteristics(receiver_mbti)

        # 톤별 가이드라인 정의
        tone_guidelines = self._get_tone_guidelines(tone)

        return f"""'{receiver_mbti.value}' 유형한테 보내는 메시지를 '{tone}' 스타일로 변환해.

수신자 MBTI: {receiver_mbti.value}
{receiver_characteristics}

원본: {original_message}

[{tone} 스타일]
{tone_guidelines}

★ 핵심: {receiver_mbti.value} 특성에 맞게 변환! ★
- E: 활발하고 에너지있게 / I: 차분하고 조용하게
- S: 구체적 사실 위주 / N: 가능성, 아이디어 위주
- T: 논리적, 직접적으로 / F: 감정 공감하며 부드럽게
- J: 명확하고 결론 먼저 / P: 유연하고 여유있게

규칙:
1. {receiver_mbti.value}가 좋아하는 방식으로 표현 (이게 제일 중요!)
2. 원본 톤 유지 (반말→반말, 존댓말→존댓말)
3. 카톡처럼 자연스럽게, AI티 금지

JSON:
{{
    "content": "{receiver_mbti.value}에게 맞춤 변환된 메시지",
    "explanation": "{receiver_mbti.value}는 ~해서 이렇게 표현했어 (1문장, 반말)"
}}"""

    def _get_tone_guidelines(self, tone: str) -> str:
        """톤별 변환 가이드라인을 반환

        Args:
            tone: 톤 ("공손한", "캐주얼한", "간결한")

        Returns:
            str: 톤별 구체적인 가이드라인
        """
        guidelines = {
            "공손한": """
• 원본 말투 유지! (반말→반말로 공손하게, 존댓말→존댓말로 공손하게)
• 배려있고 부드러운 표현
• 반말 예시: "혹시 이거 어려우면 도와줄까?", "시간 될 때 봐줄 수 있어?"
• 존댓말 예시: "혹시 시간 되실 때 봐주실 수 있을까요?"
            """,
            "캐주얼한": """
• 친구한테 말하듯 편하게
• 원본 말투 유지
• 반말 예시: "야 이거 봐봐", "어 그래 알겠어"
• 존댓말 예시: "아 네 알겠어요~", "그거 한번 봐주세요"
            """,
            "간결한": """
• 핵심만 짧게, 군더더기 제거
• 원본 말투 유지
• 반말 예시: "이거 확인해줘", "알겠어"
• 존댓말 예시: "확인 부탁드려요", "네 알겠습니다"
            """,
        }

        return guidelines.get(
            tone,
            "• 메시지의 의미를 유지하면서 자연스럽게 변환해주세요.",
        )

    def _get_mbti_characteristics(self, mbti: MBTI) -> str:
        """MBTI 차원별 특성을 문자열로 반환

        Args:
            mbti: MBTI 값 객체

        Returns:
            str: MBTI 차원별 특성 설명
        """
        characteristics = []

        # E/I 차원
        if mbti.energy == "E":
            characteristics.append("- 외향적 (Extrovert): 활발하고 직접적인 소통 선호")
        else:
            characteristics.append("- 내향적 (Introvert): 신중하고 깊이 있는 소통 선호")

        # S/N 차원
        if mbti.information == "S":
            characteristics.append("- 감각적 (Sensing): 구체적이고 실용적인 정보 선호")
        else:
            characteristics.append("- 직관적 (Intuition): 추상적이고 가능성 있는 아이디어 선호")

        # T/F 차원
        if mbti.decision == "T":
            characteristics.append("- 사고형 (Thinking): 논리적이고 객관적인 접근 선호")
        else:
            characteristics.append("- 감정형 (Feeling): 감정적이고 공감적인 접근 선호")

        # J/P 차원
        if mbti.lifestyle == "J":
            characteristics.append("- 판단형 (Judging): 체계적이고 계획적인 방식 선호")
        else:
            characteristics.append("- 인식형 (Perceiving): 유연하고 즉흥적인 방식 선호")

        return "\n".join(characteristics)
