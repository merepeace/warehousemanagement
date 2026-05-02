import sqlite3
import threading
import time
from datetime import datetime
from database_setup import SQLiteLogger


class VirtualAGV:
    """Virtual AGV for testing"""

    def __init__(self, agv_id, name, logger):
        self.agv_id = agv_id
        self.name = name
        self.logger = logger
        self.current_order_id = None
        self.status = 'idle'

    def deliver_order(self, order_id, order_name, location):
        """Simulate delivery process"""
        self.current_order_id = order_id
        self.status = 'busy'

        self.logger.info(f"{self.name} started delivering Order {order_id} ({order_name}) to {location}")

        # Simulate delivery time based on location
        delivery_time = 5  # seconds
        if location == 'Zone B':
            delivery_time = 8
        elif location == 'Zone C':
            delivery_time = 10

        # Simulate delivery steps
        for i in range(delivery_time):
            time.sleep(1)
            if i == 2:  # Update status to delivering
                self.update_order_status(order_id, 'delivering')

        # Delivery complete
        self.complete_delivery(order_id)

        self.status = 'idle'
        self.current_order_id = None

    def update_order_status(self, order_id, status):
        """Update order status in database"""
        try:
            conn = sqlite3.connect('warehouse.db')
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Failed to update order {order_id} status: {str(e)}")

    def complete_delivery(self, order_id):
        """Mark delivery as complete"""
        try:
            conn = sqlite3.connect('warehouse.db')
            cursor = conn.cursor()
            cursor.execute('''
                           UPDATE orders
                           SET status              = 'done',
                               completed_timestamp = ?
                           WHERE id = ?
                           ''', (datetime.now().isoformat(), order_id))

            # Free the AGV in database
            cursor.execute("UPDATE agvs SET status = 'idle', current_order_id = NULL WHERE id = ?", (self.agv_id,))

            conn.commit()
            conn.close()

            self.logger.info(f"{self.name} completed delivery of Order {order_id}")

        except Exception as e:
            self.logger.error(f"Failed to complete delivery for order {order_id}: {str(e)}")


class WarehouseManagementSystem:
    def __init__(self):
        self.logger = SQLiteLogger("WMS")
        self.running = True

        # Create virtual AGVs
        self.agvs = {
            1: VirtualAGV(1, "AGV-1", self.logger),
            2: VirtualAGV(2, "AGV-2", self.logger)
        }

        self.logger.info("Warehouse Management System started")

    def get_free_agv(self):
        """Get first available AGV"""
        try:
            conn = sqlite3.connect('warehouse.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM agvs WHERE status = 'idle' ORDER BY id LIMIT 1")
            result = cursor.fetchone()
            conn.close()

            if result:
                return result[0], result[1]
            return None, None
        except Exception as e:
            self.logger.error(f"Failed to get free AGV: {str(e)}")
            return None, None

    def assign_order_to_agv(self, order_id, agv_id, agv_name):
        """Assign an order to an AGV"""
        try:
            conn = sqlite3.connect('warehouse.db')
            cursor = conn.cursor()

            # Update order with assigned AGV and status
            cursor.execute('''
                           UPDATE orders
                           SET assigned_agv = ?,
                               status       = 'assigned'
                           WHERE id = ?
                             AND status = 'pending'
                           ''', (agv_id, order_id))

            # Update AGV status
            cursor.execute('''
                           UPDATE agvs
                           SET status           = 'busy',
                               current_order_id = ?,
                               last_active      = ?
                           WHERE id = ?
                           ''', (order_id, datetime.now().isoformat(), agv_id))

            conn.commit()
            conn.close()

            self.logger.info(f"Order {order_id} assigned to {agv_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to assign order {order_id} to AGV {agv_id}: {str(e)}")
            return False

    def get_order_details(self, order_id):
        """Get order details from database"""
        try:
            conn = sqlite3.connect('warehouse.db')
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT order_name, delivery_location, product_name, quantity
                           FROM orders
                           WHERE id = ?
                           ''', (order_id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'name': result[0],
                    'location': result[1],
                    'product': result[2],
                    'quantity': result[3]
                }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get order details: {str(e)}")
            return None

    def process_orders(self):
        """Main loop to process pending orders"""
        while self.running:
            try:
                conn = sqlite3.connect('warehouse.db')
                cursor = conn.cursor()

                # Get oldest pending orders (by priority and timestamp)
                cursor.execute('''
                               SELECT id, order_name, priority
                               FROM orders
                               WHERE status = 'pending'
                               ORDER BY priority DESC, timestamp ASC
                                   LIMIT 2
                               ''')

                pending_orders = cursor.fetchall()
                conn.close()

                if pending_orders:
                    # Get free AGV
                    agv_id, agv_name = self.get_free_agv()

                    if agv_id:
                        # Take first pending order
                        order = pending_orders[0]
                        order_id = order[0]

                        self.logger.info(f"Processing Order {order_id} with {agv_name}")

                        # Assign order to AGV
                        if self.assign_order_to_agv(order_id, agv_id, agv_name):
                            # Get order details
                            order_details = self.get_order_details(order_id)
                            if order_details:
                                # Start delivery in a separate thread
                                agv = self.agvs[agv_id]
                                delivery_thread = threading.Thread(
                                    target=agv.deliver_order,
                                    args=(order_id, order_details['name'], order_details['location'])
                                )
                                delivery_thread.start()

                # Wait before next check
                time.sleep(2)

            except Exception as e:
                self.logger.error(f"Error in process_orders: {str(e)}")
                time.sleep(5)

    def start(self):
        """Start the warehouse management system"""
        self.wms_thread = threading.Thread(target=self.process_orders)
        self.wms_thread.daemon = True
        self.wms_thread.start()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop the warehouse management system"""
        self.running = False
        self.logger.info("Warehouse Management System stopped")


# Run WMS
if __name__ == "__main__":
    wms = WarehouseManagementSystem()
    print("Warehouse Management System Started with Virtual AGVs...")
    print("Press Ctrl+C to stop")
    wms.start()