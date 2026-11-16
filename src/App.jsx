import { useState } from 'react';
import { ArrowUp, Bot, Check, ChevronDown, ChevronRight, CircleAlert, Copy, Globe2, Layers3, LoaderCircle, Play, Plus, ShieldCheck, TerminalSquare, Zap } from 'lucide-react';

const examples = [
  'Crawl https://example.com, extract the important information, give me a summary, and return the extracted data in JSON format.',
  'Summarize the website https://example.com',
];

function App() {
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  async function submit(prompt = input) {
    const message = prompt.trim();
    if (!message || busy) return;
    setMessages((old) => [...old, { role: 'user', text: message }, { role: 'assistant', loading: true }]);
    setInput(''); setError(''); setBusy(true);
    try {
      const response = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message }) });
      const data = await response.json();
      setMessages((old) => [...old.slice(0, -1), { role: 'assistant', data }]);
      if (!response.ok) setMessages((old) => [...old.slice(0, -1), { role: 'assistant', data: { status: 'failed', error: data.detail || 'The request could not be completed.' } }]);
    } catch {
      setMessages((old) => [...old.slice(0, -1), { role: 'assistant', data: { status: 'failed', error: 'Could not reach the TaskPilot API. Start the backend on port 8000.' } }]);
    } finally { setBusy(false); }
  }

  async function copyJson(result) {
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    setCopied(true); setTimeout(() => setCopied(false), 1500);
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon"><Layers3 size={20}/></div><div><b>TaskPilot</b><small>CLI Execution Assistant</small></div></div>
      <button className="new-task" onClick={() => { setMessages([]); setError(''); }}><Plus size={17}/> New task <span>⌘ K</span></button>
      <div className="side-label">WORKSPACE</div>
      <div className="nav-item active"><div className="nav-icon"><TerminalSquare size={16}/></div><span>Website crawler</span><span className="active-dot"/></div>
      <div className="side-card"><div className="card-icon"><ShieldCheck size={16}/></div><div><b>Safe by design</b><p>Public websites only. Robots.txt respected. Every run is a real CLI process.</p></div></div>
      <div className="sidebar-bottom"><span className="status-dot"/> Local environment <span className="version">v1.0</span></div>
    </aside>
    <main className="main-panel">
      <header className="topbar"><div className="crumb">Workspace <ChevronRight size={14}/> <strong>Website crawler</strong></div><div className="top-right"><span className="secure"><span className="status-dot"/> API connected</span><div className="avatar">TP</div></div></header>
      <div className="conversation">
        {messages.length === 0 ? <section className="welcome">
          <div className="welcome-mark"><Bot size={24}/><span className="sparkle">✦</span></div>
          <div className="eyebrow"><Zap size={13}/> TASK AUTOMATION</div>
          <h1>What should I <span>do for you?</span></h1>
          <p className="welcome-copy">Describe a website task in plain language. TaskPilot will interpret it, run the crawler CLI, and bring the results back here.</p>
          <div className="suggestion-title">TRY A TASK <span>↘</span></div>
          <div className="suggestion-grid">{examples.map((item, i) => <button className="suggestion" key={item} onClick={() => setInput(item)}><span className="suggestion-icon">{i === 0 ? <Globe2 size={16}/> : <Play size={15}/>}</span><span>{item}</span><ArrowUp className="suggestion-arrow" size={15}/></button>)}</div>
          <div className="how-row"><div><span className="step-number">01</span><b>Describe</b><small>Natural language in</small></div><i/><div><span className="step-number">02</span><b>Execute</b><small>Real CLI process</small></div><i/><div><span className="step-number">03</span><b>Review</b><small>Validated results</small></div></div>
        </section> : <div className="message-list">{messages.map((m, i) => <div className={`message ${m.role}`} key={i}>{m.role === 'user' ? <><div className="user-avatar">You</div><div className="user-bubble">{m.text}</div></> : <><div className="assistant-avatar"><Layers3 size={16}/></div><div className="assistant-content">{m.loading ? <div className="loading"><LoaderCircle className="spin" size={18}/> Running the crawler CLI…</div> : <Result data={m.data} copyJson={copyJson} copied={copied}/>}</div></>}</div>)}</div>}
      </div>
      {error && <div className="error-banner"><CircleAlert size={16}/>{error}</div>}
      <div className="composer-wrap"><div className="composer"><textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); } }} placeholder="Describe a task or paste a URL…" rows={1}/><div className="composer-bottom"><span><span className="composer-live"/> TaskPilot can crawl public websites</span><button disabled={!input.trim() || busy} onClick={() => submit()} aria-label="Run task">{busy ? <LoaderCircle className="spin" size={17}/> : <ArrowUp size={18}/>}</button></div></div><div className="composer-note">Enter to run <span>·</span> Shift + Enter for new line <span>·</span> Requests are executed locally</div></div>
    </main>
  </div>;
}

function Result({ data, copyJson, copied }) {
  const [showJson, setShowJson] = useState(true);
  const [showLog, setShowLog] = useState(false);
  const result = data.execution?.result;
  const ok = data.status === 'success';
  return <div className="result-card">
    <div className={`result-status ${ok ? 'good' : 'bad'}`}>{ok ? <Check size={14}/> : <CircleAlert size={14}/>} {ok ? 'Execution complete' : data.status === 'partial' ? 'Partial results' : 'Execution failed'}<span className="duration">{data.execution?.duration_seconds != null ? `${data.execution.duration_seconds}s` : ''}</span></div>
    {data.error && <p className="result-error">{data.error}</p>}
    {result && <><div className="summary-head"><h3>Website summary</h3><span className="page-pill"><Globe2 size={12}/> {result.pages_crawled} {result.pages_crawled === 1 ? 'page' : 'pages'} crawled</span></div><p className="summary">{result.summary}</p>
      {result.pages?.map((page) => <div className="page-detail" key={page.url}><div className="page-title">{page.title || page.url}</div><div className="page-url">{page.url}</div>{page.description && <p>{page.description}</p>}{page.headings?.length > 0 && <div className="heading-list"><b>HEADINGS</b>{page.headings.slice(0, 6).map((h, i) => <span key={i}>H{h.level} · {h.text}</span>)}</div>}</div>)}
      {!!result.errors?.length && <div className="crawl-errors">{result.errors.map((e, i) => <p key={i}><CircleAlert size={13}/>{e.error}</p>)}</div>}
      <div className="accordion-head"><button className="accordion-toggle" onClick={() => setShowJson(!showJson)}>{showJson ? <ChevronDown size={15}/> : <ChevronRight size={15}/>}<span>Extracted JSON</span></button><span className="json-valid"><Check size={12}/> Validated</span><span className="accordion-spacer"/><button className="copy-btn" onClick={() => copyJson(result)}>{copied ? <Check size={13}/> : <Copy size={13}/>} {copied ? 'Copied' : 'Copy JSON'}</button></div>
      {showJson && <pre className="json-block">{JSON.stringify(result, null, 2)}</pre>}
    </>}
    <button className="accordion-head log-head" onClick={() => setShowLog(!showLog)}>{showLog ? <ChevronDown size={15}/> : <ChevronRight size={15}/>}<span>Execution details</span><span className="tool-name"><TerminalSquare size={13}/> {data.execution?.tool || 'intent parser'}</span><span className="accordion-spacer"/><span className="exit-code">Exit {data.execution?.exit_code ?? '—'}</span></button>
    {showLog && <div className="execution-log"><div className="timeline">{(data.events || []).map((event, i) => <div className="timeline-item" key={i}><span className={`timeline-mark ${event.includes('failed') || event.includes('Failed') ? 'mark-bad' : ''}`}>{event.includes('failed') ? '!' : '✓'}</span><span>{event}</span></div>)}</div>{data.execution?.stderr && <><b>STDERR</b><pre>{data.execution.stderr}</pre></>}{data.execution?.stdout && <><b>STDOUT</b><pre>{data.execution.stdout}</pre></>}</div>}
  </div>;
}

export default App;
