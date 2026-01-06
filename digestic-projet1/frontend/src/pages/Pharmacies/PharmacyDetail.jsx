import React, { useEffect, useState } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  CircularProgress,
  Chip,
  Divider,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  FormControlLabel,
  Checkbox,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import DescriptionIcon from '@mui/icons-material/Description'
import ReceiptIcon from '@mui/icons-material/Receipt'
import AddIcon from '@mui/icons-material/Add'
import { format } from 'date-fns'
import { pharmacyService } from '../../services/pharmacyService'
import { visitService } from '../../services/visitService'
import { invoiceService } from '../../services/invoiceService'
import { visitReportService } from '../../services/visitReportService'
import VisitReportList from '../../components/VisitReportList/VisitReportList'
import VisitReportDetail from '../../components/VisitReportDetail/VisitReportDetail'
import InvoiceList from '../../components/InvoiceList/InvoiceList'
import InvoiceDetail from '../../components/InvoiceDetail/InvoiceDetail'

function PharmacyDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [pharmacy, setPharmacy] = useState(null)
  const [visits, setVisits] = useState([])
  const [visitReports, setVisitReports] = useState([])
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState(null)
  const [reportListOpen, setReportListOpen] = useState(false)
  const [reportDetailOpen, setReportDetailOpen] = useState(false)
  const [selectedReport, setSelectedReport] = useState(null)
  const [invoiceListOpen, setInvoiceListOpen] = useState(false)
  const [invoiceDetailOpen, setInvoiceDetailOpen] = useState(false)
  const [selectedInvoice, setSelectedInvoice] = useState(null)
  const [newReportOpen, setNewReportOpen] = useState(false)
  const [reportFormData, setReportFormData] = useState({
    visit_status: 'completed',
    visit_not_completed_reason: '',
    has_deposit: false,
    bottles_deposited: 0,
    free_units: 0,
    stock_status: 'unknown',
    display_stand_status: 'unknown',
    covering_status: 'unknown',
    covering_size_to_order: '',
    next_visit_date: '',
    delivery_mode: 'normal',
    notes: '',
  })

  useEffect(() => {
    fetchData()
    const storedUser = localStorage.getItem('user')
    if (storedUser) {
      setUser(JSON.parse(storedUser))
    }
  }, [id])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [pharmacyData, visitsData, invoicesData, reportsData] = await Promise.all([
        pharmacyService.getById(id),
        visitService.getAll({ pharmacy_id: id }),
        invoiceService.getAll({ pharmacy_id: id }),
        visitReportService.getAll({ pharmacy_id: id }),
      ])
      setPharmacy(pharmacyData)
      setVisits(visitsData)
      setVisitReports(reportsData)
      setInvoices(invoicesData)
    } catch (error) {
      console.error('Error fetching pharmacy details:', error)
    } finally {
      setLoading(false)
    }
  }


  const handleCreateReport = async () => {
    try {
      // Chercher une visite planifiée existante pour cette pharmacie (optionnelle)
      const plannedVisits = visits.filter(v => v.status === 'planned')
      const visitId = plannedVisits.length > 0 ? plannedVisits[0].id : null
      
      const reportData = {
        pharmacy_id: id,
        commercial_id: user.id,
        visit_date: new Date().toISOString(),
        ...reportFormData,
      }
      
      // Ajouter visit_id seulement s'il existe
      if (visitId) {
        reportData.visit_id = visitId
      }
      
      await visitReportService.create(reportData)
      
      // Si une date de prochaine visite est fournie, mettre à jour la pharmacie
      if (reportFormData.next_visit_date && reportFormData.next_visit_date.trim() !== '') {
        try {
          // Convertir la date yyyy-MM-dd en ISO format
          const dateObj = new Date(reportFormData.next_visit_date + 'T00:00:00')
          if (!isNaN(dateObj.getTime())) {
            await pharmacyService.update(id, {
              next_visit_date: dateObj.toISOString()
            })
          }
        } catch (dateError) {
          console.error('Error updating pharmacy next visit date:', dateError)
          // Ne pas bloquer si la mise à jour de la date échoue
        }
      }
      
      setNewReportOpen(false)
      setReportFormData({
        visit_status: 'completed',
        visit_not_completed_reason: '',
        has_deposit: false,
        bottles_deposited: 0,
        free_units: 0,
        stock_status: 'unknown',
        display_stand_status: 'unknown',
        covering_status: 'unknown',
        covering_size_to_order: '',
        next_visit_date: '',
        delivery_mode: 'normal',
        notes: '',
      })
      await fetchData() // Rafraîchir les données
    } catch (error) {
      console.error('Error creating report:', error)
      console.error('Error response:', error.response?.data)
      alert(`Erreur lors de la création du rapport: ${error.response?.data?.error || error.message}`)
    }
  }

  const handleReportFormChange = (e) => {
    const { name, value, type, checked } = e.target
    setReportFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  if (!pharmacy) {
    return (
      <Box>
        <Typography variant="h6">Pharmacie non trouvée</Typography>
      </Box>
    )
  }

  return (
    <Box>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => {
          // Retourner à la page précédente si elle est spécifiée dans location.state
          const fromPage = location.state?.from || '/pharmacies'
          if (fromPage === '/planning' && location.state?.tabValue !== undefined) {
            // Passer le tabValue et la date sélectionnée pour revenir au bon onglet avec la bonne date
            navigate(fromPage, { 
              state: { 
                tabValue: location.state.tabValue,
                selectedDate: location.state.selectedDate
              } 
            })
          } else {
            navigate(fromPage)
          }
        }}
        sx={{ mb: 2 }}
      >
        Retour
      </Button>

      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Typography variant="h4">
          {pharmacy.name}
        </Typography>
        <Box display="flex" gap={1}>
          {user?.role === 'commercial' && (
            <Tooltip title="Ajouter un rapport de visite">
              <IconButton
                color="primary"
                onClick={() => setNewReportOpen(true)}
              >
                <AddIcon />
              </IconButton>
            </Tooltip>
          )}
          <Tooltip title="Voir les rapports de visite">
            <IconButton
              color="primary"
              onClick={() => setReportListOpen(true)}
            >
              <DescriptionIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Voir les factures">
            <IconButton
              color="primary"
              onClick={() => setInvoiceListOpen(true)}
            >
              <ReceiptIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Informations
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Typography><strong>Adresse:</strong> {pharmacy.address}</Typography>
              <Typography><strong>Code postal:</strong> {pharmacy.postal_code}</Typography>
              <Typography><strong>Ville:</strong> {pharmacy.city}</Typography>
              <Typography><strong>Pharmacien:</strong> {pharmacy.pharmacist_name || '-'}</Typography>
              <Typography><strong>Email:</strong> {pharmacy.pharmacist_email || '-'}</Typography>
              <Typography><strong>Téléphone:</strong> {pharmacy.pharmacist_phone || '-'}</Typography>
              <Typography><strong>RIB:</strong> {pharmacy.rib || '-'}</Typography>
              <Typography><strong>Prochaine visite:</strong> {pharmacy.next_visit_date ? format(new Date(pharmacy.next_visit_date), 'dd/MM/yyyy') : '-'}</Typography>
              <Box sx={{ mt: 2 }}>
                <Chip
                  label={`Classification: ${pharmacy.classification}`}
                  color={pharmacy.classification === 'A' ? 'error' : pharmacy.classification === 'B' ? 'warning' : 'info'}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Statistiques
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Typography><strong>Rapports de visite:</strong> {visitReports.length}</Typography>
              <Typography><strong>Factures totales:</strong> {invoices.length}</Typography>
              <Typography>
                <strong>Factures payées:</strong>{' '}
                {invoices.filter((inv) => inv.status === 'paid').length}
              </Typography>
              <Typography>
                <strong>Factures en attente:</strong>{' '}
                {invoices.filter((inv) => inv.status === 'pending').length}
              </Typography>
              <Typography>
                <strong>Factures en retard:</strong>{' '}
                {invoices.filter((inv) => inv.status === 'overdue').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Modal liste des rapports */}
      <VisitReportList
        open={reportListOpen}
        onClose={() => setReportListOpen(false)}
        pharmacyId={id}
        pharmacyName={pharmacy?.name}
        onSelectReport={(report) => {
          setSelectedReport(report)
          setReportListOpen(false)
          setReportDetailOpen(true)
        }}
      />

      {/* Modal détail du rapport */}
      <VisitReportDetail
        open={reportDetailOpen}
        onClose={() => {
          setReportDetailOpen(false)
          setSelectedReport(null)
        }}
        report={selectedReport}
        onUpdate={async (reportId, updateData) => {
          try {
            await visitReportService.update(reportId, updateData)
            await fetchData() // Rafraîchir les données
          } catch (error) {
            console.error('Error updating report:', error)
            throw error
          }
        }}
      />

      {/* Modal liste des factures */}
      <InvoiceList
        open={invoiceListOpen}
        onClose={() => setInvoiceListOpen(false)}
        pharmacyId={id}
        pharmacyEmail={pharmacy?.pharmacist_email}
        onSelectInvoice={(invoice) => {
          setSelectedInvoice(invoice)
          setInvoiceListOpen(false)
          setInvoiceDetailOpen(true)
        }}
      />

      {/* Modal détail de la facture */}
      <InvoiceDetail
        open={invoiceDetailOpen}
        onClose={() => {
          setInvoiceDetailOpen(false)
          setSelectedInvoice(null)
        }}
        invoice={selectedInvoice}
        pharmacyEmail={pharmacy?.pharmacist_email}
      />

      {/* Modal pour créer un rapport de visite */}
      <Dialog open={newReportOpen} onClose={() => setNewReportOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Nouveau rapport de visite</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Statut de la visite"
                name="visit_status"
                value={reportFormData.visit_status}
                onChange={handleReportFormChange}
              >
                <MenuItem value="completed">Effectuée</MenuItem>
                <MenuItem value="not_completed">Non effectuée</MenuItem>
              </TextField>
            </Grid>
            {reportFormData.visit_status === 'not_completed' && (
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  select
                  label="Raison"
                  name="visit_not_completed_reason"
                  value={reportFormData.visit_not_completed_reason}
                  onChange={handleReportFormChange}
                >
                  <MenuItem value="pharmacy_closed">Pharmacie fermée</MenuItem>
                  <MenuItem value="owner_absent">Titulaire absent</MenuItem>
                </TextField>
              </Grid>
            )}
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={reportFormData.has_deposit}
                    onChange={handleReportFormChange}
                    name="has_deposit"
                  />
                }
                label="Dépôt effectué"
              />
            </Grid>

            {reportFormData.has_deposit && (
              <>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Nombre de bouteilles déposées"
                    type="number"
                    name="bottles_deposited"
                    value={reportFormData.bottles_deposited}
                    onChange={handleReportFormChange}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Nombre de UG"
                    type="number"
                    name="free_units"
                    value={reportFormData.free_units}
                    onChange={handleReportFormChange}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    select
                    label="Mode de livraison"
                    name="delivery_mode"
                    value={reportFormData.delivery_mode}
                    onChange={handleReportFormChange}
                  >
                    <MenuItem value="normal">Normal</MenuItem>
                    <MenuItem value="deposit_sale">Dépôt-vente</MenuItem>
                  </TextField>
                </Grid>
              </>
            )}

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="État des stocks"
                name="stock_status"
                value={reportFormData.stock_status}
                onChange={handleReportFormChange}
              >
                <MenuItem value="good">Bon</MenuItem>
                <MenuItem value="low">Faible</MenuItem>
                <MenuItem value="out_of_stock">Rupture</MenuItem>
                <MenuItem value="unknown">Inconnu</MenuItem>
              </TextField>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="État du présentoir"
                name="display_stand_status"
                value={reportFormData.display_stand_status}
                onChange={handleReportFormChange}
              >
                <MenuItem value="in_place">En place</MenuItem>
                <MenuItem value="not_in_place">Pas en place</MenuItem>
                <MenuItem value="unknown">Inconnu</MenuItem>
              </TextField>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="État de la couverture"
                name="covering_status"
                value={reportFormData.covering_status}
                onChange={handleReportFormChange}
              >
                <MenuItem value="in_place">En place</MenuItem>
                <MenuItem value="to_order">À commander</MenuItem>
                <MenuItem value="unknown">Inconnu</MenuItem>
              </TextField>
            </Grid>

            {reportFormData.covering_status === 'to_order' && (
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Taille de couverture à commander"
                  name="covering_size_to_order"
                  value={reportFormData.covering_size_to_order}
                  onChange={handleReportFormChange}
                />
              </Grid>
            )}

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="date"
                label="Date de la prochaine visite"
                name="next_visit_date"
                value={reportFormData.next_visit_date}
                onChange={handleReportFormChange}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Notes"
                name="notes"
                value={reportFormData.notes}
                onChange={handleReportFormChange}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNewReportOpen(false)}>Annuler</Button>
          <Button onClick={handleCreateReport} variant="contained">
            Enregistrer
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default PharmacyDetail

