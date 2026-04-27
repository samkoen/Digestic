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
import { productService } from '../../services/productService'
import CloseIcon from '@mui/icons-material/Close'

/** Aligné sur `delivery_note_service.issue_invoice_from_delivery_note` (lignes HT/TVA, arrondis). */
function indicativeInvoiceTotals(bottles, product) {
  const n = Math.max(0, Number(bottles) || 0)
  if (!product || n <= 0) {
    return { ht: 0, vat: 0, ttc: 0, vatRatePercent: 0 }
  }
  const unitHt = Number(product.wholesale_unit_price) || 0
  const vatRate = Number(product.vat_rate) || 0
  const lht = Math.round(n * unitHt * 10000) / 10000
  const lvat = Math.round(lht * (vatRate / 100) * 10000) / 10000
  const totalHt = Math.round(lht * 100) / 100
  const totalVat = Math.round(lvat * 100) / 100
  const ttc = Math.round((totalHt + totalVat) * 100) / 100
  return { ht: totalHt, vat: totalVat, ttc, vatRatePercent: vatRate }
}

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
  const [invoiceDialogOpen, setInvoiceDialogOpen] = useState(false)
  const [invoiceTarget, setInvoiceTarget] = useState(null)
  const [invoiceForm, setInvoiceForm] = useState({
    bottles: 0,
  })
  const [billingProduct, setBillingProduct] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const list = await productService.list({ active_only: true })
        if (cancelled) return
        const def =
          list.find((p) => p.is_default_for_billing) || list[0] || null
        setBillingProduct(def)
      } catch (e) {
        console.error('Produit facturation (montant indicatif BL):', e)
        if (!cancelled) setBillingProduct(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const invoiceIndicative = useMemo(
    () => indicativeInvoiceTotals(invoiceForm.bottles, billingProduct),
    [invoiceForm.bottles, billingProduct],
  )

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

  const openInvoiceDialog = (note) => {
    setInvoiceTarget(note)
    setInvoiceForm({
      bottles: note.bottles_count,
    })
    setInvoiceDialogOpen(true)
  }

  const closeInvoiceDialog = () => {
    setInvoiceDialogOpen(false)
    setInvoiceTarget(null)
  }

  const handleIssueInvoiceSubmit = async () => {
    if (!invoiceTarget) return
    try {
      await deliveryNoteService.issueInvoice(invoiceTarget.id, {
        bottles_to_invoice: invoiceForm.bottles,
        amount: invoiceIndicative.ttc,
      })
      closeInvoiceDialog()
      fetchDeliveryNotes()
    } catch (error) {
      console.error('Erreur lors de la facturation:', error)
      const data = error.response?.data
      const msg = [data?.error, data?.detail].filter(Boolean).join('\n') || error.message
      alert(msg || 'Erreur lors de la facturation (émission facture)')
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
                        onClick={() => openInvoiceDialog(note)}
                      >
                        Facturer
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      <Dialog open={invoiceDialogOpen} onClose={closeInvoiceDialog} maxWidth="xs" fullWidth>
        <DialogTitle>
          Émettre la facture
          <IconButton
            aria-label="fermer"
            onClick={closeInvoiceDialog}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Création de la facture à partir de ce bon de livraison (VosFactures si configuré). Les
            montants sont calculés côté serveur à partir du{' '}
            <strong>produit par défaut de facturation</strong>
            {billingProduct?.name ? (
              <>
                {' '}
                (« {billingProduct.name} », {Number(billingProduct.wholesale_unit_price).toFixed(2)}{' '}
                € HT / unité, TVA {Number(billingProduct.vat_rate).toFixed(1)} %)
              </>
            ) : null}
            . Estimation ci-dessous (même logique que la facture émise).
          </Typography>
          <TextField
            fullWidth
            label="Bouteilles à facturer"
            type="number"
            value={invoiceForm.bottles}
            inputProps={{ min: 1, max: invoiceTarget?.bottles_count || 0 }}
            onChange={(e) =>
              setInvoiceForm((prev) => ({
                ...prev,
                bottles: Math.min(
                  Math.max(Number(e.target.value), 1),
                  invoiceTarget?.bottles_count || 1,
                ),
              }))
            }
            sx={{ mb: 2 }}
          />
          {!billingProduct ? (
            <Typography variant="body2" color="warning.main">
              Aucun produit actif en base : impossible d’estimer le montant ici. La facturation
              échouera aussi sans produit de facturation (prix / TVA).
            </Typography>
          ) : (
            <Box
              sx={{
                p: 1.5,
                borderRadius: 1,
                bgcolor: 'action.hover',
                border: 1,
                borderColor: 'divider',
              }}
            >
              <Typography variant="subtitle2" gutterBottom>
                Montants indicatifs (ligne payante)
              </Typography>
              <Typography variant="body2">
                Total HT : <strong>{invoiceIndicative.ht.toFixed(2)} €</strong>
              </Typography>
              <Typography variant="body2">
                TVA ({invoiceIndicative.vatRatePercent.toFixed(1)} %) :{' '}
                <strong>{invoiceIndicative.vat.toFixed(2)} €</strong>
              </Typography>
              <Typography variant="body2">
                Total TTC : <strong>{invoiceIndicative.ttc.toFixed(2)} €</strong>
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeInvoiceDialog}>Annuler</Button>
          <Button
            variant="contained"
            onClick={handleIssueInvoiceSubmit}
            disabled={!invoiceForm.bottles || invoiceForm.bottles > (invoiceTarget?.bottles_count || 0)}
          >
            Facturer
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default DeliveryNotes

