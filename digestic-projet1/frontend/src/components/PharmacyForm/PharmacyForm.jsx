import React, { useState, useEffect } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Grid,
  MenuItem,
  InputAdornment,
  IconButton,
  Avatar,
  Tooltip,
  Box,
} from '@mui/material'
import ClearIcon from '@mui/icons-material/Clear'
import { PAYMENT_MODES, DEFAULT_PAYMENT_MODE } from '../../constants/paymentModes'
import { PHARMACY_STATUS_OPTIONS, getPharmacyStatusLabel } from '../../constants/pharmacyStatus'
import { pharmacyService } from '../../services/pharmacyService'
import { userService } from '../../services/userService'

function PharmacyForm({ open, onClose, pharmacy }) {
  const [formData, setFormData] = useState({
    name: '',
    address: '',
    city: '',
    postal_code: '',
    pharmacist_name: '',
    pharmacist_email: '',
    pharmacist_phone: '',
    rib: '',
    commercial_id: '',
    photo_url: '',
    payment_mode: DEFAULT_PAYMENT_MODE,
    status: 'actif',
  })
  const [loading, setLoading] = useState(false)
  const [commercials, setCommercials] = useState([])

  useEffect(() => {
    if (open) {
      fetchCommercials()
    }
  }, [open])

  useEffect(() => {
    if (pharmacy) {
      setFormData({
        name: pharmacy.name || '',
        address: pharmacy.address || '',
        city: pharmacy.city || '',
        postal_code: pharmacy.postal_code || '',
        pharmacist_name: pharmacy.pharmacist_name || '',
        pharmacist_email: pharmacy.pharmacist_email || '',
        pharmacist_phone: pharmacy.pharmacist_phone || '',
        rib: pharmacy.rib || '',
        commercial_id: pharmacy.commercial_id || '',
        photo_url: pharmacy.photo_url || '',
        payment_mode: pharmacy.payment_mode || DEFAULT_PAYMENT_MODE,
        status: pharmacy.status || 'actif',
      })
    } else {
      setFormData({
        name: '',
        address: '',
        city: '',
        postal_code: '',
        pharmacist_name: '',
        pharmacist_email: '',
        pharmacist_phone: '',
        rib: '',
        commercial_id: '',
        photo_url: '',
        payment_mode: DEFAULT_PAYMENT_MODE,
        status: 'actif',
      })
    }
  }, [pharmacy, open])

  const fetchCommercials = async () => {
    try {
      const data = await userService.getAll('commercial')
      setCommercials(data || [])
    } catch (error) {
      console.error('Erreur lors du chargement des commerciaux:', error)
    }
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleClearPhoto = () => {
    setFormData((prev) => ({
      ...prev,
      photo_url: '',
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      setLoading(true)
      const data = {
        ...formData,
        commercial_id: formData.commercial_id || null,
        photo_url: formData.photo_url || null,
      }

      if (pharmacy) {
        await pharmacyService.update(pharmacy.id, data)
      } else {
        await pharmacyService.create(data)
      }
      onClose()
    } catch (error) {
      console.error('Error saving pharmacy:', error)
      alert('Erreur lors de l\'enregistrement')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle>
          {pharmacy ? 'Modifier la pharmacie' : 'Nouvelle pharmacie'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                required
                label="Nom de la pharmacie"
                name="name"
                value={formData.name}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={8}>
              <TextField
                fullWidth
                required
                label="Adresse"
                name="address"
                value={formData.address}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                required
                label="Code postal"
                name="postal_code"
                value={formData.postal_code}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                required
                label="Ville"
                name="city"
                value={formData.city}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Statut (Sage : TYPE)"
                name="status"
                value={formData.status || 'actif'}
                onChange={handleChange}
                helperText="Valeurs usuelles : actif, stand by, désactivé (autre libre si besoin)"
              >
                {PHARMACY_STATUS_OPTIONS.map((o) => (
                  <MenuItem key={o.value} value={o.value}>
                    {o.label}
                  </MenuItem>
                ))}
                {formData.status &&
                  !PHARMACY_STATUS_OPTIONS.some((o) => o.value === formData.status) && (
                    <MenuItem value={formData.status}>
                      {getPharmacyStatusLabel(formData.status)} ({formData.status})
                    </MenuItem>
                  )}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Mode de paiement (dépôt)"
                name="payment_mode"
                value={formData.payment_mode}
                onChange={handleChange}
              >
                {PAYMENT_MODES.map((mode) => (
                  <MenuItem key={mode} value={mode}>
                    {mode}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Commercial"
                name="commercial_id"
                value={formData.commercial_id}
                onChange={handleChange}
              >
                <MenuItem value="">Aucun</MenuItem>
                {commercials.map((commercial) => (
                  <MenuItem key={commercial.id} value={commercial.id}>
                    {commercial.first_name} {commercial.last_name}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Nom du pharmacien"
                name="pharmacist_name"
                value={formData.pharmacist_name}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Email"
                name="pharmacist_email"
                type="email"
                value={formData.pharmacist_email}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Téléphone"
                name="pharmacist_phone"
                value={formData.pharmacist_phone}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12}>
              <Box
                display="flex"
                alignItems="center"
                gap={2}
                sx={{ flexWrap: 'wrap' }}
              >
                <TextField
                  fullWidth
                  label="URL de la photo"
                  name="photo_url"
                  value={formData.photo_url}
                  onChange={handleChange}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          edge="end"
                          aria-label="Effacer l'URL de la photo"
                          onClick={handleClearPhoto}
                          disabled={!formData.photo_url}
                        >
                          <ClearIcon fontSize="small" />
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
                {formData.photo_url && (
                  <Tooltip title="Aperçu de la photo">
                    <Avatar
                      src={formData.photo_url}
                      alt="Aperçu photo"
                      sx={{ width: 56, height: 56, border: '1px solid', borderColor: 'divider' }}
                    />
                  </Tooltip>
                )}
              </Box>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="RIB (Relevé d'Identité Bancaire)"
                name="rib"
                value={formData.rib}
                onChange={handleChange}
                placeholder="Ex: FR76 XXXX XXXX XXXX XXXX XXXX XXX"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Annuler</Button>
          <Button type="submit" variant="contained" disabled={loading}>
            {pharmacy ? 'Modifier' : 'Créer'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}

export default PharmacyForm


