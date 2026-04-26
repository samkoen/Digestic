import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  CircularProgress,
  Divider,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Avatar,
  TextField,
  List,
  ListItem,
  ListItemText,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import DescriptionIcon from '@mui/icons-material/Description'
import ReceiptIcon from '@mui/icons-material/Receipt'
import AddIcon from '@mui/icons-material/Add'
import CloseIcon from '@mui/icons-material/Close'
import EditIcon from '@mui/icons-material/Edit'
import { format, parseISO } from 'date-fns'
import { fr } from 'date-fns/locale'
import { getPharmacyStatusLabel } from '../../constants/pharmacyStatus'
import { pharmacyService } from '../../services/pharmacyService'
import { visitService } from '../../services/visitService'
import { invoiceService } from '../../services/invoiceService'
import { visitReportService } from '../../services/visitReportService'
import VisitReportList from '../../components/VisitReportList/VisitReportList'
import VisitReportDetail from '../../components/VisitReportDetail/VisitReportDetail'
import InvoiceList from '../../components/InvoiceList/InvoiceList'
import InvoiceDetail from '../../components/InvoiceDetail/InvoiceDetail'
import { PAYMENT_MODES, DEFAULT_PAYMENT_MODE } from '../../constants/paymentModes'
import { WEEKS_UNTIL_RETURN_OPTIONS } from '../../constants/visitReportForm'
import ResizableTextField from '../../components/ResizableTextField/ResizableTextField'
import PharmacyForm from '../../components/PharmacyForm/PharmacyForm'

/** Raccourcis : insertion dans le texte (curseur ou fin). */
const COMMENT_EMOJI_SHORTCUTS = [
  { emoji: '⚠️', label: 'Attention / warning' },
  { emoji: '✅', label: 'Validé' },
  { emoji: '❌', label: 'Refus / non' },
  { emoji: '❗', label: 'Important' },
  { emoji: '🔴', label: 'Urgent' },
  { emoji: '📌', label: 'À retenir' },
  { emoji: '💡', label: 'Idée' },
  { emoji: '📞', label: 'Téléphone' },
  { emoji: '📅', label: 'Rendez-vous' },
  { emoji: '⏰', label: 'Délai' },
  { emoji: '🔔', label: 'Rappel' },
  { emoji: '💬', label: 'Message' },
]

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
  const [photoDialogOpen, setPhotoDialogOpen] = useState(false)
  const [pharmacyFormOpen, setPharmacyFormOpen] = useState(false)
  const [comments, setComments] = useState([])
  const [newCommentText, setNewCommentText] = useState('')
  const [commentSubmitting, setCommentSubmitting] = useState(false)
  const commentInputRef = useRef(null)
  const getDefaultReportPaymentMode = () => pharmacy?.payment_mode || DEFAULT_PAYMENT_MODE
  const getDefaultReportFormData = () => ({
    visit_status: 'completed',
    visit_not_completed_reason: '',
    has_deposit: false,
    bottles_deposited: 0,
    free_units: 0,
    stock_status: 'unknown',
    display_stand_status: 'unknown',
    covering_status: 'unknown',
    covering_size_to_order: '',
    weeks_until_return: '',
    voice_note_url: '',
    photo_note_url: '',
    video_note_url: '',
    notes: '',
    payment_mode: getDefaultReportPaymentMode(),
  })
  const [reportFormData, setReportFormData] = useState(getDefaultReportFormData)

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
      const [pharmacyData, visitsData, invoicesData, reportsData, commentsData] = await Promise.all([
        pharmacyService.getById(id),
        visitService.getAll({ pharmacy_id: id }),
        invoiceService.getAll({ pharmacy_id: id }),
        visitReportService.getAll({ pharmacy_id: id }),
        pharmacyService.getComments(id).catch((e) => {
          console.error('Error loading comments:', e)
          return []
        }),
      ])
      setPharmacy(pharmacyData)
      setVisits(visitsData)
      setVisitReports(reportsData)
      setInvoices(invoicesData)
      setComments(Array.isArray(commentsData) ? commentsData : [])
    } catch (error) {
      console.error('Error fetching pharmacy details:', error)
    } finally {
      setLoading(false)
    }
  }


  const resetReportForm = () => setReportFormData(getDefaultReportFormData())

  const handleOpenNewReport = () => {
    resetReportForm()
    setNewReportOpen(true)
  }


  const handleReportMediaUpload = async (field) => {
    const input = document.createElement('input')
    input.type = 'file'
    if (field === 'voice_note_url') {
      input.accept = 'audio/*'
    } else if (field === 'photo_note_url') {
      input.accept = 'image/*'
    } else {
      input.accept = 'video/*'
    }
    input.onchange = async (ev) => {
      const file = ev.target?.files?.[0]
      if (!file) return
      try {
        const url = await visitReportService.uploadMedia(file)
        setReportFormData((prev) => ({ ...prev, [field]: url }))
      } catch (err) {
        console.error(err)
        alert("Échec de l'envoi du fichier")
      }
    }
    input.click()
  }

  const handleCreateReport = async () => {
    try {
      // Chercher une visite planifiée existante pour cette pharmacie (optionnelle)
      const plannedVisits = visits.filter(v => v.status === 'planned')
      const visitId = plannedVisits.length > 0 ? plannedVisits[0].id : null

      const { weeks_until_return, ...rest } = reportFormData
      const reportData = {
        pharmacy_id: id,
        commercial_id: user.id,
        visit_date: new Date().toISOString(),
        ...rest,
      }
      if (weeks_until_return) {
        reportData.weeks_until_return = parseInt(weeks_until_return, 10)
      }
      if (!reportFormData.has_deposit) {
        delete reportData.payment_mode
      }
      if (reportFormData.has_deposit && !reportData.payment_mode) {
        reportData.payment_mode = getDefaultReportPaymentMode()
      }

      // Ajouter visit_id seulement s'il existe
      if (visitId) {
        reportData.visit_id = visitId
      }

      await visitReportService.create(reportData)

      setNewReportOpen(false)
      resetReportForm()
      await fetchData() // Rafraîchir les données
    } catch (error) {
      console.error('Error creating report:', error)
      console.error('Error response:', error.response?.data)
      alert(`Erreur lors de la création du rapport: ${error.response?.data?.error || error.message}`)
    }
  }

  const handleReportFormChange = (e) => {
    const { name, value, type, checked } = e.target
    setReportFormData((prev) => {
      const next = {
        ...prev,
        [name]: type === 'checkbox' ? checked : value,
      }
      if (name === 'has_deposit' && type === 'checkbox' && checked && !next.payment_mode) {
        next.payment_mode = getDefaultReportPaymentMode()
      }
      return next
    })
  }

  const handlePhotoOpen = () => {
    setPhotoDialogOpen(true)
  }

  const handlePhotoClose = () => {
    setPhotoDialogOpen(false)
  }

  const handlePharmacyFormClose = () => {
    setPharmacyFormOpen(false)
    void fetchData()
  }

  const handleAddComment = async () => {
    const t = newCommentText.trim()
    if (!t) return
    try {
      setCommentSubmitting(true)
      const created = await pharmacyService.addComment(id, t)
      setComments((prev) => [created, ...prev])
      setNewCommentText('')
    } catch (error) {
      console.error('Error adding comment:', error)
      alert(error?.response?.data?.error || "Impossible d'ajouter le commentaire")
    } finally {
      setCommentSubmitting(false)
    }
  }

  const handleDeleteComment = async (commentId) => {
    if (!window.confirm('Supprimer ce commentaire ?')) return
    try {
      await pharmacyService.deleteComment(id, commentId)
      setComments((prev) => prev.filter((c) => c.id !== commentId))
    } catch (error) {
      console.error('Error deleting comment:', error)
      alert(error?.response?.data?.error || 'Impossible de supprimer le commentaire')
    }
  }

  const formatCommentDate = (iso) => {
    if (!iso) return '—'
    try {
      return format(parseISO(iso), "d MMM yyyy 'à' HH:mm", { locale: fr })
    } catch {
      return iso
    }
  }

  const insertCommentEmoji = useCallback((emoji) => {
    const el = commentInputRef.current
    const prev = newCommentText
    if (el && typeof el.selectionStart === 'number') {
      const start = el.selectionStart
      const end = el.selectionEnd ?? start
      const next = prev.slice(0, start) + emoji + prev.slice(end)
      setNewCommentText(next)
      const pos = start + [...emoji].length
      requestAnimationFrame(() => {
        try {
          el.focus()
          el.setSelectionRange(pos, pos)
        } catch {
          /* ignore */
        }
      })
      return
    }
    setNewCommentText((p) => {
      if (!p) return emoji
      return p + (p.endsWith(' ') || p.endsWith('\n') ? '' : ' ') + emoji
    })
  }, [newCommentText])

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

  const photoSeed = encodeURIComponent(pharmacy.id ?? pharmacy.name ?? 'pharmacy-photo')
  const photoPreviewUrl =
    pharmacy.photo_url || `https://picsum.photos/seed/${photoSeed}/400/400`
  const photoEnlargedUrl =
    pharmacy.photo_url || `https://picsum.photos/seed/${photoSeed}/1200/900`

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
        <Box display="flex" alignItems="center" gap={2}>
          <Tooltip title="Voir la photo">
            <Avatar
              alt={`Photo de ${pharmacy.name}`}
              src={photoPreviewUrl}
              sx={{
                width: 72,
                height: 72,
                cursor: 'pointer',
                border: '2px solid',
                borderColor: 'primary.main',
              }}
              onClick={handlePhotoOpen}
            />
          </Tooltip>
          <Typography variant="h4">{pharmacy.name}</Typography>
        </Box>
        <Box display="flex" gap={1}>
          {user?.role === 'admin' && (
            <Tooltip title="Modifier la pharmacie">
              <IconButton
                color="primary"
                onClick={() => setPharmacyFormOpen(true)}
              >
                <EditIcon />
              </IconButton>
            </Tooltip>
          )}
          {user?.role === 'commercial' && (
          <Tooltip title="Ajouter un rapport de visite">
            <IconButton
              color="primary"
              onClick={handleOpenNewReport}
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

      <Grid container spacing={3} sx={{ mt: 2 }} alignItems="flex-start">
        <Grid item xs={12} md={6}>
          <Card sx={{ mb: 2 }}>
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
              <Typography><strong>Mode de paiement dépôt:</strong> {pharmacy.payment_mode || '-'}</Typography>
              <Typography>
                <strong>Dépôt:</strong> {pharmacy.depot_name || '—'}
              </Typography>
              <Typography>
                <strong>Statut:</strong> {getPharmacyStatusLabel(pharmacy.status)}
              </Typography>
              <Typography><strong>Prochaine visite:</strong> {pharmacy.next_visit_date ? format(new Date(pharmacy.next_visit_date), 'dd/MM/yyyy') : '-'}</Typography>
            </CardContent>
          </Card>
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

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h6" gutterBottom>
                Commentaires
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
                Emojis
              </Typography>
              <Box
                sx={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: 0.5,
                  mb: 1,
                }}
              >
                {COMMENT_EMOJI_SHORTCUTS.map(({ emoji, label }) => (
                  <Tooltip key={emoji + label} title={label}>
                    <Button
                      type="button"
                      size="small"
                      variant="outlined"
                      onClick={() => insertCommentEmoji(emoji)}
                      disabled={commentSubmitting}
                      sx={{
                        minWidth: 40,
                        px: 0.5,
                        fontSize: '1.15rem',
                        lineHeight: 1.2,
                      }}
                    >
                      {emoji}
                    </Button>
                  </Tooltip>
                ))}
              </Box>
              <TextField
                fullWidth
                multiline
                minRows={2}
                maxRows={4}
                size="small"
                placeholder="Nouveau commentaire…"
                value={newCommentText}
                onChange={(e) => setNewCommentText(e.target.value)}
                disabled={commentSubmitting}
                inputRef={commentInputRef}
                sx={{ mb: 1.5 }}
              />
              <Button
                variant="contained"
                size="small"
                disabled={commentSubmitting || !newCommentText.trim()}
                onClick={handleAddComment}
                sx={{ alignSelf: 'flex-start', mb: 2 }}
              >
                {commentSubmitting ? 'Envoi…' : 'Ajouter une note'}
              </Button>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
                Historique
              </Typography>
              <List
                dense
                sx={{
                  flex: 1,
                  minHeight: 0,
                  maxHeight: 280,
                  overflow: 'auto',
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  py: 0,
                }}
              >
                {comments.length === 0 ? (
                  <ListItem>
                    <ListItemText
                      primary="Aucun commentaire"
                      primaryTypographyProps={{ color: 'text.secondary', variant: 'body2' }}
                    />
                  </ListItem>
                ) : (
                  comments.map((c) => (
                    <ListItem
                      key={c.id}
                      alignItems="flex-start"
                      secondaryAction={
                        <Tooltip title="Supprimer">
                          <IconButton
                            edge="end"
                            size="small"
                            aria-label="Supprimer"
                            onClick={() => handleDeleteComment(c.id)}
                          >
                            <DeleteOutlineIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      }
                      sx={{ pr: 6, borderBottom: '1px solid', borderColor: 'divider' }}
                    >
                      <ListItemText
                        primary={formatCommentDate(c.created_at)}
                        secondary={c.text}
                        primaryTypographyProps={{ variant: 'caption', color: 'text.secondary' }}
                        secondaryTypographyProps={{ variant: 'body2', color: 'text.primary', whiteSpace: 'pre-wrap' }}
                      />
                    </ListItem>
                  ))
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <PharmacyForm
        open={pharmacyFormOpen}
        onClose={handlePharmacyFormClose}
        pharmacy={pharmacy}
      />

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

      <Dialog open={photoDialogOpen} onClose={handlePhotoClose} maxWidth="lg" fullWidth>
        <DialogTitle sx={{ m: 0, p: 2 }}>
          Photo de {pharmacy.name}
          <IconButton
            aria-label="Fermer la photo"
            onClick={handlePhotoClose}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ p: 0, backgroundColor: 'common.black', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <Box
            component="img"
            src={photoEnlargedUrl}
            alt={`Photo de ${pharmacy.name}`}
            sx={{
              width: '100%',
              maxHeight: '80vh',
              objectFit: 'contain',
              display: 'block',
            }}
          />
        </DialogContent>
      </Dialog>

      {/* Modal pour créer un rapport de visite */}
      <Dialog open={newReportOpen} onClose={() => { setNewReportOpen(false); resetReportForm() }} maxWidth="md" fullWidth>
        <DialogTitle>Nouveau rapport de visite</DialogTitle>
        <DialogContent
          sx={{
            pt: 2.25,
            '& .MuiTextField-root .MuiInputLabel-root': {
              lineHeight: 1.25,
              paddingTop: '1px',
            },
          }}
        >
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12} sm={6}>
              <ResizableTextField
                fullWidth
                select
                label="Statut de la visite"
                name="visit_status"
                value={reportFormData.visit_status}
                onChange={handleReportFormChange}
              >
                <MenuItem value="completed">Effectuée</MenuItem>
                <MenuItem value="not_completed">Non effectuée</MenuItem>
              </ResizableTextField>
            </Grid>
            {reportFormData.visit_status === 'not_completed' && (
              <Grid item xs={12} sm={6}>
                <ResizableTextField
                  fullWidth
                  select
                  label="Raison"
                  name="visit_not_completed_reason"
                  value={reportFormData.visit_not_completed_reason}
                  onChange={handleReportFormChange}
                >
                  <MenuItem value="pharmacy_closed">Pharmacie fermée</MenuItem>
                  <MenuItem value="owner_absent">Titulaire absent</MenuItem>
                  <MenuItem value="refus">Refus</MenuItem>
                </ResizableTextField>
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
                  <ResizableTextField
                    fullWidth
                    label="Nombre de bouteilles déposées"
                    type="number"
                    name="bottles_deposited"
                    value={reportFormData.bottles_deposited}
                    onChange={handleReportFormChange}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <ResizableTextField
                    fullWidth
                    label="Nombre de UG"
                    type="number"
                    name="free_units"
                    value={reportFormData.free_units}
                    onChange={handleReportFormChange}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <ResizableTextField
                    fullWidth
                    select
                    label="Mode de paiement dépôt"
                    name="payment_mode"
                    value={reportFormData.payment_mode}
                    onChange={handleReportFormChange}
                  >
                    {PAYMENT_MODES.map((mode) => (
                      <MenuItem key={mode} value={mode}>
                        {mode}
                      </MenuItem>
                    ))}
                  </ResizableTextField>
                </Grid>
              </>
            )}

            <Grid item xs={12} sm={6}>
              <ResizableTextField
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
              </ResizableTextField>
            </Grid>

            <Grid item xs={12} sm={6}>
              <ResizableTextField
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
              </ResizableTextField>
            </Grid>

            <Grid item xs={12} sm={6}>
              <ResizableTextField
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
              </ResizableTextField>
            </Grid>

            {reportFormData.covering_status === 'to_order' && (
              <Grid item xs={12} sm={6}>
                <ResizableTextField
                  fullWidth
                  label="Taille de couverture à commander"
                  name="covering_size_to_order"
                  value={reportFormData.covering_size_to_order}
                  onChange={handleReportFormChange}
                />
              </Grid>
            )}

            <Grid item xs={12} sm={6}>
              <ResizableTextField
                fullWidth
                select
                label="Semaine de retour prévu"
                name="weeks_until_return"
                value={reportFormData.weeks_until_return}
                onChange={handleReportFormChange}
                InputLabelProps={{ shrink: true }}
              >
                <MenuItem value="">—</MenuItem>
                {WEEKS_UNTIL_RETURN_OPTIONS.map((o) => (
                  <MenuItem key={o.value} value={o.value}>
                    {o.label}
                  </MenuItem>
                ))}
              </ResizableTextField>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Pièces jointes
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
                <Button type="button" size="small" variant="outlined" onClick={() => handleReportMediaUpload('voice_note_url')}>
                  Note vocale
                </Button>
                <Button type="button" size="small" variant="outlined" onClick={() => handleReportMediaUpload('photo_note_url')}>
                  Photo
                </Button>
                <Button type="button" size="small" variant="outlined" onClick={() => handleReportMediaUpload('video_note_url')}>
                  Vidéo
                </Button>
              </Box>
              {reportFormData.voice_note_url && (
                <Box sx={{ mb: 1 }}>
                  <audio controls src={reportFormData.voice_note_url} style={{ maxWidth: '100%' }} />
                  <Button size="small" onClick={() => setReportFormData((p) => ({ ...p, voice_note_url: '' }))}>
                    Retirer
                  </Button>
                </Box>
              )}
              {reportFormData.photo_note_url && (
                <Box sx={{ mb: 1 }}>
                  <Box component="img" src={reportFormData.photo_note_url} alt="Note photo" sx={{ maxHeight: 120, display: 'block' }} />
                  <Button size="small" onClick={() => setReportFormData((p) => ({ ...p, photo_note_url: '' }))}>
                    Retirer
                  </Button>
                </Box>
              )}
              {reportFormData.video_note_url && (
                <Box sx={{ mb: 1 }}>
                  <video
                    src={reportFormData.video_note_url}
                    controls
                    style={{ maxWidth: '100%', maxHeight: 200 }}
                  />
                  <Button size="small" onClick={() => setReportFormData((p) => ({ ...p, video_note_url: '' }))}>
                    Retirer
                  </Button>
                </Box>
              )}
            </Grid>

            <Grid item xs={12}>
              <ResizableTextField
                fullWidth
                multiline
                rows={2}
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

