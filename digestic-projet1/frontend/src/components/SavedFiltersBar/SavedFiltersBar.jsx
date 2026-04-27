import React, { useCallback, useEffect, useState } from 'react'
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from '@mui/material'
import BookmarkAddIcon from '@mui/icons-material/BookmarkAdd'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'

function readExpandedFromStorage(storageKey) {
  try {
    const v = localStorage.getItem(storageKey)
    if (v === '0') {
      return false
    }
    if (v === '1') {
      return true
    }
  } catch {
    // ignore
  }
  return false
}

/**
 * Liste de préréglages de filtres (API via filterClient) : enregistrer / appliquer au clic.
 *
 * @param {object} p
 * @param {{ list: () => Promise, create: (b) => Promise, remove: (id) => Promise }} p.filterClient
 * @param {string} p.storageKeyExpanded — clé localStorage pour l’état replié/déplié
 * @param {string} [p.sectionTitle] — défaut « Filtres enregistrés »
 * @param {object} p.filters
 * @param {string} p.orderBy
 * @param {string} p.order
 * @param {string | null} p.activeSavedFilterId
 * @param {function} p.onSelectSaved
 * @param {function} [p.onActiveFilterRemoved]
 */
export function SavedFiltersBar(p) {
  const {
    filterClient,
    storageKeyExpanded,
    sectionTitle = 'Filtres enregistrés',
    filters,
    orderBy,
    order,
    activeSavedFilterId,
    onSelectSaved,
    onActiveFilterRemoved,
  } = p

  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(() => readExpandedFromStorage(storageKeyExpanded))
  const [listFetched, setListFetched] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saving, setSaving] = useState(false)

  const setExpandedAndStore = (next) => {
    setExpanded(next)
    try {
      localStorage.setItem(storageKeyExpanded, next ? '1' : '0')
    } catch {
      // ignore
    }
  }

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const list = await filterClient.list()
      setItems(list)
    } catch (e) {
      console.error(e)
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [filterClient])

  useEffect(() => {
    if (!expanded || listFetched) {
      return
    }
    setListFetched(true)
    void refresh()
  }, [expanded, listFetched, refresh])

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
      await filterClient.create({
        name,
        filters,
        orderBy,
        order,
      })
      setDialogOpen(false)
      setSaveName('')
      setExpandedAndStore(true)
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
      await filterClient.remove(item.id)
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
    <Box sx={{ mb: expanded ? 2 : 0.5 }}>
      <Box
        onClick={() => setExpandedAndStore(!expanded)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setExpandedAndStore(!expanded)
          }
        }}
        display="flex"
        alignItems="center"
        gap={0.5}
        aria-expanded={expanded}
        aria-label="Afficher ou masquer les filtres enregistrés"
        sx={{
          cursor: 'pointer',
          color: 'text.secondary',
          borderRadius: 1,
          px: 0.5,
          py: 0.25,
          width: 'fit-content',
          maxWidth: '100%',
          '&:hover': { color: 'text.primary', bgcolor: 'action.hover' },
        }}
      >
        <ExpandMoreIcon
          fontSize="small"
          sx={{
            flexShrink: 0,
            transform: expanded ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.2s',
          }}
        />
        <Typography variant="subtitle2" component="span">
          {sectionTitle}
          {!expanded && items.length > 0 && (
            <Typography component="span" variant="caption" color="text.disabled" sx={{ ml: 1 }}>
              ({items.length})
            </Typography>
          )}
        </Typography>
      </Box>

      <Collapse in={expanded} timeout="auto" unmountOnExit={false}>
        <Box display="flex" flexWrap="wrap" gap={1} alignItems="center" sx={{ pt: 1 }}>
          <Button
            size="small"
            variant="outlined"
            startIcon={<BookmarkAddIcon />}
            onClick={(e) => {
              e.stopPropagation()
              openSaveDialog()
            }}
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
      </Collapse>

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
