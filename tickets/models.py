from django.db import models

class Agent(models.Model):
    name = models.CharField(max_length=64, unique=True)
    email = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name

    @classmethod
    def create(cls, name, email):
      return cls(name=name, email=email)

#class Ticket(models.Model):
#    ticket_id = models.PrimaryKey()
#    ticket_type = models.CharField(max_length=64)
#    ticket_owner = models.ForeignKey(Agent, on_delete=cascade)

class Document(models.Model):
    docfile = models.FileField(upload_to='media/')
