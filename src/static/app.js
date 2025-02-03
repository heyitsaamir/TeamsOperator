let socket = null;
let messages = [];
let selectedMessageIndex = null;
let expandedMessages = new Set();
let currentGoal = null;

function updateConnectionStatus(isConnected) {
  const statusDot = document.getElementById("connection-status");
  const statusText = document.getElementById("connection-text");

  statusDot.className = `w-2 h-2 rounded-full ${
    isConnected ? "bg-green-500" : "bg-red-500"
  }`;
  statusText.textContent = isConnected ? "Connected" : "Disconnected";
}

function createMessageElement(message, index) {
  const div = document.createElement("div");
  div.className = "flex flex-col gap-1";
  div.onclick = () => handleMessageSelect(index);

  const isWebMessage = message.action.startsWith("Web:");
  const isSelected = index === selectedMessageIndex;

  const baseClasses = `p-2 rounded cursor-pointer transition-colors ${
    isWebMessage
      ? "bg-blue-900 text-gray-100"
      : isSelected
      ? "bg-gray-800 border border-gray-600 text-gray-100"
      : "bg-gray-900 border border-gray-700 text-gray-100"
  } hover:border-gray-600`;

  const hasExpandableContent =
    message.memory ||
    message.next_goal ||
    (message.actions && message.actions.length > 0);

  div.innerHTML = `
        <div class="${baseClasses}">
            <div class="flex items-center justify-between">
                <div>${message.action}</div>
                ${
                  hasExpandableContent
                    ? `
                    <button class="text-gray-400 hover:text-gray-200 transition-colors expand-button">
                        <svg class="w-4 h-4 transform transition-transform ${
                          expandedMessages.has(index) ? "rotate-180" : ""
                        }"
                            fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                        </svg>
                    </button>
                `
                    : ""
                }
            </div>
            ${expandedMessages.has(index) ? createExpandedContent(message) : ""}
        </div>
    `;

  if (hasExpandableContent) {
    const expandButton = div.querySelector(".expand-button");
    expandButton.onclick = (e) => toggleMessageExpand(index, e);
  }

  return div;
}

function createExpandedContent(message) {
  return `
        <div class="mt-2 space-y-2 text-sm border-t border-gray-700 pt-2">
            ${
              message.memory
                ? `
                <div>
                    <div class="font-medium text-gray-400">Memory:</div>
                    <div class="text-gray-300">${message.memory}</div>
                </div>
            `
                : ""
            }
            
            ${
              message.next_goal
                ? `
                <div>
                    <div class="font-medium text-gray-400">Next Goal:</div>
                    <div class="text-gray-300">${message.next_goal}</div>
                </div>
            `
                : ""
            }
            
            ${
              message.actions && message.actions.length > 0
                ? `
                <div>
                    <div class="font-medium text-gray-400">Planned Actions:</div>
                    <div class="text-gray-300">
                        ${message.actions
                          .map(
                            (action, i) => `
                            <div class="ml-2">${i + 1}. ${action}</div>
                        `
                          )
                          .join("")}
                    </div>
                </div>
            `
                : ""
            }
        </div>
    `;
}

function updateMessages() {
  console.log("Updating messages UI");
  const container = document.getElementById("messages-container");
  container.innerHTML = "";
  messages.forEach((message, index) => {
    container.appendChild(createMessageElement(message, index));
  });

  updateScreenshot();
}

function updateScreenshot() {
  const container = document.getElementById("screenshot-container");
  const img = document.getElementById("screenshot");

  if (messages.length > 0) {
    const currentMessage =
      messages[selectedMessageIndex ?? messages.length - 1];
    if (currentMessage.screenshot) {
      container.classList.remove("hidden");
      img.src = `data:image/png;base64,${currentMessage.screenshot}`;
    }
  }
}

function handleMessageSelect(index) {
  selectedMessageIndex = index;
  updateMessages();
  document.getElementById("live-button").classList.remove("hidden");
}

function returnToLive() {
  selectedMessageIndex = null;
  updateMessages();
  document.getElementById("live-button").classList.add("hidden");
}

function toggleMessageExpand(index, event) {
  event.stopPropagation();
  if (expandedMessages.has(index)) {
    expandedMessages.delete(index);
  } else {
    expandedMessages.add(index);
  }
  updateMessages();
}

function updateGoal(goal) {
  const container = document.getElementById("goal-container");
  const goalElement = document.getElementById("current-goal");

  if (goal) {
    container.classList.remove("hidden");
    goalElement.textContent = goal;
  } else {
    container.classList.add("hidden");
  }
}

function initializeApp() {
  microsoftTeams.app
    .initialize()
    .then(() => {
      return microsoftTeams.app.getContext();
    })
    .then((context) => {
      if (context.user?.id) {
        connectSocket(context.user.id);
      }
    })
    .catch(console.error);

  document.getElementById("live-button").onclick = returnToLive;
}

function connectSocket(userId) {
  socket = io("http://localhost:3978", {
    transports: ["websocket"],
    query: { userAadId: userId },
  });

  socket.on("connect", () => updateConnectionStatus(true));
  socket.on("disconnect", () => updateConnectionStatus(false));

  socket.on("message", (message) => {
    console.log("Received message:", message);
    messages.push(message);
    console.log("Messages array:", messages);
    updateMessages();
  });

  socket.on("reset", () => {
    messages = [];
    currentGoal = null;
    updateMessages();
    updateGoal(null);
  });

  socket.on("initializeState", (state) => {
    if (state.messages && Array.isArray(state.messages)) {
      messages = state.messages;
      updateMessages();
    }
  });

  socket.on("initializeGoal", (goal) => {
    currentGoal = goal;
    updateGoal(goal);
  });
}

initializeApp();
