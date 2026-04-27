import React, { useEffect, useState } from 'react'
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControlLabel,
  Checkbox,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import { productService } from '../../services/productService'

const emptyForm = () => ({
  code: '',
  ean: '',
  name: '',
  description: '',
  wholesale_unit_price: '',
  currency: 'EUR',
  vat_rate: '20',
  units_per_carton: '1',
  is_default_for_billing: false,
  is_active: true,
})

function Products() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [openForm, setOpenForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [formData, setFormData] = useState(emptyForm)

  const load = async () => {
    try {
      setLoading(true)
      const data = await productService.list({ active_only: false })
      setRows(Array.isArray(data) ? data : [])
    } catch (e) {
      console.error(e)
      setRows([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleCreate = () => {
    setEditing(null)
    setFormData(emptyForm())
    setOpenForm(true)
  }

  const handleEdit = (p) => {
    setEditing(p)
    setFormData({
      code: p.code || '',
      ean: p.ean || '',
      name: p.name || '',
      description: p.description || '',
      wholesale_unit_price: String(p.wholesale_unit_price ?? ''),
      currency: p.currency || 'EUR',
      vat_rate: String(p.vat_rate ?? ''),
      units_per_carton: String(p.units_per_carton ?? '1'),
      is_default_for_billing: Boolean(p.is_default_for_billing),
      is_active: p.is_active !== false,
    })
    setOpenForm(true)
  }

  const handleDelete = async (p) => {
    if (!window.confirm(`Désactiver le produit « ${p.name} » ?`)) return
    try {
      await productService.delete(p.id)
      await load()
    } catch (e) {
      const msg = e.response?.data?.error || e.message
      alert(typeof msg === 'string' ? msg : 'Erreur lors de la désactivation')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const payload = {
      code: formData.code.trim() || null,
      ean: formData.ean.trim() || null,
      name: formData.name.trim(),
      description: formData.description.trim() || null,
      wholesale_unit_price: Number(formData.wholesale_unit_price),
      currency: (formData.currency || 'EUR').trim().toUpperCase().slice(0, 3),
      vat_rate: Number(formData.vat_rate),
      units_per_carton: parseInt(formData.units_per_carton, 10),
      is_default_for_billing: formData.is_default_for_billing,
      is_active: formData.is_active,
    }
    try {
      if (editing) {
        await productService.update(editing.id, payload)
      } else {
        await productService.create(payload)
      }
      setOpenForm(false)
      await load()
    } catch (e) {
      const msg = e.response?.data?.error || e.message
      alert(typeof msg === 'string' ? msg : 'Erreur lors de l\'enregistrement')
    }
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const fmtMoney = (n) =>
    n == null || Number.isNaN(Number(n))
      ? '—'
      : new Intl.NumberFormat('fr-FR', {
          style: 'currency',
          currency: 'EUR',
          minimumFractionDigits: 2,
        }).format(Number(n))

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Produits</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleCreate}>
          Nouveau produit
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Code</TableCell>
              <TableCell>EAN</TableCell>
              <TableCell>Nom</TableCell>
              <TableCell align="right">PU HT</TableCell>
              <TableCell align="right">TVA %</TableCell>
              <TableCell align="right">Unités / carton</TableCell>
              <TableCell>Défaut facturation</TableCell>
              <TableCell>Actif</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9}>
                  <Typography color="text.secondary" sx={{ py: 2 }}>
                    Aucun produit. Créez-en un pour alimenter le stock et les visites.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              rows.map((p) => (
                <TableRow key={p.id} hover>
                  <TableCell>{p.code || '—'}</TableCell>
                  <TableCell>{p.ean || '—'}</TableCell>
                  <TableCell>{p.name}</TableCell>
                  <TableCell align="right">{fmtMoney(p.wholesale_unit_price)}</TableCell>
                  <TableCell align="right">
                    {p.vat_rate != null ? `${Number(p.vat_rate)} %` : '—'}
                  </TableCell>
                  <TableCell align="right">{p.units_per_carton ?? '—'}</TableCell>
                  <TableCell>
                    {p.is_default_for_billing ? (
                      <Chip label="Oui" color="primary" size="small" />
                    ) : (
                      <Chip label="Non" variant="outlined" size="small" />
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={p.is_active ? 'Oui' : 'Non'}
                      color={p.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={() => handleEdit(p)} aria-label="Modifier">
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleDelete(p)}
                      aria-label="Désactiver"
                      disabled={!p.is_active}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openForm} onClose={() => setOpenForm(false)} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit}>
          <DialogTitle>{editing ? 'Modifier le produit' : 'Nouveau produit'}</DialogTitle>
          <DialogContent>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
              <TextField
                fullWidth
                label="Code interne"
                name="code"
                value={formData.code}
                onChange={handleChange}
              />
              <TextField
                fullWidth
                label="EAN"
                name="ean"
                value={formData.ean}
                onChange={handleChange}
              />
              <TextField
                fullWidth
                required
                label="Nom"
                name="name"
                value={formData.name}
                onChange={handleChange}
              />
              <TextField
                fullWidth
                label="Description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                multiline
                minRows={2}
              />
              <TextField
                fullWidth
                required
                label="Prix unitaire HT"
                name="wholesale_unit_price"
                type="number"
                inputProps={{ step: '0.0001', min: 0 }}
                value={formData.wholesale_unit_price}
                onChange={handleChange}
              />
              <TextField
                fullWidth
                required
                label="Devise (ISO)"
                name="currency"
                value={formData.currency}
                onChange={handleChange}
                inputProps={{ maxLength: 3 }}
              />
              <TextField
                fullWidth
                required
                label="TVA (%)"
                name="vat_rate"
                type="number"
                inputProps={{ step: '0.01', min: 0, max: 100 }}
                value={formData.vat_rate}
                onChange={handleChange}
              />
              <TextField
                fullWidth
                required
                label="Unités par carton"
                name="units_per_carton"
                type="number"
                inputProps={{ min: 1, step: 1 }}
                value={formData.units_per_carton}
                onChange={handleChange}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    name="is_default_for_billing"
                    checked={formData.is_default_for_billing}
                    onChange={handleChange}
                  />
                }
                label="Produit par défaut pour la facturation des visites"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    name="is_active"
                    checked={formData.is_active}
                    onChange={handleChange}
                  />
                }
                label="Produit actif"
              />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button type="button" onClick={() => setOpenForm(false)}>
              Annuler
            </Button>
            <Button type="submit" variant="contained">
              {editing ? 'Enregistrer' : 'Créer'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  )
}

export default Products
