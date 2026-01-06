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
    next_visit_date: '',
    delivery_mode: 'normal',
    notes: '',
  })

  useEffect(() => {
    fetchVisit()
  }, [visitId])

  const fetchVisit = async () => {
    try {
      setLoading(true)
      const visitData = await visitService.getById(visitId)
      setVisit(visitData)
    } catch (error) {
      console.error('Error fetching visit:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const reportData = {
        visit_id: visitId,
        pharmacy_id: visit.pharmacy_id,
        commercial_id: visit.commercial_id,
        visit_date: new Date().toISOString(),
        ...formData,
      }
      await visitReportService.create(reportData)
      
      // Si une date de prochaine visite est fournie, mettre à jour la pharmacie
      if (formData.next_visit_date && formData.next_visit_date.trim() !== '') {
        try {
          // Convertir la date yyyy-MM-dd en ISO format
          const dateObj = new Date(formData.next_visit_date + 'T00:00:00')
          if (!isNaN(dateObj.getTime())) {
            await pharmacyService.update(visit.pharmacy_id, {
              next_visit_date: dateObj.toISOString()
            })
          }
        } catch (dateError) {
          console.error('Error updating pharmacy next visit date:', dateError)
          // Ne pas bloquer si la mise à jour de la date échoue
        }
      }
      
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
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  select
                  label="Statut de la visite"
                  name="visit_status"
                  value={formData.visit_status}
                  onChange={handleChange}
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
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      fullWidth
                      select
                      label="Mode de livraison"
                      name="delivery_mode"
                      value={formData.delivery_mode}
                      onChange={handleChange}
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
                  value={formData.stock_status}
                  onChange={handleChange}
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
                  />
                </Grid>
              )}

              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="date"
                  label="Date de la prochaine visite"
                  name="next_visit_date"
                  value={formData.next_visit_date}
                  onChange={handleChange}
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
                  value={formData.notes}
                  onChange={handleChange}
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


