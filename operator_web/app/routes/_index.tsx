import * as teamsjs from "@microsoft/teams-js";
import type { MetaFunction } from "@remix-run/node";
import { useEffect, useRef, useState } from "react";
import { io, Socket } from "socket.io-client";

const { app } = teamsjs;

export const meta: MetaFunction = () => {
  return [
    { title: "New Remix App" },
    { name: "description", content: "Welcome to Remix!" },
  ];
};

interface Message {
  screenshot: string;
  action: string;
  memory?: string;
  next_goal?: string;
  actions?: string[];
}

export default function Index() {
  const socket = useRef<Socket | null>(null);
  const [messages, setMessages] = useState<Array<Message>>([]);
  const [text, setText] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [currentGoal, setCurrentGoal] = useState<string | null>(null);
  const [selectedMessageIndex, setSelectedMessageIndex] = useState<
    number | null
  >(null);
  const [expandedMessages, setExpandedMessages] = useState<Set<number>>(
    new Set()
  );

  const clickHandler = () => {
    console.log("clicked");
    if (!text) return;
    socket.current?.emit("message", text);
    setMessages((messages) => [
      ...messages,
      { screenshot: "", action: `Web: ${text}` },
    ]);
  };

  const handleMessageSelect = (index: number) => {
    setSelectedMessageIndex(index);
  };

  const returnToLive = () => {
    setSelectedMessageIndex(null);
  };

  const toggleMessageExpand = (index: number, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent triggering message selection
    setExpandedMessages((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  useEffect(() => {
    const connectSocket = (userId: string) => {
      console.log("connecting socket");
      socket.current = io("http://localhost:3978", {
        transports: ["websocket"],
        query: { userAadId: userId },
      });

      socket.current.on("connect", () => {
        setIsConnected(true);
      });

      socket.current.on("disconnect", () => {
        setIsConnected(false);
      });

      socket.current.on("message", (message) => {
        console.log("received message", message);
        setMessages((messages) => [...messages, message]);
      });

      socket.current.on("reset", () => {
        setMessages([]);
        setCurrentGoal(null);
      });

      socket.current.on(
        "initializeState",
        (state: {
          messages: Array<{ screenshot: string; action: string }>;
        }) => {
          console.log("initializing state", state);
          if (state.messages && Array.isArray(state.messages)) {
            setMessages(state.messages);
          }
        }
      );

      socket.current.on("initializeGoal", (goal: string) => {
        setCurrentGoal(goal);
      });
    };
    console.log("initializing app");
    app
      .initialize()
      .then(() => {
        console.log("app initialized");
        return app.getContext();
      })
      .then((context) => {
        if (context.user?.id) {
          console.log(context.user);
          connectSocket(context.user.id);
        }
      })
      .catch(console.error);

    return () => {
      console.log("disconnecting socket");
      socket.current?.disconnect();
    };
  }, []);

  return (
    <div className="flex flex-col h-screen w-full bg-gray-950">
      <div className="w-full bg-gray-900 border-b border-gray-700 p-4 flex justify-between items-center">
        <h1 className="text-xl font-bold text-gray-100">Operator</h1>
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              isConnected ? "bg-green-500" : "bg-red-500"
            }`}
          />
          <span className="text-sm text-gray-300">
            {isConnected ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>

      <div className="flex flex-1 p-4">
        <div className="flex flex-col w-[80%] pr-4">
          <div className="flex flex-col gap-4 h-full overflow-y-auto">
            {messages.length > 0 && (
              <div className="border border-gray-700 rounded-lg p-2 bg-gray-900">
                <img
                  src={`data:image/png;base64,${
                    messages[selectedMessageIndex ?? messages.length - 1]
                      .screenshot
                  }`}
                  alt="Browser state"
                  className="w-full"
                />
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-col w-[20%]">
          {currentGoal && (
            <div className="mb-4 p-3 bg-gray-800 border border-gray-600 rounded-lg">
              <div className="text-sm font-medium text-gray-400 mb-1">
                Current Goal:
              </div>
              <div className="text-gray-100">{currentGoal}</div>
            </div>
          )}
          <div className="flex flex-col gap-2 overflow-y-auto">
            {messages.map((message, index) => (
              <div
                key={`action-${index}`}
                className="flex flex-col gap-1"
                onClick={() => handleMessageSelect(index)}
              >
                <div
                  className={`p-2 rounded cursor-pointer transition-colors ${
                    message.action.startsWith("Web:")
                      ? "bg-blue-900 text-gray-100"
                      : index === selectedMessageIndex
                      ? "bg-gray-800 border border-gray-600 text-gray-100"
                      : "bg-gray-900 border border-gray-700 text-gray-100"
                  } hover:border-gray-600`}
                >
                  <div className="flex items-center justify-between">
                    <div>{message.action}</div>
                    {(message.memory ||
                      message.next_goal ||
                      (message.actions && message.actions.length > 0)) && (
                      <button
                        onClick={(e) => toggleMessageExpand(index, e)}
                        className="text-gray-400 hover:text-gray-200 transition-colors"
                      >
                        <svg
                          className={`w-4 h-4 transform transition-transform ${
                            expandedMessages.has(index) ? "rotate-180" : ""
                          }`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M19 9l-7 7-7-7"
                          />
                        </svg>
                      </button>
                    )}
                  </div>

                  {expandedMessages.has(index) && (
                    <div className="mt-2 space-y-2 text-sm border-t border-gray-700 pt-2">
                      {message.memory && (
                        <div>
                          <div className="font-medium text-gray-400">
                            Memory:
                          </div>
                          <div className="text-gray-300">{message.memory}</div>
                        </div>
                      )}

                      {message.next_goal && (
                        <div>
                          <div className="font-medium text-gray-400">
                            Next Goal:
                          </div>
                          <div className="text-gray-300">
                            {message.next_goal}
                          </div>
                        </div>
                      )}

                      {message.actions && message.actions.length > 0 && (
                        <div>
                          <div className="font-medium text-gray-400">
                            Planned Actions:
                          </div>
                          <div className="text-gray-300">
                            {message.actions.map((action, i) => (
                              <div key={i} className="ml-2">
                                {i + 1}. {action}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {selectedMessageIndex !== null && (
        <div
          className="fixed bottom-4 right-4 bg-red-600 text-white px-4 py-2 rounded-lg cursor-pointer hover:bg-red-700 transition-colors shadow-lg"
          onClick={returnToLive}
        >
          Jump to live
        </div>
      )}
    </div>
  );
}
