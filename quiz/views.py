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
                session_id = quiz_history.session_id  # 현재 세션 ID
                QuizHistory.objects.filter(user=user, completed_date=None).update(completed_date=now().date())

                # 점수 계산
                correct_answers = QuizHistory.objects.filter(user=user, is_correct=True, session_id=session_id).count()
                total_questions = 10  # 한 회차에 푸는 문제 수
                final_score = correct_answers * 10  # 문제당 10점

                return Response({
                    'result': "O" if is_correct else "X",
                    'message': "All quizzes completed. Proceed to results.",
                    'session_id': str(session_id),
                    'final_score': final_score,
                    'total_score': 100,
                    'correct_answers': correct_answers,
                    'incorrect_answers': total_questions - correct_answers
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

        # 가장 최근 완료된 세션 날짜 가져오기
        latest_date = QuizHistory.objects.filter(user=user, completed_date__isnull=False) \
                                        .order_by('-completed_date') \
                                        .values_list('completed_date', flat=True) \
                                        .first()

        if not latest_date:
            return Response({"message": "No recently completed quiz session found."}, status=status.HTTP_404_NOT_FOUND)

        # 가장 최근 세션의 문제 이력 가져오기
        latest_quiz_histories = QuizHistory.objects.filter(user=user, completed_date=latest_date)
        
        total_questions = latest_quiz_histories.count()
        correct_answers = latest_quiz_histories.filter(is_correct=True).count()
        incorrect_answers = latest_quiz_histories.filter(is_correct=False).count()

        results = []
        for history in latest_quiz_histories:
            results.append({
                "question": history.quiz.question,
                "selected_option": history.selected_option,
                "is_correct": history.is_correct,
            })

        return Response({
            "latest_session_date": latest_date,
            "score": correct_answers * 5,  # 예: 문제당 5점
            "total_score": total_questions * 5,  # 총 점수 계산
            "correct_answers": correct_answers,
            "incorrect_answers": incorrect_answers,
            "results": results
        }, status=status.HTTP_200_OK)

# 최근 틀린문제 반환
class IncorrectQuizAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 가장 최근에 완료된 세션 날짜 가져오기
        latest_date = QuizHistory.objects.filter(user=user, completed_date__isnull=False) \
                                        .order_by('-completed_date') \
                                        .values_list('completed_date', flat=True) \
                                        .first()

        if not latest_date:
            return Response({"message": "No recently completed quiz session found."}, status=status.HTTP_404_NOT_FOUND)

        # 가장 최근 세션에서 틀린 문제만 가져오기
        incorrect_histories = QuizHistory.objects.filter(
            user=user,
            completed_date=latest_date,
            is_correct=False
        )

        incorrect_questions = [
            {
                "question": history.quiz.question,
                "correct_answer": history.quiz.answer + 1,  # 1-based 정답
                "selected_option": history.selected_option,  # 사용자가 선택한 답
                "options": history.quiz.get_options()
            }
            for history in incorrect_histories
        ]

        return Response({"incorrect_questions": incorrect_questions}, status=status.HTTP_200_OK)
    
# 그동안 퀴즈를 풀었던 날짜와 점수, 퀴즈아이디 반환 (사용자의 퀴즈 이력)
class QuizHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # completed_date 기준으로 그룹화
        history = (
            QuizHistory.objects.filter(user=user)
            .values("completed_date")  # 날짜별로 그룹화
            .annotate(
                score=Sum(Case(When(is_correct=True, then=10), default=0, output_field=IntegerField()))
            )
            .order_by("-completed_date")
        )
        # 결과 변환
        result = [
            {
                "id": f"{user.id}-{item['completed_date']}",  # 날짜별 고유 ID 생성
                "completed_date": item["completed_date"],
                "score": item["score"],
            }
            for item in history
        ]
        return Response({"history": result}, status=200)

# 특정 날짜의 틀린 문제를 반환
class IncorrectHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, date):
        user = request.user
        completed_date = parse_date(date)

        if not completed_date:
            return Response({"error": "Invalid date format"}, status=400)

        incorrect_histories = QuizHistory.objects.filter(user=user, completed_date=completed_date, is_correct=False)
        incorrect_questions = []

        for history in incorrect_histories:
            options = history.quiz.get_options()
            print("get_options 반환값:", options)  # 반환값 출력
            incorrect_questions.append({
                "question": history.quiz.question,
                "correct_answer": history.quiz.answer + 1,
                "options": options,
            })

        return Response({"incorrect_questions": incorrect_questions}, status=200)

# 별점주기
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

# 전체 오답 문제 데이터와 별점이 모두 포함된 데이터를 가져오기 위한 API
class QuizDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user

            # 해당 사용자의 모든 오답 퀴즈 기록 조회
            incorrect_histories = QuizHistory.objects.filter(
                user=user, is_correct=False
            )

            if not incorrect_histories.exists():
                return Response(
                    {"message": "No incorrect questions found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 오답 기록 데이터 정리
            incorrect_questions = [
                {
                    "question": history.quiz.question,
                    "correct_answer": history.quiz.answer + 1,  # 1-based 정답
                    "selected_option": history.selected_option,  # 사용자가 선택한 답
                    "options_list": history.quiz.options,
                    "rating": history.rating if history.rating else None  # 별점이 없으면 null
                }
                for history in incorrect_histories
            ]

            return Response(
                {"incorrect_questions": incorrect_questions},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)