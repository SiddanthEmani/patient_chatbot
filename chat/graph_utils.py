import logging
import datetime
from .neo4j_driver import Neo4jDriver

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Populate patient data
def populate_patient_data(patient):    
    logging.info("Starting to populate patient data for patient ID: %s", patient.id)
    driver = Neo4jDriver()
    
    # Create patient node
    parameters = {
        "patient_id": patient.id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "date_of_birth": str(patient.date_of_birth),
        "phone_number": patient.phone_number,
        "email": patient.email
    }
    query = """
    MERGE (p:Patient {id: $patient_id})
    SET p.first_name = $first_name,
        p.last_name = $last_name,
        p.date_of_birth = date($date_of_birth),
        p.phone_number = $phone_number,
        p.email = $email
    """
    logging.info("Creating patient node with parameters: %s", parameters)
    result = driver.execute_write_query(query, parameters)

    # Create doctor node and associate with patient
    if patient.doctor_name:
        parameters = {
            "patient_id": patient.id,
            "doctor_name": patient.doctor_name
        }
        query = """
        MATCH (p:Patient {id: $patient_id})
        MERGE (d:Doctor {name: $doctor_name})
        MERGE (p)-[:ASSIGNED_TO]->(d)
        """
        logging.info("Creating doctor node and associating with patient ID: %s", patient.id)
        result = driver.execute_write_query(query, parameters)

    # Create medical condition node and associate with patient
    if patient.medical_condition:
        conditions = [cond.strip() for cond in patient.medical_condition.split(",")]
        for condition in conditions:
            parameters = {
                "patient_id": patient.id,
                "medical_condition": condition
            }
            query = """
            MATCH (p:Patient {id: $patient_id})
            MERGE (mc:MedicalCondition {name: $medical_condition})
            MERGE (p)-[:HAS_CONDITION]->(mc)
            """
            logging.info("Creating medical condition node '%s' and associating with patient ID: %s", condition, patient.id)
            result = driver.execute_write_query(query, parameters)

    # Create medication regime node and associate with patient
    if patient.medication_regime:
        medications = [med.strip() for med in patient.medication_regime.split(",")]
        for medication in medications:
            parameters = {
                "patient_id": patient.id,
                "medication_regime": medication
            }
            query = """
            MATCH (p:Patient {id: $patient_id})
            MERGE (m:MedicationRegime {name: $medication_regime})
            MERGE (p)-[:TAKES_MEDICATION]->(m)
            """
            logging.info("Creating medication regime node '%s' and associating with patient ID: %s", medication, patient.id)
            result = driver.execute_write_query(query, parameters)

    # Create appointments and associate with patient
    # Last appointment
    if patient.last_appointment:
        parameters = {
            "patient_id": patient.id,
            "appointment_type": "last",
            "appointment_date": format_datetime(patient.last_appointment)
        }
        query = """
        MATCH (p:Patient {id: $patient_id})
        MERGE (a:Appointment {type: $appointment_type, date: datetime($appointment_date)})
        MERGE (p)-[:HAD_APPOINTMENT]->(a)
        """
        logging.info("Creating last appointment node and associating with patient ID: %s", patient.id)
        result = driver.execute_write_query(query, parameters)

    # Next appointment
    if patient.next_appointment:
        parameters = {
            "patient_id": patient.id,
            "appointment_type": "next",
            "appointment_date": format_datetime(patient.next_appointment)
        }
        query = """
        MATCH (p:Patient {id: $patient_id})
        MERGE (a:Appointment {type: $appointment_type, date: datetime($appointment_date)})
        MERGE (p)-[:HAS_APPOINTMENT]->(a)
        """
        logging.info("Creating next appointment node and associating with patient ID: %s", patient.id)
        result = driver.execute_write_query(query, parameters)

    # Close the driver connection
    driver.close()
    logging.info("Finished populating patient data for patient ID: %s", patient.id)

def format_datetime(dt):
        if dt:
            # Ensure the datetime is timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.isoformat()
        return None
