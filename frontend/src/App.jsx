import React, { useState, useEffect } from "react";
import { API_URL } from "./config";
import { 
  FileText, 
  MessageSquare, 
  LogOut, 
  Sun, 
  Moon, 
  Upload, 
  CheckSquare, 
  Square, 
  Send, 
  Lock, 
  Mail, 
  FileQuestion,
  HelpCircle,
  BarChart,
  ShieldAlert
} from "lucide-react";

export default function App() {
  // Theme state
  const [darkMode, setDarkMode] = useState(true);

  // Auth state
  const [userEmail, setUserEmail] = useState(localStorage.getItem("user_email") || null);
  const [authMode, setAuthMode] = useState("login"); // 'login' or 'register'
  const [emailInput, setEmailInput] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const [authError, setAuthError] = useState("");
  const [authSuccess, setAuthSuccess] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  // Active module
  const [activeTab, setActiveTab] = useState("analyzer"); // 'analyzer' or 'chatbot'

  // PDF Analyzer state
  const [pdfFile, setPdfFile] = useState(null);
  const [summarizeChecked, setSummarizeChecked] = useState(true);
  const [classifyChecked, setClassifyChecked] = useState(true);
  const [qaChecked, setQaChecked] = useState(false);
  const [qaQuery, setQaQuery] = useState("");
  const [processing, setProcessing] = useState(false);
  const [processError, setProcessError] = useState("");
  const [processResult, setProcessResult] = useState(null);

  // General Chatbot state
  const [chatInput, setChatInput] = useState("");
  const [chatHistory, setChatHistory] = useState([
    {
      sender: "bot",
      text: "Hello! I am GeniFi, your concise finance assistant. How can I help you with budgeting, loans, investing, or tax questions today?"
    }
  ]);
  const [chatLoading, setChatLoading] = useState(false);

  // Sync theme to body element
  useEffect(() => {
    if (darkMode) {
      document.body.classList.remove("light-theme");
    } else {
      document.body.classList.add("light-theme");
    }
  }, [darkMode]);

  // Auth Handlers
  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthError("");
    setAuthSuccess("");
    
    if (!emailInput.trim() || !passwordInput.trim()) {
      setAuthError("Please enter both email and password.");
      return;
    }
    if (passwordInput.length < 8) {
      setAuthError("Password must be at least 8 characters.");
      return;
    }

    setAuthLoading(true);
    const endpoint = authMode === "login" ? "/login/" : "/register/";
    
    try {
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: emailInput, password: passwordInput }),
      });

      const data = await response.json();

      if (!response.ok) {
        if (Array.isArray(data.detail)) {
          throw new Error(data.detail[0]?.msg || "Authentication failed");
        }
        throw new Error(data.detail || "Authentication failed");
      }

      if (authMode === "login") {
        localStorage.setItem("user_email", emailInput);
        setUserEmail(emailInput);
        setEmailInput("");
        setPasswordInput("");
      } else {
        setAuthSuccess("Registration successful! Please log in.");
        setAuthMode("login");
        setPasswordInput("");
      }
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("user_email");
    setUserEmail(null);
    setProcessResult(null);
    setPdfFile(null);
    setChatHistory([
      {
        sender: "bot",
        text: "Hello! I am GeniFi, your concise finance assistant. How can I help you with budgeting, loans, investing, or tax questions today?"
      }
    ]);
  };

  // PDF Upload & Process Handlers
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file && file.type === "application/pdf") {
      setPdfFile(file);
      setProcessError("");
      setProcessResult(null);
    } else if (file) {
      setProcessError("Only PDF files are supported.");
    }
  };

  const handleProcessPdf = async () => {
    if (!pdfFile) {
      setProcessError("Please select a PDF file first.");
      return;
    }
    if (!summarizeChecked && !classifyChecked && !qaChecked) {
      setProcessError("Please select at least one processing option.");
      return;
    }
    if (qaChecked && !qaQuery.trim()) {
      setProcessError("Please enter your question about the PDF.");
      return;
    }

    setProcessing(true);
    setProcessError("");
    setProcessResult(null);

    // Read file as base64 DataURL
    const reader = new FileReader();
    reader.readAsDataURL(pdfFile);
    reader.onload = async () => {
      try {
        const base64Data = reader.result;
        
        const response = await fetch(`${API_URL}/process/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            filename: pdfFile.name,
            filedata: base64Data,
            summarize_checked: summarizeChecked,
            classify_checked: classifyChecked,
            qa_checked: qaChecked,
            qa_query: qaChecked ? qaQuery : null,
            user_id: userEmail
          }),
        });

        const textResponse = await response.text();
        let data;
        try {
          data = JSON.parse(textResponse);
        } catch (e) {
          throw new Error("Invalid backend JSON response.");
        }

        if (!response.ok) {
          throw new Error(data.detail || "PDF processing failed.");
        }

        setProcessResult(data);
      } catch (err) {
        setProcessError(err.message);
      } finally {
        setProcessing(false);
      }
    };

    reader.onerror = () => {
      setProcessError("Error reading the PDF file.");
      setProcessing(false);
    };
  };

  // Chatbot Handler
  const handleSendChat = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;

    const userMessage = chatInput.trim();
    setChatInput("");
    setChatHistory(prev => [...prev, { sender: "user", text: userMessage }]);
    setChatLoading(true);

    try {
      const response = await fetch(`${API_URL}/general-chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMessage, user_id: userEmail }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Chat failed");
      }

      setChatHistory(prev => [...prev, { sender: "bot", text: data.answer }]);
    } catch (err) {
      setChatHistory(prev => [
        ...prev, 
        { sender: "bot", text: `Error: Could not reach the server. (${err.message})` }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  // Render Redacted Text Helper
  const formatRedactedText = (text) => {
    if (!text) return "";
    const parts = text.split("[REDACTED]");
    return parts.map((part, i) => (
      <React.Fragment key={i}>
        {part}
        {i < parts.length - 1 && <span className="redacted-highlight">[REDACTED]</span>}
      </React.Fragment>
    ));
  };

  // -------------------------------------------------------------
  // RENDER AUTH PAGE
  // -------------------------------------------------------------
  if (!userEmail) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <div className="auth-header">
            <span className="auth-logo">💼</span>
            <h2 className="auth-title">GeniFi AI</h2>
            <p className="auth-subtitle">Financial Document Intelligence Suite</p>
          </div>

          {authError && <div className="alert alert-danger">{authError}</div>}
          {authSuccess && <div className="alert alert-success">{authSuccess}</div>}

          <form onSubmit={handleAuth}>
            <div className="form-group">
              <label className="form-label" htmlFor="email-input">Email Address</label>
              <div style={{ position: "relative" }}>
                <Mail size={18} style={{ position: "absolute", left: "14px", top: "15px", color: "var(--text-muted)" }} />
                <input
                  id="email-input"
                  type="email"
                  className="form-input"
                  placeholder="name@company.com"
                  style={{ paddingLeft: "44px" }}
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="password-input">Password</label>
              <div style={{ position: "relative" }}>
                <Lock size={18} style={{ position: "absolute", left: "14px", top: "15px", color: "var(--text-muted)" }} />
                <input
                  id="password-input"
                  type="password"
                  className="form-input"
                  placeholder="Min. 8 characters"
                  style={{ paddingLeft: "44px" }}
                  value={passwordInput}
                  onChange={(e) => setPasswordInput(e.target.value)}
                  required
                />
              </div>
            </div>

            <button type="submit" className="btn-primary" disabled={authLoading}>
              {authLoading ? (
                <div className="btn-loading">
                  <div className="spinner"></div> Authenticating...
                </div>
              ) : (
                authMode === "login" ? "Log In" : "Register Account"
              )}
            </button>
          </form>

          <div className="auth-switch">
            {authMode === "login" ? (
              <>Don't have an account? <span onClick={() => { setAuthMode("register"); setAuthError(""); }}>Create one</span></>
            ) : (
              <>Already have an account? <span onClick={() => { setAuthMode("login"); setAuthError(""); }}>Log in</span></>
            )}
          </div>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // RENDER MAIN APPLICATION DASHBOARD
  // -------------------------------------------------------------
  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo-container">
          <span className="logo-icon">💼</span>
          <span className="logo-text">GeniFi</span>
        </div>

        <nav className="nav-links">
          <div 
            className={`nav-item ${activeTab === "analyzer" ? "active" : ""}`}
            onClick={() => setActiveTab("analyzer")}
          >
            <FileText size={18} />
            <span>Document Analyzer</span>
          </div>
          <div 
            className={`nav-item ${activeTab === "chatbot" ? "active" : ""}`}
            onClick={() => setActiveTab("chatbot")}
          >
            <MessageSquare size={18} />
            <span>Finance Chatbot</span>
          </div>
        </nav>

        <div className="sidebar-footer">
          <div className="theme-toggle" onClick={() => setDarkMode(!darkMode)}>
            <span>{darkMode ? "Dark Theme" : "Light Theme"}</span>
            <div className="theme-toggle-icon">
              {darkMode ? <Moon size={15} color="#b983ff" /> : <Sun size={15} color="#e5a93b" />}
            </div>
          </div>

          <div style={{ padding: "0 8px", fontSize: "13px", color: "var(--text-muted)", wordBreak: "break-all" }}>
            User: {userEmail}
          </div>

          <button className="logout-btn" onClick={handleLogout}>
            <LogOut size={16} />
            <span>Log Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {activeTab === "analyzer" ? (
          <div>
            <h1 className="dashboard-title">Financial Document Intelligence</h1>
            <p className="dashboard-desc">Upload reports, balance sheets, or contracts for advanced summary masking, categorization, and QA extraction.</p>

            <div className="glass-card">
              {/* File Uploader */}
              <div 
                className="upload-zone"
                onClick={() => document.getElementById("pdf-file-picker").click()}
              >
                <input 
                  id="pdf-file-picker" 
                  type="file" 
                  accept=".pdf" 
                  style={{ display: "none" }} 
                  onChange={handleFileChange}
                />
                <Upload className="upload-icon" color="var(--border-focus)" />
                <p className="upload-text">Click to choose or drop your PDF document here</p>
                <p className="upload-subtext">Supported file format: PDF (up to 10MB)</p>

                {pdfFile && (
                  <div className="selected-file-badge" onClick={(e) => e.stopPropagation()}>
                    <span>📄 {pdfFile.name} ({(pdfFile.size / 1024 / 1024).toFixed(2)} MB)</span>
                    <button 
                      className="remove-file-btn" 
                      onClick={() => { setPdfFile(null); setProcessResult(null); }}
                      title="Remove file"
                    >
                      &times;
                    </button>
                  </div>
                )}
              </div>

              {/* Analyzer Options */}
              <div style={{ marginTop: "28px" }}>
                <h3 className="options-title">AI Processing Modules</h3>
                <div className="options-grid">
                  <div 
                    className={`option-checkbox-card ${summarizeChecked ? "selected" : ""}`}
                    onClick={() => setSummarizeChecked(!summarizeChecked)}
                  >
                    <input 
                      type="checkbox" 
                      checked={summarizeChecked} 
                      onChange={() => {}} // Controlled by card click
                    />
                    <div className="option-label-container">
                      <span className="option-label">Masked Summary</span>
                      <span className="option-desc">BART-powered summary with redacted PII & financial details.</span>
                    </div>
                  </div>

                  <div 
                    className={`option-checkbox-card ${classifyChecked ? "selected" : ""}`}
                    onClick={() => setClassifyChecked(!classifyChecked)}
                  >
                    <input 
                      type="checkbox" 
                      checked={classifyChecked} 
                      onChange={() => {}}
                    />
                    <div className="option-label-container">
                      <span className="option-label">Document Classification</span>
                      <span className="option-desc">Categorizes into 9 distinct finance document structures.</span>
                    </div>
                  </div>

                  <div 
                    className={`option-checkbox-card ${qaChecked ? "selected" : ""}`}
                    onClick={() => setQaChecked(!qaChecked)}
                  >
                    <input 
                      type="checkbox" 
                      checked={qaChecked} 
                      onChange={() => {}}
                    />
                    <div className="option-label-container">
                      <span className="option-label">PDF Question Answering</span>
                      <span className="option-desc">Ask specific details and query facts inside the uploaded PDF.</span>
                    </div>
                  </div>
                </div>

                {/* PDF QA Question Input */}
                {qaChecked && (
                  <div className="qa-input-container form-group">
                    <label className="form-label" htmlFor="pdf-qa-query">Question for this PDF</label>
                    <div style={{ position: "relative" }}>
                      <FileQuestion size={18} style={{ position: "absolute", left: "14px", top: "15px", color: "var(--text-muted)" }} />
                      <input
                        id="pdf-qa-query"
                        type="text"
                        className="form-input"
                        placeholder="e.g. What is the total operating income reported?"
                        style={{ paddingLeft: "44px" }}
                        value={qaQuery}
                        onChange={(e) => setQaQuery(e.target.value)}
                      />
                    </div>
                  </div>
                )}

                {processError && <div className="alert alert-danger" style={{ marginTop: "20px" }}>{processError}</div>}

                {/* Submit button */}
                <div className="process-btn-wrapper" style={{ marginTop: "24px" }}>
                  <button 
                    className="btn-primary" 
                    style={{ width: "auto", padding: "14px 32px" }}
                    onClick={handleProcessPdf}
                    disabled={processing || !pdfFile}
                  >
                    {processing ? (
                      <div className="btn-loading">
                        <div className="spinner"></div> Processing Document...
                      </div>
                    ) : (
                      "Run AI Analysis"
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Showcase Results */}
            {processResult && (
              <div className="results-grid">
                <h2 style={{ fontSize: "22px", fontWeight: "700", borderBottom: "1px solid var(--border-glass)", paddingBottom: "8px" }}>
                  Analysis Output ({processResult.filename})
                </h2>

                {processResult.result.classification && (
                  <div className="result-card">
                    <div className="result-header">
                      <div className="result-title">
                        <BarChart size={18} color="var(--border-focus)" />
                        <span>Document Structure Class</span>
                      </div>
                      <span className="result-badge">Confidence: {(processResult.result.classification.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="result-content" style={{ textTransform: "capitalize", fontWeight: "600", fontSize: "16px", color: "var(--text-primary)" }}>
                      {processResult.result.classification.label.replace(/_/g, " ")}
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
                      Method: {processResult.result.classification.method}
                    </div>
                  </div>
                )}

                {processResult.result.summary && (
                  <div className="result-card">
                    <div className="result-header">
                      <div className="result-title">
                        <ShieldAlert size={18} color="#ef4444" />
                        <span>PII-Redacted Finance Summary</span>
                      </div>
                      <span className="result-badge" style={{ background: "rgba(239, 68, 68, 0.1)", color: "#ef4444", borderColor: "rgba(239, 68, 68, 0.2)" }}>Protected</span>
                    </div>
                    <div className="result-content">
                      {formatRedactedText(processResult.result.summary)}
                    </div>
                  </div>
                )}

                {processResult.result.pdf_answer && (
                  <div className="result-card">
                    <div className="result-header">
                      <div className="result-title">
                        <FileQuestion size={18} color="var(--border-focus)" />
                        <span>PDF Q&A Response</span>
                      </div>
                    </div>
                    <div className="result-content" style={{ color: "var(--text-primary)" }}>
                      <strong>Q: "{qaQuery}"</strong>
                      <p style={{ marginTop: "8px", borderLeft: "3px solid var(--border-focus)", paddingLeft: "12px", fontStyle: "italic" }}>
                        {processResult.result.pdf_answer}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div>
            <h1 className="dashboard-title">GeniFi Finance Assistant</h1>
            <p className="dashboard-desc">Ask queries regarding budgeting principles, stock valuation basics, EMI comparative metrics, and general financial topics.</p>

            <div className="glass-card chat-container">
              <div className="chat-history">
                {chatHistory.map((msg, i) => (
                  <div key={i} className={`chat-bubble ${msg.sender}`}>
                    {msg.text}
                  </div>
                ))}
                {chatLoading && (
                  <div className="chat-bubble bot" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div className="spinner" style={{ borderTopColor: "var(--text-primary)", width: "14px", height: "14px", borderWidth: "2px" }}></div>
                    <span>GeniFi is composing response...</span>
                  </div>
                )}
              </div>

              <form onSubmit={handleSendChat} className="chat-input-row">
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Explain compound interest vs simple interest"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  disabled={chatLoading}
                  required
                />
                <button type="submit" className="btn-primary" disabled={chatLoading || !chatInput.trim()}>
                  <Send size={16} />
                </button>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
