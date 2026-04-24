import React, { useEffect, useMemo, useState } from 'react'
import {
  Avatar,
  Box,
  Button,
  CircularProgress,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { format } from 'date-fns'
import { deliveryNoteService } from '../../services/deliveryNoteService'
import { pharmacyService } from '../../services/pharmacyService'
import { userService } from '../../services/userService'
import CloseIcon from '@mui/icons-material/Close'

function DeliveryNotes() {
  const [deliveryNotes, setDeliveryNotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [pharmacyMap, setPharmacyMap] = useState({})
  const [commercialMap, setCommercialMap] = useState({})
  const [filters, setFilters] = useState({
    pharmacy: '',
    commercial: '',
    startDate: '',
    endDate: '',
  })
  const [convertDialogOpen, setConvertDialogOpen] = useState(false)
  const [convertTarget, setConvertTarget] = useState(null)
  const [convertForm, setConvertForm] = useState({
    bottles: 0,
    amount: 0,
  })

  useEffect(() => {
    fetchDeliveryNotes()
    fetchPharmacyMap()
    fetchCommercialMap()
  }, [])

  const fetchDeliveryNotes = async () => {
    try {
      setLoading(true)
      const storedUser = localStorage.getItem('user')
      const currentUser = storedUser ? JSON.parse(storedUser) : null
      const params = {}
      if (currentUser && currentUser.role === 'commercial') {
        params.commercial_id = currentUser.id
      }
      const data = await deliveryNoteService.getAll(params)
      setDeliveryNotes(data)
    } catch (error) {
      console.error('Erreur lors du chargement des bons de livraison:', error)
      setDeliveryNotes([])
    } finally {
      setLoading(false)
    }
  }

  const fetchPharmacyMap = async () => {
    try {
      const data = await pharmacyService.getAll()
      const map = data.reduce((acc, pharmacy) => {
        acc[pharmacy.id] = {
          name: pharmacy.name,
          photo_url: pharmacy.photo_url,
        }
        return acc
      }, {})
      setPharmacyMap(map)
    } catch (error) {
      console.error('Erreur lors du chargement des pharmacies:', error)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    try {
      return format(new Date(dateString), 'dd/MM/yyyy')
    } catch {
      return dateString
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      sent: 'success',
      pending: 'warning',
      confirmed: 'primary',
      default: 'default',
    }
    return colors[status] || colors.default
  }

  const fetchCommercialMap = async () => {
    try {
      const data = await userService.getAll('commercial')
      const map = data.reduce((acc, user) => {
        acc[user.id] = `${user.first_name} ${user.last_name}`
        return acc
      }, {})
      setCommercialMap(map)
    } catch (error) {
      console.error('Erreur lors du chargement des commerciaux:', error)
    }
  }

  const getPhotoUrl = (pharmacyId) => {
    const stored = pharmacyMap[pharmacyId]
    if (stored?.photo_url) {
      return stored.photo_url
    }
    const seed = encodeURIComponent(pharmacyId || 'pharmacy')
    return `https://picsum.photos/seed/${seed}/200/200`
  }

  const filterDeliveryNotes = useMemo(() => {
    return deliveryNotes.filter((note) => {
      if (filters.pharmacy && note.pharmacy_id !== filters.pharmacy) {
        return false
      }
      if (filters.commercial && note.commercial_id !== filters.commercial) {
        return false
      }
      if (filters.startDate) {
        const start = new Date(new Date(filters.startDate).setHours(0, 0, 0, 0))
        const delivery = note.delivery_date ? new Date(note.delivery_date) : null
        if (!delivery || delivery < start) {
          return false
        }
      }
      if (filters.endDate) {
        const end = new Date(new Date(filters.endDate).setHours(23, 59, 59, 999))
        const delivery = note.delivery_date ? new Date(note.delivery_date) : null
        if (!delivery || delivery > end) {
          return false
        }
      }
      return true
    })
  }, [deliveryNotes, filters])

  const pharmacyOptions = useMemo(() => {
    return Object.entries(pharmacyMap)
      .map(([id, data]) => ({ id, name: data.name || 'Pharmacie'}))
      .sort((a, b) => a.name.localeCompare(b.name, 'fr'))
  }, [pharmacyMap])

  const commercialOptions = useMemo(() => {
    return Object.entries(commercialMap)
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name, 'fr'))
  }, [commercialMap])

  const handleFilterChange = (field, value) => {
    setFilters((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const openConvertDialog = (note) => {
    setConvertTarget(note)
    setConvertForm({
      bottles: note.bottles_count,
      amount: note.bottles_count * 10,
    })
    setConvertDialogOpen(true)
  }

  const closeConvertDialog = () => {
    setConvertDialogOpen(false)
    setConvertTarget(null)
  }

  const handleConvertSubmit = async () => {
    if (!convertTarget) return
    try {
      await deliveryNoteService.convertToInvoice(convertTarget.id, {
        bottles_to_invoice: convertForm.bottles,
        amount: convertForm.amount,
      })
      closeConvertDialog()
      fetchDeliveryNotes()
    } catch (error) {
      console.error('Erreur lors de la conversion en facture:', error)
      alert('Erreur lors de la conversion en facture')
    }
  }


  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Bons de livraison
      </Typography>
      <Box
        display="flex"
        flexWrap="wrap"
        gap={2}
        mb={2}
        alignItems="center"
      >
        <TextField
          select
          label="Pharmacie"
          size="small"
          value={filters.pharmacy}
          onChange={(e) => handleFilterChange('pharmacy', e.target.value)}
          sx={{ minWidth: 200 }}
        >
          <MenuItem value="">Toutes</MenuItem>
          {pharmacyOptions.map((pharmacy) => (
            <MenuItem key={pharmacy.id} value={pharmacy.id}>
              {pharmacy.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Commercial"
          size="small"
          value={filters.commercial}
          onChange={(e) => handleFilterChange('commercial', e.target.value)}
          sx={{ minWidth: 200 }}
        >
          <MenuItem value="">Tous</MenuItem>
          {commercialOptions.map((commercial) => (
            <MenuItem key={commercial.id} value={commercial.id}>
              {commercial.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Début"
          type="date"
          size="small"
          value={filters.startDate}
          onChange={(e) => handleFilterChange('startDate', e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Fin"
          type="date"
          size="small"
          value={filters.endDate}
          onChange={(e) => handleFilterChange('endDate', e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
      </Box>
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="240px">
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Pharmacie</TableCell>
                <TableCell>Date dépôt</TableCell>
                <TableCell align="right">Bouteilles</TableCell>
                <TableCell>Commercial</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filterDeliveryNotes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    Aucun bon de livraison
                  </TableCell>
                </TableRow>
              ) : (
                filterDeliveryNotes.map((note) => (
                <TableRow key={note.id} hover>
                    <TableCell>
                      <Box display="flex" gap={1} alignItems="center">
                        <Avatar
                          src={getPhotoUrl(note.pharmacy_id)}
                          alt={pharmacyMap[note.pharmacy_id]?.name || 'Pharmacie'}
                          sx={{ width: 40, height: 40 }}
                        >
                          {pharmacyMap[note.pharmacy_id]?.name?.[0]}
                        </Avatar>
                        <Typography variant="body2">
                          {pharmacyMap[note.pharmacy_id]?.name || note.pharmacy_id}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>{formatDate(note.delivery_date)}</TableCell>
                    <TableCell align="right">{note.bottles_count}</TableCell>
                    <TableCell>{commercialMap[note.commercial_id] || note.commercial_id}</TableCell>
                    <TableCell>
                      <Chip label={note.status} color={getStatusColor(note.status)} size="small" />
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => openConvertDialog(note)}
                      >
                        Convertir
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      <Dialog open={convertDialogOpen} onClose={closeConvertDialog} maxWidth="xs" fullWidth>
        <DialogTitle>
          Convertir en facture
          <IconButton
            aria-label="fermer"
            onClick={closeConvertDialog}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Bouteilles à facturer"
            type="number"
            value={convertForm.bottles}
            inputProps={{ min: 1, max: convertTarget?.bottles_count || 0 }}
            onChange={(e) => setConvertForm((prev) => ({
              ...prev,
              bottles: Math.min(Math.max(Number(e.target.value), 1), convertTarget?.bottles_count || 1),
            }))}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            label="Montant (en €)"
            type="number"
            value={convertForm.amount}
            inputProps={{ min: 0 }}
            onChange={(e) => setConvertForm((prev) => ({
              ...prev,
              amount: Number(e.target.value),
            }))}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={closeConvertDialog}>Annuler</Button>
          <Button
            variant="contained"
            onClick={handleConvertSubmit}
            disabled={!convertForm.bottles || convertForm.bottles > (convertTarget?.bottles_count || 0)}
          >
            Générer la facture
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default DeliveryNotes

