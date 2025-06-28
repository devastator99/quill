const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8000/ws/chat');

ws.on('open', function open() {
  console.log('Connected to WebSocket');
  
  // Send a test message
  const testMessage = {
    type: 'user_message',
    message: 'Hello, this is a test message via WebSocket',
    conversation_id: null,
    timestamp: new Date().toISOString()
  };
  
  console.log('Sending message:', testMessage);
  ws.send(JSON.stringify(testMessage));
});

ws.on('message', function message(data) {
  console.log('Received message:', JSON.parse(data.toString()));
});

ws.on('error', function error(err) {
  console.error('WebSocket error:', err);
});

ws.on('close', function close() {
  console.log('WebSocket connection closed');
});

// Keep the script running for a few seconds to receive the response
setTimeout(() => {
  ws.close();
  process.exit(0);
}, 10000); 