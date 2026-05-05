from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import Q
from .models import UserSkill, Skill, ExchangeRequest, Profile

@login_required
def dashboard(request):
    user = request.user
    search_query = request.GET.get('search', '').strip()
    
    # 1. LIVE STATS (Grouped into a dictionary to match the template)
    stats = {
        'points': user.profile.points,
        'hours_taught': ExchangeRequest.objects.filter(receiver=user, status='completed').count(),
        'skills_learned': ExchangeRequest.objects.filter(sender=user, status='completed').count(),
    }

    # 2. FILTER COMMUNITY
    community = Profile.objects.exclude(user=user).select_related('user')

    if search_query:
        community = community.filter(
            Q(user__username__icontains=search_query) | 
            Q(user__userskill__skill__name__icontains=search_query, user__userskill__is_offering=True)
        ).distinct()
    else:
        community = community.filter(user__userskill__is_offering=True).distinct()

    # 3. RECOMMENDED MATCHES
    my_wants = UserSkill.objects.filter(user=user, is_offering=False).values_list('skill', flat=True)
    matches = UserSkill.objects.filter(
        skill__in=my_wants, 
        is_offering=True
    ).exclude(user=user).select_related('user', 'skill').distinct()
    
    # 4. REQUESTS
    incoming = ExchangeRequest.objects.filter(receiver=user, status='pending').select_related('sender', 'skill')
    accepted_sent = ExchangeRequest.objects.filter(sender=user, status='accepted').select_related('receiver', 'skill')

    context = {
        'stats': stats,  # Passing the dictionary here!
        'matches': matches,
        'incoming': incoming,
        'accepted_sent': accepted_sent,
        'community': community, 
        'search_query': search_query,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def add_skill(request):
    if request.method == "POST":
        # We now get the skill name as text, not just an ID
        skill_name = request.POST.get('skill_name', '').strip().title()
        action = request.POST.get('action') 

        if not skill_name:
            messages.error(request, "Please provide a skill name.")
            return redirect('add_skill')

        # Overcoming the limit: Create the skill if it doesn't exist
        skill, created = Skill.objects.get_or_create(name=skill_name)
        
        # Link to User
        UserSkill.objects.get_or_create(
            user=request.user, 
            skill=skill, 
            is_offering=(action == 'teach')
        )
        
        messages.success(request, f"'{skill_name}' added to your profile!")
        return redirect('dashboard')
    
    all_skills = Skill.objects.all().order_by('name')
    return render(request, 'core/add_skill.html', {'all_skills': all_skills})

@login_required
def send_request(request, receiver_id, skill_id):
    receiver = get_object_or_404(User, id=receiver_id)
    skill = get_object_or_404(Skill, id=skill_id)
    
    if receiver == request.user:
        messages.warning(request, "You cannot request a lesson from yourself.")
        return redirect('dashboard')

    # Double Request Prevention
    existing = ExchangeRequest.objects.filter(
        sender=request.user, 
        receiver=receiver, 
        skill=skill,
        status__in=['pending', 'accepted']
    ).exists()

    if existing:
        messages.info(request, "You already have an active request for this skill.")
        return redirect('dashboard')

    if request.user.profile.points < 1:
        messages.error(request, "You need 1 point to request a lesson!")
        return redirect('dashboard')

    ExchangeRequest.objects.create(sender=request.user, receiver=receiver, skill=skill)
    messages.success(request, f"Request sent to {receiver.username}!")
    return redirect('dashboard')

@login_required
def accept_request(request, request_id):
    exch_request = get_object_or_404(ExchangeRequest, id=request_id, receiver=request.user)
    if request.method == "POST":
        learner_profile = exch_request.sender.profile
        if learner_profile.points >= 1:
            learner_profile.points -= 1 
            learner_profile.save()
            exch_request.meeting_link = request.POST.get('meeting_link')
            exch_request.status = 'accepted'
            exch_request.save()
            messages.success(request, "Request accepted! Point locked in escrow.")
            return redirect('dashboard')
    return render(request, 'core/accept_request.html', {'req': exch_request})

@login_required
def complete_exchange(request, request_id):
    exch_request = get_object_or_404(ExchangeRequest, id=request_id, sender=request.user)
    if exch_request.status == 'accepted':
        teacher_profile = exch_request.receiver.profile
        teacher_profile.points += 1 
        teacher_profile.save()
        exch_request.status = 'completed'
        exch_request.save()
        messages.success(request, "Lesson completed! Point released to teacher.")
    return redirect('dashboard')

@login_required
def dispute_exchange(request, request_id):
    exch_request = get_object_or_404(ExchangeRequest, id=request_id, sender=request.user)
    if exch_request.status == 'accepted':
        profile = exch_request.sender.profile
        profile.points += 1
        profile.save()
        exch_request.status = 'pending' 
        exch_request.save()
        messages.warning(request, "Exchange disputed. Point returned to your balance.")
    return redirect('dashboard')

@login_required
def view_profile(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    teaching_skills = UserSkill.objects.filter(user=target_user, is_offering=True).select_related('skill')
    learning_skills = UserSkill.objects.filter(user=target_user, is_offering=False).select_related('skill')
    return render(request, 'core/profile_view.html', {
        'target_user': target_user,
        'teaching_skills': teaching_skills,
        'learning_skills': learning_skills,
    })

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            messages.success(request, "Account created! Please login.")
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'core/signup.html', {'form': form})

@login_required
def browse_skills(request):
    """
    Enhanced Discovery page: Filters by specific Categories 
    (like Music, Tech) OR by the Search bar.
    """
    # Get filters from the URL
    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', '').strip()
    
    # 1. Start with all skills except the logged-in user's
    skills = UserSkill.objects.exclude(user=request.user).select_related('user', 'skill')

    # 2. SMART CATEGORY LOGIC
    # This checks if a category button was clicked and filters by related keywords
    if category_filter and category_filter != 'All':
        if category_filter == 'Music':
            # Add any keywords related to Music here
            skills = skills.filter(
                Q(skill__name__icontains='Music') | 
                Q(skill__name__icontains='Singing') | 
                Q(skill__name__icontains='Guitar') | 
                Q(skill__name__icontains='Piano') |
                Q(skill__name__icontains='Vocals')
            )
        elif category_filter == 'Tech':
            skills = skills.filter(
                Q(skill__name__icontains='Python') | 
                Q(skill__name__icontains='Java') | 
                Q(skill__name__icontains='Coding') | 
                Q(skill__name__icontains='Web')
            )
        elif category_filter == 'Design':
            skills = skills.filter(
                Q(skill__name__icontains='Photo') | 
                Q(skill__name__icontains='Logo') | 
                Q(skill__name__icontains='UI') | 
                Q(skill__name__icontains='UX')
            )
        else:
            # Fallback for other categories
            skills = skills.filter(skill__name__icontains=category_filter)

    # 3. SEARCH BAR LOGIC (Manual search overrides category)
    if search_query:
        skills = skills.filter(
            Q(skill__name__icontains=search_query) | 
            Q(user__username__icontains=search_query)
        ).distinct()

    context = {
        'skills': skills,
        'search_query': search_query,
        'selected_category': category_filter,
    }
    
    return render(request, 'core/browse.html', context)

@login_required
def my_profile(request):
    """
    This is your private profile view.
    It shows your personal skills and your exchange history.
    """
    user = request.user
    # Get the skills the user has added for themselves
    my_skills = UserSkill.objects.filter(user=user).select_related('skill')
    
    # Get all exchange requests where the user is either the sender or receiver
    history = ExchangeRequest.objects.filter(
        Q(sender=user) | Q(receiver=user)
    ).order_by('-created_at')

    return render(request, 'core/profile.html', {
        'my_skills': my_skills,
        'history': history
    })