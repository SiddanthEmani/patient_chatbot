import logging
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from .ai import generate_response
from .models import Patient
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    # This method is called when the connection is established
    async def connect(self):
        logger.info("ChatConsumer.connect called")
        await self.accept()
        logger.info("WebSocket connection established")
        self.conversation_history = [] # Initialize conversation history

    # This method is called when the connection is closed
    async def disconnect(self, close_code):
        logger.info(f"WebSocket connection closed with code: {close_code}")
        self.conversation_history = [] # Clear conversation history

    # This method is called whe6n the patient sends a message
    async def receive(self, text_data):
        logger.info(f"Received message: {text_data}")
        data = json.loads(text_data) # Parse the JSON data
        message = data['message'] # Get the message from the data
        patient_id = data.get('patient_id') # Get the patient ID from the message

        # Get the patient from the database
        try:
            patient = await sync_to_async(Patient.objects.get)(id=patient_id)
            logger.info(f"Patient found: {patient_id}")
        except Patient.DoesNotExist:
            logger.error(f"Patient not found: {patient_id}")
            await self.send(text_data=json.dumps({
                'message': "Error: Patient not found"
            }))
            return
        
        # Add the patient's message to the conversation history
        self.conversation_history.append({
            'sender': 'user',
            'message': message
        })        

        # Send the patient's message back to the client (echo)
        await self.send(text_data=json.dumps({
            'sender': 'user',
            'message': message
        }))

        # Generate a response from the AI
        bot_response = await generate_response(patient_id, message, self.conversation_history)
        
        # Send the bot's response back to the client
        await self.send(text_data=json.dumps({
            'sender': 'bot',
            'message': bot_response,
            'format': 'markdown'
        }))