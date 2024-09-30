import os
import json
import datetime
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_community.graphs import Neo4jGraph
from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain
from langchain.prompts import PromptTemplate
from .models import Patient
from asgiref.sync import sync_to_async
import logging
from .ai_action_helpers import schedule_appointment_helper, update_medication_helper
from .neo4j_helper import execute_cypher_query_helper
from django.conf import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AI model
llm = ChatGoogleGenerativeAI(
    model='gemini-1.5-pro', # 'gemini-1.5-pro' or 'gemini-1.5'
    api_key=settings.GEMINI_API_KEY, # Your API key
    temperature=0.3,
    max_tokens=None, # None for unlimited
    timeout=None,
    max_retries=2, # Number of retries if the request fails
)
logger.info("Initialized AI model")

def get_root_prompt(patient):
    return f"""You are an assistant providing health advice to {patient.first_name} {patient.last_name}, a patient under Dr. {patient.doctor_name}. 
    You are currently talking to this patient.
    Always be empathetic and assist based on their medical condition: {patient.medical_condition}.
    Ignore unrelated topics such as politics or personal matters.
    """

# Define the schema for LangGraph
schema = """
Nodes:
    - Patient(id, first_name, last_name, date_of_birth, phone_number, email)
    - Doctor(name)
    - MedicalCondition(name)
    - Medication(name)
    - Appointment(date, type) # type: 'last' or 'next'
Relationships:
    - (Patient)-[:ASSIGNED_TO]->(Doctor)
    - (Patient)-[:HAS_CONDITION]->(MedicalCondition)
    - (Patient)-[:TAKES_MEDICATION]->(Medication)
    - (Patient)-[:HAD_APPOINTMENT]->(Appointment {type: 'last'})
    - (Patient)-[:HAS_APPOINTMENT]->(Appointment {type: 'next'})
"""

# Define intent query map
intent_query_map = {
    "get_next_appointment": {
        "query": """
            MATCH (p:Patient {id: $patient_id})-[:HAS_APPOINTMENT]->(a:Appointment {type: 'next'})
            RETURN a.date AS next_appointment
        """,
        "process_result": lambda result: f"Your next appointment is on {result['next_appointment'].date()} at {result['next_appointment'].time()}."
    },
    "get_last_appointment": {
        "query": """
            MATCH (p:Patient {id: $patient_id})-[:HAD_APPOINTMENT]->(a:Appointment {type: 'last'})
            RETURN a.date AS last_appointment
        """,
        "process_result": lambda result: f"Your last appointment was on {result['last_appointment'].date()} at {result['last_appointment'].time()}."
    },
    "get_medications": {
        "query": """
            MATCH (p:Patient {id: $patient_id})-[:TAKES_MEDICATION]->(m:MedicationRegime)
            RETURN m.name AS medication
        """,
        "process_result": lambda results: f"You are currently taking: {', '.join([r['medication'] for r in results])}."
    },
    "get_medical_conditions": {
        "query": """
            MATCH (p:Patient {id: $patient_id})-[:HAS_CONDITION]->(c:MedicalCondition)
            RETURN c.name AS condition
        """,
        "process_result": lambda results: f"Your medical conditions are: {', '.join([r['condition'] for r in results])}."
    },
    "get_doctor_info": {
        "query": """
            MATCH (p:Patient {id: $patient_id})-[:ASSIGNED_TO]->(d:Doctor)
            RETURN d.name AS doctor_name
        """,
        "process_result": lambda result: f"Your assigned doctor is Dr. {result['doctor_name']}."
    },
}

# Generate response from AI
async def generate_response(patient_id, prompt, conversation_history):
    logger.info(f"Generating response for patient_id: {patient_id} with prompt: {prompt}")

    # Get the patient from the database
    try:
        patient = await sync_to_async(Patient.objects.get)(id=patient_id)
    except Patient.DoesNotExist:    
        logger.error(f"Patient with id {patient_id} not found")
        return "Error: Patient not found"

    # Summarize conversation histories if conversation is too long
    if len(conversation_history) > 10:
        context_summary = await summarize_conversation(patient, conversation_history)
        conversation_history = []
        conversation_history.append(SystemMessage(content=f'Summary: {context_summary}'))

    # Create a context-aware prompt
    context_conversation = '\n'.join(
        [msg['message'] if isinstance(msg, dict) else msg.content for msg in conversation_history]
    )
    latest_prompt = prompt

    contextual_prompt = f"Context: {context_conversation}\n\nUser's latest prompt: {latest_prompt}\n\Always focus on answering the latest prompt while considering the context provided."


    # Add user input to conversation history
    conversation_history.append(HumanMessage(content=prompt))
    logger.info(f"Conversation history for patient_id: {patient_id}: {conversation_history}")

    # Classify the prompt into intents
    intents = classify_prompt(patient, contextual_prompt)
    logger.info(f"Classified intents for patient_id: {patient_id}: {intents}")

    responses = []

    if not intents:
        logger.info(f"No intents detected for patient_id: {patient_id}")
        # No intents detected, generate general response
        response = generate_general_response(patient, contextual_prompt)
        responses.append(response)
    else:
        # Handle each intent
        for intent in intents:
            if intent == "get information":
                response = await get_information_helper(patient, contextual_prompt)
                responses.append(response)
            elif intent == "do some action":
                response = await do_some_action_helper(patient, contextual_prompt)
                responses.append(response)
            else:
                logger.warning(f"Unknown intent detected for patient_id: {patient_id}: {intent}")
                responses.append("I'm sorry, I couldn't understand your request. Please provide more information or try again.")

    final_response = "\n".join(responses)
    
    # Add AI response to conversation history
    conversation_history.append(AIMessage(content=final_response))

    return final_response

# Summarize conversation histories of a patient
async def summarize_conversation(patient, conversation_history):
    logger.info(f"Summarizing conversation history")
    root_prompt = get_root_prompt(patient)
    summary_response = llm.invoke([
        SystemMessage(content=f"{root_prompt} Summarize the following conversation history:"),
        HumanMessage(content='\n'.join(
            [msg['message'] if isinstance(msg, dict) else msg.content for msg in conversation_history])
        )
    ])
    return summary_response.content

# Classify prompt into intents
def classify_prompt(patient, prompt):
    logger.info(f"Classifying prompt: {prompt}")
    root_prompt = get_root_prompt(patient)
    classification_prompt = f"""
    {root_prompt}

    Classify the following user prompt into one or more of the following intents:
    1. get information
    2. do some action

    If the prompt contains multiple instructions, include all relevant intents.

    User Prompt: "{prompt}"

    **Provide only** the intents as a JSON array **without any code fences, explanations, or additional text**. **Do not include markdown formatting or code snippets**. If no intents are detected, provide an empty array: []

    Example: ["get information", "do some action"]
    """
    response = llm.invoke(classification_prompt)
    logger.info(f"Classified prompt: {prompt} into intents: {response.content}")
    response = response.content.strip()
    # Remove code fences if present
    # Use regex to remove ```json ... ``` or ``` ... ```
    response = re.sub(r'^```(?:json)?\s*([\s\S]*?)\s*```$', r'\1', response, flags=re.MULTILINE)

    # Trim any leading/trailing whitespace
    response = response.strip()
    
    # Parse the response as JSON
    try:
        intents = json.loads(response)
        return intents
    except json.JSONDecodeError:
        logger.error(f"Failed to parse intents from response: {response.content}")
        return []

def generate_general_response(patient, prompt):
    logger.info(f"Generating general response")
    root_prompt = get_root_prompt(patient)
    general_prompt = f"""
    {root_prompt}

    The user has sent the following message: "{prompt}"

    Please respond to the user in a clear and empathetic manner, as their patient assistant.
    """
    response = llm.invoke(general_prompt)
    response_text = response.content.strip()
    logger.info(f"Generated general response: {response_text}")
    return response_text
    
# Helper function to get information
async def get_information_helper(patient, prompt):        
    # Classify the prompt into intents
    intents = await classify_intent(patient, prompt)

    # No intents detected, generate general response
    if not intents:
        logger.info(f"No intents detected, generating general response")    
        return await generate_general_response(patient, prompt)
        
    graph_data = {}
    responses = []
    tasks = []

    # Handle each intent
    for intent in intents:
        if intent in intent_query_map:
            query = intent_query_map[intent]["query"]
            params = { "patient_id": patient.id }
            try:
                logger.info(f"Executing cypher query {query} with params {params} for intent: {intent}")
                results = execute_cypher_query_helper(query, params)                
                logger.info(f"Results for intent: {intent}: {results}")
                if not results:
                    responses.append("I'm sorry, I couldn't retrieve the information. Please try again.")
                    continue
                else:
                    # Process the result(s)
                    logger.info(f"Processing results for intent: {intent}")
                    process_result = intent_query_map[intent]["process_result"](results[0] if intent in ["get_next_appointment", "get_last_appointment", "get_doctor_info"] else results)                
                    logger.info(f"Processed result for intent: {intent}: {process_result}")
                responses.append(process_result)
            except Exception as e:
                logger.error(f"Failed to get information: {e}")
                responses.append("I'm sorry, I couldn't retrieve the information. Please try again.")
        else:
            logger.warning(f"Unknown intent detected: {intent}")
            responses.append("I'm sorry, I couldn't understand your request. Please provide more information or try again.")    

    # Aggregate graph data for LLM
    # Optionally, if you need raw data, you can collect it here
    # For simplicity, we assume processed responses are sufficient
    
    # Optionally, you can combine all responses into one
    aggregated_responses = "\n".join(responses)

    # Generate a response from LLM
    llm_prompt = f"""
    {get_root_prompt(patient)}
    Based on the following information, respond to the user in a clear and empathetic manner.

    SQL Data:
    - Name: {patient.first_name} {patient.last_name}
    - Date of Birth: {patient.date_of_birth}
    - Phone Number: {patient.phone_number}
    - Email: {patient.email}
    - Medical Condition: {patient.medical_condition}
    - Doctor: {patient.doctor_name}

    Graph Data:
    {aggregated_responses}

    User Prompt: "{prompt}"

    Provide a comprehensive and empathetic response to the user's query.
    """

    response = await llm.ainvoke(llm_prompt)
    final_response = response.content.strip()
    return final_response

# Classify Intent
async def classify_intent(patient, prompt):
    logger.info(f"Classifying intent for prompt: {prompt}")
    root_prompt = get_root_prompt(patient)
    classification_prompt = f"""
    {root_prompt}

    Classify the following user prompt into one or more of the following intents:
    
    1. get_next_appointment
    2. get_last_appointment
    3. get_medications
    4. get_medical_conditions
    5. get_doctor_info

    If the prompt doesn't match any of the above intents, respond with "unknown_intent".
    If multiple intents are detected, provide all relevant intents in a JSON array.

    User Prompt: "{prompt}"

    Provide only the intents as a JSON array without any code fences, explanations, or additional text.
    
    Example responses:
    - ["get_medications"]
    - ["get_next_appointment", "get_medications"]
    - ["unknown_intent"]
    """
    response = await llm.ainvoke(classification_prompt)
    intents = response.content.strip()

    # Remove code fences if present
    intents = re.sub(r'^```(?:json)?\s*([\s\S]*?)\s*```$', r'\1', intents, flags=re.MULTILINE).strip()
    
    # Parse the response as JSON
    try:
        intents = json.loads(intents)
        # Ensure its a list
        if isinstance(intents, str):
            intents = [intents]
        elif not isinstance(intents, list):
            intents = []
        #Validate against predefined intents
        valid_intents = {"get_next_appointment", "get_last_appointment", "get_medications", "get_medical_conditions", "get_doctor_info", "unknown_intent"}
        intents_list = [intent for intent in intents if intent in valid_intents]
        logger.info(f"Classified intents : {intents_list}")
        return intents_list
    except json.JSONDecodeError:
        logger.error(f"Failed to parse intents from response: {response.content}")
        return []

# Helper function to do some action
async def do_some_action_helper(patient, prompt):
    logger.info(f"Doing some action for patient_id: {patient.id} with prompt: {prompt}")
    root_prompt = get_root_prompt(patient)

    # Extract action details from LLM
    action_extraction_prompt = f"""
    {root_prompt}

    You are an assistant that extracts action intents from user prompts.

    User Prompt: "{prompt}"

    Identify the actions the user wants to perform, such as scheduling an appointment or updating medication.

    Provide the actions as a JSON array with details. Example:
    [
        {{"action": "schedule appointment", "new_date": "2023-12-01", "new_time": "10:00 AM"}},
        {{"action": "update medication", "medication": "Aspirin", "dosage": "100 mg"}}
    ]

    actions can only be one of the following:
    - schedule appointment
    - update medication

    Always provide these parameters for each action:
    - schedule appointment: new_date '%Y-%m-%d', new_time '%I:%M %p'
    - update medication: medication, dosage
    """

    response = await llm.ainvoke(action_extraction_prompt)
    llm_response = response.content.strip()
    # Remove code fences if present
    llm_response = re.sub(r'^```(?:json)?\s*([\s\S]*?)\s*```$', r'\1', llm_response, flags=re.MULTILINE).strip()

    logger.info(f"Extracted actions for patient_id: {patient.id} with prompt: {prompt}: {llm_response}")

    # Parse the response as JSON
    try:
        actions = json.loads(llm_response)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse actions from response: {llm_response}")
        return "I'm sorry, I couldn't understand the actions you want to perform. Please try again."
    
    # Process the actions
    action_responses = []
    for action in actions:
        action_type = action.get('action')
        if action_type == 'schedule appointment':
            action_response = await schedule_appointment_helper(patient, action)
            action_responses.append(action_response['message'])
        elif action_type == 'update medication':
            action_response = await update_medication_helper(patient, action)
            action_responses.append(action_response['message'])
        else:
            logger.warning(f"Unknown action detected for patient_id: {patient.id}: {action['action']}")
            action_responses.append("I'm sorry, I couldn't understand the action you want to perform. Please try again.")

    return "\n".join(action_responses)