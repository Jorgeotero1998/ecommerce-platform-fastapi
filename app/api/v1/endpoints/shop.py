from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.v1.deps import get_current_user, get_db
from app.db.models.ecommerce import Order, OrderItem, Product

router = APIRouter()


class ProductCreate(BaseModel):
    sku: str
    name: str
    price_cents: int
    currency: str = "USD"


class ProductOut(BaseModel):
    id: str
    sku: str
    name: str
    price_cents: int
    currency: str


class OrderItemIn(BaseModel):
    product_id: str
    quantity: int = 1


class OrderCreate(BaseModel):
    items: list[OrderItemIn]


class OrderOut(BaseModel):
    id: str
    status: str
    total_cents: int


@router.get("/shop/products", response_model=list[ProductOut])
async def list_products(db=Depends(get_db)):
    result = await db.execute(select(Product))
    rows = result.scalars().all()
    return [
        ProductOut(
            id=str(p.id),
            sku=p.sku,
            name=p.name,
            price_cents=p.price_cents,
            currency=p.currency,
        )
        for p in rows
    ]


@router.post("/shop/products", response_model=ProductOut)
async def create_product(payload: ProductCreate, db=Depends(get_db), _=Depends(get_current_user)):
    product = Product(
        sku=payload.sku, name=payload.name, price_cents=payload.price_cents, currency=payload.currency
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductOut(
        id=str(product.id),
        sku=product.sku,
        name=product.name,
        price_cents=product.price_cents,
        currency=product.currency,
    )


@router.post("/shop/orders", response_model=OrderOut)
async def create_order(payload: OrderCreate, db=Depends(get_db), _=Depends(get_current_user)):
    if not payload.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order requires items")

    # fetch products
    try:
        product_uuids = [uuid.UUID(i.product_id) for i in payload.items]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product_id")

    result = await db.execute(select(Product).where(Product.id.in_(product_uuids)))
    products = {str(p.id): p for p in result.scalars().all()}

    total = 0
    order = Order(status="pending", total_cents=0)
    db.add(order)
    await db.flush()

    for item in payload.items:
        p = products.get(item.product_id)
        if not p:
            raise HTTPException(status_code=404, detail=f"Product not found: {item.product_id}")
        qty = max(1, item.quantity)
        total += p.price_cents * qty
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=p.id,
                quantity=qty,
                unit_price_cents=p.price_cents,
            )
        )

    order.total_cents = total
    await db.commit()
    await db.refresh(order)
    return OrderOut(id=str(order.id), status=order.status, total_cents=order.total_cents)


@router.get("/shop/orders", response_model=list[OrderOut])
async def list_orders(db=Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Order).order_by(Order.created_at.desc()))
    orders = result.scalars().all()
    return [OrderOut(id=str(o.id), status=o.status, total_cents=o.total_cents) for o in orders]

