import React, { useEffect, useState, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  Typography,
  Button,
  Paper,
  Tabs,
  Tab,
  CircularProgress,
  Card,
  CardContent,
  Grid,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  InputAdornment,
} from '@mui/material'
import { format, startOfWeek, endOfWeek, eachDayOfInterval, isSameDay, parseISO } from 'date-fns'
import { fr } from 'date-fns/locale'
import VisibilityIcon from '@mui/icons-material/Visibility'
import RouteIcon from '@mui/icons-material/Route'
import EventRepeatIcon from '@mui/icons-material/EventRepeat'
import CalendarTodayIcon from '@mui/icons-material/CalendarToday'
import { visitService } from '../../services/visitService'
import { pharmacyService } from '../../services/pharmacyService'
import { userService } from '../../services/userService'
import { visitReportService } from '../../services/visitReportService'

function Planning() {
  const location = useLocation()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  // Récupérer le tabValue depuis location.state, sinon par défaut 0 (Aujourd'hui)
  const [tabValue, setTabValue] = useState(location.state?.tabValue ?? 0) // 0: Aujourd'hui, 1: Jour, 2: Semaine
  // Récupérer la date sélectionnée depuis location.state, sinon utiliser la date actuelle
  const [selectedDate, setSelectedDate] = useState(
    location.state?.selectedDate ? parseISO(location.state.selectedDate) : new Date()
  )
  const [pharmaciesWithNextVisit, setPharmaciesWithNextVisit] = useState([])
  const [pharmacies, setPharmacies] = useState([])
  const [commercials, setCommercials] = useState([])
  const [routeMenuAnchor, setRouteMenuAnchor] = useState(null)
  const [replanifyDialogOpen, setReplanifyDialogOpen] = useState(false)
  const [selectedPharmacyForReplanify, setSelectedPharmacyForReplanify] = useState(null)
  const [newVisitDate, setNewVisitDate] = useState('')
  const [newVisitDateISO, setNewVisitDateISO] = useState('')
  const dateInputRef = useRef(null)

  useEffect(() => {
    fetchData()
  }, [selectedDate, tabValue])
  
  // Réinitialiser le tabValue et la date sélectionnée si on vient d'une autre page avec un state
  useEffect(() => {
    if (location.state?.tabValue !== undefined) {
      setTabValue(location.state.tabValue)
    }
    if (location.state?.selectedDate) {
      setSelectedDate(parseISO(location.state.selectedDate))
    }
  }, [location.state])

  const fetchData = async () => {
    try {
      setLoading(true)
      
      // Récupérer toutes les données nécessaires
      const [pharmaciesData, commercialsData, allReports] = await Promise.all([
        pharmacyService.getAll(),
        userService.getAll('commercial'),
        visitReportService.getAll()
      ])
      
      setPharmacies(pharmaciesData)
      setCommercials(commercialsData)

      // Pour chaque pharmacie, trouver le dernier réassort (rapport avec dépôt le plus récent)
      const getLastReassort = (pharmacyId) => {
        const pharmacyReports = allReports
          .filter(report => 
            report.pharmacy_id === pharmacyId && 
            report.has_deposit === true && 
            report.bottles_deposited > 0
          )
          .sort((a, b) => new Date(b.visit_date) - new Date(a.visit_date))
        
        if (pharmacyReports.length > 0) {
          return {
            date: pharmacyReports[0].visit_date,
            quantity: pharmacyReports[0].bottles_deposited
          }
        }
        return null
      }

      // Pour chaque pharmacie, utiliser directement next_visit_date depuis la pharmacie
      const pharmaciesWithNextVisits = pharmaciesData
        .filter(pharmacy => pharmacy.next_visit_date !== null && pharmacy.next_visit_date !== undefined)
        .map((pharmacy) => {
          const lastReassort = getLastReassort(pharmacy.id)
          return {
            pharmacy,
            nextVisitDate: pharmacy.next_visit_date,
            commercialId: pharmacy.commercial_id,
            hasRIB: !!pharmacy.rib,
            lastReassortDate: lastReassort?.date || null,
            lastReassortQuantity: lastReassort?.quantity || null
          }
        })

      // Filtrer selon la date sélectionnée
      let filteredPharmacies = []
      if (tabValue === 0) {
        // Aujourd'hui
        const today = new Date()
        today.setHours(0, 0, 0, 0)
        const tomorrow = new Date(today)
        tomorrow.setDate(tomorrow.getDate() + 1)
        
        filteredPharmacies = pharmaciesWithNextVisits.filter(item => {
          const visitDate = new Date(item.nextVisitDate)
          visitDate.setHours(0, 0, 0, 0)
          return visitDate >= today && visitDate < tomorrow
        })
      } else if (tabValue === 1) {
        // Jour sélectionné
        const targetDate = new Date(selectedDate)
        targetDate.setHours(0, 0, 0, 0)
        const nextDay = new Date(targetDate)
        nextDay.setDate(nextDay.getDate() + 1)
        
        filteredPharmacies = pharmaciesWithNextVisits.filter(item => {
          const visitDate = new Date(item.nextVisitDate)
          visitDate.setHours(0, 0, 0, 0)
          return visitDate >= targetDate && visitDate < nextDay
        })
      } else if (tabValue === 2) {
        // Semaine
        const weekStart = startOfWeek(selectedDate, { weekStartsOn: 1 })
        const weekEnd = endOfWeek(selectedDate, { weekStartsOn: 1 })
        weekStart.setHours(0, 0, 0, 0)
        weekEnd.setHours(23, 59, 59, 999)
        
        filteredPharmacies = pharmaciesWithNextVisits.filter(item => {
          const visitDate = new Date(item.nextVisitDate)
          return visitDate >= weekStart && visitDate <= weekEnd
        })
      }

      setPharmaciesWithNextVisit(filteredPharmacies)
    } catch (error) {
      console.error('Error fetching planning data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue)
  }

  const handleDateChange = (event) => {
    setSelectedDate(parseISO(event.target.value))
  }

  const getCommercialName = (commercialId) => {
    if (!commercialId) return '-'
    const commercial = commercials.find(c => c.id === commercialId)
    return commercial ? `${commercial.first_name} ${commercial.last_name}` : commercialId
  }

  const formatTime = (dateString) => {
    if (!dateString) return '-'
    try {
      const date = new Date(dateString)
      const hours = date.getHours()
      const minutes = date.getMinutes()
      
      // Si l'heure est à 00:00, on affiche seulement la date
      if (hours === 0 && minutes === 0) {
        return format(date, 'dd/MM/yyyy')
      }
      return format(date, 'dd/MM/yyyy HH:mm')
    } catch {
      return dateString
    }
  }

  const formatDateDisplay = (dateString) => {
    if (!dateString) return '-'
    try {
      return format(new Date(dateString), 'dd/MM/yyyy')
    } catch {
      return dateString
    }
  }

  // Génère un itinéraire Google Maps pour toutes les pharmacies affichées
  const generateGoogleMapsRoute = (travelMode = 'driving') => {
    try {
      // Récupérer toutes les pharmacies affichées selon la vue active
      let pharmaciesToRoute = []
      
      if (tabValue === 0) {
        // Aujourd'hui
        pharmaciesToRoute = getPharmaciesForDate(new Date())
      } else if (tabValue === 1) {
        // Jour sélectionné
        pharmaciesToRoute = getPharmaciesForDate(selectedDate)
      } else if (tabValue === 2) {
        // Semaine - récupérer toutes les pharmacies de la semaine
        const weekStart = startOfWeek(selectedDate, { weekStartsOn: 1 })
        const weekEnd = endOfWeek(selectedDate, { weekStartsOn: 1 })
        const weekDays = eachDayOfInterval({ start: weekStart, end: weekEnd })
        pharmaciesToRoute = weekDays.flatMap(day => getPharmaciesForDate(day))
        // Supprimer les doublons (même pharmacie plusieurs fois dans la semaine)
        const uniquePharmacies = new Map()
        pharmaciesToRoute.forEach(item => {
          if (!uniquePharmacies.has(item.pharmacy.id)) {
            uniquePharmacies.set(item.pharmacy.id, item)
          }
        })
        pharmaciesToRoute = Array.from(uniquePharmacies.values())
      }
      
      console.log('Pharmacies à router:', pharmaciesToRoute.length)
      
      // Filtrer les pharmacies avec coordonnées ou adresse complète
      const pharmaciesWithCoords = pharmaciesToRoute.filter(item => 
        item.pharmacy && (
          (item.pharmacy.latitude != null && item.pharmacy.longitude != null) ||
          (item.pharmacy.address && item.pharmacy.postal_code && item.pharmacy.city)
        )
      )
      
      console.log('Pharmacies avec coordonnées ou adresse:', pharmaciesWithCoords.length)
      
      if (pharmaciesWithCoords.length === 0) {
        alert('Aucune pharmacie avec coordonnées géographiques ou adresse complète trouvée pour générer l\'itinéraire.')
        setRouteMenuAnchor(null)
        return
      }
      
      if (pharmaciesWithCoords.length === 1) {
        // Une seule pharmacie : ouvrir directement sa position avec le nom
        const pharmacy = pharmaciesWithCoords[0].pharmacy
        let url
        if (pharmacy.latitude && pharmacy.longitude) {
          url = `https://www.google.com/maps/search/?api=1&query=${pharmacy.latitude},${pharmacy.longitude}`
        } else {
          const address = encodeURIComponent(`${pharmacy.address}, ${pharmacy.postal_code} ${pharmacy.city}`)
          url = `https://www.google.com/maps/search/?api=1&query=${address}`
        }
        console.log('URL Google Maps (1 pharmacie):', url)
        const newWindow = window.open(url, '_blank')
        if (!newWindow) {
          alert('Veuillez autoriser les popups pour ouvrir Google Maps.')
        }
        setRouteMenuAnchor(null)
        return
      }
      
      // Optimiser l'ordre des pharmacies avec un algorithme simple du plus proche voisin
      // On commence par la première pharmacie (triée par date/heure)
      pharmaciesWithCoords.sort((a, b) => {
        const dateA = new Date(a.nextVisitDate)
        const dateB = new Date(b.nextVisitDate)
        return dateA - dateB
      })
      
      // Algorithme du plus proche voisin pour optimiser l'itinéraire
      // Séparer les pharmacies avec coordonnées de celles sans coordonnées
      const pharmaciesWithLatLon = pharmaciesWithCoords.filter(item => 
        item.pharmacy.latitude != null && item.pharmacy.longitude != null
      )
      const pharmaciesWithoutLatLon = pharmaciesWithCoords.filter(item => 
        !item.pharmacy.latitude || !item.pharmacy.longitude
      )
      
      let optimizedRoute = []
      
      // Optimiser seulement celles avec coordonnées
      if (pharmaciesWithLatLon.length > 0) {
        const remaining = [...pharmaciesWithLatLon]
        
        // Commencer par la première pharmacie (la plus tôt dans la journée)
        let current = remaining.shift()
        optimizedRoute.push(current)
        
        // Pour chaque pharmacie restante, trouver la plus proche
        while (remaining.length > 0) {
          let nearestIndex = 0
          let nearestDistance = Infinity
          
          remaining.forEach((pharmacy, index) => {
            const lat1 = current.pharmacy.latitude
            const lon1 = current.pharmacy.longitude
            const lat2 = pharmacy.pharmacy.latitude
            const lon2 = pharmacy.pharmacy.longitude
            
            // Distance euclidienne simplifiée (approximation)
            const distance = Math.sqrt(
              Math.pow(lat2 - lat1, 2) + Math.pow(lon2 - lon1, 2)
            )
            
            if (distance < nearestDistance) {
              nearestDistance = distance
              nearestIndex = index
            }
          })
          
          current = remaining.splice(nearestIndex, 1)[0]
          optimizedRoute.push(current)
        }
      }
      
      // Ajouter les pharmacies sans coordonnées à la fin (triées par date)
      pharmaciesWithoutLatLon.sort((a, b) => {
        const dateA = new Date(a.nextVisitDate)
        const dateB = new Date(b.nextVisitDate)
        return dateA - dateB
      })
      optimizedRoute = [...optimizedRoute, ...pharmaciesWithoutLatLon]
      
      // Construire l'URL Google Maps avec waypoints
      // Utiliser les coordonnées si disponibles, sinon l'adresse
      const formatLocation = (pharmacy) => {
        if (pharmacy.latitude && pharmacy.longitude) {
          return `${pharmacy.latitude},${pharmacy.longitude}`
        } else {
          return encodeURIComponent(`${pharmacy.address}, ${pharmacy.postal_code} ${pharmacy.city}`)
        }
      }
      
      const waypoints = optimizedRoute.slice(0, -1).map(item => 
        formatLocation(item.pharmacy)
      ).join('|')
      
      const lastPharmacy = optimizedRoute[optimizedRoute.length - 1].pharmacy
      const destination = formatLocation(lastPharmacy)
      
      // Construire l'URL avec les paramètres optimisés
      // Google Maps supporte jusqu'à 25 waypoints maximum
      // travelmode: driving (voiture), walking (marche), bicycling (vélo), transit (transports en commun)
      let url
      
      if (optimizedRoute.length === 1) {
        // Une seule pharmacie (déjà géré plus haut, mais au cas où)
        const pharmacy = optimizedRoute[0].pharmacy
        if (pharmacy.latitude && pharmacy.longitude) {
          url = `https://www.google.com/maps/search/?api=1&query=${pharmacy.latitude},${pharmacy.longitude}`
        } else {
          const address = encodeURIComponent(`${pharmacy.address}, ${pharmacy.postal_code} ${pharmacy.city}`)
          url = `https://www.google.com/maps/search/?api=1&query=${address}`
        }
      } else if (optimizedRoute.length === 2) {
        // Deux pharmacies : utiliser origin et destination
        const firstPharmacy = optimizedRoute[0].pharmacy
        const origin = formatLocation(firstPharmacy)
        url = `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${destination}&travelmode=${travelMode}`
      } else if (optimizedRoute.length <= 25) {
        // Pour 25 waypoints ou moins (limite Google Maps), utiliser waypoints avec destination
        if (waypoints) {
          url = `https://www.google.com/maps/dir/?api=1&waypoints=${waypoints}&destination=${destination}&travelmode=${travelMode}`
        } else {
          // Si pas de waypoints (ne devrait pas arriver ici), utiliser origin et destination
          const firstPharmacy = optimizedRoute[0].pharmacy
          const origin = formatLocation(firstPharmacy)
          url = `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${destination}&travelmode=${travelMode}`
        }
      } else {
        // Pour plus de 25 pharmacies, on prend les 24 premières comme waypoints et la dernière comme destination
        // (Google Maps limite à 25 waypoints max, donc 24 waypoints + 1 destination = 25 points)
        const limitedWaypoints = optimizedRoute.slice(0, 24).map(item => 
          formatLocation(item.pharmacy)
        ).join('|')
        url = `https://www.google.com/maps/dir/?api=1&waypoints=${limitedWaypoints}&destination=${destination}&travelmode=${travelMode}`
        alert(`Attention: Google Maps limite à 25 points. L'itinéraire inclura les 25 premières pharmacies sur ${optimizedRoute.length}.`)
      }
      
      console.log('URL Google Maps:', url)
      console.log('Nombre de pharmacies:', optimizedRoute.length)
      console.log('Mode de transport:', travelMode)
      
      // Vérifier que l'URL est valide
      if (!url || url.length === 0) {
        alert('Erreur: Impossible de générer l\'URL de l\'itinéraire.')
        setRouteMenuAnchor(null)
        return
      }
      
      // Ouvrir dans un nouvel onglet
      try {
        const newWindow = window.open(url, '_blank', 'noopener,noreferrer')
        if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
          // Popup bloquée, essayer de rediriger dans le même onglet
          if (confirm('Les popups sont bloquées. Voulez-vous ouvrir l\'itinéraire dans cet onglet ?')) {
            window.location.href = url
          }
        }
      } catch (error) {
        console.error('Erreur lors de l\'ouverture de la fenêtre:', error)
        // Essayer de rediriger dans le même onglet
        if (confirm('Impossible d\'ouvrir un nouvel onglet. Voulez-vous ouvrir l\'itinéraire dans cet onglet ?')) {
          window.location.href = url
        }
      }
      setRouteMenuAnchor(null)
    } catch (error) {
      console.error('Erreur lors de la génération de l\'itinéraire:', error)
      alert('Erreur lors de la génération de l\'itinéraire. Veuillez réessayer.')
      setRouteMenuAnchor(null)
    }
  }

  const handleRouteMenuOpen = (event) => {
    setRouteMenuAnchor(event.currentTarget)
  }

  const handleRouteMenuClose = () => {
    setRouteMenuAnchor(null)
  }

  // Fonction helper pour naviguer vers les détails d'une pharmacie
  const handlePharmacyClick = (pharmacyId, currentTabValue) => {
    const state = {
      from: '/planning',
      tabValue: currentTabValue,
    }
    
    // Ajouter la date sélectionnée pour les vues Jour et Semaine
    if (currentTabValue === 1 || currentTabValue === 2) {
      state.selectedDate = format(selectedDate, 'yyyy-MM-dd')
    }
    
    navigate(`/pharmacies/${pharmacyId}`, { state })
  }

  const handleReplanifyClick = (item, e) => {
    e.stopPropagation()
    setSelectedPharmacyForReplanify(item)
    // Convertir la date actuelle en format dd/MM/yyyy pour l'affichage
    const currentDate = item.nextVisitDate 
      ? format(new Date(item.nextVisitDate), 'dd/MM/yyyy')
      : format(new Date(), 'dd/MM/yyyy')
    // Convertir aussi en format ISO pour l'input date
    const currentDateISO = item.nextVisitDate 
      ? format(new Date(item.nextVisitDate), 'yyyy-MM-dd')
      : format(new Date(), 'yyyy-MM-dd')
    setNewVisitDate(currentDate)
    setNewVisitDateISO(currentDateISO)
    setReplanifyDialogOpen(true)
  }

  const handleReplanifyClose = () => {
    setReplanifyDialogOpen(false)
    setSelectedPharmacyForReplanify(null)
    setNewVisitDate('')
    setNewVisitDateISO('')
  }

  const handleDatePickerChange = (e) => {
    const isoDate = e.target.value
    setNewVisitDateISO(isoDate)
    // Convertir en dd/MM/yyyy pour l'affichage
    if (isoDate) {
      const dateObj = new Date(isoDate + 'T00:00:00')
      setNewVisitDate(format(dateObj, 'dd/MM/yyyy'))
    } else {
      setNewVisitDate('')
    }
  }

  const handleCalendarIconClick = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (dateInputRef.current) {
      dateInputRef.current.focus()
      // Essayer showPicker() si disponible (navigateurs modernes)
      if (typeof dateInputRef.current.showPicker === 'function') {
        dateInputRef.current.showPicker().catch(() => {
          // Si showPicker échoue, utiliser click()
          dateInputRef.current.click()
        })
      } else {
        // Fallback pour les navigateurs plus anciens
        dateInputRef.current.click()
      }
    }
  }

  const handleReplanifySave = async () => {
    if (!selectedPharmacyForReplanify || !newVisitDateISO) {
      return
    }

    try {
      // Utiliser directement la date ISO de l'input date
      const dateObj = new Date(newVisitDateISO + 'T00:00:00')
      if (isNaN(dateObj.getTime())) {
        alert('Date invalide. Veuillez vérifier la date saisie.')
        return
      }
      
      await pharmacyService.update(selectedPharmacyForReplanify.pharmacy.id, {
        next_visit_date: dateObj.toISOString()
      })
      // Rafraîchir les données
      await fetchData()
      handleReplanifyClose()
    } catch (error) {
      console.error('Error updating visit date:', error)
      alert('Erreur lors de la mise à jour de la date de visite')
    }
  }

  // Génère une couleur unique pour chaque pharmacie basée sur son ID
  const getPharmacyColor = (pharmacyId) => {
    // Liste de couleurs agréables
    const colors = [
      '#E3F2FD', // Bleu clair
      '#F3E5F5', // Violet clair
      '#E8F5E9', // Vert clair
      '#FFF3E0', // Orange clair
      '#FCE4EC', // Rose clair
      '#E0F2F1', // Turquoise clair
      '#FFF9C4', // Jaune clair
      '#E1BEE7', // Violet moyen
      '#BBDEFB', // Bleu moyen
      '#C8E6C9', // Vert moyen
      '#FFE0B2', // Orange moyen
      '#F8BBD0', // Rose moyen
      '#B2DFDB', // Turquoise moyen
      '#FFF59D', // Jaune moyen
    ]
    
    // Utiliser l'ID de la pharmacie pour sélectionner une couleur de manière cohérente
    let hash = 0
    for (let i = 0; i < pharmacyId.length; i++) {
      hash = pharmacyId.charCodeAt(i) + ((hash << 5) - hash)
    }
    return colors[Math.abs(hash) % colors.length]
  }

  const getPharmaciesForDate = (date) => {
    return pharmaciesWithNextVisit.filter(item => {
      if (!item.nextVisitDate) return false
      const visitDate = new Date(item.nextVisitDate)
      return isSameDay(visitDate, date)
    })
  }

  const renderTodayView = () => {
    const todayPharmacies = getPharmaciesForDate(new Date())
    
    if (todayPharmacies.length === 0) {
      return (
        <Typography variant="body1" color="text.secondary" sx={{ mt: 3 }}>
          Aucune visite planifiée pour aujourd'hui
        </Typography>
      )
    }

    return (
      <Grid container spacing={2} sx={{ mt: 2 }}>
        {todayPharmacies.map((item) => (
          <Grid item xs={12} sm={6} md={4} key={item.pharmacy.id}>
            <Card
              onDoubleClick={() => handlePharmacyClick(item.pharmacy.id, 0)}
              sx={{
                bgcolor: getPharmacyColor(item.pharmacy.id),
                transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
                '&:hover': {
                  transform: 'scale(1.05)',
                  boxShadow: 6,
                },
                cursor: 'pointer',
              }}
            >
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start">
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="h6" gutterBottom>
                      {item.pharmacy.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {formatTime(item.nextVisitDate)}
                    </Typography>
                    <Box sx={{ mt: 1.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Box display="flex" alignItems="center" gap={0.5}>
                        <Typography variant="caption" color="text.secondary">
                          RIB:
                        </Typography>
                        <Chip
                          label={item.hasRIB ? 'Oui' : 'Non'}
                          color={item.hasRIB ? 'success' : 'warning'}
                          size="small"
                          sx={{ height: '20px', fontSize: '0.7rem' }}
                        />
                      </Box>
                      {item.lastReassortDate && (
                        <>
                          <Typography variant="caption" color="text.secondary">
                            Dernier réassort: {format(new Date(item.lastReassortDate), 'dd/MM/yyyy')}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Quantité: {item.lastReassortQuantity} bouteilles
                          </Typography>
                        </>
                      )}
                      {!item.lastReassortDate && (
                        <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                          Aucun réassort enregistré
                        </Typography>
                      )}
                    </Box>
                  </Box>
                  <Box display="flex" gap={0.5}>
                    <Tooltip title="Replanifier la visite">
                      <IconButton
                        size="small"
                        onClick={(e) => handleReplanifyClick(item, e)}
                        color="primary"
                      >
                        <EventRepeatIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Voir les détails">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation()
                          handlePharmacyClick(item.pharmacy.id, 0)
                        }}
                      >
                        <VisibilityIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    )
  }

  const renderDayView = () => {
    const dayPharmacies = getPharmaciesForDate(selectedDate)
    
    return (
      <Box>
        <Box sx={{ mb: 3 }}>
          <Typography variant="body1" gutterBottom>
            Sélectionner une date
          </Typography>
          <input
            type="date"
            value={format(selectedDate, 'yyyy-MM-dd')}
            onChange={handleDateChange}
            style={{
              padding: '8px',
              fontSize: '16px',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
          />
        </Box>

        {dayPharmacies.length === 0 ? (
          <Typography variant="body1" color="text.secondary">
            Aucune visite planifiée pour le {formatDateDisplay(selectedDate.toISOString())}
          </Typography>
        ) : (
          <Grid container spacing={2}>
            {dayPharmacies.map((item) => (
              <Grid item xs={12} sm={6} md={4} key={item.pharmacy.id}>
                <Card
                  onDoubleClick={() => handlePharmacyClick(item.pharmacy.id, 1)}
                  sx={{
                    bgcolor: getPharmacyColor(item.pharmacy.id),
                    transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
                    '&:hover': {
                      transform: 'scale(1.05)',
                      boxShadow: 6,
                    },
                    cursor: 'pointer',
                  }}
                >
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="start">
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="h6" gutterBottom>
                          {item.pharmacy.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {formatTime(item.nextVisitDate)}
                        </Typography>
                        <Box sx={{ mt: 1.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                          <Box display="flex" alignItems="center" gap={0.5}>
                            <Typography variant="caption" color="text.secondary">
                              RIB:
                            </Typography>
                            <Chip
                              label={item.hasRIB ? 'Oui' : 'Non'}
                              color={item.hasRIB ? 'success' : 'error'}
                              size="small"
                              sx={{ height: '20px', fontSize: '0.7rem' }}
                            />
                          </Box>
                          {item.lastReassortDate && (
                            <>
                              <Typography variant="caption" color="text.secondary">
                                Dernier réassort: {format(new Date(item.lastReassortDate), 'dd/MM/yyyy')}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                Quantité: {item.lastReassortQuantity} bouteilles
                              </Typography>
                            </>
                          )}
                          {!item.lastReassortDate && (
                            <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                              Aucun réassort enregistré
                            </Typography>
                          )}
                        </Box>
                      </Box>
                      <Box display="flex" gap={0.5}>
                        <Tooltip title="Replanifier la visite">
                          <IconButton
                            size="small"
                            onClick={(e) => handleReplanifyClick(item, e)}
                            color="primary"
                          >
                            <EventRepeatIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Voir les détails">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation()
                              handlePharmacyClick(item.pharmacy.id, 1)
                            }}
                          >
                            <VisibilityIcon />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Box>
    )
  }

  const renderWeekView = () => {
    const weekStart = startOfWeek(selectedDate, { weekStartsOn: 1 })
    const weekEnd = endOfWeek(selectedDate, { weekStartsOn: 1 })
    const weekDays = eachDayOfInterval({ start: weekStart, end: weekEnd })

    return (
      <Box>
        <Box sx={{ mb: 3 }}>
          <Typography variant="body1" gutterBottom>
            Sélectionner une date de la semaine
          </Typography>
          <input
            type="date"
            value={format(selectedDate, 'yyyy-MM-dd')}
            onChange={handleDateChange}
            style={{
              padding: '8px',
              fontSize: '16px',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
          />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Semaine du {format(weekStart, 'dd/MM')} au {format(weekEnd, 'dd/MM/yyyy')}
          </Typography>
        </Box>

        <Grid container spacing={2}>
          {weekDays.map((day) => {
            const dayPharmacies = getPharmaciesForDate(day)
            const isToday = isSameDay(day, new Date())
            
            return (
              <Grid item xs={12} md={6} lg={4} key={day.toISOString()}>
                <Card sx={{ height: '100%', border: isToday ? '2px solid #1976d2' : 'none' }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      {format(day, 'EEEE dd/MM', { locale: fr })}
                      {isToday && (
                        <Chip label="Aujourd'hui" size="small" color="primary" sx={{ ml: 1 }} />
                      )}
                    </Typography>
                    
                    {dayPharmacies.length === 0 ? (
                      <Typography variant="body2" color="text.secondary">
                        Aucune visite
                      </Typography>
                    ) : (
                      <Box sx={{ mt: 2 }}>
                        {dayPharmacies.map((item) => (
                          <Box
                            key={item.pharmacy.id}
                            onDoubleClick={() => handlePharmacyClick(item.pharmacy.id, 2)}
                            sx={{
                              mb: 1,
                              p: 1,
                              bgcolor: getPharmacyColor(item.pharmacy.id),
                              borderRadius: 1,
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
                              '&:hover': {
                                transform: 'scale(1.05)',
                                boxShadow: 3,
                              },
                              cursor: 'pointer',
                            }}
                          >
                            <Box sx={{ flex: 1 }}>
                              <Typography variant="body2" fontWeight="medium">
                                {formatTime(item.nextVisitDate)} - {item.pharmacy.name}
                              </Typography>
                              <Box sx={{ mt: 0.5, display: 'flex', flexDirection: 'column', gap: 0.25 }}>
                                <Box display="flex" alignItems="center" gap={0.5}>
                                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                                    RIB:
                                  </Typography>
                                  <Chip
                                    label={item.hasRIB ? 'Oui' : 'Non'}
                                    color={item.hasRIB ? 'success' : 'error'}
                                    size="small"
                                    sx={{ height: '18px', fontSize: '0.65rem' }}
                                  />
                                </Box>
                                {item.lastReassortDate && (
                                  <>
                                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                                      Réassort: {format(new Date(item.lastReassortDate), 'dd/MM/yyyy')} ({item.lastReassortQuantity} b.)
                                    </Typography>
                                  </>
                                )}
                                {!item.lastReassortDate && (
                                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', fontStyle: 'italic' }}>
                                    Aucun réassort
                                  </Typography>
                                )}
                              </Box>
                            </Box>
                            <Box display="flex" gap={0.5}>
                              <Tooltip title="Replanifier la visite">
                                <IconButton
                                  size="small"
                                  onClick={(e) => handleReplanifyClick(item, e)}
                                  color="primary"
                                >
                                  <EventRepeatIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Voir les détails">
                                <IconButton
                                  size="small"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handlePharmacyClick(item.pharmacy.id, 2)
                                  }}
                                >
                                  <VisibilityIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </Box>
                        ))}
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            )
          })}
        </Grid>
      </Box>
    )
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
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">
          Planning des Visites
        </Typography>
        {pharmaciesWithNextVisit.length > 0 && (() => {
          // Calculer le nombre de pharmacies avec coordonnées pour l'itinéraire
          let pharmaciesCount = 0
          if (tabValue === 0) {
            pharmaciesCount = getPharmaciesForDate(new Date()).filter(item => 
              item.pharmacy.latitude && item.pharmacy.longitude
            ).length
          } else if (tabValue === 1) {
            pharmaciesCount = getPharmaciesForDate(selectedDate).filter(item => 
              item.pharmacy.latitude && item.pharmacy.longitude
            ).length
          } else if (tabValue === 2) {
            const weekStart = startOfWeek(selectedDate, { weekStartsOn: 1 })
            const weekEnd = endOfWeek(selectedDate, { weekStartsOn: 1 })
            const weekDays = eachDayOfInterval({ start: weekStart, end: weekEnd })
            const allWeekPharmacies = weekDays.flatMap(day => getPharmaciesForDate(day))
            const uniquePharmacies = new Map()
            allWeekPharmacies.forEach(item => {
              if (!uniquePharmacies.has(item.pharmacy.id)) {
                uniquePharmacies.set(item.pharmacy.id, item)
              }
            })
            pharmaciesCount = Array.from(uniquePharmacies.values()).filter(item => 
              item.pharmacy.latitude && item.pharmacy.longitude
            ).length
          }
          
          return pharmaciesCount > 0 ? (
            <>
              <Tooltip title={`Générer un itinéraire pour ${pharmaciesCount} pharmacie${pharmaciesCount > 1 ? 's' : ''}`}>
                <Button
                  variant="contained"
                  startIcon={<RouteIcon />}
                  onClick={handleRouteMenuOpen}
                  sx={{ ml: 2 }}
                >
                  Itinéraire ({pharmaciesCount})
                </Button>
              </Tooltip>
              <Menu
                anchorEl={routeMenuAnchor}
                open={Boolean(routeMenuAnchor)}
                onClose={handleRouteMenuClose}
              >
                <MenuItem onClick={() => generateGoogleMapsRoute('driving')}>
                  🚗 En voiture
                </MenuItem>
                <MenuItem onClick={() => generateGoogleMapsRoute('walking')}>
                  🚶 À pied
                </MenuItem>
                <MenuItem onClick={() => generateGoogleMapsRoute('bicycling')}>
                  🚴 À vélo
                </MenuItem>
                <MenuItem onClick={() => generateGoogleMapsRoute('transit')}>
                  🚇 Transports en commun
                </MenuItem>
              </Menu>
            </>
          ) : null
        })()}
      </Box>

      <Paper sx={{ mt: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Aujourd'hui" />
          <Tab label="Jour" />
          <Tab label="Semaine" />
        </Tabs>

        <Box sx={{ p: 3 }}>
          {tabValue === 0 && renderTodayView()}
          {tabValue === 1 && renderDayView()}
          {tabValue === 2 && renderWeekView()}
        </Box>
      </Paper>

      {/* Dialog pour replanifier la visite */}
      <Dialog open={replanifyDialogOpen} onClose={handleReplanifyClose} maxWidth="sm" fullWidth>
        <DialogTitle>Replanifier la visite</DialogTitle>
        <DialogContent>
          {selectedPharmacyForReplanify && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Pharmacie: <strong>{selectedPharmacyForReplanify.pharmacy.name}</strong>
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Date actuelle: {selectedPharmacyForReplanify.nextVisitDate 
                  ? format(new Date(selectedPharmacyForReplanify.nextVisitDate), 'dd/MM/yyyy')
                  : '-'}
              </Typography>
              <Box 
                sx={{ position: 'relative', width: '100%', cursor: 'pointer' }}
                onClick={(e) => {
                  e.stopPropagation()
                  handleCalendarIconClick(e)
                }}
              >
                <input
                  type="date"
                  ref={dateInputRef}
                  value={newVisitDateISO}
                  onChange={handleDatePickerChange}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '57px',
                    minHeight: '57px',
                    opacity: 0,
                    cursor: 'pointer',
                    zIndex: 10,
                    fontSize: '16px',
                  }}
                />
                <TextField
                  fullWidth
                  label="Nouvelle date de visite"
                  value={newVisitDate || ''}
                  InputProps={{
                    readOnly: true,
                    endAdornment: (
                      <InputAdornment position="end">
                        <CalendarTodayIcon color="action" />
                      </InputAdornment>
                    ),
                  }}
                  InputLabelProps={{
                    shrink: true,
                  }}
                  sx={{
                    pointerEvents: 'none',
                  }}
                  required
                />
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleReplanifyClose}>Annuler</Button>
          <Button 
            onClick={handleReplanifySave} 
            variant="contained" 
            disabled={!newVisitDate}
          >
            Enregistrer
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Planning

