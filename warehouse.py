
import sqlite3
import logging
from datetime import datetime

#Database design..................................................................

# Setup logging to SQLite
def setup_logging_db():
    conn = sqlite3.connect('warehouse.db')
    cursor = conn.cursor()

    # Create logs table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS system_logs
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       timestamp
                       TEXT
                       NOT
                       NULL,
                       level
                       TEXT
                       NOT
                       NULL,
                       source
                       TEXT
                       NOT
                       NULL,
                       message
                       TEXT
                       NOT
                       NULL
                   )
                   ''')
    conn.commit()
    conn.close()


# WAREHOUSE LOGGER
class SQLiteLogger:
    def __init__(self, source):
        self.source = source

    def _log(self, level, message):
        try:
            conn = sqlite3.connect('warehouse.db')
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO system_logs (timestamp, level, source, message)
                           VALUES (?, ?, ?, ?)
                           ''', (datetime.now().isoformat(), level, self.source, message))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Logging failed: {e}")

    def info(self, message):
        self._log('INFO', message)
        print(f"[INFO] [{self.source}] {message}")

    def error(self, message):
        self._log('ERROR', message)
        print(f"[ERROR] [{self.source}] {message}")

    def warning(self, message):
        self._log('WARNING', message)
        print(f"[WARNING] [{self.source}] {message}")


def create_database():
    """Create all tables for the warehouse system"""
    conn = sqlite3.connect('warehouse.db')
    cursor = conn.cursor()

    # Create orders table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS orders
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       order_name
                       TEXT
                       NOT
                       NULL,
                       timestamp
                       TEXT
                       NOT
                       NULL,
                       status
                       TEXT
                       DEFAULT
                       'pending',
                       assigned_agv
                       INTEGER,
                       product_name
                       TEXT,
                       quantity
                       INTEGER
                       DEFAULT
                       1,
                       priority
                       INTEGER
                       DEFAULT
                       1,
                       delivery_location
                       TEXT
                       DEFAULT
                       'Zone A',
                       completed_timestamp
                       TEXT
                   )
                   ''')

#AGVs table creation
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS agvs
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY,
                       name
                       TEXT
                       NOT
                       NULL,
                       status
                       TEXT
                       DEFAULT
                       'idle',
                       current_order_id
                       INTEGER,
                       last_active
                       TEXT
                   )
                   ''')

    # Insert of default AGVs if not exists
    cursor.execute("SELECT COUNT(*) FROM agvs")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO agvs (id, name, status) VALUES (1, 'AGV-1', 'idle')")
        cursor.execute("INSERT INTO agvs (id, name, status) VALUES (2, 'AGV-2', 'idle')")

    conn.commit()
    conn.close()

    print("Database created successfully!")


# Database setup
if __name__ == "__main__":
    setup_logging_db()
    create_database()






#Ordermanagement system GUI.................:



import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
from datetime import datetime
import threading
import time


class OrderManagementSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Order Management System")
        self.root.geometry("800x600")

        # Setup logger
       # from database_setup import SQLiteLogger
        self.logger = SQLiteLogger("OMS")

        # Create GUI
        self.create_widgets()

        # Refresh orders every 5 seconds
        self.refresh_orders()

        self.logger.info("Order Management System started")

    def create_widgets(self):
        # Input Frame
        input_frame = tk.LabelFrame(self.root, text="Create New Order", padx=10, pady=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        # Order Name
        tk.Label(input_frame, text="Order Name:").grid(row=0, column=0, sticky="w")
        self.order_name_entry = tk.Entry(input_frame, width=30)
        self.order_name_entry.grid(row=0, column=1, padx=5)

        # Product Name
        tk.Label(input_frame, text="Product Name:").grid(row=1, column=0, sticky="w")
        self.product_entry = tk.Entry(input_frame, width=30)
        self.product_entry.grid(row=1, column=1, padx=5)

        # Quantity
        tk.Label(input_frame, text="Quantity:").grid(row=2, column=0, sticky="w")
        self.quantity_entry = tk.Entry(input_frame, width=10)
        self.quantity_entry.insert(0, "1")
        self.quantity_entry.grid(row=2, column=1, sticky="w", padx=5)

        # Priority
        tk.Label(input_frame, text="Priority (1-5):").grid(row=3, column=0, sticky="w")
        self.priority_combo = ttk.Combobox(input_frame, values=[1, 2, 3, 4, 5], width=8)
        self.priority_combo.set(1)
        self.priority_combo.grid(row=3, column=1, sticky="w", padx=5)

        # Delivery Location
        tk.Label(input_frame, text="Delivery Location:").grid(row=4, column=0, sticky="w")
        self.location_combo = ttk.Combobox(input_frame, values=['Zone A', 'Zone B', 'Zone C'], width=15)
        self.location_combo.set('Zone A')
        self.location_combo.grid(row=4, column=1, sticky="w", padx=5)

        # Create Button
        self.create_btn = tk.Button(input_frame, text="Create Order", command=self.create_order,
                                    bg="green", fg="white", padx=20)
        self.create_btn.grid(row=5, column=0, columnspan=2, pady=10)

        # Orders Frame
        orders_frame = tk.LabelFrame(self.root, text="Current Orders", padx=10, pady=10)
        orders_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Treeview for orders
        columns = ('ID', 'Order Name', 'Product', 'Qty', 'Status', 'Assigned AGV', 'Priority', 'Location', 'Timestamp')
        self.tree = ttk.Treeview(orders_frame, columns=columns, show='headings', height=15)

        # Define headings
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        # Scrollbar
        scrollbar = ttk.Scrollbar(orders_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Buttons Frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=5)

        self.refresh_btn = tk.Button(button_frame, text="Refresh Orders", command=self.refresh_orders, bg="blue",
                                     fg="white")
        self.refresh_btn.pack(side="left", padx=5)

        self.cancel_btn = tk.Button(button_frame, text="Cancel Selected Order", command=self.cancel_order, bg="red",
                                    fg="white")
        self.cancel_btn.pack(side="left", padx=5)

        # Logs Frame
        logs_frame = tk.LabelFrame(self.root, text="System Logs", padx=10, pady=10)
        logs_frame.pack(fill="x", padx=10, pady=5)

        self.logs_text = scrolledtext.ScrolledText(logs_frame, height=8, width=80)
        self.logs_text.pack(fill="both", expand=True)

    def create_order(self):
        """Create a new order with validation"""
        try:
            # Validation
            order_name = self.order_name_entry.get().strip()
            if not order_name:
                messagebox.showwarning("Validation Error", "Order name is required!")
                return

            product_name = self.product_entry.get().strip()
            if not product_name:
                messagebox.showwarning("Validation Error", "Product name is required!")
                return

            try:
                quantity = int(self.quantity_entry.get())
                if quantity <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Validation Error", "Quantity must be a positive number!")
                return

            priority = int(self.priority_combo.get())
            location = self.location_combo.get()

            # Insert into database
            conn = sqlite3.connect('warehouse.db')
            cursor = conn.cursor()

            cursor.execute('''
                           INSERT INTO orders (order_name, timestamp, status, product_name, quantity, priority,
                                               delivery_location)
                           VALUES (?, ?, ?, ?, ?, ?, ?)
                           ''', (order_name, datetime.now().isoformat(), 'pending', product_name, quantity, priority,
                                 location))

            order_id = cursor.lastrowid
            conn.commit()
            conn.close()

            self.logger.info(f"Order created successfully - ID: {order_id}, Name: {order_name}")

            # Clear inputs
            self.order_name_entry.delete(0, tk.END)
            self.product_entry.delete(0, tk.END)
            self.quantity_entry.delete(0, tk.END)
            self.quantity_entry.insert(0, "1")

            # Refresh display
            self.refresh_orders()

            messagebox.showinfo("Success", f"Order {order_id} created successfully!")

        except Exception as e:
            self.logger.error(f"Failed to create order: {str(e)}")
            messagebox.showerror("Error", f"Failed to create order: {str(e)}")

    def refresh_orders(self):
        """Refresh the orders display"""
        try:
            conn = sqlite3.connect('warehouse.db')
            cursor = conn.cursor()

            # Get all orders ordered by priority (higher priority first) and timestamp
            cursor.execute('''
                           SELECT id,
                                  order_name,
                                  product_name,
                                  quantity,
                                  status,
                                  COALESCE(assigned_agv, ''),
                                  priority,
                                  delivery_location, timestamp
                           FROM orders
                           ORDER BY priority DESC, timestamp ASC
                           ''')

            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Insert orders
            for row in cursor.fetchall():
                # Format assigned_agv for display
                assigned = f"AGV-{row[5]}" if row[5] and row[5] != '' else 'Not assigned'
                values = (row[0], row[1], row[2], row[3], row[4], assigned, row[6], row[7], row[8][:19])

                # Color coding based on status
                tag = ''
                if row[4] == 'pending':
                    tag = 'pending'
                elif row[4] == 'delivering':
                    tag = 'delivering'
                elif row[4] == 'done':
                    tag = 'done'

                self.tree.insert('', 'end', values=values, tags=(tag,))

            # Configure tags for colors
            self.tree.tag_configure('pending', background='yellow')
            self.tree.tag_configure('delivering', background='orange')
            self.tree.tag_configure('done', background='lightgreen')

            conn.close()

            # Update logs display
            self.display_recent_logs()

        except Exception as e:
            self.logger.error(f"Failed to refresh orders: {str(e)}")

        # Schedule next refresh
        self.root.after(5000, self.refresh_orders)

    def display_recent_logs(self):
        """Display recent logs in the text widget"""
        try:
            conn = sqlite3.connect('warehouse.db')
            cursor = conn.cursor()

            cursor.execute('''
                           SELECT timestamp, source, level, message
                           FROM system_logs
                           ORDER BY id DESC
                               LIMIT 20
                           ''')

            self.logs_text.delete(1.0, tk.END)

            for row in cursor.fetchall():
                log_entry = f"[{row[0][:19]}] [{row[1]}] {row[2]}: {row[3]}\n"
                self.logs_text.insert(tk.END, log_entry)

            conn.close()
        except Exception as e:
            print(f"Failed to display logs: {e}")

    def cancel_order(self):
        """Cancel selected order"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select an order to cancel")
            return

        # Get order ID
        order_id = self.tree.item(selected[0])['values'][0]

        try:
            conn = sqlite3.connect('warehouse.db')
            cursor = conn.cursor()

            # Check if order can be cancelled (only pending orders)
            cursor.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
            status = cursor.fetchone()[0]

            if status != 'pending':
                messagebox.showwarning("Cannot Cancel", f"Order {order_id} is {status} and cannot be cancelled")
                conn.close()
                return

            # Update status to cancelled
            cursor.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
            conn.commit()

            self.logger.info(f"Order {order_id} cancelled by user")
            messagebox.showinfo("Success", f"Order {order_id} cancelled")

            self.refresh_orders()

            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to cancel order: {str(e)}")
            messagebox.showerror("Error", f"Failed to cancel order: {str(e)}")


# Run the GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = OrderManagementSystem(root)
    root.mainloop()


#...........Warehouse virtual AGV ..............


import sqlite3
import threading
import time
from datetime import datetime
#from database_setup import SQLiteLogger


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


# Now Run
if __name__ == "__main__":
    wms = WarehouseManagementSystem()
    print("Warehouse Management System Started with Virtual AGVs...")
    print("Press Ctrl+C to stop")
    wms.start()