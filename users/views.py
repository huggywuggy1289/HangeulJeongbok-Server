from django.contrib.auth.models import User
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from django.shortcuts import redirect, render
from rest_framework import generics, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.authentication import JWTAuthentication

from .permissions import CustomReadOnly
from .serializers import *
from .models import *
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import RetrieveUpdateAPIView
from .renderers import UserJSONRenderer
from .forms import *
from rest_framework_simplejwt.tokens import RefreshToken

# 토큰 발급받도록 뷰 변경
# 회원가입
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        # 유효성 검사
        if serializer.is_valid():
            # 사용자 생성
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                "userid": user.userid,
                "username": user.username,
                "token": str(refresh.access_token),
                "message": "회원가입이 완료되었습니다."
            }, status=status.HTTP_201_CREATED)

        # 유효성 검사 실패 시 200 응답으로 오류 메시지 반환
        return Response({
            "errors": serializer.errors,
            "message": "회원가입에 실패했습니다."
        }, status=status.HTTP_200_OK)
    
# 로그인 뷰
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)

        # 유효성 검사
        if not serializer.is_valid():
            return Response({
                "errors": serializer.errors,
                "message": "로그인에 실패했습니다."
            }, status=status.HTTP_200_OK)

        token = serializer.validated_data['token']  # 토큰 받아오기
        user = serializer.validated_data['user']  # 사용자 정보 가져오기
        return Response({
            "token": token.key,
            "last_login": user.last_login
        }, status=status.HTTP_200_OK)

# 로그아웃 뷰(post)
class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 요청한 사용자의 토큰을 가져옵니다.
        token = request.auth
        # 사용자의 토큰 삭제
        if token:
            token.delete()
        return Response({"message": "Successfully logged out."}, status=200)

# 프로필 모델
class ProfileView(generics.RetrieveUpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    lookup_field = 'pk'
    permission_classes = [IsAuthenticated]