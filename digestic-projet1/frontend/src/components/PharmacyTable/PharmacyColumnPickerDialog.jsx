import React, { useEffect, useMemo, useState } from 'react'
import {
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  FormGroup,
  List,
  ListItem,
  Typography,
} from '@mui/material'

/**
 * Admin : coche / décoche des colonnes. L’ordre suit `definition` (haut → bas).
 */
export default function PharmacyColumnPickerDialog({
  open,
  onClose,
  definition,
  initialKeys,
  onSave,
  saving = false,
}) {
  const keysInOrder = useMemo(
    () => (definition || []).map((c) => c.key),
    [definition],
  )
  const [sel, setSel] = useState(() => new Set())

  useEffect(() => {
    if (open) {
      setSel(new Set(initialKeys || []))
    }
  }, [open, initialKeys])

  const toggle = (k) => {
    setSel((prev) => {
      const n = new Set(prev)
      if (n.has(k)) {
        n.delete(k)
      } else {
        n.add(k)
      }
      return n
    })
  }

  const handleSave = () => {
    const out = keysInOrder.filter((k) => sel.has(k))
    if (out.length < 1) {
      return
    }
    onSave(out)
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Colonnes visibles (tableau Pharmacies)</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Au moins une colonne. L’ordre d’affichage suit la liste ci-dessous.
        </Typography>
        <List dense>
          {keysInOrder.map((key) => {
            const def = definition.find((c) => c.key === key)
            return (
              <ListItem key={key} disableGutters>
                <FormGroup>
                  <FormControlLabel
                    control={(
                      <Checkbox
                        checked={sel.has(key)}
                        onChange={() => toggle(key)}
                        size="small"
                      />
                    )}
                    label={def?.label || key}
                  />
                </FormGroup>
              </ListItem>
            )
          })}
        </List>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Annuler</Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={saving || sel.size < 1}
        >
          Enregistrer
        </Button>
      </DialogActions>
    </Dialog>
  )
}
