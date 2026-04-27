import React from 'react'
import DataTableColumnPickerDialog from '../DataTableColumnPickerDialog/DataTableColumnPickerDialog'

export default function InvoiceColumnPickerDialog(props) {
  return (
    <DataTableColumnPickerDialog
      title="Colonnes visibles (tableau Factures)"
      hint="Au moins une colonne. L'ordre d'affichage suit la liste ci-dessous."
      {...props}
    />
  )
}
