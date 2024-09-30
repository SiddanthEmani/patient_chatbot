// chat/static/chat/js/chat.js

// Patient ID to be included with each message
const patientId = document.getElementById('patient-id').value; //

// WebSocket connection
var chatSocket = new WebSocket(
    'ws://' + window.location.host + '/ws/chat/' + patientId + '/'
);

// Function to display a message in the chat history
function addMessage(sender, text, timestamp) {
    // Create a new message container
    const messageContainer = document.createElement('div');
    messageContainer.classList.add('message', sender);

    // Create a new message element
    const messageContent = document.createElement('div');
    messageContent.classList.add('message-content');

    // Add the message text
    const messageText = document.createElement('div');
    messageText.innerHTML = marked.parse(text); // Use a markdown parser like marked.js

    // Add the message timestamp
    const messageTimestamp = document.createElement('div');
    messageTimestamp.classList.add('timestamp');
    messageTimestamp.innerText = timestamp;

    // Append the message text and timestamp to the message container
    messageContent.appendChild(messageText);
    messageContent.appendChild(messageTimestamp);
    messageContainer.appendChild(messageContent);

    // Append the message container to the chat history
    const chatHistory = document.getElementById('chat-history');
    chatHistory.appendChild(messageContainer);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Handle form submission
document.getElementById('chat-form').addEventListener('submit', function(e) {
    e.preventDefault(); // Prevent the default form action
    const inputField = document.getElementById('chat-input');
    const message = inputField.value.trim();
    if (message !== '') {
        const timestamp = getFormattedTimestamp(); // Get the current timestamp
        inputField.value = ''; // Clear the input field

        // Send the message to the server or WebSocket
        sendMessageToServer(message, patientId);
    }
});

// Get the current timestamp in a formatted string
function getFormattedTimestamp() {
    const now = new Date();
    return now.toLocaleString(); // Adjust options as needed for your locale
}

// Send a message to the server or WebSocket
function sendMessageToServer(message, patientId) {
    chatSocket.send(JSON.stringify({
        'message': message,
        'patient_id': patientId
    }));
}

// Receive messages from the server or WebSocket
chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    const message = data['message'];
    const sender = data['sender'];
    const timestamp = getFormattedTimestamp(); // Or use a timestamp from the server
    addMessage(sender, message, timestamp);
};

// Handle WebSocket errors
chatSocket.onerror = function(e) {
    console.error('WebSocket error observed:', e);
};

chatSocket.onclose = function(e) {
    console.error('Chat socket closed unexpectedly. Code:', e.code, 'Reason:', e.reason);
    // Optionally, you can attempt to reconnect here
    // setTimeout(function() {
    //     chatSocket = new WebSocket('ws://' + window.location.host + '/ws/chat/' + patientId + '/');
    // }, 1000);
};