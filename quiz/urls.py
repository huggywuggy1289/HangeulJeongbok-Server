from django.urls import path
from .views import *

urlpatterns = [
    path('quizes/', QuizListAPIView.as_view(), name='quiz-list'),
    path('score/', QuizScoreAPIView.as_view(), name='quiz-score'),
    path('incorrect/', IncorrectQuizAPIView.as_view(), name='incorrect-quiz'), # 고친함수
    path('history/', QuizHistoryAPIView.as_view(), name='quiz-history'),
    path('history/incorrect/', IncorrectHistoryAPIView.as_view(), name='quiz-history-incorrect'), #전체 틀린문제 데이터 반환환
    path('history/<date>/incorrect/', IncorrectHistoryAPIView.as_view(), name='quiz-history-incorrect'), #date YYYY-MM-DD 날짜별 반환
    path('history/<int:history_id>/rate/', RateQuizAPIView.as_view(), name='quiz-rate'),
    path('history/incorrect/all/', QuizDetailAPIView.as_view(), name='quiz-incorrect-details'), #고친함수  # 전체 오답 세부 데이터
]