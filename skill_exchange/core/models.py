from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    points = models.IntegerField(default=5) # Starting points

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # Add this line:
    category = models.CharField(max_length=50, default='Other') 

    def __str__(self):
        return self.name

class UserSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    is_offering = models.BooleanField(default=True) # True=Teach, False=Learn

class ExchangeRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed')
    ]
    
    sender = models.ForeignKey(User, related_name="sent_requests", on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name="received_requests", on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    meeting_link = models.URLField(blank=True, null=True, help_text="Paste Google Meet/Zoom link here")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} -> {self.receiver} ({self.skill.name})"