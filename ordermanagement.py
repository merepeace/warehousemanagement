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
        from database_setup import SQLiteLogger
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