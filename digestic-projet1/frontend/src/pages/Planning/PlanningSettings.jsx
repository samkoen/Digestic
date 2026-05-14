import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Grid,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  MenuItem,
} from '@mui/material'
import RestoreIcon from '@mui/icons-material/Restore'
import SaveIcon from '@mui/icons-material/Save'
import HistoryIcon from '@mui/icons-material/History'
import { planningService } from '../../services/planningService'
import { useNotifier } from '../../hooks/useNotifier'
import { clearPlanningWeightsOverrides } from '../../utils/planningWeightsStorage'

/** Libellés courts pour l’UI (les détails restent dans les infobulles / hints API). */
const PARAM_LABEL_FR = {
  stock_out: 'Priorité rupture de stock',
  stock_low: 'Priorité stock faible',
  failed_closed: 'Priorité pharmacie fermée',
  failed_other: 'Priorité autre échec de visite',
  per_day_overdue: 'Bonus par jour de retard',
  max_overdue_bonus: 'Plafond du bonus retard',
  in_target_week: 'Bonus semaine ISO cible',
  geo_weight: 'Poids de la proximité géographique',
  fill_radius_km: 'Rayon de regroupement (km)',
  district_density: 'Bonus densité par quartier',
  visits_max_per_day: 'Capacité max par jour et par commercial',
  default_cycle_days: 'Cycle par défaut (jours)',
  orphan_horizon_bonus_days: 'Délai sans historique (jours)',
}

function weightsToFormState(weights) {
  const out = {}
  if (!weights) return out
  for (const [k, v] of Object.entries(weights)) {
    out[k] = v === null || v === undefined ? '' : String(v)
  }
  return out
}

function parseFieldValue(typeHint, raw) {
  const s = String(raw ?? '').trim()
  if (s === '') throw new Error('Valeur vide')
  if (typeHint === 'int') {
    const n = Number.parseInt(s, 10)
    if (!Number.isFinite(n)) throw new Error('Entier invalide')
    return n
  }
  if (typeHint === 'float') {
    const n = Number.parseFloat(s)
    if (!Number.isFinite(n)) throw new Error('Nombre invalide')
    return n
  }
  if (typeHint === 'bool') {
    return s === '1' || s.toLowerCase() === 'true' || s === 'oui'
  }
  const n = Number.parseFloat(s)
  if (!Number.isFinite(n)) throw new Error('Nombre invalide')
  return n
}

function PlanningSettings() {
  const { notify, NotifierSnackbar } = useNotifier()
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [serverWeights, setServerWeights] = useState(null)
  const [fields, setFields] = useState([])
  const [values, setValues] = useState({})
  const [saving, setSaving] = useState(false)
  const [revisionLabel, setRevisionLabel] = useState('')
  const [activeRevision, setActiveRevision] = useState(null)
  const [revisions, setRevisions] = useState([])
  const [runs, setRuns] = useState([])
  const [activatingId, setActivatingId] = useState(null)
  const [manualSegmentMode, setManualSegmentMode] = useState('inherit')
  const [segmentModeSaving, setSegmentModeSaving] = useState(false)

  const reloadAll = useCallback(async () => {
    const [defs, cfg, revList, runList] = await Promise.all([
      planningService.getWeightDefaults(),
      planningService.getActiveWeightsConfig(),
      planningService.listWeightsRevisions(80),
      planningService.listPlanningRuns(25),
    ])
    const w = defs?.weights ?? {}
    const f = Array.isArray(defs?.fields) ? defs.fields : []
    setServerWeights(w)
    setFields(f)
    const eff = cfg?.effective_weights
    const base =
      eff && typeof eff === 'object' && !Array.isArray(eff) && Object.keys(eff).length > 0 ? eff : w
    setValues(weightsToFormState(base))
    setActiveRevision(cfg?.active_revision ?? null)
    setManualSegmentMode(cfg?.manual_planning_segment_mode === 'manual_revision' ? 'manual_revision' : 'inherit')
    setRevisions(Array.isArray(revList?.revisions) ? revList.revisions : [])
    setRuns(Array.isArray(runList?.runs) ? runList.runs : [])
  }, [])

  useEffect(() => {
    clearPlanningWeightsOverrides()
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setLoadError(null)
      try {
        await reloadAll()
      } catch (e) {
        if (!cancelled) {
          console.error(e)
          const msg =
            e?.response?.data?.detail || e?.message || 'Impossible de charger les paramètres.'
          setLoadError(msg)
          notify(String(msg), 'error')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [reloadAll, notify])

  const handleChange = useCallback((key, next) => {
    setValues((prev) => ({ ...prev, [key]: next }))
  }, [])

  const handleSave = useCallback(async () => {
    if (!serverWeights || !fields.length) return
    const out = {}
    try {
      for (const f of fields) {
        const k = f.key
        const raw = values[k]
        out[k] = parseFieldValue(f.type_hint, raw)
      }
    } catch (err) {
      notify(err?.message || 'Vérifiez les valeurs saisies.', 'warning')
      return
    }
    setSaving(true)
    try {
      await planningService.createWeightsRevision({
        weights: out,
        label: revisionLabel.trim() || null,
        setActive: true,
      })
      setRevisionLabel('')
      notify(
        'Nouvelle révision enregistrée en base et activée. Les recalculs sans surcharge HTTP utiliseront ces poids.',
        'success',
      )
      await reloadAll()
    } catch (e) {
      console.error(e)
      const d = e?.response?.data?.detail
      notify(typeof d === 'string' ? d : e?.message || 'Erreur enregistrement', 'error')
    } finally {
      setSaving(false)
    }
  }, [fields, notify, reloadAll, revisionLabel, serverWeights, values])

  const handleResetActive = useCallback(async () => {
    try {
      const cfg = await planningService.getActiveWeightsConfig()
      const eff = cfg?.effective_weights
      const base =
        eff && typeof eff === 'object' && !Array.isArray(eff) && Object.keys(eff).length > 0
          ? eff
          : serverWeights
      setValues(weightsToFormState(base || {}))
      notify('Formulaire rechargé depuis la révision active en base.', 'info')
    } catch (e) {
      notify(e?.response?.data?.detail || e?.message || 'Erreur', 'error')
    }
  }, [notify, serverWeights])

  const handleSaveManualSegmentMode = useCallback(async () => {
    setSegmentModeSaving(true)
    try {
      await planningService.putRuntimeConfig({
        manualPlanningSegmentMode: manualSegmentMode,
      })
      notify('Mode segments manuels enregistré.', 'success')
      await reloadAll()
    } catch (e) {
      notify(e?.response?.data?.detail || e?.message || 'Erreur', 'error')
    } finally {
      setSegmentModeSaving(false)
    }
  }, [manualSegmentMode, notify, reloadAll])

  const handleActivate = useCallback(
    async (revisionId) => {
      setActivatingId(revisionId)
      try {
        await planningService.setActiveWeightsRevision(revisionId)
        notify('Révision activée.', 'success')
        await reloadAll()
      } catch (e) {
        notify(e?.response?.data?.detail || e?.message || 'Erreur', 'error')
      } finally {
        setActivatingId(null)
      }
    },
    [notify, reloadAll],
  )

  const activeId = activeRevision?.id

  const subtitle = useMemo(
    () =>
      activeRevision
        ? `Révision active n° ${activeRevision.revision_number}${activeRevision.label ? ` — ${activeRevision.label}` : ''}`
        : 'Aucune révision active en base — défaut code utilisé.',
    [activeRevision],
  )

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
        <CircularProgress />
      </Box>
    )
  }

  if (loadError) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>
          Paramètres du planning
        </Typography>
        <Typography variant="body2" color="error" sx={{ maxWidth: 720 }}>
          {String(loadError)}
        </Typography>
        {NotifierSnackbar}
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Paramètres du planning (révisions en base)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 900 }}>
        Les poids sont stockés en PostgreSQL sous forme de <strong>révisions immuables</strong> (JSON + numéro).
        Un recalcul sans champ <code>weights</code> dans la requête utilise la <strong>révision active</strong>.
        Ceci concerne uniquement le <strong>moteur de dates de passage</strong>, pas la{' '}
        <strong>note terrain v1</strong> (rapports de visite).
      </Typography>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 960, fontWeight: 500 }}>
        {subtitle}
      </Typography>

      <Paper sx={{ p: 2, mb: 3, maxWidth: 960 }}>
        <Typography variant="subtitle1" gutterBottom>
          Segments après changement manuel de date (fiche pharmacie)
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          <strong>Mode A</strong> (<code>inherit</code>) : pas de nouveau segment. <strong>Mode B</strong> (
          <code>manual_revision</code>) : segment dédié (révision sentinel « manuel »). Voir aussi{' '}
          <code>backend/docs/planning_revision_segments_metier.md</code>.
        </Typography>
        <Box display="flex" flexWrap="wrap" gap={2} alignItems="center">
          <TextField
            select
            label="Mode"
            size="small"
            sx={{ minWidth: 300 }}
            value={manualSegmentMode}
            onChange={(e) => setManualSegmentMode(e.target.value)}
            InputLabelProps={{ shrink: true }}
          >
            <MenuItem value="inherit">Mode A — inherit</MenuItem>
            <MenuItem value="manual_revision">Mode B — manual_revision</MenuItem>
          </TextField>
          <Button
            variant="outlined"
            onClick={() => void handleSaveManualSegmentMode()}
            disabled={segmentModeSaving}
          >
            {segmentModeSaving ? <CircularProgress size={18} /> : 'Enregistrer le mode'}
          </Button>
        </Box>
      </Paper>

      <Paper sx={{ p: 3, maxWidth: 960, mb: 3 }}>
        <TextField
          fullWidth
          size="small"
          label="Libellé de la prochaine révision (optionnel)"
          value={revisionLabel}
          onChange={(e) => setRevisionLabel(e.target.value)}
          sx={{ mb: 2 }}
          helperText="Ex. « Essai mai » — aide à retrouver une version dans l’historique."
        />
        <Grid container spacing={2}>
          {fields.map((f) => {
            const label = PARAM_LABEL_FR[f.key] ?? f.key
            return (
              <Grid item xs={12} md={6} key={f.key}>
                <TextField
                  fullWidth
                  size="small"
                  label={label}
                  value={values[f.key] ?? ''}
                  onChange={(e) => handleChange(f.key, e.target.value)}
                  helperText={f.hint || `(${f.type_hint})`}
                  inputProps={{
                    ...(f.key === 'visits_max_per_day'
                      ? { inputMode: 'numeric', min: 1, max: 200 }
                      : {}),
                  }}
                />
              </Grid>
            )
          })}
        </Grid>

        <Box display="flex" flexWrap="wrap" gap={1} sx={{ mt: 3 }}>
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress color="inherit" size={18} /> : <SaveIcon />}
            onClick={() => void handleSave()}
            disabled={saving}
          >
            Créer une révision et l’activer
          </Button>
          <Button
            variant="outlined"
            startIcon={<RestoreIcon />}
            onClick={() => void handleResetActive()}
            disabled={!serverWeights}
          >
            Recharger depuis la révision active
          </Button>
        </Box>
      </Paper>

      <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
        Historique des révisions
      </Typography>
      <TableContainer component={Paper} sx={{ maxWidth: 1100, mb: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>N°</TableCell>
              <TableCell>Libellé</TableCell>
              <TableCell>Créée le</TableCell>
              <TableCell align="right">Action</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {revisions.map((r) => (
              <TableRow key={r.id}>
                <TableCell>
                  <Chip size="small" label={`v${r.revision_number}`} sx={{ mr: 1 }} />
                  {r.id === activeId ? <Chip size="small" color="success" label="Active" /> : null}
                </TableCell>
                <TableCell>{r.label || '—'}</TableCell>
                <TableCell>{r.created_at ? String(r.created_at).replace('T', ' ').slice(0, 19) : '—'}</TableCell>
                <TableCell align="right">
                  <Button
                    size="small"
                    disabled={r.id === activeId || activatingId === r.id}
                    onClick={() => void handleActivate(r.id)}
                  >
                    {activatingId === r.id ? '…' : 'Réactiver'}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {!revisions.length ? (
              <TableRow>
                <TableCell colSpan={4}>
                  <Typography variant="body2" color="text.secondary">
                    Aucune révision.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : null}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <HistoryIcon fontSize="small" /> Derniers recalculs (audit)
      </Typography>
      <TableContainer component={Paper} sx={{ maxWidth: 1100 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Réf.</TableCell>
              <TableCell>Mode</TableCell>
              <TableCell>Révision active au run</TableCell>
              <TableCell align="right">Assign.</TableCell>
              <TableCell>Surcharge req.</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={run.id}>
                <TableCell>{run.created_at ? String(run.created_at).replace('T', ' ').slice(0, 19) : '—'}</TableCell>
                <TableCell>{run.reference_date}</TableCell>
                <TableCell>{run.dry_run ? 'Prévisualisation' : 'Appliqué'}</TableCell>
                <TableCell sx={{ maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {run.active_revision_id_at_run || '—'}
                </TableCell>
                <TableCell align="right">{run.assignments_count}</TableCell>
                <TableCell>{run.weights_request_override ? 'oui' : 'non'}</TableCell>
              </TableRow>
            ))}
            {!runs.length ? (
              <TableRow>
                <TableCell colSpan={6}>
                  <Typography variant="body2" color="text.secondary">
                    Aucun run enregistré.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : null}
          </TableBody>
        </Table>
      </TableContainer>

      {NotifierSnackbar}
    </Box>
  )
}

export default PlanningSettings
