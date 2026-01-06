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
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EventNoteIcon from '@mui/icons-material/EventNote'
import { visitService } from '../../services/visitService'
import { format } from 'date-fns'

function Visits() {
  const [visits, setVisits] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    fetchVisits()
  }, [])

  const fetchVisits = async () => {
    try {
      setLoading(true)
      const data = await visitService.getAll()
      setVisits(data)
    } catch (error) {
      console.error('Error fetching visits:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      planned: 'info',
      completed: 'success',
      cancelled: 'error',
      postponed: 'warning',
    }
    return colors[status] || 'default'
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    try {
      return format(new Date(dateString), 'dd/MM/yyyy')
    } catch {
      return dateString
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
        <Typography variant="h4">Visites</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/visits/new')}
        >
          Nouvelle Visite
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Pharmacie</TableCell>
              <TableCell>Commercial</TableCell>
              <TableCell>Statut</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {visits.map((visit) => (
              <TableRow key={visit.id} hover>
                <TableCell>{formatDate(visit.scheduled_date)}</TableCell>
                <TableCell>{visit.pharmacy_id}</TableCell>
                <TableCell>{visit.commercial_id}</TableCell>
                <TableCell>
                  <Chip
                    label={visit.status}
                    color={getStatusColor(visit.status)}
                    size="small"
                  />
                </TableCell>
                <TableCell align="right">
                  {visit.status === 'planned' && (
                    <IconButton
                      size="small"
                      onClick={() => navigate(`/visits/report/${visit.id}`)}
                    >
                      <EventNoteIcon />
                    </IconButton>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

export default Visits

