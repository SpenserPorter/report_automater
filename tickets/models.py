from django.db import models

class Agent(models.Model):
    name = models.CharField(max_length=64, unique=True)
    email = models.CharField(max_length=64, unique=True)
    is_lead = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @classmethod
    def create(cls, name, email):
      return cls(name=name, email=email)

class ReportTimeframe(models.Model):
    start_dttm = models.DateTimeField()
    end_dttm = models.DateTimeField()
    
class Ticket(models.Model):
    id = models.IntegerField(primary_key=True)
    owner = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='tickets')
    timeframe = models.ForeignKey(ReportTimeframe, on_delete=models.CASCADE, related_name='tickets')
    dttm_created = models.DateTimeField()
    dttm_updated = models.DateTimeField()
    is_missing_severity = models.BooleanField(default=False)
    is_missing_closeout = models.BooleanField(default=False)
    is_incorrect_request_source = models.BooleanField(default=False)
    is_negative_response_time = models.BooleanField(default=False)
    is_large_response_time = models.BooleanField(default=False)
    is_open = models.BooleanField(default=False)

    def __str__(self):
       return str(self.id)

    def clear_all_status(self):
        self.is_missing_severity = False
        self.is_missing_closeout = False
        self.is_incorrect_request_source = False
        self.is_open = False
        self.is_negative_response_time = False
        self.is_large_response_time = False

    @classmethod
    def create(cls, id, owner, dttm_created, dttm_updated):
       return cls(id=id, owner=owner, dttm_created=dttm_created, dttm_updated=dttm_updated)


class Document(models.Model):
    docfile = models.FileField(upload_to='media/')
