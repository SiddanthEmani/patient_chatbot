import logging
from django.shortcuts import render
from .models import Patient

# Configure logging
logger = logging.getLogger(__name__)

# Create your views here.
def home(request):
    # Redirect to the chat view with the first patient
    patient = Patient.objects.first()    
    if patient:
        logger.info("Patient ID: %s", patient.id)
        return render(request, 'chat/chat.html', {
            'patient_id': patient.id
        })
    else:
        logger.error("No patients found")
        # Redirect to error page if no patients are found
        return render(request, 'chat/error.html', {
            'error_message': 'No patients found. Please create sample data.'
        })