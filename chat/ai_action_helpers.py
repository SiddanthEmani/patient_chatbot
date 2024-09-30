import datetime
import logging
from asgiref.sync import sync_to_async
from .neo4j_helper import execute_cypher_query_helper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Utility function to create an action response
def create_action_response(priority, requires_approval, message, notification=None):
    return {
        'priority': priority,
        'requires_approval': requires_approval,
        'message': message,
        'notification': notification
    }

# Helper function to schedule an appointment
async def schedule_appointment_helper(patient, action):
    new_date = action.get('new_date')
    new_time = action.get('new_time')
    
    if new_date and new_time:
        # Assuming the doctor is available at the requested date and time

        # Check if the date and time are valid
        try:
            next_appointment_datetime = datetime.datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %I:%M %p")
            logger.info(f"Scheduling appointment for patient_id: {patient.id} on {new_date} at {new_time}")
            return create_action_response(
                priority=1, 
                requires_approval=True, 
                message=f"I will convey your request to Dr. {patient.doctor_name}. Appointment is requested for {new_date} at {new_time}.",
                notification=f"Patient {patient.first_name} {patient.last_name} has requested an appointment for {new_date} at {new_time}."
            )
        except ValueError:
            logger.warning(f"Invalid date and time format provided for patient_id: {patient.id}")
            return create_action_response(
                priority=2, 
                requires_approval=False, 
                message="Please provide a valid date and time for the appointment."
            )

        
        #try:
            # Update the patient model
            # next_appointment_datetime = datetime.datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %I:%M %p")
            # patient.next_appointment = next_appointment_datetime
            # await sync_to_async(patient.save)()

            # Update the graph database
            # Set the previous appointment of type 'next' to 'last'
            # execute_cypher_query_helper(
            #     """
            #     MATCH (p:Patient {id: $patient_id})-[:HAS_APPOINTMENT]->(a:Appointment {type: 'next'})
            #     SET a.type = 'last'
            #     """,
            #     {'patient_id': patient.id}
            # )
            
            # Create a new appointment node and connect the patient to it
            # execute_cypher_query_helper(
            #     """
            #     MATCH (p:Patient {id: $patient_id})
            #     CREATE (a:Appointment {date: $next_appointment, type: 'next'})
            #     CREATE (p)-[:HAS_APPOINTMENT]->(a)
            #     """,
            #     {
            #         'patient_id': patient.id,
            #         'next_appointment': format_datetime(next_appointment_datetime)
            #     }
            # )            

            # return create_action_response(
            #     priority=1, 
            #     requires_approval=True, 
            #     message=f"I will convey your request to Dr. {patient.doctor_name}. Appointment is requested for {new_date} at {new_time}.",
            #     notification=f"Patient {patient.first_name} {patient.last_name} has requested an appointment for {new_date} at {new_time}."
            # )
        #except Exception as e:
            # logger.error(f"Failed to schedule appointment for patient_id: {patient.id}: {e}")
            # return create_action_response(
            #     priority=2, 
            #     requires_approval=False, 
            #     message="I'm sorry, I couldn't schedule the appointment. Please try again."
            # )
    else:
        logger.warning(f"Invalid appointment details provided for patient_id: {patient.id}")
        return create_action_response(
            priority=2, 
            requires_approval=False, 
            message="Please provide a valid date and time for the appointment."
        )
    
# Helper function to update medication regime
async def update_medication_helper(patient, intent):
    medication = intent.get('medication')
    dosage = intent.get('dosage')
    
    if medication and dosage:
        if medication.lower() == "unknown" or dosage.lower() == "unknown":
            logger.warning(f"Unknown medication or dosage provided for patient_id: {patient.id}")
            return create_action_response(
                priority=2, 
                requires_approval=False, 
                message=f"I will convey your concerns to Dr. {patient.doctor_name}"
            )
        logger.info(f"Updating medication for patient_id: {patient.id} to {medication} at a dosage of {dosage}")

        return create_action_response(
            priority=1, 
            requires_approval=True, 
            message=f"I will convey your request to Dr. {patient.doctor_name} to update your medication regime to {medication} at a dosage of {dosage}.",
            notification=f"Patient {patient.first_name} {patient.last_name} has requested to update their medication regime to {medication} at a dosage of {dosage}."
        )
    else:
        logger.warning(f"Invalid medication details provided for patient_id: {patient.id}")
        return create_action_response(
            priority=2, 
            requires_approval=False, 
            message="Please provide a valid medication and dosage."
        )
    
def format_datetime(dt):
        if dt:
            # Ensure the datetime is timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.isoformat()
        return None    