// client.js

// Use sessionStorage so each tab has its own username
let username = sessionStorage.getItem("chat_username");
if (!username) {
    username = prompt("Enter your username:") || "Anonymous";
    sessionStorage.setItem("chat_username", username);
}
console.log("Using username:", username);

const ws = new WebSocket("ws://localhost:8000/ws");

ws.onopen = () => {
    console.log("✅ Connected to server");
};

ws.onmessage = (event) => {
    console.log("📩 Received:", event.data);
    addMessage(event.data);
};

function sendMessage() {
    const input = document.getElementById("messageInput");
    const message = input.value.trim();
    if (message) {
        const fullMessage = `${username}: ${message}`;
        ws.send(fullMessage);
        console.log("📤 Sent:", fullMessage);
        addMessage(fullMessage);
        input.value = "";
    }
}

function addMessage(text) {
    const chat = document.getElementById("chat");
    const msg = document.createElement("p");
    msg.textContent = text;
    chat.appendChild(msg);
}

// Function to change username only in the current tab
function changeUsername() {
    const newUsername = prompt("Enter your new username:");
    if (newUsername && newUsername.trim() !== "") {
        username = newUsername.trim();
        sessionStorage.setItem("chat_username", username);
        console.log("Username updated to:", username);
        alert("Username updated to: " + username);
    } else {
        alert("Invalid username. Username not updated.");
    }
}
