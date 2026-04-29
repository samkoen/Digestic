import React from 'react'
import { TextField, MenuItem } from '@mui/material'
import { AlignedTableCell } from '../ResizableTableColumns/ResizableHeaderCell'

const filterSx = { verticalAlign: 'top' }

const STATUS_FILTER = [
  { value: '', label: 'Tous' },
  { value: 'pending', label: 'En attente' },
  { value: 'paid', label: 'Payé' },
  { value: 'overdue', label: 'En retard' },
  { value: 'cancelled', label: 'Annulé' },
]

/**
 * @param {object} p
 * @param {Array<{key: string, filterable: boolean}>} [p.definition]
 */
export function InvoiceFilterCell(p) {
  const { columnKey, fullWidths, filters, onChange, definition = [] } = p
  const w = fullWidths[columnKey] ?? 80
  const def = definition.find((c) => c.key === columnKey)
  if (def && def.filterable === false) {
    return <AlignedTableCell width={w} dense sx={filterSx} />
  }
  if (columnKey === 'status') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <TextField
          select
          value={filters.status}
          onChange={(e) => onChange('status', e.target.value)}
          size="small"
          fullWidth
          variant="outlined"
        >
          {STATUS_FILTER.map((o) => (
            <MenuItem key={o.value || '_'} value={o.value}>
              {o.label}
            </MenuItem>
          ))}
        </TextField>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'invoiceNumber') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <TextField
          value={filters.invoiceNumber}
          onChange={(e) => onChange('invoiceNumber', e.target.value)}
          size="small"
          fullWidth
          placeholder="N°…"
        />
      </AlignedTableCell>
    )
  }
  if (columnKey === 'pharmacyName') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <TextField
          value={filters.pharmacyName}
          onChange={(e) => onChange('pharmacyName', e.target.value)}
          size="small"
          fullWidth
          placeholder="Pharmacie…"
        />
      </AlignedTableCell>
    )
  }
  if (columnKey === 'blNumber') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <TextField
          value={filters.depositId}
          onChange={(e) => onChange('depositId', e.target.value)}
          size="small"
          fullWidth
          placeholder="N° BL ou UUID…"
        />
      </AlignedTableCell>
    )
  }
  return <AlignedTableCell width={w} dense sx={filterSx} />
}
