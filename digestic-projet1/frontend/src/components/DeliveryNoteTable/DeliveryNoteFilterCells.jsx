import React from 'react'
import { Box, Checkbox, FormControlLabel, MenuItem, TextField, Typography } from '@mui/material'
import { AlignedTableCell } from '../ResizableTableColumns/ResizableHeaderCell'
import { PharmacyFilterCell } from '../PharmacyTable/PharmacyFilterCells'

const filterSx = { verticalAlign: 'top' }

const BL_STATUS = [
  { value: '', label: 'Tous' },
  { value: 'pending', label: 'En attente' },
  { value: 'validated', label: 'Validé (visite)' },
  { value: 'sent', label: 'Envoyé' },
  { value: 'confirmed', label: 'Confirmé' },
  { value: 'fully_invoiced', label: 'Facturé' },
  { value: 'draft', label: 'Brouillon' },
  { value: 'depot-vente', label: 'Dépôt-vente' },
]

const YES_NO = [
  { value: '', label: 'Tous' },
  { value: 'yes', label: 'Oui' },
  { value: 'no', label: 'Non' },
]

const EMAIL_SENT = [
  { value: '', label: 'Tous' },
  { value: 'yes', label: 'Envoyé' },
  { value: 'no', label: 'Non' },
]

/**
 * @param {object} p
 * @param {Array<{id: string, first_name: string, last_name: string}>} [p.commercials] — même forme que le tableau Pharmacies
 */
export function DeliveryNoteFilterCell(p) {
  const {
    columnKey,
    fullWidths,
    filters,
    onChange,
    definition = [],
    commercials = [],
  } = p
  const w = fullWidths[columnKey] ?? 80
  const def = definition.find((c) => c.key === columnKey)
  if (def && def.filterable === false) {
    return <AlignedTableCell width={w} dense sx={filterSx} />
  }
  if (columnKey === 'pharmacyName') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <TextField
          value={filters.pharmacyName}
          onChange={(e) => onChange('pharmacyName', e.target.value)}
          size="small"
          fullWidth
          placeholder="Nom pharmacie…"
        />
      </AlignedTableCell>
    )
  }
  if (columnKey === 'deliveryDate') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <TextField
          type="date"
          value={filters.deliveryDate}
          onChange={(e) => onChange('deliveryDate', e.target.value)}
          size="small"
          fullWidth
          label="Date"
          InputLabelProps={{ shrink: true }}
        />
      </AlignedTableCell>
    )
  }
  if (columnKey === 'commercial') {
    return (
      <PharmacyFilterCell
        columnKey="commercial"
        fullWidths={fullWidths}
        filters={filters}
        onChange={onChange}
        commercials={commercials}
      />
    )
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
        >
          {BL_STATUS.map((o) => (
            <MenuItem key={o.value || '_'} value={o.value}>
              {o.label}
            </MenuItem>
          ))}
        </TextField>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'depositId') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <TextField
          value={filters.depositId}
          onChange={(e) => onChange('depositId', e.target.value)}
          size="small"
          fullWidth
          placeholder="UUID dépôt…"
        />
        <FormControlLabel
          sx={{ mt: 0.5, alignItems: 'flex-start', ml: 0 }}
          control={(
            <Checkbox
              size="small"
              checked={Boolean(filters.includeArchived)}
              onChange={(e) => onChange('includeArchived', e.target.checked)}
            />
          )}
          label={<Typography variant="caption">Inclure clôturés</Typography>}
        />
      </AlignedTableCell>
    )
  }
  if (columnKey === 'sageReference') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <TextField
          value={filters.sageReference}
          onChange={(e) => onChange('sageReference', e.target.value)}
          size="small"
          fullWidth
          placeholder="Réf…"
        />
      </AlignedTableCell>
    )
  }
  if (columnKey === 'isDepositSale') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <TextField
          select
          value={filters.isDepositSale}
          onChange={(e) => onChange('isDepositSale', e.target.value)}
          size="small"
          fullWidth
        >
          {YES_NO.map((o) => (
            <MenuItem key={o.value || '_'} value={o.value}>
              {o.label}
            </MenuItem>
          ))}
        </TextField>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'emailSent') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <TextField
          select
          value={filters.emailSent}
          onChange={(e) => onChange('emailSent', e.target.value)}
          size="small"
          fullWidth
        >
          {EMAIL_SENT.map((o) => (
            <MenuItem key={o.value || '_'} value={o.value}>
              {o.label}
            </MenuItem>
          ))}
        </TextField>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'linkedInvoices') {
    return (
      <AlignedTableCell width={w} dense sx={filterSx}>
        <Box sx={{ opacity: 0.5, fontSize: '0.7rem' }}>—</Box>
      </AlignedTableCell>
    )
  }
  return <AlignedTableCell width={w} dense sx={filterSx} />
}
