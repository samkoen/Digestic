import React from 'react'
import { SavedFiltersBar } from '../SavedFiltersBar/SavedFiltersBar'
import { getPharmacySavedFiltersClient } from '../../services/savedListFiltersApi'

/**
 * Barre « Filtres enregistrés » pour la page Pharmacies (client API pharmacies).
 * @param {object} p — voir SavedFiltersBar
 */
export function PharmacySavedFiltersBar(props) {
  return (
    <SavedFiltersBar
      filterClient={getPharmacySavedFiltersClient()}
      storageKeyExpanded="pharmacySavedFiltersBarExpanded"
      {...props}
    />
  )
}
