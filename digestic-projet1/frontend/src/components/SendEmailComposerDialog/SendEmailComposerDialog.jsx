import React, { useEffect, useState } from 'react'
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

/** Dialogue : destinataire (lecture seule), objet et corps HTML modifiables. */
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

  useEffect(() => {
    if (!open) {
      return
    }
    if (draft) {
      setSubject(draft.subject ?? '')
      setBodyHtml(draft.body_html ?? '')
    }
  }, [open, draft])

  const canSend =
    !draftLoading &&
    !draftError &&
    draft &&
    String(subject).trim().length > 0 &&
    String(bodyHtml).trim().length > 0

  const handleSend = () => {
    if (!canSend || sending) {
      return
    }
    void onSend({ subject: subject.trim(), body_html: bodyHtml })
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
            <TextField
              margin="normal"
              fullWidth
              multiline
              minRows={12}
              label="Corps du message (HTML)"
              value={bodyHtml}
              onChange={(e) => setBodyHtml(e.target.value)}
              sx={{ '& textarea': { fontFamily: 'ui-monospace, monospace', fontSize: '0.875rem' } }}
            />
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
              Vous pouvez modifier le rendu avant envoi. Le corps est interprété en HTML lors de l&apos;envoi réel
              (SMTP à venir).
            </Typography>
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
