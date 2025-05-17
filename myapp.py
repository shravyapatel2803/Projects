import sqlite3
import os
import sys
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.app import App
from kivy.lang import Builder
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class Login(Screen):
    conn = sqlite3.connect('myapp.db')
    cursor = conn.cursor()
    def login(self):
        username = self.ids.username.text
        password = self.ids.password.text
        # Check if the username and password fields are not empty
        if not username or not password:
            self.ids.error_label.text = "Please enter both username and password"
            return
        # Check if the user exists in the database
        self.cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        result = self.cursor.fetchone()

        if result:
            # If user exists, switch to Home screen
            self.manager.current = 'home'
        else:
            # Show error message
            self.ids.error_label.text = "Invalid username or password"

class Register(Screen):
    conn = sqlite3.connect('myapp.db')
    cursor = conn.cursor()
    # Ensure the users table exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    conn.commit()
    def register(self):
        username = self.ids.R_username.text
        password = self.ids.R_password.text
        confirm_password = self.ids.R_confirm_password.text
        # Check if the username and password fields are not empty
        if not username or not password or not confirm_password:
            self.ids.error_label.text = "Please fill all fields"
            # self.ids.error_label.text = "Please enter both username and password"
            return
        # Check if the user already exists in the database
        self.cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        result = self.cursor.fetchone()

        if result:
            # If user exists, show error message
            self.ids.error_label.text = "Username already exists"
        else:
            # Check if the passwords match
            if password != confirm_password:
                self.ids.error_label.text = "Passwords do not match"
                return
            # Insert new user into the database
            self.cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            self.conn.commit()
            # Switch to Login screen
            self.manager.current = 'login'

class Home(Screen):
    def export_not_paid_pdf(self):
        import sqlite3
        conn = sqlite3.connect('myapp.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, phone, not_paid FROM customers WHERE not_paid > 0")
        customers = cursor.fetchall()
        conn.close()

        filename = "not_paid_customers.pdf"
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter

        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Customers with Not Paid Amount")

        c.setFont("Helvetica", 12)
        y = height - 80
        c.drawString(50, y, "Name")
        c.drawString(250, y, "Phone")
        c.drawString(400, y, "Not Paid Amount")
        y -= 20

        for name, phone, not_paid in customers:
            c.drawString(50, y, str(name))
            c.drawString(250, y, str(phone))
            c.drawString(400, y, f"{not_paid:.2f}")
            y -= 20
            if y < 50:
                c.showPage()
                y = height - 50

        c.save()
        # Optional: show a popup or print a message
        print(f"Exported to {filename}")

class Bill(Screen):
    pass

class MyScreenManager(ScreenManager):
    pass

class BillGST(Screen):
    conn = sqlite3.connect('myapp.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            not_paid REAL DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
    def generate_bill(self):
        # Get purchase item info
        try:
            item_weight = float(self.ids.item_weight.text)
            item_rate = float(self.ids.item_rate.text)
            
        except ValueError:
            item_weight = 0
            item_rate = 0
            
        item_type = self.ids.item_type.text  # 'Gold', 'Silver', etc.

        # Handle return item
        try:
            return_weight = float(self.ids.return_item_weight.text)
            return_type = self.ids.return_item_type.text
            return_quality = self.ids.return_item_quality.text
            item_return_rate = float(self.ids.return_item_rate.text)
            
        except ValueError:
            return_weight = 0
            return_type = ""
            return_quality = ""
            item_return_rate = 0

        return_money = 0
        
        if return_weight != "":
            # If return item is not empty
            try:
                return_weight = float(self.ids.return_item_weight.text)
                return_type = str(self.ids.return_item_type.text)
            except ValueError:
                return_type = ""
                return_quality = ""
            # If material matches
            if item_type == return_type:
                if item_type == 'Gold':
                    # User selects quality: 20 Carat or 18 Carat
                    if return_quality == '20 Carat':
                        # Assume 20 carat is 20/24 pure
                        purity_factor = 20 / 24
                    elif return_quality == '18 Carat':
                        purity_factor = 18 / 24
                    else:
                        purity_factor = 22/24  # fallback
                    adjusted_return_weight = return_weight * purity_factor
                    item_weight -= adjusted_return_weight
                elif item_type == 'Silver':
                    # For silver, 60% quality
                    if return_quality == '60% Silver':
                        purity_factor = 0.6
                    else:
                        purity_factor = 0.8
                    adjusted_return_weight = return_weight * purity_factor
                    item_weight -= adjusted_return_weight
                # Add more materials if needed
            else:
                    # If material does not match, subtract return item's value from total
                    # For simplicity, assume return item value = return_weight * item_rate
                    if return_type == 'Gold':
                        return_money = (return_weight * item_return_rate)/10
                    elif return_type == 'Silver':
                        return_money = (return_weight*item_return_rate)/1000

        # Calculate net weight and amount
        net_weight = item_weight
        if item_type == 'Gold':
            net_amount = (net_weight * item_rate)/10
        elif item_type == 'Silver':
            net_amount = (net_weight * item_rate)/1000

        # GST calculation (let's assume 3% GST for example)
        gst = net_amount * 0.03
        total_amount = net_amount + gst

        # Subtract return_money if material did not match
        total_amount -= return_money
        # paid amount details
        try:
            paid_amount = float(self.ids.paid_amount.text)

        except ValueError:
            paid_amount = 0

        not_paid = total_amount - paid_amount
        if not_paid != 0:
        # Update the database with not paid amount
            customer_name =  self.ids.customer_name.text
            customer_phone = self.ids.customer_phone.text
            conn = sqlite3.connect('myapp.db')
            cursor = conn.cursor()
            #check if customer exists
            cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_name,))  
            result = cursor.fetchone()
            if result:
                # If customer exists, update not paid amount
                cursor.execute("UPDATE customers SET not_paid = ? WHERE id = ?", (not_paid, customer_name))
            else:
                # If customer does not exist, insert new customer
                cursor.execute("INSERT INTO customers (name, phone, not_paid) VALUES (?, ?, ?)", (customer_name, customer_phone, not_paid))
            # Update the readonly fields
        self.ids.net_weight.text = f"{net_weight:.2f}"
        self.ids.net_amount.text = f"{net_amount:.2f}"
        self.ids.gst_amount.text = f"{gst:.2f}"
        self.ids.total_amount.text = f"{total_amount:.2f}"
        self.ids.not_paid_amount.text = f"{not_paid:.2f}"

class BillNoGST(Screen):
    def generate_bill_no_GST(self):
        # Get purchase item info
        try:
            item_weight = float(self.ids.item_weight_nogst.text or 0)
            item_rate = float(self.ids.item_rate_nogst.text or 0)
            item_type = self.ids.item_type_nogst.text
        except Exception:
            item_weight = 0
            item_rate = 0
            item_type = ""

        # Handle return item 
        try:
            return_weight = float(self.ids.return_item_weight_nogst.text or 0)
            return_type = self.ids.return_item_type_nogst.text
            return_quality = self.ids.return_item_quality_nogst.text
            item_return_rate = float(self.ids.return_item_rate_nogst.text or 0) if 'item_return_rate_nogst' in self.ids else item_rate
        except Exception:
            return_weight = 0
            return_type = ""
            return_quality = ""
            item_return_rate = item_rate

        return_money = 0
        if return_weight > 0:
            # If return item is not empty
            try:
                return_weight = float(self.ids.return_item_weight_nogst.text or 0)
                return_type = self.ids.return_item_type_nogst.text
                return_quality = self.ids.return_item_quality_nogst.text
            except ValueError:
                return_weight = 0
                return_type = ""
                return_quality = ""
        # If material matches
            if item_type == return_type:
                if item_type == 'Gold':
                    if return_quality == '20 Carat':
                        purity_factor = 20 / 24
                    elif return_quality == '18 Carat':
                        purity_factor = 18 / 24
                    else:
                        purity_factor = 22/24  # fallback
                    adjusted_return_weight = return_weight * purity_factor
                    item_weight -= adjusted_return_weight
                elif item_type == 'Silver':
                    if return_quality == '60% Silver':
                        purity_factor = 0.6
                    else:
                        purity_factor = 0.8
                    adjusted_return_weight = return_weight * purity_factor
                    item_weight -= adjusted_return_weight
                # Add more materials if needed
            else:
                # If material does not match, subtract return item's value from total
                if return_type == 'Gold':
                    return_money = (return_weight * item_return_rate)/10
                elif return_type == 'Silver':
                    return_money = (return_weight*item_return_rate)/1000

        # Calculate net weight and amount
        net_weight = item_weight
        if item_type == 'Gold':
            net_amount = (net_weight * item_rate)/10
        elif item_type == 'Silver':
            net_amount = (net_weight * item_rate)/1000

        # No GST calculation here!
        total_amount = net_amount - return_money

        # Update the readonly fields
        self.ids.net_weight_nogst.text = f"{net_weight:.2f}"
        self.ids.net_amount_nogst.text = f"{net_amount:.2f}"
        self.ids.total_amount_nogst.text = f"{total_amount:.2f}"

sm = Builder.load_file(resource_path("my.kv"))

class MyApp(App):
    def build(self):
        return sm

MyApp().run()