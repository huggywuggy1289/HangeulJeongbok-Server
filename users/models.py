from django.db import models
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser

# 유저 모델
class User(AbstractUser):
    userid = models.CharField(max_length=40, unique=True)

# 연동할 프로필 모델
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)