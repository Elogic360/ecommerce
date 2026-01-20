"""
WebSocket Router for Real-Time Features
Handles WebSocket connections and message routing
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
import json

from app.websockets import manager, ChannelType
from app.dependencies import get_current_user_optional
from app.db.session import get_db
from app.models import User
from sqlalchemy.orm import Session


router = APIRouter()


async def get_user_from_token(
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Extract user from WebSocket query token"""
    if not token:
        return None
    
    try:
        from app.core.security import decode_token
        payload = decode_token(token)
        if payload is None:
            return None
        
        user_id = payload.get("sub")
        if user_id is None:
            return None
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        return user
    except Exception:
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    Main WebSocket endpoint for real-time updates.
    
    Query Parameters:
    - token: Optional JWT token for authenticated connections
    
    Message Types (from client):
    - subscribe_channel: {"action": "subscribe", "channel": "inventory|order_status|notifications"}
    - unsubscribe_channel: {"action": "unsubscribe", "channel": "..."}
    - watch_product: {"action": "watch_product", "product_id": 123}
    - unwatch_product: {"action": "unwatch_product", "product_id": 123}
    - watch_order: {"action": "watch_order", "order_id": 456}
    - unwatch_order: {"action": "unwatch_order", "order_id": 456}
    - ping: {"action": "ping"}
    
    Message Types (from server):
    - inventory_update: Product stock changes
    - order_update: Order status changes
    - price_alert: Wishlist price drops
    - notification: User notifications
    - admin_broadcast: Admin announcements
    - pong: Response to ping
    - error: Error messages
    """
    # Try to authenticate
    user = None
    is_admin = False
    
    if token:
        try:
            from app.core.security import decode_token
            from app.db.session import SessionLocal
            
            db = SessionLocal()
            try:
                payload = decode_token(token)
                if payload:
                    user_id = payload.get("sub")
                    if user_id:
                        user = db.query(User).filter(User.id == int(user_id)).first()
                        if user:
                            is_admin = user.role == "admin"
            finally:
                db.close()
        except Exception:
            pass
    
    # Accept connection
    connection_id = await manager.connect(
        websocket,
        user_id=user.id if user else None,
        is_admin=is_admin
    )
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "connection_id": connection_id,
            "authenticated": user is not None,
            "is_admin": is_admin
        })
        
        # Listen for messages
        while True:
            try:
                data = await websocket.receive_json()
                action = data.get("action")
                
                if action == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif action == "subscribe":
                    channel_name = data.get("channel")
                    try:
                        channel = ChannelType(channel_name)
                        
                        # Admin-only channels
                        if channel in [ChannelType.ADMIN_BROADCAST, ChannelType.INVENTORY] and not is_admin:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Admin access required for this channel"
                            })
                            continue
                        
                        # Authenticated-only channels
                        if channel == ChannelType.NOTIFICATIONS and not user:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Authentication required for notifications"
                            })
                            continue
                        
                        await manager.subscribe_channel(connection_id, channel)
                        await websocket.send_json({
                            "type": "subscribed",
                            "channel": channel_name
                        })
                    except ValueError:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Unknown channel: {channel_name}"
                        })
                
                elif action == "unsubscribe":
                    channel_name = data.get("channel")
                    try:
                        channel = ChannelType(channel_name)
                        await manager.unsubscribe_channel(connection_id, channel)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "channel": channel_name
                        })
                    except ValueError:
                        pass
                
                elif action == "watch_product":
                    product_id = data.get("product_id")
                    if product_id:
                        await manager.watch_product(connection_id, int(product_id))
                        await websocket.send_json({
                            "type": "watching_product",
                            "product_id": product_id
                        })
                
                elif action == "unwatch_product":
                    product_id = data.get("product_id")
                    if product_id:
                        await manager.unwatch_product(connection_id, int(product_id))
                        await websocket.send_json({
                            "type": "unwatched_product",
                            "product_id": product_id
                        })
                
                elif action == "watch_order":
                    order_id = data.get("order_id")
                    if order_id and user:
                        # Verify user owns this order or is admin
                        from app.db.session import SessionLocal
                        from app.models import Order
                        
                        db = SessionLocal()
                        try:
                            order = db.query(Order).filter(Order.id == int(order_id)).first()
                            if order and (order.user_id == user.id or is_admin):
                                await manager.watch_order(connection_id, int(order_id))
                                await websocket.send_json({
                                    "type": "watching_order",
                                    "order_id": order_id
                                })
                            else:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": "Order not found or access denied"
                                })
                        finally:
                            db.close()
                    elif not user:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Authentication required to watch orders"
                        })
                
                elif action == "unwatch_order":
                    order_id = data.get("order_id")
                    if order_id:
                        await manager.unwatch_order(connection_id, int(order_id))
                        await websocket.send_json({
                            "type": "unwatched_order",
                            "order_id": order_id
                        })
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    })
            
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
    
    except WebSocketDisconnect:
        await manager.disconnect(connection_id)
    except Exception as e:
        await manager.disconnect(connection_id)
        raise


@router.websocket("/ws/admin")
async def admin_websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    Admin-only WebSocket endpoint with full access to all channels.
    
    Requires valid admin JWT token.
    
    Additional admin actions:
    - broadcast: {"action": "broadcast", "message": {...}}
    - stats: {"action": "stats"} - Get connection statistics
    """
    # Authenticate admin
    user = None
    
    try:
        from app.core.security import decode_token
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        try:
            payload = decode_token(token)
            if payload:
                user_id = payload.get("sub")
                if user_id:
                    user = db.query(User).filter(User.id == int(user_id)).first()
        finally:
            db.close()
    except Exception:
        pass
    
    if not user or user.role != "admin":
        await websocket.close(code=4003, reason="Admin access required")
        return
    
    # Accept connection
    connection_id = await manager.connect(
        websocket,
        user_id=user.id,
        is_admin=True
    )
    
    # Auto-subscribe to all channels
    for channel in ChannelType:
        await manager.subscribe_channel(connection_id, channel)
    
    try:
        await websocket.send_json({
            "type": "admin_connected",
            "connection_id": connection_id,
            "subscribed_channels": [c.value for c in ChannelType]
        })
        
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif action == "broadcast":
                message = data.get("message", {})
                await manager.admin_broadcast(message)
                await websocket.send_json({
                    "type": "broadcast_sent",
                    "message": message
                })
            
            elif action == "stats":
                stats = {
                    "total_connections": manager.get_connection_count(),
                    "channel_stats": {
                        channel.value: manager.get_channel_subscriber_count(channel)
                        for channel in ChannelType
                    }
                }
                await websocket.send_json({
                    "type": "stats",
                    "data": stats
                })
            
            else:
                # Handle regular actions
                pass
    
    except WebSocketDisconnect:
        await manager.disconnect(connection_id)
    except Exception:
        await manager.disconnect(connection_id)
        raise
