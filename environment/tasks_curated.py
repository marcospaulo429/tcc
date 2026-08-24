"""Pool curado D4b/D5 (gerado por d5_chain.sh a partir de runs/v5_curation.json)."""
from environment import tasks_v4 as _v4, tasks_v5 as _v5

_SURV = ['h_cargo_manifest', 'h_customs_clearance', 'h_donation_matcher', 'h_hotel_folio', 'h_sku_validator', 'h_telco_roaming', 'h_turnstile_fsm', 'x_badge_gate', 'x_courier_dispatch', 'x_escrow_ledger', 'x_freight_zones', 'x_grant_allocator', 'x_hours_bank', 'x_loyalty_ledger', 'x_night_surcharge', 'x_parcel_locker', 'x_plate_validator', 'x_prepaid_meter', 'x_reactor_protocol', 'x_scale_barcode', 'x_vault_lock', 'x_vending_fsm']
_ALL = {t['task_id']: t for t in _v4.TASKS + _v5.TASKS}
TASKS = [_ALL[tid] for tid in _SURV]
STRATA = {tid: 'H' for tid in _SURV}
CRITICAL_CONSTANTS = {tid: (_v4.CRITICAL_CONSTANTS | _v5.CRITICAL_CONSTANTS).get(tid, []) for tid in _SURV}

def get_task(task_id: str) -> dict:
    return _ALL[task_id]
