from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import Post, Profile

# Auto create profile when user registers
def get_or_create_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile

# Register
@api_view(['POST'])
@permission_classes([AllowAny])
def user_register(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response({'error': 'Username and password required'}, status=400)
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=400)
    user = User.objects.create_user(username=username, password=password)
    get_or_create_profile(user)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'username': user.username}, status=201)

# Login
@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if not user:
        return Response({'error': 'Invalid credentials'}, status=400)
    get_or_create_profile(user)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'username': user.username})

# Posts — feed
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def post_list(request):
    if request.method == 'GET':
        feed_type = request.query_params.get('type', 'all')
        if feed_type == 'feed' and request.user.is_authenticated:
            # Only posts from people you follow
            profile = get_or_create_profile(request.user)
            following_users = profile.followers.all()
            posts = Post.objects.filter(author__in=following_users).order_by('-created_at')
        else:
            posts = Post.objects.all().order_by('-created_at')

        data = [{
            'id': p.id,
            'content': p.content,
            'author': p.author.username,
            'created_at': p.created_at,
            'likes_count': p.likes.count(),
            'liked': request.user in p.likes.all() if request.user.is_authenticated else False
        } for p in posts]
        return Response(data)

    elif request.method == 'POST':
        content = request.data.get('content')
        if not content:
            return Response({'error': 'Content required'}, status=400)
        post = Post.objects.create(author=request.user, content=content)
        return Response({
            'id': post.id,
            'content': post.content,
            'author': post.author.username,
            'created_at': post.created_at,
            'likes_count': 0,
            'liked': False
        }, status=201)

# Like / Unlike
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_like(request, pk):
    try:
        post = Post.objects.get(pk=pk)
    except Post.DoesNotExist:
        return Response({'error': 'Post not found'}, status=404)

    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True

    return Response({'liked': liked, 'likes_count': post.likes.count()})

# Delete post
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def post_detail(request, pk):
    try:
        post = Post.objects.get(pk=pk)
    except Post.DoesNotExist:
        return Response({'error': 'Post not found'}, status=404)
    if post.author != request.user:
        return Response({'error': 'Not authorized'}, status=403)
    post.delete()
    return Response(status=204)

# User profile
@api_view(['GET'])
@permission_classes([AllowAny])
def user_profile(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    profile = get_or_create_profile(user)
    posts = Post.objects.filter(author=user).order_by('-created_at')
    is_following = False
    if request.user.is_authenticated:
        is_following = request.user in profile.followers.all()

    data = {
        'username': user.username,
        'bio': profile.bio,
        'followers_count': profile.followers.count(),
        'following_count': Profile.objects.filter(followers=user).count(),
        'is_following': is_following,
        'posts': [{
            'id': p.id,
            'content': p.content,
            'created_at': p.created_at,
            'likes_count': p.likes.count(),
            'liked': request.user in p.likes.all() if request.user.is_authenticated else False
        } for p in posts]
    }
    return Response(data)

# Follow / Unfollow
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_follow(request, username):
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    if target_user == request.user:
        return Response({'error': 'Cannot follow yourself'}, status=400)

    profile = get_or_create_profile(target_user)

    if request.user in profile.followers.all():
        profile.followers.remove(request.user)
        following = False
    else:
        profile.followers.add(request.user)
        following = True

    return Response({'following': following, 'followers_count': profile.followers.count()})

# All users
@api_view(['GET'])
@permission_classes([AllowAny])
def user_list(request):
    users = User.objects.all()
    data = []
    for user in users:
        profile = get_or_create_profile(user)
        data.append({
            'username': user.username,
            'followers_count': profile.followers.count(),
            'is_following': request.user in profile.followers.all() if request.user.is_authenticated else False
        })
    return Response(data)

# Update bio
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_bio(request):
    profile = get_or_create_profile(request.user)
    profile.bio = request.data.get('bio', profile.bio)
    profile.save()
    return Response({'bio': profile.bio})