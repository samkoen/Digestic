import React, { useCallback, useEffect, useState } from 'react'
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from '@mui/material'
import BookmarkAddIcon from '@mui/icons-material/BookmarkAdd'
import {
  createPharmacySavedFilter,
  deletePharmacySavedFilter,
  fetchPharmacySavedFilters,
} from '../../services/pharmacySavedFiltersService'

/**
 * Liste de préréglages de filtres : enregistrer la combinaison actuelle, appliquer au clic.
 *
 * @param {object} p
 * @param {object} p.filters
 * @param {string} p.orderBy
 * @param {string} p.order
 * @param {string | null} p.activeSavedFilterId
 * @param {function} p.onSelectSaved — (item) => void
 * @param {function} [p.onActiveFilterRemoved] — si le filtre actif est supprimé
 */
export function PharmacySavedFiltersBar(p) {
  const {
    filters,
    orderBy,
    order,
    activeSavedFilterId,
    onSelectSaved,
    onActiveFilterRemoved,
  } = p

  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saving, setSaving] = useState(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const list = await fetchPharmacySavedFilters()
      setItems(list)
    } catch (e) {
      console.error(e)
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const openSaveDialog = () => {
    setSaveName('')
    setDialogOpen(true)
  }

  const handleSave = async () => {
    const name = saveName.trim()
    if (!name) {
      return
    }
    setSaving(true)
    try {
      await createPharmacySavedFilter({
        name,
        filters,
        orderBy,
        order,
      })
      setDialogOpen(false)
      setSaveName('')
      await refresh()
    } catch (e) {
      console.error(e)
      alert(e?.response?.data?.error || e.message || 'Erreur à l’enregistrement')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteChip = async (item, e) => {
    e.stopPropagation()
    if (!window.confirm(`Supprimer le filtre « ${item.name} » ?`)) {
      return
    }
    try {
      await deletePharmacySavedFilter(item.id)
      if (activeSavedFilterId === item.id && onActiveFilterRemoved) {
        onActiveFilterRemoved()
      }
      await refresh()
    } catch (err) {
      console.error(err)
      alert(err?.response?.data?.error || err.message || 'Erreur à la suppression')
    }
  }

  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
        Filtres enregistrés
      </Typography>
      <Box display="flex" flexWrap="wrap" gap={1} alignItems="center">
        <Button
          size="small"
          variant="outlined"
          startIcon={<BookmarkAddIcon />}
          onClick={openSaveDialog}
        >
          Enregistrer le filtre actuel
        </Button>
        {loading && <CircularProgress size={22} />}
        {!loading && items.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            Aucun pour l’instant — réglez les filtres du tableau puis enregistrez-les ici.
          </Typography>
        )}
        {items.map((item) => (
          <Chip
            key={item.id}
            label={item.name}
            onClick={() => onSelectSaved(item)}
            onDelete={(ev) => void handleDeleteChip(item, ev)}
            color={activeSavedFilterId === item.id ? 'primary' : 'default'}
            variant={activeSavedFilterId === item.id ? 'filled' : 'outlined'}
            size="small"
          />
        ))}
      </Box>

      <Dialog open={dialogOpen} onClose={() => !saving && setDialogOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>Enregistrer ce filtre</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Nom du filtre"
            fullWidth
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            disabled={saving}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                void handleSave()
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} disabled={saving}>
            Annuler
          </Button>
          <Button onClick={() => void handleSave()} variant="contained" disabled={saving || !saveName.trim()}>
            {saving ? '…' : 'Enregistrer'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
