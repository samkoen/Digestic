import React, { useLayoutEffect, useRef, useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Box,
  CircularProgress,
  Alert,
} from '@mui/material'

function isEmailBodyVisuallyEmpty(html) {
  if (!html || !String(html).trim()) return true
  const d = document.createElement('div')
  d.innerHTML = html
  const t = (d.textContent || '').replace(/\u00a0/g, ' ').trim()
  return t.length === 0
}

/** Dialogue : destinataire (lecture seule), objet et corps éditables (aperçu + code source). */
export default function SendEmailComposerDialog({
  open,
  title = "Envoyer l'e-mail",
  onClose,
  draftLoading,
  draftError,
  draft,
  onSend,
  sending,
  sendError,
}) {
  const [subject, setSubject] = useState('')
  const [bodyHtml, setBodyHtml] = useState('')
  const previewRef = useRef(null)
  const skipCodeToPreviewOnce = useRef(false)

  /** Charger le brouillon — synchrone avant affichage pour éviter un flash avec l’ancien corps. */
  useLayoutEffect(() => {
    if (!open || !draft) return
    skipCodeToPreviewOnce.current = true
    const html = draft.body_html ?? ''
    setSubject(draft.subject ?? '')
    setBodyHtml(html)
    const el = previewRef.current
    const next = html.trim() ? html : '<p><br></p>'
    if (el && document.activeElement !== el) {
      el.innerHTML = next
    }
  }, [open, draft])

  /** Champ « code source » — refléter dans l’aperçu tant que la saisie n’a pas lieu dans l’aperçu. */
  useLayoutEffect(() => {
    if (skipCodeToPreviewOnce.current) {
      skipCodeToPreviewOnce.current = false
      return
    }
    const el = previewRef.current
    if (!open || !draft || !el) return
    if (document.activeElement === el) return
    const next = bodyHtml.trim() ? bodyHtml : '<p><br></p>'
    if (el.innerHTML !== next) {
      el.innerHTML = next
    }
  }, [bodyHtml, open, draft])

  const syncFromPreview = () => {
    const el = previewRef.current
    if (!el) return
    setBodyHtml(el.innerHTML)
  }

  const canSend =
    !draftLoading &&
    !draftError &&
    draft &&
    String(subject).trim().length > 0 &&
    !isEmailBodyVisuallyEmpty(bodyHtml)

  const handleSend = () => {
    if (!canSend || sending) {
      return
    }
    void onSend({ subject: subject.trim(), body_html: bodyHtml })
  }

  const previewSx = {
    display: 'block',
    width: '100%',
    minHeight: 240,
    maxHeight: 380,
    overflow: 'auto',
    border: 'none',
    outline: 'none',
    bgcolor: '#fff',
    p: 2,
    fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
    fontSize: 15,
    lineHeight: 1.5,
    color: '#222',
    '& img': { maxWidth: '100%', height: 'auto' },
    '& table': { maxWidth: '100%' },
    '& a': { color: '#1565c0' },
  }

  return (
    <Dialog open={open} onClose={sending ? undefined : onClose} maxWidth="md" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        {draftLoading && (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        )}
        {!draftLoading && draftError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {draftError}
          </Alert>
        )}
        {!draftLoading && !draftError && draft && (
          <>
            <TextField
              margin="normal"
              fullWidth
              label="Destinataire"
              value={draft.to_email || ''}
              disabled
              InputProps={{ readOnly: true }}
            />
            <TextField
              margin="normal"
              fullWidth
              label="Objet"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1.5 }}>
              Le rendu final peut encore varier dans Gmail, Outlook, Apple Mail, etc. Les pièces jointes PDF ne
              sont pas affichées ici.
            </Typography>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Message — saisie directe dans l’aperçu
            </Typography>
            <Box
              sx={{
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
                overflow: 'hidden',
                bgcolor: 'grey.50',
                mb: 2,
              }}
            >
              <Box
                ref={previewRef}
                contentEditable={!sending}
                suppressContentEditableWarning
                tabIndex={0}
                aria-label="Corps du message — édition directe"
                onInput={syncFromPreview}
                onBlur={syncFromPreview}
                sx={previewSx}
              />
            </Box>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Code source HTML
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
              Synchronisé avec l’aperçu ci-dessus (utile pour coller du HTML ou corriger les balises).
            </Typography>
            <TextField
              margin="normal"
              fullWidth
              multiline
              minRows={6}
              label="Corps du message (code source)"
              value={bodyHtml}
              onChange={(e) => setBodyHtml(e.target.value)}
              disabled={sending}
              sx={{ '& textarea': { fontFamily: 'ui-monospace, monospace', fontSize: '0.875rem' } }}
            />
          </>
        )}
        {sendError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {sendError}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={sending}>
          Annuler
        </Button>
        <Button variant="contained" onClick={handleSend} disabled={!canSend || sending}>
          {sending ? <CircularProgress size={22} color="inherit" /> : 'Envoyer'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
