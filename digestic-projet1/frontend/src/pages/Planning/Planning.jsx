import React, { useEffect, useState, useRef, useMemo, useCallback } from 'react'
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
  Avatar,
  FormControl,
  InputLabel,
  Select,
  OutlinedInput,
  FormGroup,
  FormControlLabel,
  Checkbox,
} from '@mui/material'
import { format, startOfWeek, endOfWeek, eachDayOfInterval, isSameDay, parseISO } from 'date-fns'
import { fr } from 'date-fns/locale'
import VisibilityIcon from '@mui/icons-material/Visibility'
import RouteIcon from '@mui/icons-material/Route'
import EventRepeatIcon from '@mui/icons-material/EventRepeat'
import CalendarTodayIcon from '@mui/icons-material/CalendarToday'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import { visitService } from '../../services/visitService'
import { pharmacyService } from '../../services/pharmacyService'
import { userService } from '../../services/userService'
import { visitReportService } from '../../services/visitReportService'
import { authService } from '../../services/authService'
import { planningService } from '../../services/planningService'
import { useNotifier } from '../../hooks/useNotifier'

/** Prépare PUT pharmacie : vide la prochaine visite ; retire le RDV fixe s’il tombait ce jour. */
function buildClearPlanningDayPayload(pharmacy, dayIso) {
  const payload = {
    next_visit_date: null,
    planning_manual_override: false,
  }
  const h = pharmacy?.planning_hard_rdv_date
  if (h && String(h).trim().slice(0, 10) === dayIso) {
    payload.planning_hard_rdv_date = null
  }
  return payload
}

function Planning() {
  const location = useLocation()
  const navigate = useNavigate()
  const { notify, dismiss, NotifierSnackbar } = useNotifier()
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

  const [currentUser, setCurrentUser] = useState(null)
  const [planningDialogOpen, setPlanningDialogOpen] = useState(false)
  const [planningHorizon, setPlanningHorizon] = useState(7)
  const [planningBusy, setPlanningBusy] = useState(false)
  /**
   * Admin — filtre d’affichage de la grille : null = tous ; [] = aucun ; sinon liste d’UUID.
   * Non pertinent pour le rôle commercial (filtré côté liste sur `currentUser.id`).
   */
  const [adminVisibleCommercialIds, setAdminVisibleCommercialIds] = useState(null)
  /**
   * Admin — périmètre dans le dialogue de recalcul : null = tous les commerciaux ; liste explicite = sous-ensemble ; [] invalide avant envoi.
   */
  const [planningDialogCommercialIds, setPlanningDialogCommercialIds] = useState(null)
  /** Suppression massive du planning pour un jour civile donné */
  const [clearingPlanningDay, setClearingPlanningDay] = useState(false)

  useEffect(() => {
    fetchData()
  }, [selectedDate, tabValue])

  useEffect(() => {
    let cancelled = false
    authService
      .getCurrentUser()
      .then((data) => {
        // GET /auth/me renvoie { user: { id, role, ... } }, pas le user à la racine
        const u = data?.user ?? data ?? null
        if (!cancelled) setCurrentUser(u)
      })
      .catch(() => {
        if (!cancelled) setCurrentUser(null)
      })
    return () => {
      cancelled = true
    }
  }, [])
  
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

  const sortedCommercialsForFilter = useMemo(
    () =>
      [...commercials].sort((a, b) =>
        `${a.first_name || ''} ${a.last_name || ''}`.localeCompare(
          `${b.first_name || ''} ${b.last_name || ''}`,
          'fr',
          { sensitivity: 'base' },
        ),
      ),
    [commercials],
  )

  const visiblePlanningItems = useMemo(() => {
    const list = pharmaciesWithNextVisit
    const role = (currentUser?.role ?? '').toString().toLowerCase().trim()

    if (role === 'commercial' && currentUser?.id) {
      return list.filter((item) => String(item.commercialId) === String(currentUser.id))
    }

    if (role === 'admin') {
      if (adminVisibleCommercialIds === null) {
        return list
      }
      return list.filter((item) =>
        adminVisibleCommercialIds.includes(String(item.commercialId)),
      )
    }

    return list
  }, [pharmaciesWithNextVisit, currentUser?.role, currentUser?.id, adminVisibleCommercialIds])

  const isAdminCommercialFilterChecked = useCallback(
    (commercialUuid) => {
      const sid = String(commercialUuid)
      if (adminVisibleCommercialIds === null) return true
      return adminVisibleCommercialIds.includes(sid)
    },
    [adminVisibleCommercialIds],
  )

  const toggleAdminCommercialFilter = useCallback(
    (commercialUuid) => {
      const sid = String(commercialUuid)
      setAdminVisibleCommercialIds((prev) => {
        const allIds = sortedCommercialsForFilter.map((c) => String(c.id))
        const currentSet = new Set(prev === null ? allIds : prev)
        if (currentSet.has(sid)) {
          currentSet.delete(sid)
        } else {
          currentSet.add(sid)
        }
        return Array.from(currentSet)
      })
    },
    [sortedCommercialsForFilter],
  )

  const openPlanningDialog = useCallback(() => {
    const role = (currentUser?.role ?? '').toString().toLowerCase().trim()
    if (role === 'admin') {
      const allIds = sortedCommercialsForFilter.map((c) => String(c.id))
      if (adminVisibleCommercialIds === null) {
        setPlanningDialogCommercialIds(null)
      } else {
        const filtered = adminVisibleCommercialIds.filter((id) => allIds.includes(id))
        setPlanningDialogCommercialIds(filtered.length ? filtered : [])
      }
    }
    setPlanningDialogOpen(true)
  }, [currentUser?.role, adminVisibleCommercialIds, sortedCommercialsForFilter])

  const handlePlanningDialogCommercialChange = useCallback(
    (e) => {
      const ALL = sortedCommercialsForFilter.map((c) => String(c.id))
      const raw = e.target.value
      const next = typeof raw === 'string' ? raw.split(',') : [...raw].map(String)
      if (!next.length) {
        setPlanningDialogCommercialIds([])
        return
      }
      const allSelected =
        ALL.length > 0 &&
        ALL.length === next.length &&
        ALL.every((id) => next.includes(id))
      setPlanningDialogCommercialIds(allSelected ? null : next)
    },
    [sortedCommercialsForFilter],
  )

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

  const getPhotoPreviewUrl = (pharmacy, size = 64) => {
    const seed = encodeURIComponent(pharmacy.id ?? pharmacy.name ?? 'pharmacy-photo')
    return pharmacy.photo_url || `https://picsum.photos/seed/${seed}/${size}/${size}`
  }

  /** Pop-ups bloquées : proposer l’ouverture dans le même onglet (snackbar avec actions). */
  const promptOpenMapsInThisTab = (url) => {
    notify(
      'Les fenêtres pop-up sont bloquées ou indisponibles. Ouvrir l’itinéraire Google Maps dans cet onglet ?',
      'warning',
      {
        action: (
          <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', flexShrink: 0 }}>
            <Button color="inherit" size="small" onClick={() => dismiss()}>
              Annuler
            </Button>
            <Button
              color="inherit"
              size="small"
              variant="outlined"
              sx={{
                borderColor: 'rgba(255,255,255,0.65)',
                color: 'inherit',
                '&:hover': { borderColor: 'rgba(255,255,255,0.9)' },
              }}
              onClick={() => {
                dismiss()
                window.location.href = url
              }}
            >
              Ouvrir ici
            </Button>
          </Box>
        ),
      },
    )
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
        notify(
          'Aucune pharmacie avec coordonnées géographiques ou adresse complète trouvée pour générer l’itinéraire.',
          'warning',
        )
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
          promptOpenMapsInThisTab(url)
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
        notify(
          `Google Maps limite à 25 points : seules les 25 premières pharmacies sur ${optimizedRoute.length} sont incluses dans l’itinéraire.`,
          'warning',
        )
      }
      
      console.log('URL Google Maps:', url)
      console.log('Nombre de pharmacies:', optimizedRoute.length)
      console.log('Mode de transport:', travelMode)
      
      // Vérifier que l'URL est valide
      if (!url || url.length === 0) {
        notify('Impossible de générer l’URL de l’itinéraire.', 'error')
        setRouteMenuAnchor(null)
        return
      }
      
      // Ouvrir dans un nouvel onglet
      try {
        const newWindow = window.open(url, '_blank', 'noopener,noreferrer')
        if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
          promptOpenMapsInThisTab(url)
        }
      } catch (error) {
        console.error('Erreur lors de l\'ouverture de la fenêtre:', error)
        promptOpenMapsInThisTab(url)
      }
      setRouteMenuAnchor(null)
    } catch (error) {
      console.error('Erreur lors de la génération de l\'itinéraire:', error)
      notify('Erreur lors de la génération de l’itinéraire. Veuillez réessayer.', 'error')
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

  const handlePlanningRun = async (dryRun) => {
    const hz = Math.min(60, Math.max(1, Number(planningHorizon) || 7))
    const role = (currentUser?.role ?? '').toString().toLowerCase().trim()
    if (role === 'admin') {
      if (!sortedCommercialsForFilter.length) {
        notify('Aucun commercial disponible pour le planning.', 'warning')
        return
      }
      if (Array.isArray(planningDialogCommercialIds) && planningDialogCommercialIds.length === 0) {
        notify(
          'Sélectionnez au moins un commercial dans la liste déroulante du recalcul.',
          'warning',
        )
        return
      }
    }
    try {
      setPlanningBusy(true)
      const payload = {
        horizon_days: hz,
        dry_run: dryRun,
        pharmacy_status_actif_only: true,
      }
      if (
        role === 'admin' &&
        planningDialogCommercialIds !== null &&
        planningDialogCommercialIds.length > 0
      ) {
        payload.commercial_ids = planningDialogCommercialIds
      }
      const res = await planningService.run(payload)
      if (dryRun) {
        const n = res.planned_count ?? 0
        const sk = res.skipped_manual_override_count ?? 0
        notify(
          `Prévisualisation : ${n} pharmacie(s) replanifiée(s) (hors ${sk} en ajustement manuel). Détails dans la console (F12).`,
          'info',
        )
        console.info('Planning preview', res)
      } else {
        notify(
          `Planning appliqué : ${res.updated_count ?? 0} date(s) mise(s) à jour. ${res.skipped_manual_override_count ?? 0} fiche(s) ignorée(s) (verrou manuel).`,
          'success',
        )
        await fetchData()
      }
      if (!dryRun) setPlanningDialogOpen(false)
    } catch (e) {
      console.error(e)
      const d = e?.response?.data?.detail
      let msg
      if (Array.isArray(d)) {
        msg = d.map((x) => x.msg || JSON.stringify(x)).join(' ; ')
      } else if (typeof d === 'string') {
        msg = d
      } else if (d && typeof d === 'object') {
        msg = JSON.stringify(d)
      } else {
        msg = e?.message || 'Erreur inconnue'
      }
      notify(msg, 'error')
    } finally {
      setPlanningBusy(false)
    }
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
        notify('Date invalide. Veuillez vérifier la date saisie.', 'warning')
        return
      }

      await pharmacyService.update(selectedPharmacyForReplanify.pharmacy.id, {
        next_visit_date: dateObj.toISOString(),
        planning_manual_override: true,
      })
      // Rafraîchir les données
      await fetchData()
      handleReplanifyClose()
      notify('Date de prochaine visite mise à jour.', 'success')
    } catch (error) {
      console.error('Error updating visit date:', error)
      notify('Erreur lors de la mise à jour de la date de visite.', 'error')
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
    return visiblePlanningItems.filter((item) => {
      if (!item.nextVisitDate) return false
      const visitDate = new Date(item.nextVisitDate)
      return isSameDay(visitDate, date)
    })
  }

  const executeClearPlanningForDay = async (items, dayDate) => {
    const dayIso = format(dayDate, 'yyyy-MM-dd')
    setClearingPlanningDay(true)
    try {
      await Promise.all(
        items.map((item) =>
          pharmacyService.update(item.pharmacy.id, buildClearPlanningDayPayload(item.pharmacy, dayIso)),
        ),
      )
      notify(
        `Planning du ${format(dayDate, 'dd/MM/yyyy')} effacé pour ${items.length} pharmacie${items.length > 1 ? 's' : ''}.`,
        'success',
      )
      await fetchData()
    } catch (e) {
      console.error(e)
      notify('Erreur lors de la suppression du planning pour ce jour.', 'error')
    } finally {
      setClearingPlanningDay(false)
    }
  }

  const promptClearPlanningForDay = (dayDate) => {
    const items = getPharmaciesForDate(dayDate)
    if (items.length === 0) {
      notify('Aucune visite planifiée ce jour.', 'info')
      return
    }
    const n = items.length
    const dayLabel = format(dayDate, 'EEEE dd/MM/yyyy', { locale: fr })
    notify(
      `Retirer la prochaine visite pour ${n} pharmacie${n > 1 ? 's' : ''} (${dayLabel}) ? ` +
        'Les dates seront réinitialisées ; un éventuel jour de RDV fixe tombant ce jour sera aussi retiré.',
      'warning',
      {
        action: (
          <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', flexShrink: 0 }}>
            <Button color="inherit" size="small" onClick={() => dismiss()}>
              Annuler
            </Button>
            <Button
              color="inherit"
              size="small"
              variant="outlined"
              sx={{
                borderColor: 'rgba(255,255,255,0.65)',
                color: 'inherit',
                '&:hover': { borderColor: 'rgba(255,255,255,0.9)' },
              }}
              disabled={clearingPlanningDay}
              onClick={() => {
                dismiss()
                void executeClearPlanningForDay(items, dayDate)
              }}
            >
              Confirmer
            </Button>
          </Box>
        ),
      },
    )
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
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
          <Button
            size="small"
            color="error"
            variant="outlined"
            startIcon={<DeleteOutlineIcon />}
            disabled={clearingPlanningDay}
            onClick={() => promptClearPlanningForDay(new Date())}
          >
            Effacer le planning du jour
          </Button>
        </Box>
      <Grid container spacing={2} sx={{ mt: 0 }}>
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
                  <Box display="flex" justifyContent="space-between" alignItems="start" gap={1}>
                    <Box display="flex" gap={1} alignItems="flex-start" sx={{ flex: 1 }}>
                      <Tooltip title={`Photo de ${item.pharmacy.name}`}>
                        <Avatar
                          src={getPhotoPreviewUrl(item.pharmacy, 72)}
                          alt={`Photo de ${item.pharmacy.name}`}
                          sx={{ width: 64, height: 64 }}
                        />
                      </Tooltip>
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
      </Box>
    )
  }

  const renderDayView = () => {
    const dayPharmacies = getPharmaciesForDate(selectedDate)
    
    return (
      <Box>
        <Box
          sx={{
            mb: 3,
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 2,
          }}
        >
          <Box>
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
          {dayPharmacies.length > 0 ? (
            <Tooltip title={`Retire la prochaine visite pour les ${dayPharmacies.length} pharmacie(s) affichée(s) ce jour`}>
              <Button
                size="small"
                color="error"
                variant="outlined"
                startIcon={<DeleteOutlineIcon />}
                disabled={clearingPlanningDay}
                onClick={() => promptClearPlanningForDay(selectedDate)}
              >
                Effacer cette journée
              </Button>
            </Tooltip>
          ) : null}
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
                  <Box display="flex" justifyContent="space-between" alignItems="start" gap={1}>
                    <Box display="flex" gap={1} alignItems="flex-start" sx={{ flex: 1 }}>
                      <Tooltip title={`Photo de ${item.pharmacy.name}`}>
                        <Avatar
                          src={getPhotoPreviewUrl(item.pharmacy, 64)}
                          alt={`Photo de ${item.pharmacy.name}`}
                          sx={{ width: 56, height: 56 }}
                        />
                      </Tooltip>
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
                    <Box
                      display="flex"
                      justifyContent="space-between"
                      alignItems="flex-start"
                      gap={1}
                      sx={{ mb: dayPharmacies.length === 0 ? 0 : 2 }}
                    >
                      <Typography variant="h6" component="div" sx={{ flex: 1 }}>
                        {format(day, 'EEEE dd/MM', { locale: fr })}
                        {isToday ? (
                          <Chip label="Aujourd'hui" size="small" color="primary" sx={{ ml: 1 }} />
                        ) : null}
                      </Typography>
                      {dayPharmacies.length > 0 ? (
                        <Tooltip title="Effacer les prochaines visites prévues ce jour (pharmacies affichées)">
                          <IconButton
                            size="small"
                            color="error"
                            aria-label={`Effacer le planning du ${format(day, 'yyyy-MM-dd')}`}
                            disabled={clearingPlanningDay}
                            onClick={(e) => {
                              e.stopPropagation()
                              promptClearPlanningForDay(day)
                            }}
                          >
                            <DeleteOutlineIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      ) : null}
                    </Box>
                    
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
                              <Box display="flex" alignItems="center" gap={1}>
                                <Tooltip title={`Photo de ${item.pharmacy.name}`}>
                                  <Avatar
                                    src={getPhotoPreviewUrl(item.pharmacy, 48)}
                                    alt={`Photo de ${item.pharmacy.name}`}
                                    sx={{ width: 40, height: 40 }}
                                  />
                                </Tooltip>
                                <Typography variant="body2" fontWeight="medium">
                                  {formatTime(item.nextVisitDate)} - {item.pharmacy.name}
                                </Typography>
                              </Box>
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

  const planningUserRole = (currentUser?.role ?? '').toString().toLowerCase().trim()
  const canUseAutoPlanning =
    planningUserRole === 'admin' || planningUserRole === 'commercial'

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} flexWrap="wrap" gap={1}>
        <Typography variant="h4">
          Planning des Visites
        </Typography>
        <Box display="flex" alignItems="center" gap={1} flexWrap="wrap" justifyContent="flex-end">
          {canUseAutoPlanning && (
            <Tooltip title="Recalcule les prochaines visites selon les règles Digestic (sauf fiches verrouillées manuellement)">
              <Button
                variant="outlined"
                onClick={openPlanningDialog}
                disabled={planningBusy}
              >
                Recalcul automatique
              </Button>
            </Tooltip>
          )}
          {visiblePlanningItems.length > 0 && (() => {
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
      </Box>

      {planningUserRole === 'admin' && sortedCommercialsForFilter.length > 0 ? (
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Afficher le planning pour
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 1.5 }} display="block">
            Cochez les commerciaux dont les visites à venir apparaissent ci-dessous. Par défaut, tous sont
            affichés.
          </Typography>
          <Box display="flex" flexWrap="wrap" gap={1} sx={{ mb: 2 }}>
            <Button
              size="small"
              variant="outlined"
              onClick={() => setAdminVisibleCommercialIds(null)}
            >
              Tout sélectionner
            </Button>
            <Button
              size="small"
              variant="outlined"
              onClick={() => setAdminVisibleCommercialIds([])}
            >
              Tout désélectionner
            </Button>
          </Box>
          <FormGroup row sx={{ flexWrap: 'wrap', gap: 0.5, columnGap: 2 }}>
            {sortedCommercialsForFilter.map((c) => {
              const sid = String(c.id)
              const label = `${c.first_name || ''} ${c.last_name || ''}`.trim() || sid
              return (
                <FormControlLabel
                  key={sid}
                  control={
                    <Checkbox
                      size="small"
                      checked={isAdminCommercialFilterChecked(sid)}
                      onChange={() => toggleAdminCommercialFilter(sid)}
                    />
                  }
                  label={label}
                  sx={{ mr: 1 }}
                />
              )
            })}
          </FormGroup>
        </Paper>
      ) : null}

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

      <Dialog open={planningDialogOpen} onClose={() => !planningBusy && setPlanningDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Recalcul automatique du planning</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Les pharmacies avec un ajustement manuel (<em>override</em>) ne sont pas modifiées. Les pharmacies sans
            commercial assigné ne sont jamais prises en compte.
            {planningUserRole === 'admin'
              ? ' Utilisez la liste ci-dessous pour cocher un ou plusieurs commerciaux, ou tous à la fois '
                + '(liste déroulante à choix multiples). À l’ouverture du dialogue, la sélection reflète vos cases '
                + '« Afficher le planning pour » ; les deux boutons raccourcis permettent de tout sélectionner ou '
                + 'de tout désélectionner.'
              : ' Portée : votre portefeuille uniquement.'}
          </Typography>
          {planningUserRole === 'admin' &&
            (sortedCommercialsForFilter.length > 0 ? (
              <>
                <FormControl fullWidth size="small" sx={{ mb: 1 }}>
                  <InputLabel id="planning-run-commercials-label">
                    Commerciaux concernés par le recalcul
                  </InputLabel>
                  <Select
                    labelId="planning-run-commercials-label"
                    id="planning-run-commercials-multiple"
                    multiple
                    value={
                      planningDialogCommercialIds === null
                        ? sortedCommercialsForFilter.map((c) => String(c.id))
                        : planningDialogCommercialIds
                    }
                    onChange={handlePlanningDialogCommercialChange}
                    input={<OutlinedInput label="Commerciaux concernés par le recalcul" />}
                    renderValue={(selected) => {
                      const allLen = sortedCommercialsForFilter.length
                      const selArr = [...selected].map(String)
                      if (
                        planningDialogCommercialIds === null ||
                        (allLen > 0 && selArr.length === allLen)
                      ) {
                        return 'Tous les commerciaux'
                      }
                      if (!selArr.length) return 'Aucune sélection'
                      const labelOne = (id) => {
                        const c = sortedCommercialsForFilter.find((x) => String(x.id) === id)
                        return (
                          (c ? `${c.first_name || ''} ${c.last_name || ''}`.trim() : '') || String(id)
                        )
                      }
                      if (selArr.length <= 2) return selArr.map(labelOne).join(', ')
                      return `${selArr.length} commerciaux sélectionnés`
                    }}
                    MenuProps={{
                      PaperProps: { sx: { maxHeight: 320 } },
                      disableAutoFocusItem: true,
                    }}
                  >
                    {sortedCommercialsForFilter.map((c) => {
                      const sid = String(c.id)
                      const nm = `${c.first_name || ''} ${c.last_name || ''}`.trim() || sid
                      const checked =
                        planningDialogCommercialIds === null ||
                        planningDialogCommercialIds.includes(sid)
                      return (
                        <MenuItem key={sid} value={sid} dense sx={{ gap: 0.5 }}>
                          <Checkbox
                            size="small"
                            checked={checked}
                            tabIndex={-1}
                            sx={{ mr: 0.5, pointerEvents: 'none' }}
                          />
                          {nm}
                        </MenuItem>
                      )
                    })}
                  </Select>
                </FormControl>
                <Box display="flex" flexWrap="wrap" gap={0.75} sx={{ mb: 2 }}>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => setPlanningDialogCommercialIds(null)}
                  >
                    Tous les commerciaux
                  </Button>
                  <Button size="small" variant="outlined" onClick={() => setPlanningDialogCommercialIds([])}>
                    Aucun
                  </Button>
                </Box>
              </>
            ) : (
              <Typography variant="body2" color="warning.main" sx={{ mb: 2 }}>
                Aucun commercial disponible dans l’application.
              </Typography>
            ))}
          <TextField
            label="Horizon (jours)"
            type="number"
            fullWidth
            size="small"
            inputProps={{ min: 1, max: 60 }}
            value={planningHorizon}
            onChange={(ev) => setPlanningHorizon(ev.target.value)}
            sx={{ mb: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPlanningDialogOpen(false)} disabled={planningBusy}>
            Fermer
          </Button>
          <Button
            onClick={() => handlePlanningRun(true)}
            disabled={planningBusy}
          >
            {planningBusy ? <CircularProgress size={20} /> : 'Prévisualiser'}
          </Button>
          <Button
            variant="contained"
            onClick={() => {
              notify(
                'Appliquer le planning automatique aux dates « prochaine visite » en base ?',
                'warning',
                {
                  action: (
                    <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', flexShrink: 0 }}>
                      <Button color="inherit" size="small" onClick={() => dismiss()}>
                        Annuler
                      </Button>
                      <Button
                        color="inherit"
                        size="small"
                        variant="outlined"
                        sx={{
                          borderColor: 'rgba(255,255,255,0.65)',
                          color: 'inherit',
                          '&:hover': { borderColor: 'rgba(255,255,255,0.9)' },
                        }}
                        onClick={() => {
                          dismiss()
                          void handlePlanningRun(false)
                        }}
                      >
                        Confirmer
                      </Button>
                    </Box>
                  ),
                },
              )
            }}
            disabled={planningBusy}
            color="primary"
          >
            Appliquer
          </Button>
        </DialogActions>
      </Dialog>

      {NotifierSnackbar}
    </Box>
  )
}

export default Planning

