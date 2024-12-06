from rest_framework import serializers
from .models import Quiz

# GET 호출할때 위와 어떤 형식으로 나타낼지 지정
class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ['id', 'question', 'options']

    def validate_options(self, value):
        """
        options 필드가 JSON 배열인지 확인
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("`options` 필드는 JSON 배열이어야 합니다.")
        return value

    def to_representation(self, instance):
        """
        데이터를 반환할 때만 options 필드의 형식을 변경
        """
        representation = super().to_representation(instance)
        options = representation['options']

        # 쉼표 기준으로 인덱스 값 추가(python 내장함수 enumerate사용)
        if isinstance(options, list):
            formatted_options = [
                f"{idx + 1}. {option}" for idx, option in enumerate(options)
            ]
            representation['options'] = formatted_options
        return representation

# 사용자의 답안이 맞는지 확인하는 답안제출 시리얼라이저
class AnswerSerializer(serializers.Serializer):
    quiz_id = serializers.IntegerField()
    selected_option = serializers.IntegerField()

    def validate(self, data):
        try:
            quiz = Quiz.objects.get(id=data['quiz_id'])
        except Quiz.DoesNotExist:
            raise serializers.ValidationError("Quiz not found.")

        # 선택지 유효성 검증: 1 <= selected_option <= len(quiz.options)
        if not (1 <= data['selected_option'] <= len(quiz.options)):
            raise serializers.ValidationError("Invalid option selected.")
        return data

    def check_answer(self):
        quiz_id = self.validated_data['quiz_id']
        user_answer = self.validated_data['selected_option']

        try:
            quiz = Quiz.objects.get(id=quiz_id)
            # 데이터베이스의 정답(0-based)을 1-based로 변환하여 비교
            correct_answer = quiz.answer + 1
            return correct_answer == user_answer
        except Quiz.DoesNotExist:
            raise serializers.ValidationError("Invalid quiz ID")
