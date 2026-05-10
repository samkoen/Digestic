import React, { useCallback, useEffect, useState } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import {
  ADVANCED_FILTER_COMBINE,
  FIELD_OPTIONS_BY_SUBJECT,
  SUBJECT_OPTIONS,
  emptyCondition,
  emptyPayload,
  getFieldMeta,
  optionsForValueSelect,
} from '../../utils/pharmacyAdvancedFilterSchema'
import {
  createPharmacyAdvancedFilter,
  deletePharmacyAdvancedFilter,
  listPharmacyAdvancedFilters,
  updatePharmacyAdvancedFilter,
} from '../../services/pharmacyAdvancedFilterService'
import { useNotifier } from '../../hooks/useNotifier'

function normalizeConditionsFromApi(conds) {
  if (!Array.isArray(conds)) {
    return []
  }
  return conds.map((c) => {
    const subject = c.subject || 'pharmacy'
    const field = c.field || 'pharmacy_status'
    let value = c.value != null ? String(c.value) : ''
    const meta = getFieldMeta(subject, field)
    const opts = optionsForValueSelect(meta?.valueSelect)
    if (opts && (!value || !opts.some((o) => o.value === value))) {
      value = opts[0].value
    }
    return {
      ...emptyCondition(),
      subject,
      field,
      op: c.op || '=',
      value,
    }
  })
}

export default function PharmacyAdvancedFiltersPage() {
  const { notify, NotifierSnackbar } = useNotifier()
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [name, setName] = useState('')
  const [payload, setPayload] = useState(() => emptyPayload())
  const [saving, setSaving] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const list = await listPharmacyAdvancedFilters()
      setRows(Array.isArray(list) ? list : [])
    } catch (e) {
      console.error(e)
      notify(e?.response?.data?.error || e.message || 'Erreur de chargement', 'error')
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [notify])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const openCreate = () => {
    setEditingId(null)
    setName('')
    setPayload(emptyPayload())
    setDialogOpen(true)
  }

  const openEdit = (row) => {
    setEditingId(row.id)
    setName(row.name || '')
    const p = row.payload && typeof row.payload === 'object' ? row.payload : emptyPayload()
    setPayload({
      combine: p.combine === 'or' ? 'or' : 'and',
      conditions: normalizeConditionsFromApi(p.conditions),
    })
    setDialogOpen(true)
  }

  const closeDialog = () => {
    if (!saving) {
      setDialogOpen(false)
    }
  }

  const addCondition = () => {
    setPayload((prev) => ({
      ...prev,
      conditions: [...prev.conditions, emptyCondition()],
    }))
  }

  const updateCondition = (idx, patch) => {
    setPayload((prev) => {
      const conditions = prev.conditions.map((c, i) => (i === idx ? { ...c, ...patch } : c))
      return { ...prev, conditions }
    })
  }

  const removeCondition = (idx) => {
    setPayload((prev) => ({
      ...prev,
      conditions: prev.conditions.filter((_, i) => i !== idx),
    }))
  }

  const handleSubjectChange = (idx, subject) => {
    const fields = FIELD_OPTIONS_BY_SUBJECT[subject] || []
    const first = fields[0]?.value || 'pharmacy_status'
    const m = getFieldMeta(subject, first)
    const opts = optionsForValueSelect(m?.valueSelect)
    const value = opts ? opts[0].value : ''
    updateCondition(idx, { subject, field: first, op: '=', value })
  }

  const handleSave = async () => {
    const n = name.trim()
    if (!n) {
      notify('Nom requis', 'error')
      return
    }
    setSaving(true)
    try {
      const apiPayload = {
        combine: payload.combine === 'or' ? 'or' : 'and',
        conditions: payload.conditions.map(({ subject, field, op, value }) => ({
          subject,
          field,
          op,
          value,
        })),
      }
      if (editingId) {
        await updatePharmacyAdvancedFilter(editingId, { name: n, payload: apiPayload })
        notify('Filtre mis à jour', 'success')
      } else {
        await createPharmacyAdvancedFilter({ name: n, payload: apiPayload })
        notify('Filtre créé', 'success')
      }
      setDialogOpen(false)
      await refresh()
    } catch (e) {
      console.error(e)
      notify(e?.response?.data?.error || e.message || 'Erreur de sauvegarde', 'error')
    } finally {
      setSaving(false)
    }
  }

  const runDelete = async () => {
    if (!deleteTarget) {
      return
    }
    try {
      await deletePharmacyAdvancedFilter(deleteTarget.id)
      notify('Filtre supprimé', 'success')
      setDeleteTarget(null)
      await refresh()
    } catch (e) {
      console.error(e)
      notify(e?.response?.data?.error || e.message || 'Erreur', 'error')
    }
  }

  return (
    <Box>
      <Box display="flex" alignItems="center" gap={2} mb={2} flexWrap="wrap">
        <Button component={RouterLink} to="/pharmacies" startIcon={<ArrowBackIcon />} size="small">
          Retour à la liste
        </Button>
        <Typography variant="h4" component="span" sx={{ flex: 1, minWidth: 200 }}>
          Filtres avancés (liste pharmacies)
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
          Nouveau filtre
        </Button>
      </Box>

      <Typography variant="body2" color="text.secondary" paragraph>
        Définissez des préréglages à base de conditions (pharmacie, facture, BL) avec combinaison ET ou
        OU. Ces filtres sont ensuite sélectionnables sur la page Pharmacies.
      </Typography>

      <Paper elevation={1}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Nom</TableCell>
              <TableCell>Mis à jour</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading && (
              <TableRow>
                <TableCell colSpan={3}>
                  <Typography variant="body2">Chargement…</Typography>
                </TableCell>
              </TableRow>
            )}
            {!loading && rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={3}>
                  <Typography variant="body2" color="text.secondary">
                    Aucun filtre défini pour l’instant.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
            {!loading &&
              rows.map((r) => (
                <TableRow key={r.id} hover>
                  <TableCell>{r.name}</TableCell>
                  <TableCell>{r.updatedAt ? String(r.updatedAt).slice(0, 19).replace('T', ' ') : '—'}</TableCell>
                  <TableCell align="right">
                    <IconButton size="small" aria-label="Modifier" onClick={() => openEdit(r)}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      aria-label="Supprimer"
                      onClick={() => setDeleteTarget(r)}
                    >
                      <DeleteOutlineIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Paper>

      <Dialog open={dialogOpen} onClose={closeDialog} maxWidth="md" fullWidth>
        <DialogTitle>{editingId ? 'Modifier le filtre' : 'Nouveau filtre'}</DialogTitle>
        <DialogContent dividers>
          <TextField
            label="Nom du filtre"
            value={name}
            onChange={(e) => setName(e.target.value)}
            fullWidth
            margin="normal"
            autoFocus
          />
          <FormControl fullWidth margin="normal" size="small">
            <InputLabel id="comb-label">Comment combiner les conditions</InputLabel>
            <Select
              labelId="comb-label"
              label="Comment combiner les conditions"
              value={payload.combine === 'or' ? 'or' : 'and'}
              onChange={(e) => setPayload((p) => ({ ...p, combine: e.target.value }))}
            >
              {ADVANCED_FILTER_COMBINE.map((o) => (
                <MenuItem key={o.value} value={o.value}>
                  {o.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
            Conditions
          </Typography>

          {payload.conditions.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              Ajoutez au moins une condition (sinon le filtre ne restreint pas la liste).
            </Typography>
          )}

          {payload.conditions.map((c, idx) => {
            const fieldList = FIELD_OPTIONS_BY_SUBJECT[c.subject] || []
            const meta = getFieldMeta(c.subject, c.field)
            const ops = meta?.ops || [{ value: '=', label: '=' }]
            const valueOpts = optionsForValueSelect(meta?.valueSelect)

            return (
              <Box
                key={c._key}
                display="grid"
                gridTemplateColumns={{ xs: '1fr', sm: '1fr 1fr 120px 1fr auto' }}
                gap={1}
                alignItems="center"
                sx={{ mb: 1.5, p: 1, bgcolor: 'action.hover', borderRadius: 1 }}
              >
                <FormControl size="small" fullWidth>
                  <InputLabel id={`s-${idx}`}>Portée</InputLabel>
                  <Select
                    labelId={`s-${idx}`}
                    label="Portée"
                    value={c.subject}
                    onChange={(e) => handleSubjectChange(idx, e.target.value)}
                  >
                    {SUBJECT_OPTIONS.map((o) => (
                      <MenuItem key={o.value} value={o.value}>
                        {o.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small" fullWidth>
                  <InputLabel id={`f-${idx}`}>Champ</InputLabel>
                  <Select
                    labelId={`f-${idx}`}
                    label="Champ"
                    value={c.field}
                    onChange={(e) => {
                      const nf = e.target.value
                      const m = getFieldMeta(c.subject, nf)
                      const nextOp = m?.ops?.[0]?.value || '='
                      const prevMeta = getFieldMeta(c.subject, c.field)
                      const opts = optionsForValueSelect(m?.valueSelect)
                      let nextVal = c.value
                      if (opts) {
                        nextVal = opts.some((o) => o.value === String(c.value)) ? c.value : opts[0].value
                      } else if (optionsForValueSelect(prevMeta?.valueSelect)) {
                        nextVal = ''
                      }
                      updateCondition(idx, { field: nf, op: nextOp, value: nextVal })
                    }}
                  >
                    {fieldList.map((o) => (
                      <MenuItem key={o.value} value={o.value}>
                        {o.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small" fullWidth>
                  <InputLabel id={`o-${idx}`}>Opérateur</InputLabel>
                  <Select
                    labelId={`o-${idx}`}
                    label="Opérateur"
                    value={c.op}
                    onChange={(e) => updateCondition(idx, { op: e.target.value })}
                  >
                    {ops.map((o) => (
                      <MenuItem key={o.value} value={o.value}>
                        {o.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                {valueOpts ? (
                  <FormControl size="small" fullWidth>
                    <InputLabel id={`v-${idx}`}>Valeur</InputLabel>
                    <Select
                      labelId={`v-${idx}`}
                      label="Valeur"
                      value={
                        valueOpts.some((o) => o.value === c.value) ? c.value : valueOpts[0].value
                      }
                      onChange={(e) => updateCondition(idx, { value: e.target.value })}
                    >
                      {valueOpts.map((o) => (
                        <MenuItem key={o.value} value={o.value}>
                          {o.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                ) : (
                  <TextField
                    size="small"
                    label="Valeur"
                    value={c.value}
                    onChange={(e) => updateCondition(idx, { value: e.target.value })}
                    fullWidth
                    placeholder={meta?.valueHint || ''}
                  />
                )}
                <Button size="small" color="inherit" onClick={() => removeCondition(idx)}>
                  Retirer
                </Button>
              </Box>
            )
          })}

          <Button size="small" onClick={addCondition} sx={{ mt: 1 }}>
            + Condition
          </Button>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialog} disabled={saving}>
            Annuler
          </Button>
          <Button variant="contained" onClick={() => void handleSave()} disabled={saving}>
            {saving ? '…' : 'Enregistrer'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Supprimer « {deleteTarget?.name} » ?</DialogTitle>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Annuler</Button>
          <Button color="error" onClick={() => void runDelete()}>
            Supprimer
          </Button>
        </DialogActions>
      </Dialog>

      {NotifierSnackbar}
    </Box>
  )
}
