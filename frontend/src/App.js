import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = 'http://localhost:8000';

function ConnectionStatus() {
  const [connected, setConnected] = useState(false);
  const [lastChecked, setLastChecked] = useState(null);

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${API_BASE}/status`);
        const data = await res.json();
        setConnected(data.status === 'connected');
        setLastChecked(new Date().toLocaleTimeString());
      } catch {
        setConnected(false);
        setLastChecked(new Date().toLocaleTimeString());
      }
    };

    check();
    const id = setInterval(check, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="status-card">
      <span className={`status-dot ${connected ? 'connected' : 'disconnected'}`} />
      <div>
        <p className="status-label">{connected ? 'Agent connected' : 'Agent offline'}</p>
        {lastChecked && <p className="status-time">Checked at {lastChecked}</p>}
      </div>
    </div>
  );
}

function TaskCard({ task }) {
  const time = new Date(task.timestamp).toLocaleTimeString();
  const priorityClass = (task.priority || 'low').toLowerCase();

  return (
    <div className="task-card">
      <div className="task-header">
        <span className="task-name">{task.task_name}</span>
        <span className={`priority-badge ${priorityClass}`}>{task.priority || 'Low'}</span>
      </div>
      <div className="task-meta">
        {task.category && <span className="tag">{task.category}</span>}
        {task.deadline && <span className="tag">Due: {task.deadline}</span>}
        <span className="tag muted">{time}</span>
      </div>
      {task.notion_url && (
        <a className="notion-link" href={task.notion_url} target="_blank" rel="noopener noreferrer">
          Open in Notion →
        </a>
      )}
    </div>
  );
}

function LiveLog() {
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const res = await fetch(`${API_BASE}/tasks`);
        const data = await res.json();
        setTasks(data.tasks || []);
      } catch {
        // server may still be starting
      }
    };

    fetchTasks();
    const id = setInterval(fetchTasks, 3000);
    return () => clearInterval(id);
  }, []);

  return (
    <section className="log-section">
      <h2 className="section-label">Live Task Log</h2>
      {tasks.length === 0 ? (
        <p className="empty-state">
          No tasks captured yet — start typing to the agent in your terminal.
        </p>
      ) : (
        [...tasks].reverse().map((task, i) => <TaskCard key={i} task={task} />)
      )}
    </section>
  );
}

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="header-icon">&#129504;</div>
        <div>
          <h1>Second Brain</h1>
          <p className="subtitle">Notion Task Agent</p>
        </div>
      </header>

      <main className="app-main">
        <section>
          <h2 className="section-label">Connection Status</h2>
          <ConnectionStatus />
        </section>
        <LiveLog />
      </main>
    </div>
  );
}
