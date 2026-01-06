import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
  TextField,
  MenuItem,
  TableSortLabel,
  InputAdornment,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import VisibilityIcon from '@mui/icons-material/Visibility'
import ClearIcon from '@mui/icons-material/Clear'
import DeleteIcon from '@mui/icons-material/Delete'
import { format } from 'date-fns'
import { pharmacyService } from '../../services/pharmacyService'
import { userService } from '../../services/userService'
import { visitReportService } from '../../services/visitReportService'
import { visitService } from '../../services/visitService'
import PharmacyForm from '../../components/PharmacyForm/PharmacyForm'

function Pharmacies() {
  const [pharmacies, setPharmacies] = useState([])
  const [enrichedPharmacies, setEnrichedPharmacies] = useState([])
  const [loading, setLoading] = useState(true)
  const [openForm, setOpenForm] = useState(false)
  const [editingPharmacy, setEditingPharmacy] = useState(null)
  const [orderBy, setOrderBy] = useState('name')
  const [order, setOrder] = useState('asc')
  const [commercials, setCommercials] = useState([])
  const [user, setUser] = useState(null)
  const [filters, setFilters] = useState({
    name: '',
    address: '',
    commercial: '',
    lastVisit: '',
    nextVisit: '',
    classification: '',
  })
  const [editingNextVisitId, setEditingNextVisitId] = useState(null)
  const [editingNextVisitValue, setEditingNextVisitValue] = useState('')
  const [shouldSaveOnBlur, setShouldSaveOnBlur] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    const storedUser = localStorage.getItem('user')
    if (storedUser) {
      setUser(JSON.parse(storedUser))
    }
  }, [])

  useEffect(() => {
    fetchPharmacies()
    fetchCommercials()
  }, [])

  const fetchCommercials = async () => {
    try {
      const data = await userService.getAll('commercial')
      setCommercials(data || [])
    } catch (error) {
      console.error('Erreur lors du chargement des commerciaux:', error)
    }
  }

  const fetchPharmacies = async () => {
    try {
      setLoading(true)
      setEnrichedPharmacies([]) // Réinitialiser
      const data = await pharmacyService.getAll()
      setPharmacies(data)
      
      // Enrichir les données avec les informations des commerciaux et visites
      if (data && data.length > 0) {
        await enrichPharmaciesData(data)
      } else {
        setEnrichedPharmacies([])
      }
    } catch (error) {
      console.error('Error fetching pharmacies:', error)
      setEnrichedPharmacies([])
    } finally {
      setLoading(false)
    }
  }

  const enrichPharmaciesData = async (pharmaciesData) => {
    try {
      // Récupérer uniquement les commerciaux (pas l'admin) pour mapper les IDs aux noms
      const commercialUsers = await userService.getAll('commercial')
      console.log('Commercial users loaded:', commercialUsers.length, commercialUsers.map(u => `${u.first_name} ${u.last_name} (${u.id})`))
      const usersMap = new Map(commercialUsers.map(u => [u.id, u]))
      
      // Récupérer tous les rapports de visite en une seule fois (plus efficace)
      const allReports = await visitReportService.getAll()
      const reportsByPharmacy = new Map()
      allReports.forEach(report => {
        if (!reportsByPharmacy.has(report.pharmacy_id)) {
          reportsByPharmacy.set(report.pharmacy_id, [])
        }
        reportsByPharmacy.get(report.pharmacy_id).push(report)
      })
      
      // Récupérer toutes les visites en une seule fois (plus efficace)
      const allVisits = await visitService.getAll()
      const visitsByPharmacy = new Map()
      allVisits.forEach(visit => {
        if (!visitsByPharmacy.has(visit.pharmacy_id)) {
          visitsByPharmacy.set(visit.pharmacy_id, [])
        }
        visitsByPharmacy.get(visit.pharmacy_id).push(visit)
      })
      
      // Enrichir chaque pharmacie
      const enriched = pharmaciesData.map((pharmacy) => {
        // Récupérer le nom du commercial
        let commercialName = '-'
        if (pharmacy.commercial_id) {
          const commercial = usersMap.get(pharmacy.commercial_id)
          if (commercial) {
            commercialName = `${commercial.first_name} ${commercial.last_name}`
          } else {
            // Debug: commercial non trouvé
            console.warn(`Commercial not found for pharmacy ${pharmacy.name} (ID: ${pharmacy.commercial_id})`)
            console.log('Available commercial IDs:', Array.from(usersMap.keys()))
          }
        }
        
        // Récupérer la dernière visite (rapport de visite)
        let lastVisitDate = null
        const pharmacyReports = reportsByPharmacy.get(pharmacy.id) || []
        if (pharmacyReports.length > 0) {
          const sortedReports = pharmacyReports
            .filter(r => r.visit_date)
            .sort((a, b) => new Date(b.visit_date) - new Date(a.visit_date))
          
          if (sortedReports.length > 0) {
            lastVisitDate = sortedReports[0].visit_date
          }
        }
        
        // Récupérer la prochaine visite directement depuis le champ de la pharmacie
        const nextVisitDate = pharmacy.next_visit_date || null
        
        return {
          ...pharmacy,
          commercialName,
          lastVisitDate,
          nextVisitDate,
        }
      })
      
      console.log('Enriched pharmacies:', enriched.length)
      if (enriched.length > 0) {
        console.log('Sample:', {
          name: enriched[0].name,
          commercial: enriched[0].commercialName,
          lastVisit: enriched[0].lastVisitDate,
          nextVisit: enriched[0].nextVisitDate
        })
      }
      setEnrichedPharmacies(enriched)
    } catch (error) {
      console.error('Error enriching pharmacies data:', error)
      // En cas d'erreur, au moins afficher les pharmacies avec des valeurs par défaut
      const fallback = pharmaciesData.map(p => ({
        ...p,
        commercialName: p.commercial_id ? '-' : '-',
        lastVisitDate: null,
        nextVisitDate: null,
      }))
      setEnrichedPharmacies(fallback)
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

  const handleCreate = () => {
    setEditingPharmacy(null)
    setOpenForm(true)
  }

  const handleEdit = (pharmacy) => {
    setEditingPharmacy(pharmacy)
    setOpenForm(true)
  }

  const handleFormClose = () => {
    setOpenForm(false)
    setEditingPharmacy(null)
    fetchPharmacies()
  }

  const handleDelete = async (pharmacy) => {
    if (window.confirm(`Êtes-vous sûr de vouloir supprimer la pharmacie "${pharmacy.name}" ?`)) {
      try {
        await pharmacyService.delete(pharmacy.id)
        fetchPharmacies()
      } catch (error) {
        console.error('Error deleting pharmacy:', error)
        alert('Erreur lors de la suppression de la pharmacie')
      }
    }
  }

  const handleSort = (property) => {
    const isAsc = orderBy === property && order === 'asc'
    setOrder(isAsc ? 'desc' : 'asc')
    setOrderBy(property)
  }

  const filteredAndSortedPharmacies = React.useMemo(() => {
    let data = enrichedPharmacies.length > 0 ? enrichedPharmacies : pharmacies
    
    // Appliquer les filtres
    data = data.filter((pharmacy) => {
      // Filtre par nom
      if (filters.name && !pharmacy.name?.toLowerCase().includes(filters.name.toLowerCase())) {
        return false
      }
      
      // Filtre par adresse
      const fullAddress = `${pharmacy.address}, ${pharmacy.postal_code} ${pharmacy.city}`.toLowerCase()
      if (filters.address && !fullAddress.includes(filters.address.toLowerCase())) {
        return false
      }
      
      // Filtre par commercial (par ID)
      if (filters.commercial && pharmacy.commercial_id !== filters.commercial) {
        return false
      }
      
      // Filtre par dernière visite
      if (filters.lastVisit) {
        const lastVisitStr = formatDate(pharmacy.lastVisitDate).toLowerCase()
        if (!lastVisitStr.includes(filters.lastVisit.toLowerCase()) && lastVisitStr !== '-') {
          return false
        }
      }
      
      // Filtre par prochaine visite (comparaison de dates)
      if (filters.nextVisit) {
        if (!pharmacy.nextVisitDate) {
          return false // Si pas de date et qu'on filtre, on exclut
        }
        const filterDate = new Date(filters.nextVisit)
        filterDate.setHours(0, 0, 0, 0)
        const pharmacyDate = new Date(pharmacy.nextVisitDate)
        pharmacyDate.setHours(0, 0, 0, 0)
        // Comparer les dates (égalité)
        if (pharmacyDate.getTime() !== filterDate.getTime()) {
          return false
        }
      }
      
      // Filtre par classification
      if (filters.classification && pharmacy.classification !== filters.classification) {
        return false
      }
      
      return true
    })
    
    // Appliquer le tri
    return [...data].sort((a, b) => {
      let aValue, bValue
      
      switch (orderBy) {
        case 'name':
          aValue = a.name || ''
          bValue = b.name || ''
          break
        case 'address':
          aValue = `${a.address}, ${a.postal_code} ${a.city}` || ''
          bValue = `${b.address}, ${b.postal_code} ${b.city}` || ''
          break
        case 'commercial':
          aValue = a.commercialName || ''
          bValue = b.commercialName || ''
          break
        case 'lastVisit':
          aValue = a.lastVisitDate ? new Date(a.lastVisitDate).getTime() : 0
          bValue = b.lastVisitDate ? new Date(b.lastVisitDate).getTime() : 0
          break
        case 'nextVisit':
          aValue = a.nextVisitDate ? new Date(a.nextVisitDate).getTime() : 0
          bValue = b.nextVisitDate ? new Date(b.nextVisitDate).getTime() : 0
          break
        case 'classification':
          const classOrder = { A: 1, B: 2, C: 3 }
          aValue = classOrder[a.classification] || 999
          bValue = classOrder[b.classification] || 999
          break
        default:
          return 0
      }
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return order === 'asc' 
          ? aValue.localeCompare(bValue, 'fr')
          : bValue.localeCompare(aValue, 'fr')
      } else {
        return order === 'asc' ? aValue - bValue : bValue - aValue
      }
    })
  }, [enrichedPharmacies, pharmacies, orderBy, order, filters])

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const clearFilters = () => {
    setFilters({
      name: '',
      address: '',
      commercial: '',
      lastVisit: '',
      nextVisit: '',
      classification: '',
    })
  }

  const hasActiveFilters = Object.values(filters).some(v => v !== '')

  const getClassificationColor = (classification) => {
    const colors = {
      A: 'error',
      B: 'warning',
      C: 'info',
    }
    return colors[classification] || 'default'
  }

  const handleNextVisitClick = (pharmacy) => {
    setEditingNextVisitId(pharmacy.id)
    // Convertir la date ISO en format YYYY-MM-DD pour l'input date
    const dateValue = pharmacy.nextVisitDate 
      ? format(new Date(pharmacy.nextVisitDate), 'yyyy-MM-dd')
      : ''
    setEditingNextVisitValue(dateValue)
    setShouldSaveOnBlur(true)
  }

  const handleNextVisitChange = (e) => {
    setEditingNextVisitValue(e.target.value)
  }

  const handleNextVisitSave = async (pharmacyId) => {
    if (!shouldSaveOnBlur) {
      setShouldSaveOnBlur(true)
      return
    }
    
    try {
      // Convertir la date YYYY-MM-DD en ISO format (midnight UTC pour éviter les problèmes de fuseau horaire)
      let isoDate = null
      if (editingNextVisitValue) {
        const date = new Date(editingNextVisitValue)
        // S'assurer que la date est à minuit pour éviter les problèmes de fuseau horaire
        date.setHours(0, 0, 0, 0)
        isoDate = date.toISOString()
      }
      
      await pharmacyService.update(pharmacyId, {
        next_visit_date: isoDate
      })
      
      // Mettre à jour l'état local
      setEnrichedPharmacies(prev => 
        prev.map(p => 
          p.id === pharmacyId 
            ? { ...p, nextVisitDate: isoDate }
            : p
        )
      )
      
      setEditingNextVisitId(null)
      setEditingNextVisitValue('')
      setShouldSaveOnBlur(true)
    } catch (error) {
      console.error('Erreur lors de la mise à jour de la date:', error)
      alert('Erreur lors de la mise à jour de la date de prochaine visite')
      handleNextVisitCancel()
    }
  }

  const handleNextVisitCancel = () => {
    setEditingNextVisitId(null)
    setEditingNextVisitValue('')
    setShouldSaveOnBlur(true)
  }

  const handleNextVisitKeyDown = (e, pharmacyId) => {
    if (e.key === 'Enter') {
      handleNextVisitSave(pharmacyId)
    } else if (e.key === 'Escape') {
      handleNextVisitCancel()
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
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Pharmacies</Typography>
        <Box display="flex" gap={2}>
          {hasActiveFilters && (
            <Button
              variant="outlined"
              onClick={clearFilters}
              size="small"
            >
              Réinitialiser filtres
            </Button>
          )}
          {user?.role === 'admin' && (
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleCreate}
            >
              Nouvelle Pharmacie
            </Button>
          )}
        </Box>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            {/* Ligne des en-têtes avec tri */}
            <TableRow>
              <TableCell>
                <TableSortLabel
                  active={orderBy === 'name'}
                  direction={orderBy === 'name' ? order : 'asc'}
                  onClick={() => handleSort('name')}
                >
                  Nom
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={orderBy === 'address'}
                  direction={orderBy === 'address' ? order : 'asc'}
                  onClick={() => handleSort('address')}
                >
                  Adresse
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={orderBy === 'commercial'}
                  direction={orderBy === 'commercial' ? order : 'asc'}
                  onClick={() => handleSort('commercial')}
                >
                  Commercial
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={orderBy === 'lastVisit'}
                  direction={orderBy === 'lastVisit' ? order : 'asc'}
                  onClick={() => handleSort('lastVisit')}
                >
                  Dernière visite
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={orderBy === 'nextVisit'}
                  direction={orderBy === 'nextVisit' ? order : 'asc'}
                  onClick={() => handleSort('nextVisit')}
                >
                  Prochaine visite
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={orderBy === 'classification'}
                  direction={orderBy === 'classification' ? order : 'asc'}
                  onClick={() => handleSort('classification')}
                >
                  Classification
                </TableSortLabel>
              </TableCell>
              <TableCell>RIB</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
            {/* Ligne des filtres */}
            <TableRow>
              <TableCell>
                <TextField
                  value={filters.name}
                  onChange={(e) => handleFilterChange('name', e.target.value)}
                  size="small"
                  placeholder="Filtrer..."
                  fullWidth
                  variant="outlined"
                />
              </TableCell>
              <TableCell>
                <TextField
                  value={filters.address}
                  onChange={(e) => handleFilterChange('address', e.target.value)}
                  size="small"
                  placeholder="Filtrer..."
                  fullWidth
                  variant="outlined"
                />
              </TableCell>
              <TableCell>
                <TextField
                  select
                  value={filters.commercial}
                  onChange={(e) => handleFilterChange('commercial', e.target.value)}
                  size="small"
                  fullWidth
                  variant="outlined"
                >
                  <MenuItem value="">Tous</MenuItem>
                  {commercials.map((commercial) => (
                    <MenuItem key={commercial.id} value={commercial.id}>
                      {commercial.first_name} {commercial.last_name}
                    </MenuItem>
                  ))}
                </TextField>
              </TableCell>
              <TableCell>
                <TextField
                  value={filters.lastVisit}
                  onChange={(e) => handleFilterChange('lastVisit', e.target.value)}
                  size="small"
                  placeholder="Filtrer..."
                  fullWidth
                  variant="outlined"
                />
              </TableCell>
              <TableCell>
                <TextField
                  type="date"
                  value={filters.nextVisit}
                  onChange={(e) => handleFilterChange('nextVisit', e.target.value)}
                  size="small"
                  fullWidth
                  variant="outlined"
                  InputLabelProps={{
                    shrink: true,
                  }}
                  inputProps={{
                    style: { fontSize: '14px' }
                  }}
                />
              </TableCell>
              <TableCell>
                <TextField
                  select
                  value={filters.classification}
                  onChange={(e) => handleFilterChange('classification', e.target.value)}
                  size="small"
                  fullWidth
                  variant="outlined"
                >
                  <MenuItem value="">Toutes</MenuItem>
                  <MenuItem value="A">A</MenuItem>
                  <MenuItem value="B">B</MenuItem>
                  <MenuItem value="C">C</MenuItem>
                </TextField>
              </TableCell>
              <TableCell></TableCell>
              <TableCell align="right"></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredAndSortedPharmacies.map((pharmacy) => (
              <TableRow 
                key={pharmacy.id} 
                hover
                onDoubleClick={() => navigate(`/pharmacies/${pharmacy.id}`)}
                sx={{ cursor: 'pointer' }}
              >
                <TableCell>{pharmacy.name}</TableCell>
                <TableCell>
                  {pharmacy.address}, {pharmacy.postal_code} {pharmacy.city}
                </TableCell>
                <TableCell>{pharmacy.commercialName || '-'}</TableCell>
                <TableCell>{formatDate(pharmacy.lastVisitDate)}</TableCell>
                <TableCell
                  onClick={(e) => {
                    e.stopPropagation()
                    if (editingNextVisitId !== pharmacy.id) {
                      handleNextVisitClick(pharmacy)
                    }
                  }}
                  sx={{ 
                    cursor: 'pointer',
                    position: 'relative',
                    '&:hover': {
                      backgroundColor: editingNextVisitId === pharmacy.id ? 'transparent' : 'action.hover',
                    }
                  }}
                >
                  {editingNextVisitId === pharmacy.id ? (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <TextField
                        type="date"
                        value={editingNextVisitValue}
                        onChange={handleNextVisitChange}
                        onBlur={() => handleNextVisitSave(pharmacy.id)}
                        onKeyDown={(e) => handleNextVisitKeyDown(e, pharmacy.id)}
                        onClick={(e) => e.stopPropagation()}
                        autoFocus
                        size="small"
                        InputLabelProps={{
                          shrink: true,
                        }}
                        inputProps={{
                          style: { fontSize: '14px' }
                        }}
                        sx={{
                          width: '180px',
                          '& .MuiOutlinedInput-root': {
                            paddingRight: '8px',
                          }
                        }}
                        InputProps={{
                          endAdornment: editingNextVisitValue && (
                            <InputAdornment position="end">
                              <IconButton
                                size="small"
                                onMouseDown={(e) => {
                                  e.preventDefault()
                                  e.stopPropagation()
                                  setShouldSaveOnBlur(false)
                                }}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setEditingNextVisitValue('')
                                  // Réactiver la sauvegarde après un court délai
                                  setTimeout(() => {
                                    setShouldSaveOnBlur(true)
                                  }, 100)
                                }}
                                edge="end"
                              >
                                <ClearIcon fontSize="small" />
                              </IconButton>
                            </InputAdornment>
                          ),
                        }}
                      />
                    </Box>
                  ) : (
                    <span>{formatDate(pharmacy.nextVisitDate)}</span>
                  )}
                </TableCell>
                <TableCell>
                  <Chip
                    label={pharmacy.classification}
                    color={getClassificationColor(pharmacy.classification)}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Chip
                    label={pharmacy.rib ? 'Oui' : 'Non'}
                    color={pharmacy.rib ? 'success' : 'default'}
                    size="small"
                  />
                </TableCell>
                <TableCell align="right">
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation()
                      navigate(`/pharmacies/${pharmacy.id}`)
                    }}
                  >
                    <VisibilityIcon />
                  </IconButton>
                  {user?.role === 'admin' && (
                    <>
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleEdit(pharmacy)
                        }}
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDelete(pharmacy)
                        }}
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <PharmacyForm
        open={openForm}
        onClose={handleFormClose}
        pharmacy={editingPharmacy}
      />
    </Box>
  )
}

export default Pharmacies

