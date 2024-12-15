import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Quiz, QuizHistory
from .serializers import QuizSerializer, AnswerSerializer

# 추가한 부분
from django.utils.timezone import now
from django.db.models import Sum, Case, When, IntegerField
from django.utils.dateparse import parse_date

# 퀴즈 목록 API
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Quiz
from .serializers import QuizSerializer, AnswerSerializer

# 퀴즈 목록 API, 정답 제출, 다음 퀴즈로 이동, 그리고 퀴즈 완료 후 결과 반환
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .models import Quiz, QuizHistory
from .serializers import QuizSerializer, AnswerSerializer

# 퀴즈 응시, 다음문제 이동, 점수계산, 결과 확인 기능 전부 포함
class QuizListAPIView(APIView):
    permission_classes = [IsAuthenticated]  # 인증된 사용자만 접근 가능

    def get(self, request):
        user = request.user
        
        # 유저의 진행 중인 퀴즈 이력을 가져옴
        quiz_history = QuizHistory.objects.filter(user=user, is_correct=None)

        if not quiz_history.exists():
            # 새로운 퀴즈 세션을 초기화 (10문제씩 푼다)
            quiz_ids = list(Quiz.objects.values_list('id', flat=True))[:10]  # 10문제만
            random.shuffle(quiz_ids)  # 퀴즈 순서를 랜덤으로 섞기
            for quiz_id in quiz_ids:
                QuizHistory.objects.create(user=user, quiz_id=quiz_id, selected_option=-1, is_correct=None)

        # 진행 중인 퀴즈를 반환
        current_quiz_history = QuizHistory.objects.filter(user=user, is_correct=None).first()
        if current_quiz_history:
            quiz = current_quiz_history.quiz
            serializer = QuizSerializer(quiz)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # 10문제가 다 풀렸으면 점수 계산 후 반환
            correct_answer = QuizHistory.objects.filter(user=user, is_correct=True).count()
            final_score = correct_answer * 10  # 문제당 10점
            total_score = 100  # 총점

            # 점수 저장 (선택사항: 퀴즈 기록에 저장하거나 별도의 테이블에 저장 가능)
            QuizHistory.objects.filter(user=user, completed_date=None).update(completed_date=now().date())

            return Response({
                'message': "All quizzes completed. Proceed to results.",
                'final_score': final_score,
                'total_score': total_score,
                'correct_answers': correct_answer,
                'incorrect_answers': 10 - correct_answer  # 10문제에서 맞힌 것 제외
            }, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        serializer = AnswerSerializer(data=request.data)
        if serializer.is_valid():
            quiz_id = request.data.get('quiz_id')
            selected_option = request.data.get('selected_option')
            quiz = Quiz.objects.get(id=quiz_id)
            
            # 현재 진행 중인 퀴즈 이력 가져오기
            quiz_history = QuizHistory.objects.get(user=user, quiz=quiz, is_correct=None)

            is_correct = (quiz.answer == selected_option)
            
            # 퀴즈 이력 업데이트
            quiz_history.selected_option = selected_option
            quiz_history.is_correct = is_correct
            quiz_history.save()

            # 다음 퀴즈로 이동
            next_quiz_history = QuizHistory.objects.filter(user=user, is_correct=None).first()

            if not next_quiz_history:
                QuizHistory.objects.filter(user=user, completed_date=None).update(completed_date=now().date())

                return Response({
                    'result': "X" if not is_correct else "O",
                    'message': "All quizzes completed. Proceed to results."
                }, status=status.HTTP_200_OK)

            # 다음 퀴즈를 반환
            next_quiz = next_quiz_history.quiz
            next_quiz_serializer = QuizSerializer(next_quiz)
            return Response({
                'result': "O" if is_correct else "X",
                'next_quiz': next_quiz_serializer.data  # 다음 문제를 반환
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 응답 제출 API
class QuizAnswerAPIView(APIView):
    def post(self, request):
        serializer = AnswerSerializer(data=request.data)
        if serializer.is_valid():
            is_correct = serializer.check_answer()
            return Response({'result':'O' if is_correct else 'X'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class QuizScoreAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 방금 완료한 세션의 퀴즈 이력만 가져오기
        latest_session = QuizHistory.objects.filter(user=user, completed_date=now().date())

        if not latest_session.exists():
            return Response({"error": "No recent quiz session found."}, status=404)

        # 점수 계산
        total_questions = latest_session.count()
        correct_answers = latest_session.filter(is_correct=True).count()
        incorrect_answers = latest_session.filter(is_correct=False).count()
        score = correct_answers * 10  # 문제당 10점

        # 각 문제의 결과 (O/X) 포함하여 반환
        results = []
        for history in latest_session:
            results.append({
                "question": history.quiz.question,
                "selected_option": history.selected_option,
                "correct_answer": history.quiz.answer + 1,  # 정답은 1-based
                "result": "O" if history.is_correct else "X",
            })

        return Response({
            "score": score,  # 이번 세션 점수
            "total_score": total_questions * 10,  # 만점
            "correct_answers": correct_answers,
            "incorrect_answers": incorrect_answers,
            "results": results  # 각 문제 결과
        }, status=200)

class IncorrectQuizAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        incorrect_histories = QuizHistory.objects.filter(user=user, is_correct=False)

        incorrect_questions = []
        for history in incorrect_histories:
            incorrect_questions.append({
                "question": history.quiz.question,
                "correct_answer": history.quiz.answer + 1,  # 정답은 1-based로 반환
                "selected_option": history.selected_option,
                "options": history.quiz.get_options()
            })

        return Response({"incorrect_questions": incorrect_questions})

class QuizHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        history = (
            QuizHistory.objects.filter(user=user)
            .values("id", "completed_date")  # id 값을 추가
            .annotate(score=Sum(Case(When(is_correct=True, then=10), default=0, output_field=IntegerField())))
            .order_by("-completed_date")
        )
        return Response({"history": list(history)}, status=200)

class IncorrectHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, date):
        user = request.user
        completed_date = parse_date(date)

        if not completed_date:
            return Response({"error": "Invalid date format"}, status=400)

        incorrect_histories = QuizHistory.objects.filter(user=user, completed_date=completed_date, is_correct=False)
        incorrect_questions = [
            {
                "question": history.quiz.question,
                "correct_answer": history.quiz.answer + 1,
                "options": history.quiz.get_options(),
            }
            for history in incorrect_histories
        ]
        return Response({"incorrect_questions": incorrect_questions}, status=200)
    

class RateQuizAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, history_id):
        rating = request.data.get("rating")

        if not (1 <= rating <= 5):
            return Response({"error": "Rating must be between 1 and 5"}, status=400)

        try:
            history = QuizHistory.objects.get(id=history_id, user=request.user)
            history.rating = rating
            history.save()
            return Response({"message": "Rating saved successfully"}, status=200)
        except QuizHistory.DoesNotExist:
            return Response({"error": "Quiz history not found"}, status=404)

# 퀴즈 정복 데이터 api
class QuizDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, history_id):
        try:
            history = QuizHistory.objects.get(id=history_id, user=request.user)
            quiz = history.quiz

            return Response({
                "id": history.id,
                "question": quiz.question,
                "options_list": quiz.options,
                "rating": history.rating if history.rating else None  # 별점이 없으면 null 반환
            }, status=status.HTTP_200_OK)
        except QuizHistory.DoesNotExist:
            return Response({"error": "Quiz history not found"}, status=status.HTTP_404_NOT_FOUND)
