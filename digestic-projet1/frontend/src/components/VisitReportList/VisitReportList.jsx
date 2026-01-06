import React, { useEffect, useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Typography,
  CircularProgress,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from '@mui/material'
import { format } from 'date-fns'
import { visitReportService } from '../../services/visitReportService'

function VisitReportList({ open, onClose, pharmacyId, pharmacyName, onSelectReport }) {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (open) {
      fetchReports()
    }
  }, [open, pharmacyId])

  const fetchReports = async () => {
    try {
      setLoading(true)
      const params = pharmacyId ? { pharmacy_id: pharmacyId } : {}
      const data = await visitReportService.getAll(params)
      
      // Trier par date décroissante (plus récent en premier)
      const sorted = data.sort((a, b) => 
        new Date(b.visit_date) - new Date(a.visit_date)
      )
      setReports(sorted)
    } catch (error) {
      console.error('Error fetching visit reports:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    try {
      return format(new Date(dateString), 'dd/MM/yyyy HH:mm')
    } catch {
      return dateString
    }
  }

  const getStatusChip = (report) => {
    if (report.visit_status === 'completed') {
      return <Chip label="Effectuée" color="success" size="small" />
    } else {
      const reason = report.visit_not_completed_reason === 'pharmacy_closed' 
        ? 'Pharmacie fermée' 
        : report.visit_not_completed_reason === 'owner_absent'
        ? 'Titulaire absent'
        : 'Non effectuée'
      return <Chip label={reason} color="error" size="small" />
    }
  }

  const handleReportClick = (report) => {
    if (onSelectReport) {
      onSelectReport(report)
    }
  }

  const getDialogTitle = () => {
    if (pharmacyName) {
      return `Rapports de visite - ${pharmacyName}`
    }
    return 'Rapports de visite'
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle sx={{ pb: 2 }}>
        <Typography variant="h5" component="div" fontWeight="bold">
          {getDialogTitle()}
        </Typography>
      </DialogTitle>
      <DialogContent>
        {loading ? (
          <Box display="flex" justifyContent="center" p={3}>
            <CircularProgress />
          </Box>
        ) : reports.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
            {pharmacyId ? 'Aucun rapport de visite pour cette pharmacie' : 'Aucun rapport de visite'}
          </Typography>
        ) : (
          <TableContainer component={Paper} elevation={0} sx={{ maxHeight: '70vh' }}>
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>
                    Date de visite
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>
                    Statut
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>
                    Dépôt
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>
                    Notes
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {reports.map((report) => (
                  <TableRow
                    key={report.id}
                    onClick={() => handleReportClick(report)}
                    sx={{
                      cursor: 'pointer',
                      '&:hover': {
                        backgroundColor: '#f0f7ff',
                        transform: 'scale(1.01)',
                        transition: 'all 0.2s ease-in-out',
                      },
                      transition: 'all 0.2s ease-in-out',
                    }}
                  >
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {formatDate(report.visit_date)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {getStatusChip(report)}
                    </TableCell>
                    <TableCell>
                      {report.has_deposit ? (
                        <Box>
                          <Typography variant="body2" color="success.main" fontWeight="medium">
                            {report.bottles_deposited} bouteilles
                          </Typography>
                          {report.free_units > 0 && (
                            <Typography variant="caption" color="text.secondary">
                              {report.free_units} UG
                            </Typography>
                          )}
                        </Box>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          Aucun dépôt
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography 
                        variant="body2" 
                        color="text.secondary"
                        sx={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          maxWidth: '200px',
                        }}
                      >
                        {report.notes || '-'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default VisitReportList


