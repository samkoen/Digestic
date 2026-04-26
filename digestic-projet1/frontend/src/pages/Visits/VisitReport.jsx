import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  FormControlLabel,
  Checkbox,
  MenuItem,
  Grid,
  CircularProgress,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import SaveIcon from '@mui/icons-material/Save'
import { visitReportService } from '../../services/visitReportService'
import { visitService } from '../../services/visitService'
import { pharmacyService } from '../../services/pharmacyService'
import { PAYMENT_MODES, DEFAULT_PAYMENT_MODE } from '../../constants/paymentModes'
import { WEEKS_UNTIL_RETURN_OPTIONS } from '../../constants/visitReportForm'

function VisitReport() {
  const { visitId } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [visit, setVisit] = useState(null)
  const [formData, setFormData] = useState({
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
    payment_mode: DEFAULT_PAYMENT_MODE,
  })
  const [defaultPaymentMode, setDefaultPaymentMode] = useState(DEFAULT_PAYMENT_MODE)

  useEffect(() => {
    fetchVisit()
  }, [visitId])

  const fetchVisit = async () => {
    try {
      setLoading(true)
      const visitData = await visitService.getById(visitId)
      setVisit(visitData)
      try {
        const pharmacyData = await pharmacyService.getById(visitData.pharmacy_id)
        const mode = pharmacyData?.payment_mode || DEFAULT_PAYMENT_MODE
        setDefaultPaymentMode(mode)
        setFormData((prev) => ({
          ...prev,
          payment_mode: mode,
        }))
      } catch (pharmacyError) {
        console.error('Erreur lors de la récupération de la pharmacie:', pharmacyError)
      }
    } catch (error) {
      console.error('Error fetching visit:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => {
      const next = {
        ...prev,
        [name]: type === 'checkbox' ? checked : value,
      }
      if (name === 'has_deposit' && type === 'checkbox' && checked && !prev.payment_mode) {
        next.payment_mode = defaultPaymentMode
      }
      return next
    })
  }

  const handleMediaUpload = async (field) => {
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
        setFormData((prev) => ({ ...prev, [field]: url }))
      } catch (err) {
        console.error(err)
        alert("Échec de l'envoi du fichier")
      }
    }
    input.click()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const { weeks_until_return, ...rest } = formData
      const reportData = {
        visit_id: visitId,
        pharmacy_id: visit.pharmacy_id,
        commercial_id: visit.commercial_id,
        visit_date: new Date().toISOString(),
        ...rest,
      }
      if (weeks_until_return) {
        reportData.weeks_until_return = parseInt(weeks_until_return, 10)
      }
      await visitReportService.create(reportData)
      navigate('/visits')
    } catch (error) {
      console.error('Error creating report:', error)
      alert('Erreur lors de la création du rapport')
    }
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate('/visits')}
        sx={{ mb: 2 }}
      >
        Retour
      </Button>

      <Typography variant="h4" gutterBottom>
        Rapport de Visite
      </Typography>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <form onSubmit={handleSubmit}>
            <Grid
              container
              spacing={3}
              sx={{
                '& .MuiTextField-root .MuiInputLabel-root': {
                  lineHeight: 1.25,
                  paddingTop: '1px',
                },
              }}
            >
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  select
                  label="Statut de la visite"
                  name="visit_status"
                  value={formData.visit_status}
                  onChange={handleChange}
                  InputLabelProps={{ shrink: true }}
                >
                  <MenuItem value="completed">Effectuée</MenuItem>
                  <MenuItem value="not_completed">Non effectuée</MenuItem>
                </TextField>
              </Grid>
              {formData.visit_status === 'not_completed' && (
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    select
                    label="Raison"
                    name="visit_not_completed_reason"
                    value={formData.visit_not_completed_reason}
                    onChange={handleChange}
                    InputLabelProps={{ shrink: true }}
                  >
                    <MenuItem value="pharmacy_closed">Pharmacie fermée</MenuItem>
                    <MenuItem value="owner_absent">Titulaire absent</MenuItem>
                    <MenuItem value="refus">Refus</MenuItem>
                  </TextField>
                </Grid>
              )}
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={formData.has_deposit}
                      onChange={handleChange}
                      name="has_deposit"
                    />
                  }
                  label="Dépôt effectué"
                />
              </Grid>

              {formData.has_deposit && (
                <>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      fullWidth
                      label="Nombre de bouteilles déposées"
                      type="number"
                      name="bottles_deposited"
                      value={formData.bottles_deposited}
                      onChange={handleChange}
                      InputLabelProps={{ shrink: true }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      fullWidth
                      label="Nombre de UG"
                      type="number"
                      name="free_units"
                      value={formData.free_units}
                      onChange={handleChange}
                      InputLabelProps={{ shrink: true }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      select
                      label="Mode de paiement dépôt"
                      name="payment_mode"
                      value={formData.payment_mode}
                      onChange={handleChange}
                      InputLabelProps={{ shrink: true }}
                    >
                      {PAYMENT_MODES.map((mode) => (
                        <MenuItem key={mode} value={mode}>
                          {mode}
                        </MenuItem>
                      ))}
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
                  value={formData.stock_status}
                  onChange={handleChange}
                  InputLabelProps={{ shrink: true }}
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
                  value={formData.display_stand_status}
                  onChange={handleChange}
                  InputLabelProps={{ shrink: true }}
                >
                  <MenuItem value="in_place">En place</MenuItem>
                  <MenuItem value="not_in_place">Non en place</MenuItem>
                  <MenuItem value="unknown">Inconnu</MenuItem>
                </TextField>
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  select
                  label="État du covering"
                  name="covering_status"
                  value={formData.covering_status}
                  onChange={handleChange}
                  InputLabelProps={{ shrink: true }}
                >
                  <MenuItem value="in_place">En place</MenuItem>
                  <MenuItem value="to_order">À commander</MenuItem>
                  <MenuItem value="unknown">Inconnu</MenuItem>
                </TextField>
              </Grid>

              {formData.covering_status === 'to_order' && (
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Taille du covering à commander"
                    name="covering_size_to_order"
                    value={formData.covering_size_to_order}
                    onChange={handleChange}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
              )}

              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  select
                  label="Semaine de retour prévu"
                  name="weeks_until_return"
                  value={formData.weeks_until_return}
                  onChange={handleChange}
                  InputLabelProps={{ shrink: true }}
                >
                  <MenuItem value="">—</MenuItem>
                  {WEEKS_UNTIL_RETURN_OPTIONS.map((o) => (
                    <MenuItem key={o.value} value={o.value}>
                      {o.label}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Pièces jointes
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
                  <Button type="button" size="small" variant="outlined" onClick={() => handleMediaUpload('voice_note_url')}>
                    Note vocale
                  </Button>
                  <Button type="button" size="small" variant="outlined" onClick={() => handleMediaUpload('photo_note_url')}>
                    Photo
                  </Button>
                  <Button type="button" size="small" variant="outlined" onClick={() => handleMediaUpload('video_note_url')}>
                    Vidéo
                  </Button>
                </Box>
                {formData.voice_note_url && (
                  <Box sx={{ mb: 1 }}>
                    <audio controls src={formData.voice_note_url} style={{ maxWidth: '100%' }} />
                    <Button size="small" onClick={() => setFormData((p) => ({ ...p, voice_note_url: '' }))}>
                      Retirer
                    </Button>
                  </Box>
                )}
                {formData.photo_note_url && (
                  <Box sx={{ mb: 1 }}>
                    <Box component="img" src={formData.photo_note_url} alt="Note photo" sx={{ maxHeight: 120, display: 'block' }} />
                    <Button size="small" onClick={() => setFormData((p) => ({ ...p, photo_note_url: '' }))}>
                      Retirer
                    </Button>
                  </Box>
                )}
                {formData.video_note_url && (
                  <Box sx={{ mb: 1 }}>
                    <video
                      src={formData.video_note_url}
                      controls
                      style={{ maxWidth: '100%', maxHeight: 200 }}
                    />
                    <Button size="small" onClick={() => setFormData((p) => ({ ...p, video_note_url: '' }))}>
                      Retirer
                    </Button>
                  </Box>
                )}
              </Grid>

              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={2}
                  label="Notes"
                  name="notes"
                  value={formData.notes}
                  onChange={handleChange}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>

              <Grid item xs={12}>
                <Button
                  type="submit"
                  variant="contained"
                  startIcon={<SaveIcon />}
                  size="large"
                >
                  Enregistrer le rapport
                </Button>
              </Grid>
            </Grid>
          </form>
        </CardContent>
      </Card>
    </Box>
  )
}

export default VisitReport


