import React from 'react'
import DataTableColumnPickerDialog from '../DataTableColumnPickerDialog/DataTableColumnPickerDialog'

export default function DeliveryNoteColumnPickerDialog(props) {
  return (
    <DataTableColumnPickerDialog
      title="Colonnes visibles (tableau Bons de livraison)"
      hint="Au moins une colonne. L'ordre d'affichage suit la liste ci-dessous."
      {...props}
    />
  )
}
