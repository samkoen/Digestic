import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Box,
  Typography,
  Paper,
  Button,
  CircularProgress,
  TextField,
  MenuItem,
  Divider,
  FormControlLabel,
  Checkbox,
} from '@mui/material'
import AssessmentIcon from '@mui/icons-material/Assessment'
import { format, subMonths } from 'date-fns'
import { authService } from '../../services/authService'
import { userService } from '../../services/userService'
import { planningEvaluationService } from '../../services/planningEvaluationService'
import { useNotifier } from '../../hooks/useNotifier'
import ReactMarkdown from 'react-markdown'

function defaultRange() {
  const end = new Date()
  const start = subMonths(end, 1)
  return {
    startIso: format(start, 'yyyy-MM-dd'),
    endIso: format(end, 'yyyy-MM-dd'),
  }
}

function PlanningEvaluation() {
  const { notify, NotifierSnackbar } = useNotifier()
  const [{ startIso, endIso }, setRange] = useState(() => defaultRange())
  const [commercialId, setCommercialId] = useState('')
  const [commercials, setCommercials] = useState([])
  const [currentUser, setCurrentUser] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [planningRevisionId, setPlanningRevisionId] = useState('')
  const [pureAutoPlanningOnly, setPureAutoPlanningOnly] = useState(true)

  const isAdmin = useMemo(
    () => (currentUser?.role ?? '').toString().toLowerCase().trim() === 'admin',
    [currentUser?.role],
  )

  useEffect(() => {
    let cancelled = false
    authService
      .getCurrentUser()
      .then((data) => {
        const u = data?.user ?? data ?? null
        if (!cancelled) setCurrentUser(u)
      })
      .catch(() => {
        if (!cancelled) setCurrentUser(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!isAdmin) return
    let cancelled = false
    userService
      .getAll('commercial')
      .then((rows) => {
        if (!cancelled) setCommercials(Array.isArray(rows) ? rows : [])
      })
      .catch(() => {
        if (!cancelled) setCommercials([])
      })
    return () => {
      cancelled = true
    }
  }, [isAdmin])

  const handleFetch = useCallback(async () => {
    try {
      setLoading(true)
      const payload = await planningEvaluationService.getEvaluation({
        startDate: startIso,
        endDate: endIso,
        commercialId: isAdmin && commercialId ? commercialId : null,
        planningWeightsRevisionId: planningRevisionId.trim() || null,
        pureAutoPlanningWeightsOnly: pureAutoPlanningOnly,
      })
      setResult(payload)
      const pr = payload?.planning_revision_filter
      const lines = []
      if (pr) {
        lines.push(
          `Filtre révision planning : ${pr.reports_before_filter} → ${pr.reports_after_filter} rapport(s). Excl. sans segment : ${pr.excluded_no_segment}, autre révision : ${pr.excluded_revision_mismatch}, garde pure-auto : ${pr.excluded_manual_or_override_guard}.`,
        )
      }
      if (payload?.message_fr) {
        lines.push(payload.message_fr)
      }
      if (lines.length > 0) {
        notify(lines.join('\n'), 'info')
      }
    } catch (e) {
      console.error(e)
      const d = e?.response?.data?.detail
      notify(typeof d === 'string' ? d : e?.message || 'Erreur lors du calcul.', 'error')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }, [commercialId, endIso, isAdmin, notify, planningRevisionId, pureAutoPlanningOnly, startIso])

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <AssessmentIcon color="primary" />
        Évaluation terrain (note v1)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 720 }}>
        La note agrège les <strong>rapports de visite réels</strong> sur la période choisie : réalisation des passages,
        stock déclaré et ressenti commercial lorsqu’il est renseigné.
      </Typography>

      <Paper sx={{ p: 2, mb: 2, maxWidth: 720 }}>
        <Box display="flex" flexWrap="wrap" gap={2} alignItems="flex-end">
          <TextField
            label="Début"
            type="date"
            size="small"
            InputLabelProps={{ shrink: true }}
            value={startIso}
            onChange={(e) => setRange((r) => ({ ...r, startIso: e.target.value }))}
          />
          <TextField
            label="Fin"
            type="date"
            size="small"
            InputLabelProps={{ shrink: true }}
            value={endIso}
            onChange={(e) => setRange((r) => ({ ...r, endIso: e.target.value }))}
          />
          {isAdmin ? (
            <TextField
              select
              label="Commercial (optionnel)"
              size="small"
              sx={{ minWidth: 220 }}
              value={commercialId}
              onChange={(e) => setCommercialId(e.target.value)}
              InputLabelProps={{ shrink: true }}
            >
              <MenuItem value="">Tous les commerciaux</MenuItem>
              {commercials.map((c) => (
                <MenuItem key={c.id} value={String(c.id)}>
                  {`${c.first_name || ''} ${c.last_name || ''}`.trim() || c.id}
                </MenuItem>
              ))}
            </TextField>
          ) : (
            <Typography variant="caption" color="text.secondary">
              Périmètre : vos rapports uniquement.
            </Typography>
          )}
          <TextField
            label="Révision planning (UUID, optionnel)"
            size="small"
            sx={{ minWidth: 320 }}
            value={planningRevisionId}
            onChange={(e) => setPlanningRevisionId(e.target.value)}
            helperText="Filtre les rapports dont le segment ce jour-là pointe vers cette révision."
            InputLabelProps={{ shrink: true }}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={pureAutoPlanningOnly}
                onChange={(e) => setPureAutoPlanningOnly(e.target.checked)}
              />
            }
            label="Exclure segments manuels / auto avec surcharge weights"
          />
          <Button variant="contained" onClick={() => void handleFetch()} disabled={loading}>
            {loading ? <CircularProgress size={22} /> : 'Calculer'}
          </Button>
        </Box>
      </Paper>

      {result && result.report_count > 0 ? (
        <Paper sx={{ p: 2, mb: 2, maxWidth: 720 }}>
          <Typography variant="subtitle2" color="text.secondary">
            Rapports inclus : {result.report_count}
          </Typography>
          <Typography variant="h3" sx={{ mt: 1, fontWeight: 700 }}>
            {result.composite_0_100 != null ? `${result.composite_0_100} / 100` : '—'}
          </Typography>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle1" gutterBottom>
            Détail
          </Typography>
          <Typography variant="body2" component="div">
            Réalisation :{' '}
            <strong>{result.subscores?.completion?.value_0_100 ?? '—'}</strong> / 100 (pond.{' '}
            {(Number(result.subscores?.completion?.weight) || 0) * 100}%)
          </Typography>
          <Typography variant="body2" component="div">
            Stock déclaré :{' '}
            <strong>{result.subscores?.stock_declared?.value_0_100 ?? '—'}</strong> / 100 (pond.{' '}
            {(Number(result.subscores?.stock_declared?.weight) || 0) * 100}%)
          </Typography>
          <Typography variant="body2" component="div">
            Ressenti : <strong>{result.subscores?.feeling?.value_0_100 ?? '—'}</strong> / 100 (pond.{' '}
            {(Number(result.subscores?.feeling?.weight) || 0) * 100}%)
            {result.subscores?.feeling?.neutral_assumption_used ? (
              <span> — hypothèse neutre appliquée (aucune note saisie).</span>
            ) : (
              <span>
                {' '}
                — {result.subscores?.feeling?.ratings_used_count ?? 0} note(s) exploitée(s).
              </span>
            )}
          </Typography>
        </Paper>
      ) : null}

      {result?.formula_documentation_fr ? (
        <Paper sx={{ p: 2, maxWidth: 900 }}>
          <Typography variant="subtitle1" gutterBottom>
            Documentation de la formule ({result.version})
          </Typography>
          <Box
            sx={{
              typography: 'body2',
              color: 'text.primary',
              '& h2': {
                typography: 'h6',
                fontWeight: 600,
                mt: 2,
                mb: 1,
                '&:first-of-type': { mt: 0 },
              },
              '& h3': {
                typography: 'subtitle1',
                fontWeight: 600,
                mt: 1.5,
                mb: 0.75,
              },
              '& p': { mb: 1.25, lineHeight: 1.6 },
              '& ul': { pl: 2.5, mb: 1.25 },
              '& li': { mb: 0.5 },
              '& hr': {
                border: 'none',
                borderTop: '1px solid',
                borderColor: 'divider',
                my: 2,
              },
              '& strong': { fontWeight: 600 },
              '& code': {
                fontFamily: 'ui-monospace, monospace',
                fontSize: '0.85em',
                bgcolor: 'action.hover',
                px: 0.5,
                py: 0.125,
                borderRadius: 0.5,
              },
              '& em': { fontStyle: 'italic' },
            }}
          >
            <ReactMarkdown>{result.formula_documentation_fr}</ReactMarkdown>
          </Box>
        </Paper>
      ) : null}

      {NotifierSnackbar}
    </Box>
  )
}

export default PlanningEvaluation
