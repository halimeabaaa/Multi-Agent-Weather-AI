from django.db import models

# Create your models here.
# backend/ai_orchestrator/models.py
from django.db import models
from django.contrib.auth.models import User

class DailySummary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="daily_summaries")
    date = models.DateField(auto_now_add=True)
    risk_level = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')])
    summary_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'date')
       

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.risk_level}"