"""
Shipping Router
Shipping zone and rate management.
"""
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.customer import User
from app.models.features import ShippingZone
from app.schemas.features import (
    ShippingZone as ShippingZoneSchema,
    ShippingZoneCreate,
    ShippingZoneUpdate,
    ShippingEstimate,
)
from app.core.security import get_current_admin_user

router = APIRouter(prefix="/shipping", tags=["shipping"])


@router.get("/estimate")
def estimate_shipping(
    country: str = Query(..., max_length=2),
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    cart_total: Decimal = Query(..., ge=0),
    item_count: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    """Get shipping estimate for a location"""
    # Find matching shipping zone
    query = db.query(ShippingZone).filter(ShippingZone.is_active == True)

    # Find zone that contains this country
    zones = query.all()
    matching_zone = None

    for zone in zones:
        if country in zone.countries:
            # Check state match if specified
            if zone.states and state:
                if state not in zone.states:
                    continue
            # Check postal code if specified
            if zone.postal_codes and postal_code:
                if postal_code not in zone.postal_codes:
                    continue
            matching_zone = zone
            break

    if not matching_zone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shipping not available for this location"
        )

    # Calculate rate
    shipping_rate = matching_zone.base_rate + (matching_zone.per_item_rate * item_count)

    # Check free shipping threshold
    free_shipping = False
    if matching_zone.free_shipping_threshold and cart_total >= matching_zone.free_shipping_threshold:
        shipping_rate = Decimal("0")
        free_shipping = True

    # Format estimated days
    if matching_zone.estimated_days_min and matching_zone.estimated_days_max:
        estimated_days = f"{matching_zone.estimated_days_min}-{matching_zone.estimated_days_max} business days"
    elif matching_zone.estimated_days_min:
        estimated_days = f"{matching_zone.estimated_days_min}+ business days"
    else:
        estimated_days = "Contact for estimate"

    return ShippingEstimate(
        zone_id=matching_zone.id,
        zone_name=matching_zone.name,
        rate=shipping_rate,
        estimated_days=estimated_days,
        free_shipping=free_shipping,
    )


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.get("/zones", response_model=List[ShippingZoneSchema])
def list_shipping_zones(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """List all shipping zones (admin only)"""
    query = db.query(ShippingZone)
    if is_active is not None:
        query = query.filter(ShippingZone.is_active == is_active)
    return query.all()


@router.post("/zones", response_model=ShippingZoneSchema, status_code=status.HTTP_201_CREATED)
def create_shipping_zone(
    data: ShippingZoneCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Create a shipping zone (admin only)"""
    zone = ShippingZone(**data.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.get("/zones/{zone_id}", response_model=ShippingZoneSchema)
def get_shipping_zone(
    zone_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Get a shipping zone (admin only)"""
    zone = db.query(ShippingZone).filter(ShippingZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipping zone not found")
    return zone


@router.patch("/zones/{zone_id}", response_model=ShippingZoneSchema)
def update_shipping_zone(
    zone_id: int,
    data: ShippingZoneUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Update a shipping zone (admin only)"""
    zone = db.query(ShippingZone).filter(ShippingZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipping zone not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(zone, field, value)

    db.commit()
    db.refresh(zone)
    return zone


@router.delete("/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shipping_zone(
    zone_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Delete a shipping zone (admin only)"""
    zone = db.query(ShippingZone).filter(ShippingZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipping zone not found")

    db.delete(zone)
    db.commit()
