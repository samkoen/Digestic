import React, { useState, useEffect } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Grid,
  Chip,
  Divider,
  Card,
  CardContent,
  TextField,
  MenuItem,
  FormControlLabel,
  Checkbox,
  CircularProgress,
} from '@mui/material'
import { format } from 'date-fns'
import EditIcon from '@mui/icons-material/Edit'
import SaveIcon from '@mui/icons-material/Save'
import CancelIcon from '@mui/icons-material/Cancel'
import { visitReportService } from '../../services/visitReportService'
import {
  WEEKS_UNTIL_RETURN_OPTIONS,
  formatExpectedReturnIso,
  getVisitNotCompletedReasonLabel,
} from '../../constants/visitReportForm'

function VisitReportDetail({ open, onClose, report, onUpdate }) {
  const [isEditing, setIsEditing] = useState(false)
  const [loading, setLoading] = useState(false)
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
    next_visit_date: '',
    weeks_until_return: '',
    voice_note_url: '',
    photo_note_url: '',
    video_note_url: '',
    delivery_mode: 'normal',
    notes: '',
  })

  useEffect(() => {
    if (report) {
      setFormData({
        visit_status: report.visit_status || 'completed',
        visit_not_completed_reason: report.visit_not_completed_reason || '',
        has_deposit: report.has_deposit || false,
        bottles_deposited: report.bottles_deposited || 0,
        free_units: report.free_units || 0,
        stock_status: report.stock_status || 'unknown',
        display_stand_status: report.display_stand_status || 'unknown',
        covering_status: report.covering_status || 'unknown',
        covering_size_to_order: report.covering_size_to_order || '',
        next_visit_date: report.next_visit_date
          ? format(new Date(report.next_visit_date), 'yyyy-MM-dd')
          : '',
        weeks_until_return: '',
        voice_note_url: report.voice_note_url || '',
        photo_note_url: report.photo_note_url || '',
        video_note_url: report.video_note_url || '',
        delivery_mode: report.delivery_mode || 'normal',
        notes: report.notes || '',
      })
      setIsEditing(false)
    }
  }, [report])

  if (!report) return null

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    try {
      return format(new Date(dateString), 'dd/MM/yyyy HH:mm')
    } catch {
      return dateString
    }
  }

  const getStatusLabel = (status) => {
    const labels = {
      good: 'Bon',
      low: 'Faible',
      out_of_stock: 'Rupture',
      unknown: 'Inconnu',
    }
    return labels[status] || status
  }

  const getStatusColor = (status) => {
    const colors = {
      good: 'success',
      low: 'warning',
      out_of_stock: 'error',
      unknown: 'default',
    }
    return colors[status] || 'default'
  }

  const getDisplayStandLabel = (status) => {
    const labels = {
      in_place: 'En place',
      not_in_place: 'Non en place',
      unknown: 'Inconnu',
    }
    return labels[status] || status
  }

  const getCoveringLabel = (status) => {
    const labels = {
      in_place: 'En place',
      to_order: 'À commander',
      unknown: 'Inconnu',
    }
    return labels[status] || status
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
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

  const handleSave = async () => {
    try {
      setLoading(true)
      const { weeks_until_return, next_visit_date: _nvd, ...rest } = formData
      const updateData = {
        ...rest,
        voice_note_url: formData.voice_note_url || null,
        photo_note_url: formData.photo_note_url || null,
        video_note_url: formData.video_note_url || null,
      }
      if (weeks_until_return) {
        updateData.weeks_until_return = parseInt(weeks_until_return, 10)
      }
      if (onUpdate) {
        await onUpdate(report.id, updateData)
      }
      setIsEditing(false)
    } catch (error) {
      console.error('Error updating report:', error)
      alert('Erreur lors de la mise à jour du rapport')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    if (report) {
      setFormData({
        visit_status: report.visit_status || 'completed',
        visit_not_completed_reason: report.visit_not_completed_reason || '',
        has_deposit: report.has_deposit || false,
        bottles_deposited: report.bottles_deposited || 0,
        free_units: report.free_units || 0,
        stock_status: report.stock_status || 'unknown',
        display_stand_status: report.display_stand_status || 'unknown',
        covering_status: report.covering_status || 'unknown',
        covering_size_to_order: report.covering_size_to_order || '',
        next_visit_date: report.next_visit_date
          ? format(new Date(report.next_visit_date), 'yyyy-MM-dd')
          : '',
        weeks_until_return: '',
        voice_note_url: report.voice_note_url || '',
        photo_note_url: report.photo_note_url || '',
        video_note_url: report.video_note_url || '',
        delivery_mode: report.delivery_mode || 'normal',
        notes: report.notes || '',
      })
    }
    setIsEditing(false)
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          Détail du Rapport de Visite
          {!isEditing && (
            <Button
              startIcon={<EditIcon />}
              onClick={() => setIsEditing(true)}
              variant="outlined"
              size="small"
            >
              Modifier
            </Button>
          )}
        </Box>
      </DialogTitle>
      <DialogContent
        sx={{
          pt: 2.75,
          '& .MuiTextField-root .MuiInputLabel-root': {
            lineHeight: 1.25,
            paddingTop: '1px',
          },
        }}
      >
        <Box sx={{ mt: 0 }}>
          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Informations Générales
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2" color="text.secondary">
                    Date de la visite
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {formatDate(report.visit_date)}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2" color="text.secondary">
                    Retour prévu
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {formatExpectedReturnIso(
                      report.expected_return_iso_year,
                      report.expected_return_iso_week
                    ) ||
                      (report.next_visit_date
                        ? format(new Date(report.next_visit_date), 'dd/MM/yyyy')
                        : '—')}
                  </Typography>
                </Grid>
                {isEditing && (
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      select
                      label="Nouvelle semaine de retour (optionnel)"
                      name="weeks_until_return"
                      value={formData.weeks_until_return}
                      onChange={handleChange}
                      InputLabelProps={{ shrink: true }}
                    >
                      <MenuItem value="">— inchangé</MenuItem>
                      {WEEKS_UNTIL_RETURN_OPTIONS.map((o) => (
                        <MenuItem key={o.value} value={o.value}>
                          {o.label}
                        </MenuItem>
                      ))}
                    </TextField>
                  </Grid>
                )}
                <Grid item xs={12} sm={6}>
                  {!isEditing && (
                    <Typography variant="body2" color="text.secondary">
                      Statut de la visite
                    </Typography>
                  )}
                  {isEditing ? (
                    <TextField
                      fullWidth
                      select
                      label="Statut de la visite"
                      name="visit_status"
                      value={formData.visit_status}
                      onChange={handleChange}
                      sx={{ mt: 0.5 }}
                      InputLabelProps={{ shrink: true }}
                    >
                      <MenuItem value="completed">Effectuée</MenuItem>
                      <MenuItem value="not_completed">Non effectuée</MenuItem>
                    </TextField>
                  ) : (
                    <Chip
                      label={report.visit_status === 'completed' ? 'Effectuée' : 'Non effectuée'}
                      color={report.visit_status === 'completed' ? 'success' : 'error'}
                      size="small"
                      sx={{ mt: 1 }}
                    />
                  )}
                </Grid>
                {(isEditing ? formData.visit_status === 'not_completed' : report.visit_status === 'not_completed') && (
                  <Grid item xs={12} sm={6}>
                    {!isEditing && (
                      <Typography variant="body2" color="text.secondary">
                        Raison
                      </Typography>
                    )}
                    {isEditing ? (
                      <TextField
                        fullWidth
                        select
                        label="Raison"
                        name="visit_not_completed_reason"
                        value={formData.visit_not_completed_reason}
                        onChange={handleChange}
                        sx={{ mt: 0.5 }}
                        InputLabelProps={{ shrink: true }}
                      >
                        <MenuItem value="pharmacy_closed">Pharmacie fermée</MenuItem>
                        <MenuItem value="owner_absent">Titulaire absent</MenuItem>
                        <MenuItem value="refus">Refus</MenuItem>
                      </TextField>
                    ) : (
                      <Typography variant="body1" fontWeight="medium" sx={{ mt: 1 }}>
                        {getVisitNotCompletedReasonLabel(report.visit_not_completed_reason)}
                      </Typography>
                    )}
                  </Grid>
                )}
              </Grid>
            </CardContent>
          </Card>

          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Dépôt
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  {isEditing ? (
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
                  ) : (
                    <>
                      <Typography variant="body2" color="text.secondary">
                        Dépôt effectué
                      </Typography>
                      <Chip
                        label={report.has_deposit ? 'Oui' : 'Non'}
                        color={report.has_deposit ? 'success' : 'default'}
                        size="small"
                        sx={{ mt: 1 }}
                      />
                    </>
                  )}
                </Grid>
                {(isEditing ? formData.has_deposit : report.has_deposit) && (
                  <>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="body2" color="text.secondary">
                        Nombre de bouteilles
                      </Typography>
                      {isEditing ? (
                        <TextField
                          fullWidth
                          type="number"
                          name="bottles_deposited"
                          value={formData.bottles_deposited}
                          onChange={handleChange}
                          sx={{ mt: 1 }}
                        />
                      ) : (
                        <Typography variant="body1" fontWeight="medium" sx={{ mt: 1 }}>
                          {report.bottles_deposited}
                        </Typography>
                      )}
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="body2" color="text.secondary">
                        Nombre de UG
                      </Typography>
                      {isEditing ? (
                        <TextField
                          fullWidth
                          type="number"
                          name="free_units"
                          value={formData.free_units}
                          onChange={handleChange}
                          sx={{ mt: 1 }}
                        />
                      ) : (
                        <Typography variant="body1" fontWeight="medium" sx={{ mt: 1 }}>
                          {report.free_units || 0}
                        </Typography>
                      )}
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Typography variant="body2" color="text.secondary">
                        Mode de livraison
                      </Typography>
                      {isEditing ? (
                        <TextField
                          fullWidth
                          select
                          name="delivery_mode"
                          value={formData.delivery_mode}
                          onChange={handleChange}
                          sx={{ mt: 1 }}
                        >
                          <MenuItem value="normal">Normal</MenuItem>
                          <MenuItem value="deposit_sale">Dépôt-vente</MenuItem>
                        </TextField>
                      ) : (
                        <Chip
                          label={report.delivery_mode === 'deposit_sale' ? 'Dépôt-vente' : 'Normal'}
                          color={report.delivery_mode === 'deposit_sale' ? 'warning' : 'info'}
                          size="small"
                          sx={{ mt: 1 }}
                        />
                      )}
                    </Grid>
                  </>
                )}
              </Grid>
            </CardContent>
          </Card>

          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                État des Stocks et Présentoirs
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Typography variant="body2" color="text.secondary">
                    État des stocks
                  </Typography>
                  {isEditing ? (
                    <TextField
                      fullWidth
                      select
                      name="stock_status"
                      value={formData.stock_status}
                      onChange={handleChange}
                      sx={{ mt: 1 }}
                    >
                      <MenuItem value="good">Bon</MenuItem>
                      <MenuItem value="low">Faible</MenuItem>
                      <MenuItem value="out_of_stock">Rupture</MenuItem>
                      <MenuItem value="unknown">Inconnu</MenuItem>
                    </TextField>
                  ) : (
                    <Chip
                      label={getStatusLabel(report.stock_status)}
                      color={getStatusColor(report.stock_status)}
                      size="small"
                      sx={{ mt: 1 }}
                    />
                  )}
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Typography variant="body2" color="text.secondary">
                    État du présentoir
                  </Typography>
                  {isEditing ? (
                    <TextField
                      fullWidth
                      select
                      name="display_stand_status"
                      value={formData.display_stand_status}
                      onChange={handleChange}
                      sx={{ mt: 1 }}
                    >
                      <MenuItem value="in_place">En place</MenuItem>
                      <MenuItem value="not_in_place">Pas en place</MenuItem>
                      <MenuItem value="unknown">Inconnu</MenuItem>
                    </TextField>
                  ) : (
                    <Chip
                      label={getDisplayStandLabel(report.display_stand_status)}
                      color={report.display_stand_status === 'in_place' ? 'success' : 'default'}
                      size="small"
                      sx={{ mt: 1 }}
                    />
                  )}
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Typography variant="body2" color="text.secondary">
                    État du covering
                  </Typography>
                  {isEditing ? (
                    <TextField
                      fullWidth
                      select
                      name="covering_status"
                      value={formData.covering_status}
                      onChange={handleChange}
                      sx={{ mt: 1 }}
                    >
                      <MenuItem value="in_place">En place</MenuItem>
                      <MenuItem value="to_order">À commander</MenuItem>
                      <MenuItem value="unknown">Inconnu</MenuItem>
                    </TextField>
                  ) : (
                    <Chip
                      label={getCoveringLabel(report.covering_status)}
                      color={report.covering_status === 'in_place' ? 'success' : 'warning'}
                      size="small"
                      sx={{ mt: 1 }}
                    />
                  )}
                </Grid>
                {(isEditing ? formData.covering_status === 'to_order' : report.covering_status === 'to_order') && 
                 (isEditing ? formData.covering_size_to_order : report.covering_size_to_order) && (
                  <Grid item xs={12}>
                    <Typography variant="body2" color="text.secondary">
                      Taille du covering à commander
                    </Typography>
                    {isEditing ? (
                      <TextField
                        fullWidth
                        name="covering_size_to_order"
                        value={formData.covering_size_to_order}
                        onChange={handleChange}
                        sx={{ mt: 1 }}
                      />
                    ) : (
                      <Typography variant="body1" fontWeight="medium" sx={{ mt: 1 }}>
                        {report.covering_size_to_order}
                      </Typography>
                    )}
                  </Grid>
                )}
              </Grid>
            </CardContent>
          </Card>

          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Pièces jointes
              </Typography>
              <Divider sx={{ mb: 2 }} />
              {isEditing && (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
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
              )}
              {(isEditing ? formData.voice_note_url : report.voice_note_url) && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" color="text.secondary">
                    Audio
                  </Typography>
                  <audio
                    controls
                    src={isEditing ? formData.voice_note_url : report.voice_note_url}
                    style={{ display: 'block', maxWidth: '100%' }}
                  />
                  {isEditing && (
                    <Button size="small" onClick={() => setFormData((p) => ({ ...p, voice_note_url: '' }))}>
                      Retirer
                    </Button>
                  )}
                </Box>
              )}
              {(isEditing ? formData.photo_note_url : report.photo_note_url) && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" color="text.secondary">
                    Photo
                  </Typography>
                  <Box
                    component="img"
                    src={isEditing ? formData.photo_note_url : report.photo_note_url}
                    alt="Note photo"
                    sx={{ maxHeight: 160, display: 'block' }}
                  />
                  {isEditing && (
                    <Button size="small" onClick={() => setFormData((p) => ({ ...p, photo_note_url: '' }))}>
                      Retirer
                    </Button>
                  )}
                </Box>
              )}
              {(isEditing ? formData.video_note_url : report.video_note_url) && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    Vidéo
                  </Typography>
                  <video
                    src={isEditing ? formData.video_note_url : report.video_note_url}
                    controls
                    style={{ maxWidth: '100%', maxHeight: 220 }}
                  />
                  {isEditing && (
                    <Button size="small" onClick={() => setFormData((p) => ({ ...p, video_note_url: '' }))}>
                      Retirer
                    </Button>
                  )}
                </Box>
              )}
              {!isEditing &&
                !report.voice_note_url &&
                !report.photo_note_url &&
                !report.video_note_url && <Typography color="text.secondary">—</Typography>}
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Notes
              </Typography>
              <Divider sx={{ mb: 2 }} />
              {isEditing ? (
                <TextField
                  fullWidth
                  multiline
                  rows={2}
                  name="notes"
                  value={formData.notes}
                  onChange={handleChange}
                />
              ) : (
                <Typography variant="body1">{report.notes || '-'}</Typography>
              )}
            </CardContent>
          </Card>
        </Box>
      </DialogContent>
      <DialogActions>
        {isEditing ? (
          <>
            <Button 
              onClick={handleCancel} 
              startIcon={<CancelIcon />}
              disabled={loading}
            >
              Annuler
            </Button>
            <Button 
              onClick={handleSave} 
              variant="contained"
              startIcon={loading ? <CircularProgress size={20} /> : <SaveIcon />}
              disabled={loading}
            >
              Enregistrer
            </Button>
          </>
        ) : (
          <Button onClick={onClose}>Fermer</Button>
        )}
      </DialogActions>
    </Dialog>
  )
}

export default VisitReportDetail


