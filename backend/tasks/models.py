from django.db import models

class Task(models.Model):
    title = models.CharField(max_length=255)
    domain = models.CharField(max_length=100)
    difficulty = models.CharField(max_length=50)
    topic = models.CharField(max_length=100)
    scenario = models.TextField()
    given_code = models.TextField()
    expected_output = models.TextField()
    constraints = models.JSONField(default=list)
    solution = models.TextField()
    evaluation_criteria = models.JSONField(default=list)
    hints = models.JSONField(default=list) # Pool of hints for the user
    solution_approach = models.TextField(blank=True, null=True) # Expert perspective briefing
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
