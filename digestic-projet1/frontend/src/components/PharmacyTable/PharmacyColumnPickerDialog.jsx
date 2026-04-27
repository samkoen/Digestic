import React from 'react'
import DataTableColumnPickerDialog from '../DataTableColumnPickerDialog/DataTableColumnPickerDialog'

/**
 * Sélecteur de colonnes du tableau Pharmacies (titre / texte adaptés).
 */
export default function PharmacyColumnPickerDialog(props) {
  return (
    <DataTableColumnPickerDialog
      title="Colonnes visibles (tableau Pharmacies)"
      hint="Au moins une colonne. L'ordre d'affichage suit la liste ci-dessous."
      {...props}
    />
  )
}
