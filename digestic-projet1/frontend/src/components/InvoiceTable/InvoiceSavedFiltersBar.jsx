import React from 'react'
import { SavedFiltersBar } from '../SavedFiltersBar/SavedFiltersBar'
import { getInvoiceSavedFiltersClient } from '../../services/savedListFiltersApi'

/**
 * Filtres enregistrés (vue `invoices`).
 * @param {object} p — voir `SavedFiltersBar`
 */
export function InvoiceSavedFiltersBar(props) {
  return (
    <SavedFiltersBar
      filterClient={getInvoiceSavedFiltersClient()}
      storageKeyExpanded="invoiceSavedFiltersBarExpanded"
      sectionTitle="Filtres enregistrés (factures)"
      {...props}
    />
  )
}
