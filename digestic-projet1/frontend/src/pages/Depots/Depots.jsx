import React, { useCallback, useEffect, useState } from 'react'
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
import { depotService } from '../../services/depotService'
import ResizableTextField from '../../components/ResizableTextField/ResizableTextField'

const emptyForm = {
  name: '',
  address: '',
  city: '',
  postal_code: '',
  depot_type: 'secondaire',
  quantity: 0,
}

function Depots() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [addStockRow, setAddStockRow] = useState(null)
  const [addQty, setAddQty] = useState(0)
  const [transferOpen, setTransferOpen] = useState(false)
  const [transfer, setTransfer] = useState({
    from_warehouse_id: '',
    to_warehouse_id: '',
    quantity: 0,
  })

  const load = useCallback(async () => {
    setError(null)
    setLoading(true)
    try {
      const data = await depotService.list()
      setRows(Array.isArray(data) ? data : [])
    } catch (e) {
      setError("Impossible de charger les dépôts")
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const openNew = () => {
    setEditing(null)
    setForm(emptyForm)
    setFormOpen(true)
  }

  const openEdit = (r) => {
    setEditing(r)
    setForm({
      name: r.name || '',
      address: r.address || '',
      city: r.city || '',
      postal_code: r.postal_code || '',
      depot_type: r.depot_type || 'secondaire',
      quantity: r.quantity ?? 0,
    })
    setFormOpen(true)
  }

  const handleFormChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (editing) {
        await depotService.update(editing.id, {
          name: form.name,
          address: form.address,
          city: form.city,
          postal_code: form.postal_code,
          depot_type: form.depot_type,
          quantity: Number(form.quantity) || 0,
        })
      } else {
        await depotService.create({
          name: form.name,
          address: form.address,
          city: form.city,
          postal_code: form.postal_code,
          depot_type: form.depot_type,
          quantity: Number(form.quantity) || 0,
        })
      }
      setFormOpen(false)
      await load()
    } catch (err) {
      const msg = err.response?.data?.error || "Enregistrement impossible"
      alert(msg)
    } finally {
      setSaving(false)
    }
  }

  const handleAddStock = async (e) => {
    e.preventDefault()
    if (!addStockRow) return
    setSaving(true)
    try {
      await depotService.addStock(addStockRow.id, addQty)
      setAddStockRow(null)
      setAddQty(0)
      await load()
    } catch (err) {
      const msg = err.response?.data?.error || "Opération refusée"
      alert(msg)
    } finally {
      setSaving(false)
    }
  }

  const handleTransfer = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await depotService.transfer({
        from_warehouse_id: transfer.from_warehouse_id,
        to_warehouse_id: transfer.to_warehouse_id,
        quantity: Number(transfer.quantity) || 0,
      })
      setTransferOpen(false)
      setTransfer({ from_warehouse_id: '', to_warehouse_id: '', quantity: 0 })
      await load()
    } catch (err) {
      const msg = err.response?.data?.error || "Transfert impossible"
      alert(msg)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Dépôts</Typography>
        <Box display="flex" gap={1} flexWrap="wrap">
          <Button variant="outlined" startIcon={<SwapHorizIcon />} onClick={() => setTransferOpen(true)}>
            Transfert
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={openNew}>
            Nouveau dépôt
          </Button>
        </Box>
      </Box>
      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Nom</TableCell>
            <TableCell>Ville</TableCell>
            <TableCell>Adresse</TableCell>
            <TableCell align="right">Quantité</TableCell>
            <TableCell align="right">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={r.id} hover>
              <TableCell>{r.name}</TableCell>
              <TableCell>{r.city || '—'}</TableCell>
              <TableCell>{r.address || '—'}</TableCell>
              <TableCell align="right">{r.quantity ?? 0}</TableCell>
              <TableCell align="right">
                <Button size="small" onClick={() => openEdit(r)}>
                  Modifier
                </Button>
                {r.depot_type === 'central' && (
                  <Button
                    size="small"
                    onClick={() => {
                      setAddStockRow(r)
                      setAddQty(0)
                    }}
                  >
                    Ajout stock
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {rows.length === 0 && !error && (
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          Aucun dépôt. Créez-en un ou lancez le script d&apos;initialisation (entrepôt par défaut).
        </Typography>
      )}

      <Dialog open={formOpen} onClose={() => !saving && setFormOpen(false)} maxWidth="sm" fullWidth>
        <form onSubmit={handleSave}>
          <DialogTitle>{editing ? 'Modifier le dépôt' : 'Nouveau dépôt'}</DialogTitle>
          <DialogContent>
            <ResizableTextField
              fullWidth
              required
              margin="normal"
              name="name"
              label="Nom"
              value={form.name}
              onChange={handleFormChange}
            />
            <ResizableTextField
              fullWidth
              select
              margin="normal"
              name="depot_type"
              label="Type"
              value={form.depot_type}
              onChange={handleFormChange}
            >
              <MenuItem value="central">Central</MenuItem>
              <MenuItem value="secondaire">Secondaire</MenuItem>
            </ResizableTextField>
            <ResizableTextField
              fullWidth
              margin="normal"
              name="address"
              label="Adresse"
              value={form.address}
              onChange={handleFormChange}
            />
            <ResizableTextField
              fullWidth
              margin="normal"
              name="city"
              label="Ville"
              value={form.city}
              onChange={handleFormChange}
            />
            <ResizableTextField
              fullWidth
              margin="normal"
              name="postal_code"
              label="Code postal"
              value={form.postal_code}
              onChange={handleFormChange}
            />
            <ResizableTextField
              fullWidth
              type="number"
              margin="normal"
              name="quantity"
              label="Quantité initiale (stock sur site)"
              value={form.quantity}
              onChange={handleFormChange}
              inputProps={{ min: 0 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setFormOpen(false)} disabled={saving}>
              Annuler
            </Button>
            <Button type="submit" variant="contained" disabled={saving}>
              {saving ? '…' : 'Enregistrer'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <Dialog
        open={!!addStockRow}
        onClose={() => !saving && setAddStockRow(null)}
        maxWidth="xs"
        fullWidth
      >
        <form onSubmit={handleAddStock}>
          <DialogTitle>
            Ajout de stock{addStockRow ? ` : ${addStockRow.name}` : ''}
          </DialogTitle>
          <DialogContent>
            <TextField
              fullWidth
              type="number"
              margin="normal"
              label="Quantité à ajouter"
              value={addQty}
              onChange={(e) => setAddQty(parseInt(e.target.value, 10) || 0)}
              inputProps={{ min: 1 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setAddStockRow(null)} disabled={saving}>
              Annuler
            </Button>
            <Button type="submit" variant="contained" disabled={saving || addQty < 1}>
              Ajouter
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <Dialog open={transferOpen} onClose={() => !saving && setTransferOpen(false)} maxWidth="sm" fullWidth>
        <form onSubmit={handleTransfer}>
          <DialogTitle>Transfert entre dépôts</DialogTitle>
          <DialogContent>
            <ResizableTextField
              fullWidth
              select
              required
              margin="normal"
              label="Dépôt source"
              value={transfer.from_warehouse_id}
              onChange={(e) => setTransfer((p) => ({ ...p, from_warehouse_id: e.target.value }))}
            >
              <MenuItem value="">Choisir…</MenuItem>
              {rows.map((r) => (
                <MenuItem key={r.id} value={r.id}>
                  {r.name} (stock: {r.quantity})
                </MenuItem>
              ))}
            </ResizableTextField>
            <ResizableTextField
              fullWidth
              select
              required
              margin="normal"
              label="Dépôt destination"
              value={transfer.to_warehouse_id}
              onChange={(e) => setTransfer((p) => ({ ...p, to_warehouse_id: e.target.value }))}
            >
              <MenuItem value="">Choisir…</MenuItem>
              {rows.map((r) => (
                <MenuItem key={r.id} value={r.id}>
                  {r.name} (stock: {r.quantity})
                </MenuItem>
              ))}
            </ResizableTextField>
            <ResizableTextField
              fullWidth
              type="number"
              required
              margin="normal"
              label="Quantité"
              value={transfer.quantity}
              onChange={(e) =>
                setTransfer((p) => ({ ...p, quantity: parseInt(e.target.value, 10) || 0 }))
              }
              inputProps={{ min: 1 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setTransferOpen(false)} disabled={saving}>
              Annuler
            </Button>
            <Button type="submit" variant="contained" disabled={saving}>
              Transférer
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  )
}

export default Depots
