import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Box,
  Typography,
  Button,
  Paper,
  TextField,
  MenuItem,
  Chip,
  Alert,
  CircularProgress,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material'
import SaveIcon from '@mui/icons-material/Save'
import AddIcon from '@mui/icons-material/Add'
import { emailTemplateService } from '../../services/emailTemplateService'

export default function EmailTemplates() {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedKey, setSelectedKey] = useState('')
  const [subject, setSubject] = useState('')
  const [bodyHtml, setBodyHtml] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)

  const [createOpen, setCreateOpen] = useState(false)
  const [newKey, setNewKey] = useState('')
  const [newSubject, setNewSubject] = useState('Sujet — {{ variable }}')
  const [newBody, setNewBody] = useState(
    '<p>Bonjour {{ pharmacy_name }},</p>\n<p>Votre message…</p>'
  )

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const rows = await emailTemplateService.list()
      const list = rows || []
      setTemplates(list)
      setSelectedKey((prev) => {
        if (prev && list.some((r) => r.template_key === prev)) return prev
        return list[0]?.template_key ?? ''
      })
    } catch (e) {
      console.error(e)
      setError(e.response?.data?.error || 'Impossible de charger les modèles')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const current = useMemo(
    () => templates.find((t) => t.template_key === selectedKey),
    [templates, selectedKey]
  )

  useEffect(() => {
    if (!current) return
    setSubject(current.subject_template || '')
    setBodyHtml(current.body_html_template || '')
  }, [current])

  const handleSave = async () => {
    if (!selectedKey) return
    try {
      setSaving(true)
      setMessage(null)
      setError(null)
      await emailTemplateService.update(selectedKey, {
        subject_template: subject,
        body_html_template: bodyHtml,
      })
      setMessage('Modèle enregistré.')
      await load()
    } catch (e) {
      console.error(e)
      setError(e.response?.data?.error || 'Erreur à l\'enregistrement')
    } finally {
      setSaving(false)
    }
  }

  const handleCreate = async () => {
    try {
      setSaving(true)
      setError(null)
      await emailTemplateService.createCustom({
        template_key: newKey.trim().toLowerCase(),
        subject_template: newSubject,
        body_html_template: newBody,
      })
      setCreateOpen(false)
      setNewKey('')
      setMessage('Modèle personnalisé créé.')
      await load()
    } catch (e) {
      console.error(e)
      setError(e.response?.data?.error || 'Création impossible')
    } finally {
      setSaving(false)
    }
  }

  if (loading && !templates.length) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box maxWidth={960}>
      <Typography variant="h4" gutterBottom sx={{ mb: 2 }}>
        Modèles d'e-mail (HTML)
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Ces modèles servent aux envois automatisés ou manuels (factures, BL, relances…). Variables au
        format <code>{`{{ nom_variable }}`}</code>.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {message && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      )}

      <Paper sx={{ p: 2 }}>
        <Box display="flex" flexWrap="wrap" gap={2} alignItems="flex-start" sx={{ mb: 2 }}>
          <TextField
            select
            label="Modèle"
            value={selectedKey}
            onChange={(e) => setSelectedKey(e.target.value)}
            sx={{ minWidth: 280 }}
            size="small"
          >
            {templates.map((t) => (
              <MenuItem key={t.template_key} value={t.template_key}>
                {t.label_fr || t.template_key}
                {t.catalog === false ? ' (personnalisé)' : ''}
              </MenuItem>
            ))}
          </TextField>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={() => void handleSave()}
            disabled={saving || !selectedKey}
          >
            Enregistrer
          </Button>
          <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>
            Nouveau modèle personnalisé
          </Button>
        </Box>

        {current?.description_fr && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {current.description_fr}
          </Typography>
        )}

        {current?.placeholders?.length ? (
          <Box sx={{ mb: 2 }}>
            <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
              Variables conseillées
            </Typography>
            <Box display="flex" flexWrap="wrap" gap={0.5}>
              {current.placeholders.map((ph) => (
                <Chip
                  key={ph}
                  size="small"
                  label={`{{ ${ph} }}`}
                  variant="outlined"
                  onClick={() => navigator.clipboard.writeText(`{{ ${ph} }}`)}
                />
              ))}
            </Box>
          </Box>
        ) : null}

        <Divider sx={{ my: 2 }} />

        <TextField
          label="Objet"
          fullWidth
          margin="normal"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          helperText='Ex. Facture {{ invoice_number }} — {{ pharmacy_name }}'
        />
        <TextField
          label="Corps HTML"
          fullWidth
          margin="normal"
          multiline
          minRows={14}
          value={bodyHtml}
          onChange={(e) => setBodyHtml(e.target.value)}
          sx={{ fontFamily: 'ui-monospace, monospace' }}
          InputProps={{ sx: { fontFamily: 'ui-monospace, Consolas, monospace', fontSize: 13 } }}
        />
      </Paper>

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Nouveau modèle (clé personnalisée)</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Clé en snake_case (lettres minuscules, chiffres, underscores). À ne pas confondre avec les
            modèles officiels déjà présents.
          </Typography>
          <TextField
            autoFocus
            margin="dense"
            label="Clé technique"
            fullWidth
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            placeholder="relance_contractuelle_annuelle"
          />
          <TextField margin="dense" label="Objet" fullWidth value={newSubject} onChange={(e) => setNewSubject(e.target.value)} />
          <TextField
            margin="dense"
            label="Corps HTML"
            fullWidth
            multiline
            minRows={10}
            value={newBody}
            onChange={(e) => setNewBody(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Annuler</Button>
          <Button onClick={() => void handleCreate()} variant="contained" disabled={saving || !newKey.trim()}>
            Créer
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
