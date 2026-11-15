import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';
import { EvidenceChip } from '../components';
import { TrafficLight, StatusBadge } from '../components';
import type { Assessment, Astronaut } from '../types';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  assessment?: Assessment;
  streaming?: boolean;
}

export function Chat() {
  const { user } = useAuth();
  const { chatStream, getStatus, getCrewMembers } = useApi();

  const [astronautId, setAstronautId] = useState<string>('');
  const [astronaut, setAstronaut] = useState<Astronaut | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [crew, setCrew] = useState<{ id: string; name: string }[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!user) return;
    if (user.role === 'astronaut') {
      if (user.astronaut_id) setAstronautId(user.astronaut_id);
      return;
    }
    if (crew.length > 0) {
      setAstronautId(prev => prev || crew[0].id);
    }
  }, [user, crew]);

  useEffect(() => {
    if (astronautId) {
      getStatus(astronautId).then(setAstronaut);
    }
  }, [astronautId, getStatus]);

  useEffect(() => {
    if (user?.role === 'astronaut') return;
    getCrewMembers().then(data => {
      if (data) setCrew(data as { id: string; name: string }[]);
    });
  }, [getCrewMembers, user?.role]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !astronautId || loading) return;
    const userMessage = input;
    setInput('');
    setLoading(true);

    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    // Create placeholder for streaming response
    const assistantIndex = messages.length + 1;
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }]);

    chatStream(
      {
        astronaut_id: astronautId,
        message: userMessage,
        locale: 'en',
        explanation_level: 'simple',
      },
      (chunk) => {
        setMessages(prev => {
          const next = [...prev];
          next[assistantIndex] = { ...next[assistantIndex], content: next[assistantIndex].content + chunk };
          return next;
        });
      },
      (assessment) => {
        setMessages(prev => {
          const next = [...prev];
          next[assistantIndex] = { role: 'assistant', content: assessment.summary_simple, assessment };
          return next;
        });
        setLoading(false);
      }
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!user) return null;

  return (
    <div className="flex flex-col h-[calc(100vh-200px)] max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold">Medical Chat</h1>
          <p className="text-gray-400 text-sm">Ask about symptoms, trends, or protocols</p>
        </div>
        <div className="flex items-center gap-4">
          {user.role !== 'astronaut' && (
            <select
              value={astronautId}
              onChange={e => setAstronautId(e.target.value)}
              className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
            >
              {crew.map(a => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          )}
          {astronaut && (
            <div className="flex items-center gap-2">
              <TrafficLight level={astronaut.level} size="sm" showLabel={false} />
              <StatusBadge level={astronaut.level} compact />
            </div>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 py-12">
            <p className="text-lg">Start a conversation</p>
            <p className="text-sm mt-2">Ask about symptoms, trends, or protocols</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] px-4 py-3 rounded-2xl ${
                msg.role === 'user'
                  ? 'bg-teal-500 text-gray-900 rounded-br-none'
                  : 'bg-gray-800 text-gray-100 rounded-bl-none'
              } ${msg.streaming ? 'animate-pulse' : ''}`}
            >
              <div className="whitespace-pre-wrap">{msg.content}</div>
              {msg.assessment && (
                <div className="mt-3 space-y-2">
                  <div className="flex flex-wrap gap-1">
                    {msg.assessment.sources.map((s, idx) => (
                      <EvidenceChip key={idx} cardId={s} />
                    ))}
                  </div>
                  {msg.assessment.do_now.length > 0 && (
                    <div className="p-3 bg-gray-700/50 rounded-lg text-sm">
                      <p className="font-medium mb-1">What to do now:</p>
                      <ol className="list-decimal list-inside space-y-1">
                        {msg.assessment.do_now.map((step, idx) => (
                          <li key={idx}>{step}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                  {msg.assessment.questions_for_user.length > 0 && (
                    <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg text-sm">
                      <p className="font-medium mb-1">I need to ask:</p>
                      <ul className="list-disc list-inside space-y-1">
                        {msg.assessment.questions_for_user.map((q, idx) => (
                          <li key={idx}>{q}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="mt-4 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message... (Shift+Enter for new line)"
          disabled={loading || !astronautId}
          className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim() || !astronautId}
          className="px-6 py-3 bg-teal-500 text-gray-900 font-medium rounded-lg hover:bg-teal-400 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
}