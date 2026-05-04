import { PHARM_TABLE_PX_STORAGE_V } from './pharmacyTableMinWidths'

export const DELIVERY_NOTE_COLUMN_MIN_PX = {
  pharmacyName: 160,
  deliveryDate: 112,
  blNumber: 128,
  bottlesCount: 88,
  freeUnits: 72,
  commercial: 120,
  status: 96,
  linkedInvoices: 120,
  isDepositSale: 96,
  sageReference: 100,
  depositId: 120,
  emailSent: 88,
}

export const DELIVERY_NOTE_TABLE_ACTIONS_PX = 340

/** Colonne case à cocher (sélection facturation groupée). */
export const DELIVERY_NOTE_SELECT_COL_PX = 52

export { PHARM_TABLE_PX_STORAGE_V as DELIVERY_NOTE_TABLE_PX_STORAGE_V }
