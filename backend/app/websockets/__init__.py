"""
WebSocket Connection Manager for Real-Time Features
Handles live inventory updates, order status notifications, and admin broadcasts
"""
from typing import Dict, List, Set, Optional
from fastapi import WebSocket
from dataclasses import dataclass, field
import json
import asyncio
from enum import Enum


class ChannelType(str, Enum):
    """WebSocket channel types"""
    INVENTORY = "inventory"
    ORDER_STATUS = "order_status"
    NOTIFICATIONS = "notifications"
    ADMIN_BROADCAST = "admin_broadcast"
    PRICE_ALERTS = "price_alerts"


@dataclass
class ConnectionInfo:
    """Stores connection metadata"""
    websocket: WebSocket
    user_id: Optional[int] = None
    is_admin: bool = False
    subscribed_channels: Set[str] = field(default_factory=set)
    subscribed_products: Set[int] = field(default_factory=set)
    subscribed_orders: Set[int] = field(default_factory=set)


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.
    
    Features:
    - User-specific connections
    - Channel-based subscriptions
    - Admin broadcast capability
    - Product/Order-specific subscriptions for targeted updates
    """
    
    def __init__(self):
        # connection_id -> ConnectionInfo
        self._connections: Dict[str, ConnectionInfo] = {}
        # user_id -> list of connection_ids
        self._user_connections: Dict[int, List[str]] = {}
        # channel -> set of connection_ids
        self._channel_subscriptions: Dict[str, Set[str]] = {
            channel.value: set() for channel in ChannelType
        }
        # product_id -> set of connection_ids (for inventory alerts)
        self._product_watchers: Dict[int, Set[str]] = {}
        # order_id -> set of connection_ids (for order status updates)
        self._order_watchers: Dict[int, Set[str]] = {}
        
        self._connection_counter = 0
        self._lock = asyncio.Lock()
    
    def _generate_connection_id(self) -> str:
        """Generate unique connection ID"""
        self._connection_counter += 1
        return f"conn_{self._connection_counter}"
    
    async def connect(
        self, 
        websocket: WebSocket, 
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> str:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            user_id: Optional user ID for authenticated connections
            is_admin: Whether the user is an admin
            
        Returns:
            Connection ID for this connection
        """
        await websocket.accept()
        
        async with self._lock:
            conn_id = self._generate_connection_id()
            self._connections[conn_id] = ConnectionInfo(
                websocket=websocket,
                user_id=user_id,
                is_admin=is_admin
            )
            
            if user_id:
                if user_id not in self._user_connections:
                    self._user_connections[user_id] = []
                self._user_connections[user_id].append(conn_id)
            
            # Auto-subscribe admins to admin channel
            if is_admin:
                self._channel_subscriptions[ChannelType.ADMIN_BROADCAST.value].add(conn_id)
                self._connections[conn_id].subscribed_channels.add(ChannelType.ADMIN_BROADCAST.value)
        
        return conn_id
    
    async def disconnect(self, connection_id: str):
        """Remove a connection and clean up subscriptions"""
        async with self._lock:
            if connection_id not in self._connections:
                return
            
            conn_info = self._connections[connection_id]
            
            # Remove from user connections
            if conn_info.user_id and conn_info.user_id in self._user_connections:
                self._user_connections[conn_info.user_id] = [
                    cid for cid in self._user_connections[conn_info.user_id] 
                    if cid != connection_id
                ]
                if not self._user_connections[conn_info.user_id]:
                    del self._user_connections[conn_info.user_id]
            
            # Remove from channel subscriptions
            for channel in conn_info.subscribed_channels:
                if channel in self._channel_subscriptions:
                    self._channel_subscriptions[channel].discard(connection_id)
            
            # Remove from product watchers
            for product_id in conn_info.subscribed_products:
                if product_id in self._product_watchers:
                    self._product_watchers[product_id].discard(connection_id)
            
            # Remove from order watchers
            for order_id in conn_info.subscribed_orders:
                if order_id in self._order_watchers:
                    self._order_watchers[order_id].discard(connection_id)
            
            del self._connections[connection_id]
    
    async def subscribe_channel(self, connection_id: str, channel: ChannelType):
        """Subscribe a connection to a channel"""
        async with self._lock:
            if connection_id in self._connections:
                self._channel_subscriptions[channel.value].add(connection_id)
                self._connections[connection_id].subscribed_channels.add(channel.value)
    
    async def unsubscribe_channel(self, connection_id: str, channel: ChannelType):
        """Unsubscribe a connection from a channel"""
        async with self._lock:
            if connection_id in self._connections:
                self._channel_subscriptions[channel.value].discard(connection_id)
                self._connections[connection_id].subscribed_channels.discard(channel.value)
    
    async def watch_product(self, connection_id: str, product_id: int):
        """Subscribe to inventory updates for a specific product"""
        async with self._lock:
            if connection_id in self._connections:
                if product_id not in self._product_watchers:
                    self._product_watchers[product_id] = set()
                self._product_watchers[product_id].add(connection_id)
                self._connections[connection_id].subscribed_products.add(product_id)
    
    async def unwatch_product(self, connection_id: str, product_id: int):
        """Unsubscribe from product inventory updates"""
        async with self._lock:
            if connection_id in self._connections:
                if product_id in self._product_watchers:
                    self._product_watchers[product_id].discard(connection_id)
                self._connections[connection_id].subscribed_products.discard(product_id)
    
    async def watch_order(self, connection_id: str, order_id: int):
        """Subscribe to status updates for a specific order"""
        async with self._lock:
            if connection_id in self._connections:
                if order_id not in self._order_watchers:
                    self._order_watchers[order_id] = set()
                self._order_watchers[order_id].add(connection_id)
                self._connections[connection_id].subscribed_orders.add(order_id)
    
    async def unwatch_order(self, connection_id: str, order_id: int):
        """Unsubscribe from order status updates"""
        async with self._lock:
            if connection_id in self._connections:
                if order_id in self._order_watchers:
                    self._order_watchers[order_id].discard(connection_id)
                self._connections[connection_id].subscribed_orders.discard(order_id)
    
    async def _send_to_connection(self, connection_id: str, message: dict) -> bool:
        """Send a message to a specific connection. Returns success status."""
        if connection_id not in self._connections:
            return False
        
        try:
            await self._connections[connection_id].websocket.send_json(message)
            return True
        except Exception:
            # Connection is broken, schedule cleanup
            asyncio.create_task(self.disconnect(connection_id))
            return False
    
    async def send_personal(self, user_id: int, message: dict):
        """Send a message to all connections of a specific user"""
        connection_ids = self._user_connections.get(user_id, [])
        for conn_id in connection_ids:
            await self._send_to_connection(conn_id, message)
    
    async def broadcast_channel(self, channel: ChannelType, message: dict):
        """Broadcast a message to all subscribers of a channel"""
        connection_ids = self._channel_subscriptions.get(channel.value, set())
        for conn_id in list(connection_ids):
            await self._send_to_connection(conn_id, message)
    
    async def broadcast_inventory_update(self, product_id: int, data: dict):
        """Broadcast inventory update to product watchers and inventory channel"""
        message = {
            "type": "inventory_update",
            "product_id": product_id,
            "data": data
        }
        
        # Send to product-specific watchers
        watchers = self._product_watchers.get(product_id, set())
        for conn_id in list(watchers):
            await self._send_to_connection(conn_id, message)
        
        # Also broadcast to inventory channel (for admins)
        await self.broadcast_channel(ChannelType.INVENTORY, message)
    
    async def broadcast_order_update(self, order_id: int, user_id: int, data: dict):
        """Broadcast order status update to order watchers and order owner"""
        message = {
            "type": "order_update",
            "order_id": order_id,
            "data": data
        }
        
        # Send to order-specific watchers
        watchers = self._order_watchers.get(order_id, set())
        for conn_id in list(watchers):
            await self._send_to_connection(conn_id, message)
        
        # Send to the order owner
        await self.send_personal(user_id, message)
        
        # Broadcast to order status channel (for admins)
        await self.broadcast_channel(ChannelType.ORDER_STATUS, message)
    
    async def broadcast_price_alert(self, product_id: int, user_ids: List[int], data: dict):
        """Send price drop alerts to users watching a product"""
        message = {
            "type": "price_alert",
            "product_id": product_id,
            "data": data
        }
        
        for user_id in user_ids:
            await self.send_personal(user_id, message)
    
    async def admin_broadcast(self, message: dict):
        """Broadcast a message to all admin connections"""
        admin_message = {
            "type": "admin_broadcast",
            "data": message
        }
        await self.broadcast_channel(ChannelType.ADMIN_BROADCAST, admin_message)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self._connections)
    
    def get_user_connection_count(self, user_id: int) -> int:
        """Get number of connections for a specific user"""
        return len(self._user_connections.get(user_id, []))
    
    def get_channel_subscriber_count(self, channel: ChannelType) -> int:
        """Get number of subscribers for a channel"""
        return len(self._channel_subscriptions.get(channel.value, set()))


# Global connection manager instance
manager = ConnectionManager()
