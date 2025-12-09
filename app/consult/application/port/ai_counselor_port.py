from abc import ABC, abstractmethod
from typing import Iterator

from app.shared.vo.mbti import MBTI
from app.shared.vo.gender import Gender
from app.consult.domain.consult_session import ConsultSession


class AICounselorPort(ABC):
    """AI 상담사 포트 인터페이스"""

    @abstractmethod
    def generate_greeting(self, mbti: MBTI, gender: Gender) -> str:
        """
        사용자의 MBTI와 성별에 맞는 인사말을 생성한다.

        Args:
            mbti: 사용자의 MBTI
            gender: 사용자의 성별

        Returns:
            AI가 생성한 인사말
        """
        pass

    @abstractmethod
    def generate_response(self, session: ConsultSession, user_message: str) -> str:
        """
        사용자 메시지에 대한 AI 응답을 생성한다.

        Args:
            session: 상담 세션 (MBTI, Gender, 대화 히스토리 포함)
            user_message: 사용자가 보낸 메시지

        Returns:
            AI 응답 메시지
        """
        pass

    @abstractmethod
    def generate_response_stream(self, session: ConsultSession, user_message: str) -> Iterator[str]:
        """
        사용자 메시지에 대한 AI 응답을 스트리밍 방식으로 생성한다.

        Args:
            session: 상담 세션 (MBTI, Gender, 대화 히스토리 포함)
            user_message: 사용자가 보낸 메시지

        Returns:
            AI 응답 메시지 스트림 (Iterator)
        """
        pass