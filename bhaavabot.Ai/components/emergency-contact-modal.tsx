'use client'

import React, { useState } from 'react'
import {
  ShieldCheck,
  Heart,
  AlertCircle,
  Phone,
  User,
  Users,
  Send,
  CheckCircle2,
  Link2,
  Unlink,
  RefreshCw,
  ExternalLink,
  Copy,
  Check,
  Share2
} from 'lucide-react'
import {
  saveEmergencyContact,
  generatePairingCode,
  disconnectEmergencyContact,
  sendTestTelegramAlert,
  type EmergencyContact,
  type PairingCodeResponse
} from '@/lib/api'

interface EmergencyContactModalProps {
  userId: string
  userName?: string
  initialContact?: EmergencyContact | null
  onSaved: (contact: EmergencyContact) => void
  onCancel?: () => void
  isMandatory?: boolean
}

export function EmergencyContactModal({
  userId,
  userName = 'Mitwa Ninama',
  initialContact,
  onSaved,
  onCancel,
  isMandatory = true,
}: EmergencyContactModalProps) {
  const [name, setName] = useState(initialContact?.name || '')
  const [relationship, setRelationship] = useState(initialContact?.relationship || 'Parent')
  const [phone, setPhone] = useState(initialContact?.phone || '')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  // Telegram pairing states
  const [telegramStatus, setTelegramStatus] = useState<string>(
    initialContact?.telegram_status || 'NOT_CONNECTED'
  )
  const [telegramUsername, setTelegramUsername] = useState<string | null>(
    initialContact?.telegram_username || null
  )
  const [pairingData, setPairingData] = useState<PairingCodeResponse | null>(null)
  const [pairingLoading, setPairingLoading] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [testLoading, setTestLoading] = useState(false)
  const [disconnectLoading, setDisconnectLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  const relationships = ['Parent', 'Sibling', 'Partner', 'Close Friend', 'Relative', 'Other']

  async function handleGeneratePairing() {
    setError(null)
    const trimmedName = name.trim()
    if (!trimmedName) {
      setError('Please provide your contact person\'s name first.')
      return
    }

    try {
      setPairingLoading(true)
      const res = await generatePairingCode(userId, trimmedName, phone.trim(), relationship, userName || 'Mitwa Ninama')
      if (res && res.success) {
        setPairingData(res)
        setTelegramStatus('PENDING')
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to generate Telegram pairing code.')
    } finally {
      setPairingLoading(false)
    }
  }

  async function handleDisconnect() {
    if (!confirm(`Are you sure you want to disconnect Telegram alerts for ${name || 'this contact'}? You can then generate a new link to pair your relative's phone.`)) return
    try {
      setDisconnectLoading(true)
      const ok = await disconnectEmergencyContact(userId)
      if (ok) {
        setTelegramStatus('NOT_CONNECTED')
        setTelegramUsername(null)
        setPairingData(null)
        setTestResult(null)
        if (initialContact) {
          onSaved({
            ...initialContact,
            telegram_status: 'NOT_CONNECTED',
            telegram_chat_id: null,
            telegram_username: null,
          })
        }
      }
    } catch (err: any) {
      setError('Failed to disconnect Telegram.')
    } finally {
      setDisconnectLoading(false)
    }
  }

  async function handleSendTest() {
    try {
      setTestLoading(true)
      setTestResult(null)
      const res = await sendTestTelegramAlert(userId)
      setTestResult(res)
    } catch (err: any) {
      setTestResult({ success: false, message: err?.message || 'Failed to send test alert' })
    } finally {
      setTestLoading(false)
    }
  }

  function getInviteMessage() {
    if (!pairingData?.pairing_link) return ''
    const recipientName = name.trim() || 'there'
    const sender = userName || 'Mitwa Ninama'
    return `Hi ${recipientName}, ${sender} has added you as their trusted emergency safety contact on BhaavaBot.\n\nPlease click this link and tap 'Start' to connect:\n${pairingData.pairing_link}`
  }

  function handleCopyLink() {
    const textToCopy = getInviteMessage()
    if (!textToCopy) return
    navigator.clipboard.writeText(textToCopy)
    setCopied(true)
    setTimeout(() => setCopied(false), 3000)
  }

  function handleShareWhatsApp() {
    const textToShare = getInviteMessage()
    if (!textToShare) return
    const cleanPhone = phone.replace(/[^\d]/g, '')
    const url = cleanPhone.length >= 10
      ? `https://api.whatsapp.com/send?phone=${cleanPhone}&text=${encodeURIComponent(textToShare)}`
      : `https://api.whatsapp.com/send?text=${encodeURIComponent(textToShare)}`
    window.open(url, '_blank')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    const trimmedName = name.trim()
    const trimmedPhone = phone.trim()

    if (!trimmedName) {
      setError('Please provide the name of your family member or close friend.')
      return
    }

    if (trimmedPhone) {
      const digitsOnly = trimmedPhone.replace(/[^\d]/g, '')
      if (digitsOnly.length < 7) {
        setError('Please enter a valid phone number (at least 7 digits with country/area code).')
        return
      }
    }

    try {
      setSaving(true)
      const res = await saveEmergencyContact(userId, trimmedName, trimmedPhone, relationship)
      if (res) {
        onSaved(res)
      } else {
        const fallback: EmergencyContact = {
          user_id: userId,
          name: trimmedName,
          phone: trimmedPhone,
          relationship,
          telegram_status: telegramStatus as any,
          telegram_username: telegramUsername,
          updated_at: new Date().toISOString(),
        }
        onSaved(fallback)
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to save emergency contact. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="panel-backdrop"
      style={{
        zIndex: 100,
        backgroundColor: 'rgba(23, 49, 44, 0.72)',
        backdropFilter: 'blur(6px)',
      }}
    >
      <div
        className="emergency-modal-card"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(540px, 94vw)',
          backgroundColor: '#ffffff',
          borderRadius: '26px',
          padding: '28px 24px',
          boxShadow: '0 25px 70px rgba(25, 60, 52, 0.35)',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          maxHeight: '92vh',
          overflowY: 'auto',
        }}
      >
        {/* Header Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '50%',
              backgroundColor: '#eaf4f0',
              color: '#286b5c',
              display: 'grid',
              placeItems: 'center',
              flexShrink: 0,
            }}
          >
            <ShieldCheck style={{ width: 24, height: 24 }} />
          </div>
          <div>
            <span
              style={{
                color: '#65968b',
                fontSize: '10.5px',
                fontWeight: 750,
                letterSpacing: '.14em',
                textTransform: 'uppercase',
              }}
            >
              SAFETY & SUPPORT CIRCLE
            </span>
            <h2
              style={{
                margin: '2px 0 0',
                color: '#244e4e',
                fontFamily: 'Georgia, serif',
                fontSize: '22px',
                fontWeight: 600,
              }}
            >
              {isMandatory ? 'A Trusted Person Before You Begin' : 'Emergency Contact & Safety Circle'}
            </h2>
          </div>
        </div>

        {/* Informational Context */}
        <div
          style={{
            backgroundColor: '#f5faf8',
            border: '1px solid #dbeae4',
            borderRadius: '16px',
            padding: '14px 16px',
            fontSize: '13px',
            color: '#496d66',
            lineHeight: 1.55,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 650, color: '#27564d', marginBottom: '4px' }}>
            <Heart style={{ width: 15, height: 15, color: '#3ea684' }} />
            <span>How does emergency alerting work?</span>
          </div>
          BhaavaBot keeps your trusted relative or loved one on standby.
          <strong> If our clinical engine detects acute suicidal thoughts or crisis, an emergency alert is sent directly to your relative's Telegram app</strong> so they can contact you immediately.
        </div>

        {error && (
          <div
            style={{
              backgroundColor: '#fdf2f4',
              border: '1px solid #f8d7dc',
              borderRadius: '12px',
              padding: '10px 14px',
              color: '#a84d5b',
              fontSize: '12.5px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <AlertCircle style={{ width: 16, height: 16, flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Name Field */}
          <div>
            <label
              htmlFor="emergency-name"
              style={{
                display: 'block',
                fontSize: '12.5px',
                fontWeight: 650,
                color: '#385e58',
                marginBottom: '6px',
              }}
            >
              Relative / Trusted Contact's Name
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="emergency-name"
                type="text"
                placeholder="e.g. Mom, Brother, Friend..."
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '11px 14px 11px 38px',
                  borderRadius: '12px',
                  border: '1px solid #cfe0db',
                  backgroundColor: '#fbfdfc',
                  color: '#244e4e',
                  fontSize: '14px',
                  outline: 'none',
                }}
              />
              <User
                style={{
                  position: 'absolute',
                  left: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: '16px',
                  height: '16px',
                  color: '#7fa29b',
                }}
              />
            </div>
          </div>

          {/* Relationship Chips */}
          <div>
            <label
              style={{
                display: 'block',
                fontSize: '12.5px',
                fontWeight: 650,
                color: '#385e58',
                marginBottom: '6px',
              }}
            >
              Relationship to You
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {relationships.map((rel) => (
                <button
                  key={rel}
                  type="button"
                  onClick={() => setRelationship(rel)}
                  style={{
                    padding: '5px 12px',
                    borderRadius: '999px',
                    fontSize: '12px',
                    fontWeight: relationship === rel ? 650 : 500,
                    border: relationship === rel ? '1px solid #2b5647' : '1px solid #dce9e5',
                    backgroundColor: relationship === rel ? '#2b5647' : '#ffffff',
                    color: relationship === rel ? '#ffffff' : '#52756f',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {rel}
                </button>
              ))}
            </div>
          </div>

          {/* Phone Field */}
          <div>
            <label
              htmlFor="emergency-phone"
              style={{
                display: 'block',
                fontSize: '12.5px',
                fontWeight: 650,
                color: '#385e58',
                marginBottom: '6px',
              }}
            >
              Their Phone Number (WhatsApp / Mobile)
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="emergency-phone"
                type="tel"
                placeholder="e.g. +91 98765 43210"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                style={{
                  width: '100%',
                  padding: '11px 14px 11px 38px',
                  borderRadius: '12px',
                  border: '1px solid #cfe0db',
                  backgroundColor: '#fbfdfc',
                  color: '#244e4e',
                  fontSize: '14px',
                  outline: 'none',
                }}
              />
              <Phone
                style={{
                  position: 'absolute',
                  left: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: '16px',
                  height: '16px',
                  color: '#7fa29b',
                }}
              />
            </div>
          </div>

          {/* Telegram Bot Pairing Section */}
          <div
            style={{
              marginTop: '4px',
              padding: '16px',
              borderRadius: '16px',
              backgroundColor: '#f3f8f6',
              border: '1px solid #d5e6df',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: 650, color: '#255047' }}>
                <Send style={{ width: 15, height: 15, color: '#2d8471' }} />
                <span>Telegram Safety Bot Pairing</span>
              </div>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 650,
                  padding: '3px 8px',
                  borderRadius: '999px',
                  backgroundColor:
                    telegramStatus === 'CONNECTED'
                      ? '#d4edda'
                      : telegramStatus === 'PENDING'
                      ? '#fff3cd'
                      : '#e9ecef',
                  color:
                    telegramStatus === 'CONNECTED'
                      ? '#155724'
                      : telegramStatus === 'PENDING'
                      ? '#856404'
                      : '#6c757d',
                }}
              >
                {telegramStatus === 'CONNECTED'
                  ? '✓ Connected'
                  : telegramStatus === 'PENDING'
                  ? 'Pairing Pending'
                  : 'Not Paired'}
              </span>
            </div>

            {telegramStatus === 'CONNECTED' ? (
              <div style={{ fontSize: '12.5px', color: '#3d6159', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ padding: '10px 12px', backgroundColor: '#eaf5f0', borderRadius: '10px', border: '1px solid #cce5dc' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 650, color: '#1d5447' }}>
                    <CheckCircle2 style={{ width: 16, height: 16, color: '#278d6b' }} />
                    <span>Linked Telegram Account: @{telegramUsername || initialContact?.telegram_username || 'Unknown'}</span>
                  </div>
                  <div style={{ fontSize: '11.5px', color: '#5b7871', marginTop: '4px' }}>
                    Emergency crisis alerts are dispatched to this Telegram account.
                  </div>
                </div>

                {/* Important Who is Linked warning */}
                <div
                  style={{
                    backgroundColor: '#fff9e6',
                    border: '1px solid #ffe8a1',
                    borderRadius: '10px',
                    padding: '10px 12px',
                    fontSize: '11.5px',
                    color: '#855b00',
                    lineHeight: 1.5,
                  }}
                >
                  <strong>⚠️ Receiving alerts yourself?</strong> If <em>@{telegramUsername || initialContact?.telegram_username}</em> is YOUR own Telegram account (instead of {name || 'your relative'}), click <strong>Unlink & Re-pair</strong> below. Then send the new invite link to {name || 'your relative'} so they open it on their phone!
                </div>

                <div style={{ display: 'flex', gap: '8px', marginTop: '2px' }}>
                  <button
                    type="button"
                    onClick={handleSendTest}
                    disabled={testLoading}
                    style={{
                      padding: '7px 14px',
                      borderRadius: '8px',
                      backgroundColor: '#2b5647',
                      color: '#ffffff',
                      border: 'none',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: testLoading ? 'wait' : 'pointer',
                    }}
                  >
                    {testLoading ? 'Sending...' : 'Send Test Alert'}
                  </button>
                  <button
                    type="button"
                    onClick={handleDisconnect}
                    disabled={disconnectLoading}
                    style={{
                      padding: '7px 14px',
                      borderRadius: '8px',
                      backgroundColor: 'transparent',
                      color: '#9c4453',
                      border: '1px solid #e8b8c0',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: disconnectLoading ? 'wait' : 'pointer',
                    }}
                  >
                    {disconnectLoading ? 'Unlinking...' : 'Unlink & Re-pair'}
                  </button>
                </div>
                {testResult && (
                  <div
                    style={{
                      marginTop: '2px',
                      padding: '8px 10px',
                      borderRadius: '8px',
                      fontSize: '11.5px',
                      backgroundColor: testResult.success ? '#e8f5e9' : '#ffebee',
                      color: testResult.success ? '#2e7d32' : '#c62828',
                    }}
                  >
                    {testResult.message}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ fontSize: '12px', color: '#4d6f68', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <p style={{ margin: 0, lineHeight: 1.5 }}>
                  To send emergency alerts to <strong>{name || 'your relative'}</strong>, generate a 10-minute pairing link and send it to them.
                </p>

                {pairingData ? (
                  <div
                    style={{
                      padding: '14px',
                      borderRadius: '14px',
                      backgroundColor: '#ffffff',
                      border: '1px solid #b7dcd2',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '11px', color: '#7a9b93', fontWeight: 650 }}>INVITE CODE FOR {name.toUpperCase() || 'CONTACT'}</span>
                      <strong style={{ fontFamily: 'monospace', fontSize: '16px', letterSpacing: '2px', color: '#244e4e' }}>
                        {pairingData.pairing_code}
                      </strong>
                    </div>

                    {/* Step-by-step instructions */}
                    <div
                      style={{
                        backgroundColor: '#fff8e6',
                        border: '1px solid #fedc84',
                        borderRadius: '10px',
                        padding: '10px 12px',
                        fontSize: '11.5px',
                        color: '#7a5a00',
                        lineHeight: 1.5,
                      }}
                    >
                      <strong>⚠️ Crucial Step:</strong><br />
                      Send this link to <strong>{name || 'your relative'}</strong>. They must open it on <strong>their phone</strong> and tap <strong>Start</strong> in Telegram.<br />
                      <em style={{ color: '#c0392b' }}>Do NOT tap Start yourself on this device, or alerts will be sent to your account instead!</em>
                    </div>

                    {/* Pre-composed message preview */}
                    <div
                      style={{
                        backgroundColor: '#f6faf8',
                        border: '1px dashed #b2d5cc',
                        borderRadius: '10px',
                        padding: '10px 12px',
                        fontSize: '11.5px',
                        color: '#2d544c',
                        lineHeight: 1.5,
                      }}
                    >
                      <div style={{ fontWeight: 650, color: '#1f4e44', marginBottom: '4px' }}>
                        📋 Message to be shared with {name || 'contact'}:
                      </div>
                      <div style={{ whiteSpace: 'pre-line', fontStyle: 'italic', color: '#355c54' }}>
                        {getInviteMessage()}
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          type="button"
                          onClick={handleCopyLink}
                          style={{
                            flex: 1,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '6px',
                            padding: '10px 14px',
                            borderRadius: '10px',
                            backgroundColor: copied ? '#2e7d32' : '#2b5647',
                            color: '#ffffff',
                            border: 'none',
                            fontSize: '12.5px',
                            fontWeight: 650,
                            cursor: 'pointer',
                            transition: 'background 0.2s ease',
                          }}
                        >
                          {copied ? <Check style={{ width: 15, height: 15 }} /> : <Copy style={{ width: 15, height: 15 }} />}
                          {copied ? 'Message & Link Copied!' : `Copy Message & Link`}
                        </button>

                        <button
                          type="button"
                          onClick={handleShareWhatsApp}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '6px',
                            padding: '10px 14px',
                            borderRadius: '10px',
                            backgroundColor: '#25D366',
                            color: '#ffffff',
                            border: 'none',
                            fontSize: '12.5px',
                            fontWeight: 650,
                            cursor: 'pointer',
                          }}
                        >
                          <Share2 style={{ width: 15, height: 15 }} />
                          Share via WhatsApp
                        </button>
                      </div>

                      <a
                        href={pairingData.pairing_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          textAlign: 'center',
                          fontSize: '11px',
                          color: '#658a82',
                          textDecoration: 'underline',
                          marginTop: '4px',
                        }}
                      >
                        (Testing only: Open on this device if logged into {name || 'contact'}'s Telegram)
                      </a>
                    </div>

                    <small style={{ color: '#7a9b93', fontSize: '11px', textAlign: 'center' }}>
                      Expires in 10 minutes. As soon as {name || 'your contact'} taps Start on Telegram, pairing activates automatically.
                    </small>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={handleGeneratePairing}
                    disabled={pairingLoading}
                    style={{
                      padding: '9px 16px',
                      borderRadius: '10px',
                      backgroundColor: '#2b5647',
                      color: '#ffffff',
                      border: 'none',
                      fontSize: '12.5px',
                      fontWeight: 600,
                      cursor: pairingLoading ? 'wait' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      width: 'fit-content',
                    }}
                  >
                    <Link2 style={{ width: 14, height: 14 }} />
                    {pairingLoading ? 'Generating...' : `Generate Pairing Link for ${name || 'Contact'}`}
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
            {!isMandatory && onCancel && (
              <button
                type="button"
                onClick={onCancel}
                style={{
                  flex: 1,
                  padding: '12px',
                  borderRadius: '12px',
                  border: '1px solid #dce9e5',
                  backgroundColor: 'transparent',
                  color: '#6d8985',
                  fontSize: '13.5px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
            )}
            <button
              type="submit"
              disabled={saving}
              style={{
                flex: 2,
                padding: '12px 20px',
                borderRadius: '12px',
                border: 'none',
                backgroundColor: '#2b5647',
                color: '#ffffff',
                fontSize: '14px',
                fontWeight: 650,
                cursor: saving ? 'wait' : 'pointer',
                boxShadow: '0 4px 14px rgba(43, 86, 71, 0.25)',
                opacity: saving ? 0.7 : 1,
                transition: 'background 0.15s ease',
              }}
            >
              {saving ? 'Saving...' : 'Save & Enter BhaavaBot'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
