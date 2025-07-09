import "./react-select.scss";
import cn from "classnames";
import { useEffect, useRef, useState } from "react";
import { RiSidebarFoldLine, RiSidebarUnfoldLine } from "react-icons/ri";
import Select from "react-select";
import { useLiveAPIContext } from "../../contexts/LiveAPIContext";
import { useLoggerStore } from "../../lib/store-logger";
import Logger, { LoggerFilterType } from "../logger/Logger";
import "./side-panel.scss";

const filterOptions = [
  { value: "conversations", label: "Conversations" },
  { value: "tools", label: "Tool Use" },
  { value: "none", label: "All" },
];

export default function SidePanel() {
  const { connected, client } = useLiveAPIContext();
  const [open, setOpen] = useState(false); // Start with the panel minimized
  const loggerRef = useRef<HTMLDivElement>(null);
  const loggerLastHeightRef = useRef<number>(-1);
  const { log, logs } = useLoggerStore();

  const [textInput, setTextInput] = useState("");
  const [selectedOption, setSelectedOption] = useState<{
    value: string;
    label: string;
  } | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Scroll the log to the bottom when new logs come in
  useEffect(() => {
    if (loggerRef.current) {
      const el = loggerRef.current;
      const scrollHeight = el.scrollHeight;
      if (scrollHeight !== loggerLastHeightRef.current) {
        el.scrollTop = scrollHeight;
        loggerLastHeightRef.current = scrollHeight;
      }
    }
  }, [logs]);

  // Listen for log events and store them
  useEffect(() => {
    client.on("log", log);
    return () => {
      client.off("log", log);
    };
  }, [client, log]);

  const handleSubmit = () => {
    client.send([{ text: textInput }]);
    setTextInput("");
    if (inputRef.current) {
      inputRef.current.innerText = "";
    }
  };

  return (
    <>
      {/* Minimized Panel Button */}
      <div
        className={`chat-toggle-btn ${open ? "open" : ""}`}
        onClick={() => setOpen((prev) => !prev)}
      >
        {open ? (
          <RiSidebarFoldLine size={30} color="#fff" />
        ) : (
          <RiSidebarUnfoldLine size={30} color="#fff" />
        )}
      </div>

      {/* Side Panel */}
      <div className={`side-panel ${open ? "open" : "closed"}`}>
        <header className="top">
          <h2>Virtual Teacher AI</h2>
          <button className="opener" onClick={() => setOpen(false)}>
            <RiSidebarFoldLine color="#b4b8bb" />
          </button>
        </header>

        <section className="indicators">
          {/* React Select for filter options */}
          {/* <Select
            className="react-select"
            classNamePrefix="react-select"
            styles={{
              control: (baseStyles) => ({
                ...baseStyles,
                background: "var(--Neutral-15)",
                color: "var(--Neutral-90)",
                minHeight: "33px",
                maxHeight: "33px",
                border: 0,
              }),
              option: (styles, { isFocused, isSelected }) => ({
                ...styles,
                backgroundColor: isFocused
                  ? "var(--Neutral-30)"
                  : isSelected
                  ? "var(--Neutral-20)"
                  : undefined,
              }),
            }}
            defaultValue={selectedOption}
            options={filterOptions}
            onChange={(e) => setSelectedOption(e)}
          /> */}
          <div
            style={{ width: "100%" }}
            className={cn("streaming-indicator", { connected })}
          >
            {connected ? `🔵${open ? " Streaming" : ""}` : ""}
          </div>
        </section>

        <div className="chat-console">
          <div className="side-panel-container" ref={loggerRef}>
            <Logger
              filter={(selectedOption?.value as LoggerFilterType) || "none"}
            />
          </div>

          <div className={cn("input-container", { disabled: !connected })}>
            <div className="input-content">
              <textarea
                className="input-area"
                ref={inputRef}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    e.stopPropagation();
                    handleSubmit();
                  }
                }}
                onChange={(e) => setTextInput(e.target.value)}
                value={textInput}
                placeholder={!connected ? "Turn on the Streaming and start Messaging..." : "Write your message..."}
              ></textarea>
              <button className="send-button" onClick={handleSubmit}>
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
