from django.urls import path
from .views import *

urlpatterns = [
    path('quizes/', QuizListAPIView.as_view(), name='quiz-list'),
    path('score/', QuizScoreAPIView.as_view(), name='quiz-score'),
    path('incorrect/', IncorrectQuizAPIView.as_view(), name='incorrect-quiz'),
    path('continue/', ContinueQuizAPIView.as_view(), name='continue-quiz'),
    path('history/', QuizHistoryAPIView.as_view(), name='quiz-history'),
    path('history/<date>/incorrect/', IncorrectHistoryAPIView.as_view(), name='quiz-history-incorrect'), #date YYYY-MM-DD
    path('history/<int:history_id>/rate/', RateQuizAPIView.as_view(), name='quiz-rate'),
]