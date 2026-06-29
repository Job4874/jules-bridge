import { useState, useEffect, useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler
} from 'chart.js';
import { Line, Doughnut } from 'react-chartjs-2';
import './index.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler
);

const BRIDGE = 'http://127.0.0.1:5000';
const TOKEN = 'JULES-SECURE-999';

// Chart common options
const lineOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 0 },
  scales: {
    x: { display: false },
    y: {
      min: 0,
      max: 100,
      border: { display: false },
      grid: { color: 'rgba(255,255,255,0.05)' },
      ticks: { stepSize: 25, font: { size: 10, family: "'JetBrains Mono', monospace" } }
    }
  },
  plugins: { legend: { display: false }, tooltip: { enabled: false } },
  elements: { point: { radius: 0 }, line: { tension: 0.4, borderWidth: 2 } }
};

const ringOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '80%',
  plugins: { legend: { display: false }, tooltip: { enabled: false } },
  animation: { animateScale: true }
};

function App() {
  const [sysStatus, setSysStatus] = useState({
    uptime: '--',
    online: false,
    tunnel: false,
    cpu: 0,
    mem: 0,
    fleet: { launched: 0, completed: 0, pending: 0 },
    logs: []
  });

  const [cpuHistory, setCpuHistory] = useState(Array(30).fill(0));
  const [memHistory, setMemHistory] = useState(Array(30).fill(0));

  const [chatHistory, setChatHistory] = useState([
    { role: 'sys', content: 'JULES ONLINE. Secure channel established.' }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [pendingImage, setPendingImage] = useState(null);
  const [model, setModel] = useState('fast');
  const [isThinking, setIsThinking] = useState(false);
  
  const chatBoxRef = useRef(null);
  const logFeedRef = useRef(null);

  // Polling
  useEffect(() => {
    let mounted = true;
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${BRIDGE}/dashboard/status`, { cache: 'no-store' });
        if (!res.ok) throw new Error('Bad response');
        const d = await res.json();
        
        if (!mounted) return;

        const cpu = d.resource_pressure?.cpu_percent ?? 0;
        const mem = d.resource_pressure?.memory_percent ?? 0;

        setSysStatus({
          uptime: d.bridge?.uptime_human || '--',
          online: true,
          tunnel: !!d.bridge?.ngrok_url,
          cpu,
          mem,
          fleet: d.jules_fleet || { launched: 0, completed: 0, pending: 0 },
          logs: d.recent_logs || []
        });

        setCpuHistory(prev => {
          const next = [...prev, cpu];
          next.shift();
          return next;
        });
        setMemHistory(prev => {
          const next = [...prev, mem];
          next.shift();
          return next;
        });

      } catch (err) {
        if (mounted) {
          setSysStatus(s => ({ ...s, online: false, uptime: 'OFFLINE' }));
        }
      }
    };

    const timer = setInterval(fetchStatus, 2000);
    fetchStatus(); // initial
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  // Auto-scroll logs and chat
  useEffect(() => {
    if (logFeedRef.current) {
      logFeedRef.current.scrollTop = logFeedRef.current.scrollHeight;
    }
  }, [sysStatus.logs]);

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [chatHistory, isThinking]);

  // Handle paste
  useEffect(() => {
    const handlePaste = (e) => {
      const items = (e.clipboardData || window.clipboardData).items;
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          e.preventDefault();
          const blob = item.getAsFile();
          const reader = new FileReader();
          reader.onload = (ev) => {
            const b64 = ev.target.result.split(',')[1];
            setPendingImage({ base64: b64, src: ev.target.result });
          };
          reader.readAsDataURL(blob);
          break;
        }
      }
    };
    document.addEventListener('paste', handlePaste);
    return () => document.removeEventListener('paste', handlePaste);
  }, []);

  const sendChat = async () => {
    const msg = inputValue.trim();
    if (!msg && !pendingImage) return;

    const currentImg = pendingImage;
    setInputValue('');
    setPendingImage(null);

    const newUserMsg = { role: 'user', content: msg || '[screenshot]', img: currentImg?.src };
    setChatHistory(prev => [...prev, newUserMsg]);
    setIsThinking(true);

    try {
      const payload = { message: msg || 'Analyze this visual data.', model };
      if (currentImg) payload.image_base64 = currentImg.base64;
      
      const res = await fetch(`${BRIDGE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${TOKEN}` },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      
      const reply = data.response || 'No response.';
      const meta = data.model_used ? `${data.model_used} · ${data.elapsed_ms}ms` : '';
      setChatHistory(prev => [...prev, { role: 'ai', content: reply, meta }]);
    } catch (e) {
      setChatHistory(prev => [...prev, { role: 'sys', content: 'COMM LINK FAILED: ' + e.message }]);
    } finally {
      setIsThinking(false);
    }
  };

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  };

  return (
    <div className="dashboard-container">
      <div className="header">
        <h1>
          <div className={`status-dot ${!sysStatus.online ? 'offline' : ''}`} />
          JULES NEXUS
        </h1>
        <div className="header-metrics">
          <div className={`badge ${sysStatus.online ? '' : 'danger'}`}>
            SYS_UP: {sysStatus.uptime}
          </div>
          <div className={`badge ${sysStatus.tunnel ? 'success' : 'danger'}`}>
            TUNNEL: {sysStatus.tunnel ? 'ACTIVE' : 'OFFLINE'}
          </div>
        </div>
      </div>

      <div className="main-content">
        {/* Left Side: Telemetry & Logs */}
        <div className="left-panel">
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">CPU Utilization</div>
              <div className="metric-value blue">{sysStatus.cpu.toFixed(1)}%</div>
              <div className="chart-container">
                <Line
                  data={{
                    labels: Array(30).fill(''),
                    datasets: [{
                      data: cpuHistory,
                      borderColor: '#58a6ff',
                      backgroundColor: 'rgba(88, 166, 255, 0.1)',
                      fill: true,
                    }]
                  }}
                  options={lineOptions}
                />
              </div>
            </div>
            
            <div className="metric-card">
              <div className="metric-label">Memory Utilization</div>
              <div className="metric-value green">{sysStatus.mem.toFixed(1)}%</div>
              <div className="chart-container">
                <Line
                  data={{
                    labels: Array(30).fill(''),
                    datasets: [{
                      data: memHistory,
                      borderColor: '#3fb950',
                      backgroundColor: 'rgba(63, 185, 80, 0.1)',
                      fill: true,
                    }]
                  }}
                  options={lineOptions}
                />
              </div>
            </div>
          </div>

          <div className="panel" style={{ height: '140px', flex: 'none', marginBottom: '1rem' }}>
            <div className="panel-header">Fleet Status</div>
            <div className="panel-content" style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'center' }}>
              <div style={{ position: 'relative', height: '80px', width: '80px' }}>
                <Doughnut
                  data={{
                    datasets: [{
                      data: [sysStatus.fleet.launched, sysStatus.fleet.pending === 0 && sysStatus.fleet.launched === 0 ? 1 : sysStatus.fleet.pending],
                      backgroundColor: ['#58a6ff', 'rgba(255,255,255,0.05)'],
                      borderWidth: 0
                    }]
                  }}
                  options={ringOptions}
                />
                <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 'bold' }}>{sysStatus.fleet.launched}</div>
                  <div style={{ fontSize: '9px', color: 'var(--text-dim)' }}>LAUNCHED</div>
                </div>
              </div>
              
              <div style={{ position: 'relative', height: '80px', width: '80px' }}>
                <Doughnut
                  data={{
                    datasets: [{
                      data: [sysStatus.fleet.completed, sysStatus.fleet.launched > sysStatus.fleet.completed ? sysStatus.fleet.launched - sysStatus.fleet.completed : (sysStatus.fleet.completed === 0 ? 1 : 0)],
                      backgroundColor: ['#3fb950', 'rgba(255,255,255,0.05)'],
                      borderWidth: 0
                    }]
                  }}
                  options={ringOptions}
                />
                <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 'bold', color: 'var(--accent-green)' }}>{sysStatus.fleet.completed}</div>
                  <div style={{ fontSize: '9px', color: 'var(--text-dim)' }}>COMPLETED</div>
                </div>
              </div>
            </div>
          </div>

          <div className="panel" style={{ flex: 1 }}>
            <div className="panel-header">Terminal Stream</div>
            <div className="panel-content log-feed" ref={logFeedRef}>
              {sysStatus.logs.length === 0 ? (
                <div style={{ color: 'var(--text-dim)' }}>Awaiting telemetry...</div>
              ) : (
                sysStatus.logs.slice(-50).map((line, i) => {
                  const match = line.match(/^(\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\]) (.*)/);
                  let ts = '', msg = line, lvl = 'INFO';
                  if (match) { ts = match[1]; msg = match[2]; }
                  if (msg.includes('ERROR') || msg.includes('FAIL')) lvl = 'ERROR';
                  else if (msg.includes('WARN')) lvl = 'WARN';
                  
                  return (
                    <div className="log-line" key={i}>
                      <span className="log-ts">{ts}</span>
                      <span className={`log-lvl ${lvl}`}>[{lvl}]</span>
                      <span className="log-msg">{msg}</span>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Side: Chat */}
        <div className="panel right-panel">
          <div className="panel-header">
            <span>Comm Link</span>
            <select
              value={model}
              onChange={e => setModel(e.target.value)}
              title="Select LLM model"
              style={{
                background: 'transparent',
                color: 'var(--accent-blue)',
                border: 'none',
                outline: 'none',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
            >
              <option value="fast">flash (fast)</option>
              <option value="smart">pro (smart)</option>
            </select>
          </div>
          <div className="panel-content chat-messages" ref={chatBoxRef}>
            {chatHistory.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                {m.content}
                {m.img && <img src={m.img} alt="clip" className="img-preview" />}
                {m.meta && <div className="msg-meta">{m.meta}</div>}
              </div>
            ))}
            {isThinking && (
              <div className="msg ai" style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--text-dim)', animation: 'bounce 0.6s infinite alternate' }}></span>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--text-dim)', animation: 'bounce 0.6s infinite alternate 0.2s' }}></span>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--text-dim)', animation: 'bounce 0.6s infinite alternate 0.4s' }}></span>
              </div>
            )}
          </div>
          
          <div className="chat-input-area">
            {pendingImage && (
              <div className="img-strip">
                <img src={pendingImage.src} alt="thumbnail" />
                <span className="img-label">Visual data attached</span>
                <button className="btn-clear" onClick={() => setPendingImage(null)} title="Remove attachment">✕</button>
              </div>
            )}
            <div className="chat-row">
              <textarea
                className="chat-input"
                placeholder="Enter command or paste image..."
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                onKeyDown={onKey}
                rows={1}
                title="Message Input"
              />
              <button 
                className="btn-send"
                onClick={sendChat}
                disabled={isThinking}
                title="Send Message"
              >
                ➤
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
