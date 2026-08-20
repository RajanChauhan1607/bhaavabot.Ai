'use client'

import { useState } from 'react'
import {
  ArrowUp, Bell, BookOpen, ChevronDown, CircleHelp, Headphones, Heart,
  Home, LifeBuoy, Menu, Mic, MoreHorizontal, Music2, Paperclip, Play,
  Plus, Search, Send, Settings, ShieldCheck, Sparkles, Square, X, Film,
} from 'lucide-react'

const starters = [
  { icon: '☼', title: 'I feel anxious', text: 'I have been feeling anxious lately.' },
  { icon: '◌', title: 'Help me reflect', text: 'Can you help me reflect on my day?' },
  { icon: '♪', title: 'Suggest music', text: 'Suggest something calming to listen to.' },
  { icon: '◒', title: 'Find a movie', text: 'I want a comforting movie recommendation.' },
]

const initialMessages = [
  { from: 'bot', text: 'Hi Alex, I’m BhaavaBot. I’m here to listen, without judgment. What’s on your mind today?', time: '10:42 AM' },
  { from: 'user', text: 'I’ve been feeling a little overwhelmed with everything lately.', time: '10:43 AM' },
  { from: 'bot', text: 'That sounds like a lot to carry. You don’t have to solve everything at once. Would it help to talk through what feels heaviest right now?', time: '10:43 AM' },
]

function CompanionMark() {
  return <div className="companion-mark" aria-hidden="true"><span /><span /><span /></div>
}

export default function Page() {
  const [mode, setMode] = useState('Chat')
  const [messages, setMessages] = useState(initialMessages)
  const [draft, setDraft] = useState('')
  const [thinking, setThinking] = useState(false)
  const [listening, setListening] = useState(false)
  const [panel, setPanel] = useState<'settings' | 'safety' | null>(null)
  const [mobileNav, setMobileNav] = useState(false)

  function sendMessage(value = draft) {
    const text = value.trim()
    if (!text) return
    setMessages((current) => [...current, { from: 'user', text, time: 'Just now' }])
    setDraft('')
    setThinking(true)
    window.setTimeout(() => {
      setMessages((current) => [...current, { from: 'bot', text: 'Thank you for sharing that with me. We can take this one small thought at a time. What would feel supportive right now?', time: 'Just now' }])
      setThinking(false)
    }, 800)
  }

  return (
    <main className="app-shell">
      <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
        <div className="brand"><CompanionMark /><div><strong>BhaavaBot</strong><span>your calm companion</span></div></div>
        <button className="new-chat" onClick={() => setMessages([])}><Plus data-icon="inline-start" /> New conversation</button>
        <nav aria-label="Main navigation" className="side-nav">
          <button className="nav-item active"><Home data-icon="inline-start" /> Home</button>
          <button className="nav-item"><Heart data-icon="inline-start" /> My reflections</button>
          <button className="nav-item"><BookOpen data-icon="inline-start" /> Resources</button>
        </nav>
        <div className="side-bottom">
          <button className="nav-item" onClick={() => setPanel('safety')}><ShieldCheck data-icon="inline-start" /> Safety & privacy</button>
          <button className="nav-item" onClick={() => setPanel('settings')}><Settings data-icon="inline-start" /> Settings</button>
          <div className="profile"><div className="avatar">A</div><div><strong>Alex Morgan</strong><span>Member since 2024</span></div><MoreHorizontal /></div>
        </div>
      </aside>

      <section className="conversation">
        <header className="topbar">
          <button className="icon-button mobile-menu" aria-label="Open menu" onClick={() => setMobileNav(!mobileNav)}><Menu /></button>
          <div className="mobile-brand"><CompanionMark /><strong>BhaavaBot</strong></div>
          <div className="top-actions"><button className="icon-button" aria-label="Notifications"><Bell /></button><div className="online"><i /> Online</div></div>
        </header>
        <div className="conversation-inner">
          <div className="conversation-heading"><div><p className="eyebrow">TUESDAY, AUGUST 21</p><h1>How are you feeling today?</h1><p className="subheading">Take a breath. There’s no rush here.</p></div><button className="help-button"><CircleHelp /> <span>Need help?</span></button></div>
          <div className="mode-switcher" aria-label="Conversation mode">
            {(['Chat', 'Music', 'Movies'] as const).map((item) => <button key={item} className={mode === item ? 'mode active' : 'mode'} onClick={() => setMode(item)}>{item === 'Chat' ? <Sparkles /> : item === 'Music' ? <Music2 /> : <Film />}{item}</button>)}
          </div>
          <div className="message-area" aria-live="polite">
            {messages.length === 0 ? <div className="empty-state"><div className="empty-orb"><CompanionMark /></div><h2>A fresh start</h2><p>What would you like to explore together?</p></div> : messages.map((message, index) => <div className={`message-row ${message.from}`} key={`${message.time}-${index}`}><div className="message-avatar">{message.from === 'bot' ? <CompanionMark /> : 'A'}</div><div className="message-content"><div className="message-bubble">{message.text}</div><span className="message-time">{message.time}</span></div></div>)}
            {thinking && <div className="message-row bot"><div className="message-avatar"><CompanionMark /></div><div className="thinking"><i /><i /><i /></div></div>}
          </div>
          {messages.length > 0 && <div className="quick-prompts"><span>Try asking</span>{starters.slice(0, 3).map((item) => <button key={item.title} onClick={() => sendMessage(item.text)}>{item.icon} {item.title}</button>)}</div>}
          {messages.length === 0 && <div className="starter-grid">{starters.map((item) => <button key={item.title} className="starter-card" onClick={() => sendMessage(item.text)}><b>{item.icon}</b><span>{item.title}</span><small>{item.text}</small><ArrowUp /></button>)}</div>}
          <div className="composer-wrap"><div className="composer"><button className="composer-icon" aria-label="Attach file"><Paperclip /></button><input value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.nativeEvent.isComposing) sendMessage() }} placeholder="Share what’s on your mind..." aria-label="Message BhaavaBot"/><button className={`mic-button ${listening ? 'listening' : ''}`} aria-label="Use voice input" onClick={() => setListening(!listening)}>{listening ? <Square /> : <Mic />}</button><button className="send-button" aria-label="Send message" onClick={() => sendMessage()}><Send /></button></div><p className="composer-note"><ShieldCheck /> Your conversations are private and secure</p></div>
        </div>
      </section>
      <div className={`scrim ${mobileNav ? 'visible' : ''}`} onClick={() => setMobileNav(false)} />
      {listening && <div className="voice-toast"><div className="voice-pulse"><Mic /></div><div><strong>Listening...</strong><span>Tell me what’s on your mind</span></div><button onClick={() => setListening(false)} aria-label="Stop listening"><Square /></button></div>}
      {panel && <div className="panel-backdrop" onClick={() => setPanel(null)}><section className="info-panel" onClick={(event) => event.stopPropagation()}><button className="close-panel" onClick={() => setPanel(null)} aria-label="Close"><X /></button>{panel === 'settings' ? <><Settings className="panel-icon" /><h2>Your settings</h2><p>Choose the way BhaavaBot shows up for you. Your preferences are saved on this device.</p><label className="setting-row"><span>Gentle reminders</span><input type="checkbox" defaultChecked /></label><label className="setting-row"><span>Sound effects</span><input type="checkbox" /></label></> : <><ShieldCheck className="panel-icon" /><h2>A safe space</h2><p>BhaavaBot is here to support reflection, not replace professional care. Your conversations stay private and you can clear them anytime.</p><button className="panel-action" onClick={() => setPanel(null)}>I understand</button></>}</section></div>}
    </main>
  )
}
