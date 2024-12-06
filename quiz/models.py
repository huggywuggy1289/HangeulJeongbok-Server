from django.conf import settings  # settings에서 AUTH_USER_MODEL을 가져옵니다.
from django.db import models
import json
from django.utils.timezone import now

# 퀴즈 내용 데이터베이스에 저장(문제, 선택지, 답안)
class Quiz(models.Model):
    question = models.TextField()
    options = models.JSONField(default=list)  # JSON 데이터를 저장할 수 있는 필드
    answer = models.IntegerField()

    def set_options(self, data):
        self.options = json.dumps(data)

    def get_options(self):
        return json.loads(self.options)
    
    def __str__(self):
        return self.question
    
# 퀴즈 이력을 저장하는 모델
class QuizHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='quiz_histories', on_delete=models.CASCADE)  # 'auth.User' 대신 settings.AUTH_USER_MODEL 사용
    quiz = models.ForeignKey(Quiz, related_name='histories', on_delete=models.CASCADE)  # 퀴즈 정보
    selected_option = models.IntegerField()  # 사용자가 선택한 옵션 번호
    is_correct = models.BooleanField(null=True, default=None)
    completed_date = models.DateField(null=True, default=None)  # 퀴즈 완료 날짜
    rating = models.IntegerField(null=True, blank=True)  # 별점 저장 (1~5 사이)
    
    def __str__(self):
        return f"{self.user.username} - {self.quiz.id} - {self.is_correct}"