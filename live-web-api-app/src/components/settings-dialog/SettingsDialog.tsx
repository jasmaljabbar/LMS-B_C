import {
  ChangeEvent,
  FormEventHandler,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import "./settings-dialog.scss";
import { useLiveAPIContext } from "../../contexts/LiveAPIContext";
import { LiveConfig } from "../../multimodal-live-types";
import {
  FunctionDeclaration,
  FunctionDeclarationsTool,
  Tool,
} from "@google/generative-ai";
import VoiceSelector from "./VoiceSelector";
import ResponseModalitySelector from "./ResponseModalitySelector";

export default function SettingsDialog() {
  const [open, setOpen] = useState(false);
  const { config, setConfig, connected } = useLiveAPIContext();
  const [editing, setEditing] = useState<boolean>(false);
  const [editableInstruction, setEditableInstruction] = useState<string>("");

  const languages = [
    "English",
    "French",
    "Spanish",
    "German",
    "Hindi",
    "Tamil",
    "Malayalam",
    "Chinese",
    "Japanese",
  ];

  const [selectedLanguage, setSelectedLanguage] = useState("English");
  const params = new URLSearchParams(window.location.search);
  const subjectName = params.get('subjectName')
  const accesstoken = params.get('accessToken')
  const termId = params.get('termId')
  const [term, setTerm] = useState(null)

  const functionDeclarations: FunctionDeclaration[] = useMemo(() => {
    if (!Array.isArray(config.tools)) {
      return [];
    }
    return (config.tools as Tool[])
      .filter((t: Tool): t is FunctionDeclarationsTool =>
        Array.isArray((t as any).functionDeclarations)
      )
      .map((t) => t.functionDeclarations)
      .filter((fc) => !!fc)
      .flat();
  }, [config]);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const response = await fetch(`https://lms-backend-931876132356.us-central1.run.app/terms/${termId}`, {
          headers: {
            Authorization: `Bearer ${accesstoken}`,
            'Content-Type': 'application/json',
          },
        });

        const termName = await response.json()
        setTerm(termName?.name)

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

      } catch (err) {
        console.error('Error fetching student data:', err);
      }
    };
    fetchInitialData();
  }, [])

  // const systemInstruction = useMemo(() => {
  //   const s = config.systemInstruction?.parts.find((p) => p.text)?.text || "";

  //   return s;
  // }, [config]);

  const systemInstruction = useMemo(() => {
    return `You are a student of <span style="color:#4A90E2;font-weight:bold;">Grade 6</span> and you should only reply based on this grade student IQ level and it should reply in <span style="color:#4A90E2;font-weight:bold;">${selectedLanguage}</span> language.`;
  }, [selectedLanguage]);


  useEffect(() => {
    // const updatedInstruction = `You are a student of Grade 6 and you should only reply based on this grade student IQ level and it should reply in ${selectedLanguage} language.`;
    const updatedInstruction = `You are a ${subjectName} Teacher of ${term ? term : ""}   and you should only reply based on
     this student IQ level and it should reply in ${selectedLanguage} language.`
    const newConfig: LiveConfig = {
      ...config,
      systemInstruction: {
        parts: [{ text: updatedInstruction }],
      },
    };
    setConfig(newConfig);
    setEditableInstruction(updatedInstruction); // Keep editable state in sync
  }, [selectedLanguage, term])


  const updateConfig: FormEventHandler<HTMLTextAreaElement> = useCallback(
    (event: ChangeEvent<HTMLTextAreaElement>) => {
      const newConfig: LiveConfig = {
        ...config,
        systemInstruction: {
          parts: [{ text: event.target.value }],
        },
      };
      setConfig(newConfig);
    },
    [config, setConfig]
  );

  const updateFunctionDescription = useCallback(
    (editedFdName: string, newDescription: string) => {
      const newConfig: LiveConfig = {
        ...config,
        tools:
          config.tools?.map((tool) => {
            const fdTool = tool as FunctionDeclarationsTool;
            if (!Array.isArray(fdTool.functionDeclarations)) {
              return tool;
            }
            return {
              ...tool,
              functionDeclarations: fdTool.functionDeclarations.map((fd) =>
                fd.name === editedFdName
                  ? { ...fd, description: newDescription }
                  : fd
              ),
            };
          }) || [],
      };
      setConfig(newConfig);
    },
    [config, setConfig]
  );

  return (
    <div className="settings-dialog">
      <button
        className="action-button material-symbols-outlined"
        onClick={() => setOpen(!open)}
      >
        settings
      </button>
      <dialog className="dialog" style={{ display: open ? "block" : "none" }}>
        <div className={`dialog-container ${connected ? "disabled" : ""}`}>
          {connected && (
            <div className="connected-indicator">
              <p>
                These settings can only be applied before connecting and will
                override other settings.
              </p>
            </div>
          )}
          <div className="mode-selectors">
            {/* <ResponseModalitySelector /> */}
            <VoiceSelector />
          </div>

          <div className="language-selector">
            <label htmlFor="language">Choose Language:</label>
            <select
              id="language"
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              style={{
                backgroundColor: "var(--Neutral-15)",
                color: "var(--Neutral-90)",
                border: "none",
                minHeight: "33px",
                maxHeight: "33px",
                padding: "4px 12px",
                borderRadius: "4px",
                fontSize: "14px",
                width: "100%",
                appearance: "none",
                WebkitAppearance: "none",
                MozAppearance: "none",
                backgroundImage:
                  "url(\"data:image/svg+xml;charset=US-ASCII,%3Csvg width='10' height='6' viewBox='0 0 10 6' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23999' stroke-width='1.5' fill='none' fill-rule='evenodd'/%3E%3C/svg%3E\")",
                backgroundRepeat: "no-repeat",
                backgroundPosition: "right 12px center",
                backgroundSize: "10px 6px",
                cursor: "pointer",
              }}
            >
              {languages.map((lang) => (
                <option key={lang} value={lang}>
                  {lang}
                </option>
              ))}
            </select>
          </div>


          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginTop: "20px",
            }}
          >
            <h3 style={{ margin: 0 }}>System Instructions</h3>
            <button
              onClick={() => {
                if (editing) {
                  // Save updated config
                  const newConfig: LiveConfig = {
                    ...config,
                    systemInstruction: {
                      parts: [{ text: editableInstruction }],
                    },
                  };
                  setConfig(newConfig);
                }
                setEditing(!editing);
              }}
              style={{
                background: "none",
                border: "none",
                color: "#4A90E2",
                fontWeight: "bold",
                cursor: "pointer",
                textDecoration: "underline",
                fontSize: "14px",
              }}
            >
              {editing ? "Save" : "Edit"}
            </button>
          </div>

          {editing ? (
            <textarea
              className="system"
              value={editableInstruction}
              onChange={(e: ChangeEvent<HTMLTextAreaElement>) =>
                setEditableInstruction(e.target.value)
              }
              style={{
                width: "100%",
                minHeight: "100px",
                padding: "10px",
                backgroundColor: "var(--Neutral-15)",
                color: "var(--Neutral-90)",
                border: "1px solid var(--Neutral-30)",
                borderRadius: "4px",
                fontSize: "14px",
              }}
            />
          ) : (
            <div
              className="system"
              style={{
                padding: "10px",
                backgroundColor: "var(--Neutral-15)",
                color: "var(--Neutral-90)",
                borderRadius: "4px",
                lineHeight: "1.5em",
              }}
              dangerouslySetInnerHTML={{ __html: editableInstruction }}
            />
          )}


          {/* <div
            className="system"
            style={{
              padding: "10px",
              backgroundColor: "var(--Neutral-15)",
              color: "var(--Neutral-90)",
              borderRadius: "4px",
              lineHeight: "1.5em",
            }}
            dangerouslySetInnerHTML={{ __html: systemInstruction }}
          /> */}

          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              marginTop: "20px",
            }}
          >
            <button
              onClick={() => setOpen(false)}
              style={{
                padding: "8px 16px",
                backgroundColor: "#4A90E2",
                color: "#fff",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
                fontWeight: "bold",
              }}
            >
              OK
            </button>
          </div>
        </div>
      </dialog>
    </div>
  );
}
