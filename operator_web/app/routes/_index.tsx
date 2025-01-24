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

export default function Index() {
  const socket = useRef<Socket | null>(null);
  const [messages, setMessages] = useState<
    Array<{ screenshot: string; action: string }>
  >([]);
  const [text, setText] = useState("");
  const clickHandler = () => {
    console.log("clicked");
    if (!text) return;
    socket.current?.emit("message", text);
    setMessages((messages) => [
      ...messages,
      { screenshot: "", action: `Web: ${text}` },
    ]);
  };

  useEffect(() => {
    const connectSocket = (userId: string) => {
      console.log("connecting socket");
      socket.current = io("http://localhost:3978", {
        transports: ["websocket"],
        query: { userAadId: userId },
      });

      socket.current.on("message", (message) => {
        console.log("received message", message);
        setMessages((messages) => [...messages, message]);
      });

      socket.current.on("initializeState", (state) => {
        console.log("initializing state", state);
        setMessages(state.messages ?? []);
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
    <div className="flex h-screen w-full p-4 bg-gray-950">
      <div className="flex flex-col w-[80%] pr-4">
        <div className="flex flex-col gap-4 h-full overflow-y-auto">
          {messages.length > 0 && messages[messages.length - 1].screenshot && (
            <div className="border border-gray-700 rounded-lg p-2 bg-gray-900">
              <img
                src={`data:image/png;base64,${
                  messages[messages.length - 1].screenshot
                }`}
                alt="Current browser state"
                className="w-full"
              />
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-col w-[20%]">
        <div className="flex flex-col gap-2 overflow-y-auto">
          {messages.map((message, index) => (
            <div
              key={`action-${index}`}
              className={`p-2 rounded ${
                message.action.startsWith("Web:")
                  ? "bg-blue-900 text-gray-100"
                  : "bg-gray-900 border border-gray-700 text-gray-100"
              }`}
            >
              {message.action}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
