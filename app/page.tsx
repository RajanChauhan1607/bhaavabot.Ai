'use client'

import { useState } from 'react'
import type React from 'react'
import Link from 'next/link'
import { authClient } from '@/lib/auth-client'
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

const musicItems = [
  { title: 'Quiet corners', artist: 'BhaavaBot sessions', kind: 'Focus · 42 min', icon: '◒', tone: 'mint' },
  { title: 'Soft landing', artist: 'The Sunday Room', kind: 'Ambient · 38 min', icon: '◌', tone: 'lavender' },
  { title: 'A little lighter', artist: 'Mira Sol', kind: 'Acoustic · 31 min', icon: '☼', tone: 'peach' },
  { title: 'Evening tea', artist: 'Low Tide Club', kind: 'Lo-fi · 46 min', icon: '♪', tone: 'blue' },
]

const movieItems = [
  { title: 'Paterson', year: '2016', kind: 'Quiet · Tender', icon: 'P', tone: 'lavender' },
  { title: 'Perfect Days', year: '2023', kind: 'Gentle · Observant', icon: 'PD', tone: 'mint' },
  { title: 'The Secret Life of Walter Mitty', year: '2013', kind: 'Hopeful · Warm', icon: 'W', tone: 'peach' },
  { title: 'Kiki’s Delivery Service', year: '1989', kind: 'Comforting · Bright', icon: 'K', tone: 'blue' },
]

function CompanionMark() {
  return <div className="companion-mark" aria-hidden="true"><span /><span /><span /></div>
}

function MediaView({ type, filter, setFilter, activeMedia, setActiveMedia, favorites, setFavorites }: { type: string; filter: string; setFilter: (filter: string) => void; activeMedia: string | null; setActiveMedia: (title: string | null) => void; favorites: string[]; setFavorites: (items: string[]) => void }) {
  const isMusic = type === 'Music'
  const items = isMusic ? musicItems : movieItems
  const filters = isMusic ? ['For you', 'Focus', 'Sleep', 'Uplift'] : ['For you', 'Comfort', 'Thoughtful', 'Light']
  const featured = items[0]
  const toggleFavorite = (title: string) => setFavorites(favorites.includes(title) ? favorites.filter((item) => item !== title) : [...favorites, title])
  return <div className="media-view">
    <div className={`media-hero ${isMusic ? 'music-hero' : 'movie-hero'}`}><div><span className="media-kicker">{isMusic ? 'A gentle listen' : 'A thoughtful watch'}</span><h2>{isMusic ? 'Let the room get quieter.' : 'Something kind for tonight.'}</h2><p>{isMusic ? 'A small collection for the moments when you want less noise.' : 'Stories with a little warmth, a little wonder, and no rush to get anywhere.'}</p><button className="media-primary" onClick={() => setActiveMedia(featured.title)}>{isMusic ? <Play /> : <Film />}{activeMedia === featured.title ? 'Playing now' : isMusic ? 'Start listening' : 'View recommendation'}</button></div><div className="feature-art"><span>{featured.icon}</span><small>{isMusic ? 'BHAAVABOT' : 'TONIGHT'}</small></div></div>
    <div className="media-toolbar"><div className="filter-row">{filters.map((item) => <button key={item} className={filter === item ? 'filter-chip active' : 'filter-chip'} onClick={() => setFilter(item)}>{item}</button>)}</div><button className="media-library" onClick={() => setFilter(isMusic ? 'Saved' : 'My list')}><Heart /> {isMusic ? 'Saved' : 'My list'}</button></div>
    <div className="media-section-heading"><div><span className="eyebrow">CURATED FOR YOU</span><h3>{isMusic ? 'A softer soundtrack' : 'A warm little watchlist'}</h3></div><span className="media-count">{items.length} picks</span></div>
    <div className="media-grid">{items.map((item) => <article className="media-card" key={item.title}><button className={`cover-art ${item.tone}`} onClick={() => setActiveMedia(item.title)} aria-label={`${isMusic ? 'Play' : 'Open'} ${item.title}`}><span>{item.icon}</span><i>{isMusic ? <Play /> : <Film />}</i></button><div className="media-card-body"><div><h4>{item.title}</h4><p>{isMusic ? item.artist : item.year}</p><small>{item.kind}</small></div><button className={favorites.includes(item.title) ? 'favorite active' : 'favorite'} onClick={() => toggleFavorite(item.title)} aria-label={`Save ${item.title}`}><Heart /></button></div></article>)}</div>
    {activeMedia && <div className="now-playing"><div className="now-playing-mark">{isMusic ? <Music2 /> : <Film />}</div><div><strong>{activeMedia}</strong><span>{isMusic ? 'Now playing · breathe easy' : 'Selected for your evening'}</span></div><button onClick={() => setActiveMedia(null)} aria-label="Close selection"><X /></button></div>}
  </div>
}

function HomeDashboard({ onStart }: { onStart: () => void }) {
  return <div className="home-dashboard"><div className="welcome-card"><div><span className="eyebrow">A MOMENT FOR YOU</span><h2>Welcome back, Alex.</h2><p>You have made it here. That is already something.</p></div><div className="welcome-sun">☼</div></div><div className="checkin-card"><div><span className="eyebrow">DAILY CHECK-IN</span><h3>What is your inner weather today?</h3><p>Choose a word, or simply notice what is here.</p></div><div className="mood-row">{['Calm', 'Tired', 'Heavy', 'Hopeful'].map((mood) => <button key={mood} onClick={onStart}>{mood}</button>)}</div></div><div className="home-section"><div className="section-title"><span className="eyebrow">A SMALL STEP</span><span>2 min</span></div><button className="reflection-prompt" onClick={onStart}><div className="prompt-icon"><Sparkles /></div><div><strong>Put it into words</strong><p>What has been taking up space in your mind?</p></div><ArrowUp /></button></div></div>
}

function NewConversationView({ onPrompt }: { onPrompt: (prompt: string) => void }) {
  return <div className="new-conversation-view"><div className="new-conversation-orb"><CompanionMark /></div><span className="eyebrow">A PRIVATE MOMENT</span><h2>Start a new conversation.</h2><p>This space is yours. You can talk about what is happening right now, or begin with one of the prompts below.</p><div className="new-prompt-list">{['Something has been on my mind…', 'Help me make sense of my feelings', 'I just need someone to listen'].map((prompt) => <button key={prompt} onClick={() => onPrompt(prompt)}><Sparkles /><span>{prompt}</span><ArrowUp /></button>)}</div></div>
}

function ResourcesView(props: Omit<React.ComponentProps<typeof MediaView>, 'type'>) {
  const [category, setCategory] = useState<'Music' | 'Movies'>('Music')
  return <div className="resources-view"><div className="resources-intro"><span className="eyebrow">A PLACE TO UNWIND</span><h2>Resources</h2><p>Choose something gentle for the feeling you are carrying.</p></div><div className="resource-category"><button className={category === 'Music' ? 'category active' : 'category'} onClick={() => setCategory('Music')}><Music2 /><span><strong>Music</strong><small>For your mood</small></span></button><button className={category === 'Movies' ? 'category active' : 'category'} onClick={() => setCategory('Movies')}><Film /><span><strong>Movies</strong><small>For your evening</small></span></button></div><MediaView {...props} type={category} /></div>
}

function ReflectionsView() { return <div className="simple-page"><span className="eyebrow">YOUR INNER WORLD</span><h2>My reflections</h2><p>Your check-ins and saved thoughts will live here.</p><div className="empty-reflection"><Heart /><strong>A clear page can be a kind beginning.</strong><span>Start a new conversation to capture a reflection.</span></div></div> }
function ProfileView({ onSettings, onSafety }: { onSettings: () => void; onSafety: () => void }) { return <div className="simple-page"><span className="eyebrow">YOUR SPACE</span><h2>Profile</h2><p>Make BhaavaBot feel right for you.</p><button className="profile-action" onClick={onSettings}><Settings /><span><strong>Settings</strong><small>Preferences and reminders</small></span><ChevronDown /></button><button className="profile-action" onClick={onSafety}><ShieldCheck /><span><strong>Safety & privacy</strong><small>Learn how your space stays private</small></span><ChevronDown /></button></div> }

export default function Page() {
  const [mode, setMode] = useState('Chat')
  const [view, setView] = useState<'home' | 'reflections' | 'new' | 'resources' | 'profile'>('home')
  const [messages, setMessages] = useState(initialMessages)
  const [draft, setDraft] = useState('')
  const [thinking, setThinking] = useState(false)
  const [listening, setListening] = useState(false)
  const [panel, setPanel] = useState<'settings' | 'safety' | null>(null)
  const [mobileNav, setMobileNav] = useState(false)
  const [activeMedia, setActiveMedia] = useState<string | null>(null)
  const [favorites, setFavorites] = useState<string[]>([])
  const [mediaFilter, setMediaFilter] = useState('For you')
  const { data: session } = authClient.useSession()

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
          <div className="profile"><div className="avatar">{session?.user?.name?.slice(0, 1) ?? 'A'}</div><div><strong>{session?.user?.name ?? 'Guest explorer'}</strong><span>{session?.user ? 'Member space' : 'Sign in to save history'}</span></div><MoreHorizontal /></div>
        </div>
      </aside>

      <section className="conversation">
        <header className="topbar">
          <div className="mobile-brand"><CompanionMark /><strong>BhaavaBot</strong></div>
          <div className="top-actions"><button className="icon-button" aria-label="Notifications"><Bell /></button>{session?.user ? <button className="account-link" onClick={() => authClient.signOut()}>Sign out</button> : <Link className="account-link" href="/sign-in">Sign in</Link>}</div>
        </header>
        <div className="conversation-inner">
          <div className="conversation-heading"><div><p className="eyebrow">TUESDAY, AUGUST 21</p><h1>{view === 'resources' ? 'Find something that feels good.' : view === 'reflections' ? 'Notice what has changed.' : view === 'profile' ? 'Your calm space.' : view === 'new' ? 'A fresh place to begin.' : 'How are you feeling today?'}</h1><p className="subheading">{view === 'resources' ? 'Music and movies, chosen with care.' : 'Take a breath. There’s no rush here.'}</p></div><button className="help-button"><CircleHelp /> <span>Need help?</span></button></div>
          {view === 'home' ? <>
            <HomeDashboard onStart={() => { setView('new'); setMessages([]) }} />
            <div className="conversation-label"><Sparkles /> CONVERSATION</div>
            <div className="message-area" aria-live="polite">
              {messages.length === 0 ? <div className="empty-state"><div className="empty-orb"><CompanionMark /></div><h2>A fresh start</h2><p>What would you like to explore together?</p></div> : messages.map((message, index) => <div className={`message-row ${message.from}`} key={`${message.time}-${index}`}><div className="message-avatar">{message.from === 'bot' ? <CompanionMark /> : 'A'}</div><div className="message-content"><div className="message-bubble">{message.text}</div><span className="message-time">{message.time}</span></div></div>)}
              {thinking && <div className="message-row bot"><div className="message-avatar"><CompanionMark /></div><div className="thinking"><i /><i /><i /></div></div>}
            </div>
            {messages.length > 0 && <div className="quick-prompts"><span>Try asking</span>{starters.slice(0, 3).map((item) => <button key={item.title} onClick={() => sendMessage(item.text)}>{item.icon} {item.title}</button>)}</div>}
            {messages.length === 0 && <div className="starter-grid">{starters.map((item) => <button key={item.title} className="starter-card" onClick={() => sendMessage(item.text)}><b>{item.icon}</b><span>{item.title}</span><small>{item.text}</small><ArrowUp /></button>)}</div>}
            <div className="composer-wrap"><div className="composer"><button className="composer-icon" aria-label="Attach file"><Paperclip /></button><input value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.nativeEvent.isComposing) sendMessage() }} placeholder="Share what’s on your mind..." aria-label="Message BhaavaBot"/><button className={`mic-button ${listening ? 'listening' : ''}`} aria-label="Use voice input" onClick={() => setListening(!listening)}>{listening ? <Square /> : <Mic />}</button><button className="send-button" aria-label="Send message" onClick={() => sendMessage()}><Send /></button></div><p className="composer-note"><ShieldCheck /> Your conversations are private and secure</p></div>
          </> : view === 'new' ? <NewConversationView onPrompt={(prompt) => { setDraft(prompt); setView('home') }} /> : view === 'resources' ? <ResourcesView filter={mediaFilter} setFilter={setMediaFilter} activeMedia={activeMedia} setActiveMedia={setActiveMedia} favorites={favorites} setFavorites={setFavorites} /> : view === 'reflections' ? <ReflectionsView /> : <ProfileView onSettings={() => setPanel('settings')} onSafety={() => setPanel('safety')} />}
        </div>
      </section>
      <nav className="bottom-nav" aria-label="Primary navigation">
        <button className={`bottom-nav-item ${view === 'home' ? 'active' : ''}`} onClick={() => setView('home')}><Home /><span>Home</span></button>
        <button className={`bottom-nav-item ${view === 'reflections' ? 'active' : ''}`} onClick={() => setView('reflections')}><Heart /><span>My reflections</span></button>
        <button className="bottom-nav-new" onClick={() => { setView('new'); setMessages([]) }} aria-label="New conversation"><Plus /><span>New</span></button>
        <button className={`bottom-nav-item ${view === 'resources' ? 'active' : ''}`} onClick={() => setView('resources')}><BookOpen /><span>Resources</span></button>
        <button className={`bottom-nav-item ${view === 'profile' ? 'active' : ''}`} onClick={() => setView('profile')}><div className="bottom-avatar">{session?.user?.name?.slice(0, 1) ?? 'A'}</div><span>Profile</span></button>
      </nav>
      <div className={`scrim ${mobileNav ? 'visible' : ''}`} onClick={() => setMobileNav(false)} />
      {listening && <div className="voice-toast"><div className="voice-pulse"><Mic /></div><div><strong>Listening...</strong><span>Tell me what’s on your mind</span></div><button onClick={() => setListening(false)} aria-label="Stop listening"><Square /></button></div>}
      {panel && <div className="panel-backdrop" onClick={() => setPanel(null)}><section className="info-panel" onClick={(event) => event.stopPropagation()}><button className="close-panel" onClick={() => setPanel(null)} aria-label="Close"><X /></button>{panel === 'settings' ? <><Settings className="panel-icon" /><h2>Your settings</h2><p>Choose the way BhaavaBot shows up for you. Your preferences are saved on this device.</p><label className="setting-row"><span>Gentle reminders</span><input type="checkbox" defaultChecked /></label><label className="setting-row"><span>Sound effects</span><input type="checkbox" /></label></> : <><ShieldCheck className="panel-icon" /><h2>A safe space</h2><p>BhaavaBot is here to support reflection, not replace professional care. Your conversations stay private and you can clear them anytime.</p><button className="panel-action" onClick={() => setPanel(null)}>I understand</button></>}</section></div>}
    </main>
  )
}
