import React from 'react'
import {
  Avatar,
  Box,
  Chip,
  IconButton,
  InputAdornment,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import ClearIcon from '@mui/icons-material/Clear'
import { AlignedTableCell } from '../ResizableTableColumns/ResizableHeaderCell'
import { getPharmacyStatusLabel } from '../../constants/pharmacyStatus'

/**
 * @param {object} p
 * @param {string} p.columnKey
 * @param {object} p.pharmacy
 * @param {Record<string, number>} p.fullWidths
 * @param {object} p.ctx
 * @returns {React.ReactNode}
 */
export function PharmacyTableBodyCell(p) {
  const {
    columnKey,
    pharmacy,
    fullWidths,
    ctx,
  } = p
  const w = fullWidths[columnKey] ?? 80
  if (columnKey === 'name') {
    return (
      <AlignedTableCell width={w} contentSx={{ overflow: 'visible' }}>
        <Box display="flex" alignItems="center" gap={1} sx={{ minWidth: 0 }}>
          <Tooltip title={`Photo de ${pharmacy.name}`}>
            <Avatar
              src={ctx.getPhotoPreviewUrl(pharmacy, 120)}
              alt={pharmacy.name}
              sx={{ width: 48, height: 48, flexShrink: 0 }}
            />
          </Tooltip>
          <Typography variant="body1" fontWeight="medium" noWrap title={pharmacy.name}>
            {pharmacy.name}
          </Typography>
        </Box>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'address') {
    return (
      <AlignedTableCell width={w}>
        <Typography
          variant="body2"
          noWrap
          title={`${pharmacy.address}, ${pharmacy.postal_code} ${pharmacy.city}`}
        >
          {pharmacy.address}, {pharmacy.postal_code} {pharmacy.city}
        </Typography>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'nextVisit') {
    return <NextVisitCell pharmacy={pharmacy} fullWidth={w} ctx={ctx} />
  }
  if (columnKey === 'status') {
    return (
      <AlignedTableCell width={w}>
        <Chip
          label={getPharmacyStatusLabel(pharmacy.status)}
          color={pharmacy.status === 'actif' ? 'success' : 'default'}
          size="small"
          variant="outlined"
        />
      </AlignedTableCell>
    )
  }
  if (columnKey === 'rib') {
    return (
      <AlignedTableCell width={w}>
        <Chip
          label={pharmacy.rib ? 'Oui' : 'Non'}
          color={pharmacy.rib ? 'success' : 'default'}
          size="small"
        />
      </AlignedTableCell>
    )
  }
  if (columnKey === 'commercial') {
    return <AlignedTableCell width={w}>{pharmacy.commercialName || '-'}</AlignedTableCell>
  }
  if (columnKey === 'depot') {
    const name = (pharmacy.depot_name || '').trim()
    return (
      <AlignedTableCell width={w} sx={{ minWidth: 0 }}>
        <Typography variant="body2" noWrap title={name || undefined}>
          {name || '—'}
        </Typography>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'lastVisit') {
    return (
      <AlignedTableCell width={w} sx={{ whiteSpace: 'nowrap' }}>
        {ctx.formatDate(pharmacy.lastVisitDate)}
      </AlignedTableCell>
    )
  }
  if (columnKey === 'createdAt') {
    return (
      <AlignedTableCell width={w} sx={{ whiteSpace: 'nowrap' }}>
        {ctx.formatDate(pharmacy.created_at)}
      </AlignedTableCell>
    )
  }
  const textMap = {
    city: pharmacy.city,
    postalCode: pharmacy.postal_code,
    country: pharmacy.country,
    email: pharmacy.email,
    phone: pharmacy.phone,
    pharmacistName: pharmacy.pharmacist_name,
    paymentMode: pharmacy.payment_mode,
  }
  if (Object.prototype.hasOwnProperty.call(textMap, columnKey)) {
    return (
      <AlignedTableCell width={w}>
        <Typography variant="body2" noWrap>
          {textMap[columnKey] || '-'}
        </Typography>
      </AlignedTableCell>
    )
  }
  return <AlignedTableCell width={w} />
}

function NextVisitCell({ pharmacy, fullWidth, ctx }) {
  const {
    editingNextVisitId,
    editingNextVisitValue,
    handleNextVisitClick,
    handleNextVisitChange,
    handleNextVisitSave,
    handleNextVisitKeyDown,
    setShouldSaveOnBlur,
    setEditingNextVisitValue,
    formatDate,
  } = ctx
  return (
    <AlignedTableCell
      width={fullWidth}
      sx={{ cursor: 'pointer', whiteSpace: 'nowrap' }}
      onClick={(e) => {
        e.stopPropagation()
        if (editingNextVisitId !== pharmacy.id) {
          handleNextVisitClick(pharmacy)
        }
      }}
    >
      <Box
        sx={{
          position: 'relative',
          width: '100%',
          minHeight: 32,
          '&:hover': {
            backgroundColor: editingNextVisitId === pharmacy.id ? 'transparent' : 'action.hover',
          },
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
              fullWidth
              InputLabelProps={{ shrink: true }}
              inputProps={{ style: { fontSize: '14px' } }}
              sx={{
                maxWidth: '100%',
                '& .MuiOutlinedInput-root': { paddingRight: '8px' },
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
      </Box>
    </AlignedTableCell>
  )
}
