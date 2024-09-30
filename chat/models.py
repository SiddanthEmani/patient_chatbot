from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from .graph_utils import populate_patient_data

# Create your models here.
class Patient(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    medical_condition = models.TextField()
    medication_regime = models.TextField()
    last_appointment = models.DateTimeField()
    next_appointment = models.DateTimeField()
    doctor_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
@receiver(post_save, sender=Patient)
def update_patient_in_graph(sender, instance, **kwargs):
    populate_patient_data(instance)