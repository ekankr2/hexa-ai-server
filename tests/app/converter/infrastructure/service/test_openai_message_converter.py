"""OpenAIMessageConverter 어댑터 테스트"""

import pytest
from unittest.mock import Mock, patch

from app.converter.application.port.message_converter_port import MessageConverterPort
from app.converter.domain.tone_message import ToneMessage
from app.shared.vo.mbti import MBTI


class TestOpenAIMessageConverter:
    """OpenAIMessageConverter 어댑터 테스트"""

    def test_should_implement_message_converter_port(self):
        """MessageConverterPort 인터페이스를 구현해야 함"""
        # Given
        from app.converter.infrastructure.service.openai_message_converter import (
            OpenAIMessageConverter,
        )

        # Then
        assert issubclass(OpenAIMessageConverter, MessageConverterPort)

    @patch("app.converter.infrastructure.service.openai_message_converter.OpenAI")
    def test_should_convert_message_with_tone(self, mock_openai_class):
        """특정 톤으로 메시지를 변환해야 함"""
        # Given
        from app.converter.infrastructure.service.openai_message_converter import (
            OpenAIMessageConverter,
        )

        # OpenAI API 응답 모킹
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content='{"content": "안녕하세요, 내일 회의 시간을 조정해주실 수 있을까요?", "explanation": "ESTP 유형에게는 직설적이면서도 존중하는 표현이 효과적입니다."}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        converter = OpenAIMessageConverter()

        # When
        result = converter.convert(
            original_message="내일 회의 시간 바꿀 수 있어?",
            sender_mbti=MBTI("INTJ"),
            receiver_mbti=MBTI("ESTP"),
            tone="공손한",
        )

        # Then
        assert isinstance(result, ToneMessage)
        assert result.tone == "공손한"
        assert result.content == "안녕하세요, 내일 회의 시간을 조정해주실 수 있을까요?"
        assert "ESTP" in result.explanation
        assert mock_client.chat.completions.create.called

    @patch("app.converter.infrastructure.service.openai_message_converter.OpenAI")
    def test_should_include_mbti_context_in_prompt(self, mock_openai_class):
        """프롬프트에 MBTI 정보를 포함해야 함"""
        # Given
        from app.converter.infrastructure.service.openai_message_converter import (
            OpenAIMessageConverter,
        )

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content='{"content": "변환된 메시지", "explanation": "설명"}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        converter = OpenAIMessageConverter()

        # When
        converter.convert(
            original_message="안녕",
            sender_mbti=MBTI("INTJ"),
            receiver_mbti=MBTI("ESTP"),
            tone="공손한",
        )

        # Then
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        prompt_text = str(messages)

        assert "INTJ" in prompt_text
        assert "ESTP" in prompt_text
        assert "공손한" in prompt_text

    @patch("app.converter.infrastructure.service.openai_message_converter.OpenAI")
    def test_should_include_mbti_dimension_characteristics_in_prompt(self, mock_openai_class):
        """프롬프트에 MBTI 차원별 특성을 포함해야 함 (HAIS-19)"""
        # Given
        from app.converter.infrastructure.service.openai_message_converter import (
            OpenAIMessageConverter,
        )

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content='{"content": "변환된 메시지", "explanation": "ESTP는 외향적이고 감각적이므로 직접적인 표현이 효과적입니다."}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        converter = OpenAIMessageConverter()

        # When
        converter.convert(
            original_message="안녕",
            sender_mbti=MBTI("INTJ"),
            receiver_mbti=MBTI("ESTP"),
            tone="공손한",
        )

        # Then
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        prompt_text = str(messages)

        # MBTI 4차원 특성이 프롬프트에 포함되어야 함
        # E/I, S/N, T/F, J/P 중 일부가 포함되어야 함
        has_ei_dimension = any(keyword in prompt_text for keyword in ["외향", "내향", "Extrovert", "Introvert"])
        has_sn_dimension = any(keyword in prompt_text for keyword in ["감각", "직관", "Sensing", "Intuition"])
        has_tf_dimension = any(keyword in prompt_text for keyword in ["사고", "감정", "Thinking", "Feeling"])
        has_jp_dimension = any(keyword in prompt_text for keyword in ["판단", "인식", "Judging", "Perceiving"])

        # 최소 2개 이상의 차원 특성이 언급되어야 함
        dimension_count = sum([has_ei_dimension, has_sn_dimension, has_tf_dimension, has_jp_dimension])
        assert dimension_count >= 2, f"프롬프트에 MBTI 차원 특성이 충분히 포함되지 않았습니다. 포함된 차원 수: {dimension_count}"
