import React from 'react'
import { SavedFiltersBar } from '../SavedFiltersBar/SavedFiltersBar'
import { getDeliveryNotesSavedFiltersClient } from '../../services/savedListFiltersApi'

export function DeliveryNoteSavedFiltersBar(props) {
  return (
    <SavedFiltersBar
      filterClient={getDeliveryNotesSavedFiltersClient()}
      storageKeyExpanded="deliveryNoteSavedFiltersBarExpanded"
      sectionTitle="Filtres enregistrés (bons de livraison)"
      {...props}
    />
  )
}
