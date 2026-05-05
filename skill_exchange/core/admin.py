from django.contrib import admin
from .models import Profile, Skill, UserSkill

admin.site.register(Profile)
admin.site.register(Skill)
admin.site.register(UserSkill)