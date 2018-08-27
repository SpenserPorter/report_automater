from django.db import models

class Agent(models.Model):
    agent_name = models.CharField(max_length=200)
    agent_email = models.CharField(max_length=200)
    agent_squire_id = models.CharField(max_length=200)

class Document(models.Model):
    docfile = models.FileField(upload_to='media/')
