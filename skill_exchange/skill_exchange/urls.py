from django.contrib import admin
from django.urls import path
from core import views
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect

def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_redirect, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('browse/', views.browse_skills, name='browse'),
    path('profile/', views.my_profile, name='my_profile'),  # Your personal profile/history
    path('profile/<int:user_id>/', views.view_profile, name='view_profile'), # Public profile
    path('add-skill/', views.add_skill, name='add_skill'),
    
    # Auth
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', views.signup, name='signup'),
    
    # Escrow & Requests
    path('send-request/<int:receiver_id>/<int:skill_id>/', views.send_request, name='send_request'),
    path('accept-request/<int:request_id>/', views.accept_request, name='accept_request'),
    path('complete-exchange/<int:request_id>/', views.complete_exchange, name='complete_exchange'),
    path('dispute-exchange/<int:request_id>/', views.dispute_exchange, name='dispute_exchange'),
]