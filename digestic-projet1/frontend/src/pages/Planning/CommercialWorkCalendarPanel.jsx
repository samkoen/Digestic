import React, { useCallback, useEffect, useState } from 'react'
import {
  Box,
  Button,
  Checkbox,
  Divider,
  FormControlLabel,
  IconButton,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import SaveIcon from '@mui/icons-material/Save'
import { planningService } from '../../services/planningService'

/** Conventions backend : même que Python `date.weekday()` — 0 = lundi, 6 = dimanche. */
const WEEKDAYS = [
  { key: 0, label: 'Lun' },
  { key: 1, label: 'Mar' },
  { key: 2, label: 'Mer' },
  { key: 3, label: 'Jeu' },
  { key: 4, label: 'Ven' },
  { key: 5, label: 'Sam' },
  { key: 6, label: 'Dim' },
]

/**
 * Éditer le calendrier « fermé » d’un commercial (weekends, congés en date).
 *
 * `notify(message, severity)` : snackbar depuis le parent (une seule instance par écran).
 */
export default function CommercialWorkCalendarPanel({
  commercialId,
  subtitle,
  notify,
}) {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [blockedWeekdays, setBlockedWeekdays] = useState(new Set())
  const [blockedRows, setBlockedRows] = useState([])
  /** Dernière réponse API : aucune règle en base (« tous les jours » pour le calcul). */
  const [configured, setConfigured] = useState(false)

  const load = useCallback(async () => {
    if (!commercialId) return
    setLoading(true)
    try {
      const res = await planningService.getWorkCalendar(commercialId)
      const wd = Array.isArray(res.off_weekdays) ? res.off_weekdays : []
      const dates = Array.isArray(res.off_dates) ? res.off_dates : []
      setBlockedWeekdays(new Set(wd.map((x) => Number(x))))
      setBlockedRows(
        dates.map((r) => ({
          date: (r.date || '').slice(0, 10),
          label: r.label ?? '',
        })),
      )
      setConfigured(Boolean(res.configured))
    } catch (e) {
      const d = e?.response?.data?.detail
      notify(typeof d === 'string' ? d : e?.message || 'Chargement calendrier impossible', 'error')
    } finally {
      setLoading(false)
    }
  }, [commercialId, notify])

  useEffect(() => {
    let ok = true
    ;(async () => {
      if (!commercialId) return
      await load()
    })().catch(() => {
      if (!ok) return
    })
    return () => {
      ok = false
    }
  }, [commercialId, load])

  const toggleWeekday = (wk) => {
    setBlockedWeekdays((prev) => {
      const n = new Set(prev)
      if (n.has(wk)) n.delete(wk)
      else n.add(wk)
      return n
    })
  }

  const addBlockedDateRow = () => {
    setBlockedRows((r) => [...r, { date: '', label: '' }])
  }

  const updateRow = (idx, patch) => {
    setBlockedRows((rows) => rows.map((row, i) => (i === idx ? { ...row, ...patch } : row)))
  }

  const removeRow = (idx) => {
    setBlockedRows((rows) => rows.filter((_, i) => i !== idx))
  }

  const handleSave = async () => {
    if (!commercialId) return
    const off_dates = []
    for (let i = 0; i < blockedRows.length; i += 1) {
      const dt = String(blockedRows[i].date ?? '').trim()
      if (!dt) continue
      if (!/^\d{4}-\d{2}-\d{2}$/.test(dt)) {
        notify(`Date invalide ligne ${i + 1} (attendu AAAA-MM-JJ).`, 'warning')
        return
      }
      const lab = String(blockedRows[i].label ?? '').trim()
      off_dates.push({ date: dt, label: lab || null })
    }
    const off_weekdays = Array.from(blockedWeekdays.values()).sort((a, b) => a - b)
    setSaving(true)
    try {
      await planningService.putWorkCalendar(commercialId, { off_weekdays, off_dates })
      notify('Calendrier planning enregistré.', 'success')
      await load()
    } catch (e) {
      const d = e?.response?.data?.detail
      notify(typeof d === 'string' ? d : e?.message || 'Erreur enregistrement', 'error')
    } finally {
      setSaving(false)
    }
  }

  const wdSummary = WEEKDAYS.filter((w) => blockedWeekdays.has(w.key)).map((w) => w.label).join(', ')

  if (!commercialId) {
    return null
  }

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Typography variant="subtitle1" gutterBottom>
        Calendrier du commercial (repos récurrent + dates fermées)
      </Typography>
      {subtitle ? (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {subtitle}
        </Typography>
      ) : null}
      <Typography variant="caption" color="text.secondary" sx={{ mb: 1.5 }} display="block">
        Ces jours sont <strong>exclus</strong> du passage automatique des visites flexibles ; si vos jours ouvrés sont
        saturés sous la capacité journalière, les autres pharmacies du même run gardent leur date actuelle (
        <strong>aucune attribution sur une journée fermée</strong>). Un RDV fixe qui tombe là-dessus déclenchera une{' '}
        <strong>alerte</strong> (e-mail). Convention : lun = 0, …, dim = 6 — comme dans Python.
      </Typography>
      {loading ? (
        <Typography variant="body2">Chargement…</Typography>
      ) : (
        <>
          <Typography variant="body2" color={configured ? 'text.primary' : 'text.secondary'} sx={{ mb: 1 }}>
            {configured ? 'Règles actives dans la base.' : 'Aucune règle : le moteur considère que vous travaillez tous les jours de l’horizon.'}
            {configured && wdSummary ? (
              <>
                {' '}
                Jours fermés chaque semaine : <strong>{wdSummary}</strong>
              </>
            ) : null}
          </Typography>
          <Divider sx={{ my: 1.5 }} />
          <Typography variant="body2" sx={{ mb: 0.75 }} fontWeight="medium">
            Journées fermées chaque semaine
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75, mb: 2 }}>
            {WEEKDAYS.map(({ key, label }) => (
              <FormControlLabel
                key={key}
                sx={{ mr: 1 }}
                control={
                  <Checkbox
                    size="small"
                    checked={blockedWeekdays.has(key)}
                    onChange={() => toggleWeekday(key)}
                  />
                }
                label={label}
              />
            ))}
          </Box>
          <Typography variant="body2" sx={{ mb: 0.75 }} fontWeight="medium">
            Dates ponctuelles (congés, formation…)
          </Typography>
          <Stack spacing={1} sx={{ mb: 2 }}>
            {blockedRows.map((row, idx) => (
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'center' }} key={idx}>
                <TextField
                  size="small"
                  type="date"
                  label="Date"
                  InputLabelProps={{ shrink: true }}
                  value={row.date}
                  onChange={(ev) => updateRow(idx, { date: ev.target.value })}
                />
                <TextField
                  size="small"
                  label="Motif (optionnel)"
                  value={row.label}
                  onChange={(ev) => updateRow(idx, { label: ev.target.value })}
                  sx={{ flex: 1, minWidth: 160 }}
                />
                <IconButton size="small" color="error" onClick={() => removeRow(idx)} aria-label="Supprimer ligne">
                  <DeleteOutlineIcon fontSize="small" />
                </IconButton>
              </Stack>
            ))}
            {!blockedRows.length ? (
              <Typography variant="caption" color="text.secondary">
                Aucune date bloquée.
              </Typography>
            ) : null}
            <Box>
              <Button size="small" startIcon={<AddIcon />} onClick={addBlockedDateRow} variant="outlined">
                Ajouter une date
              </Button>
            </Box>
          </Stack>
          <Stack direction="row" spacing={1}>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={() => void handleSave()}
              disabled={saving}
            >
              {saving ? '…' : 'Enregistrer'}
            </Button>
            <Button size="small" variant="text" onClick={() => void load()} disabled={saving}>
              Recharger
            </Button>
          </Stack>
        </>
      )}
    </Paper>
  )
}
