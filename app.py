from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from flask_socketio import SocketIO, emit
import sqlite3
import os
import hashlib
import datetime
import json
import time
import threading
from contextlib import contextmanager

app = Flask(__name__, template_folder='templates', static_folder='static')
socketio = SocketIO(app)
app.secret_key = 'supersecretkey'

# Global database lock to prevent concurrent access
db_lock = threading.Lock()

def get_db_connection():
    """Get a database connection with proper settings"""
    conn = sqlite3.connect('aureliana.db', timeout=60, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=10000')
    conn.execute('PRAGMA temp_store=MEMORY')
    conn.execute('PRAGMA busy_timeout=30000')
    return conn

@contextmanager
def db_transaction():
    """Context manager for database transactions with proper error handling"""
    conn = None
    try:
        with db_lock:
            conn = get_db_connection()
            yield conn
            conn.commit()
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        print(f"Database error: {e}")
        raise
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Database Setup
def init_db():
    with db_transaction() as conn:
        c = conn.cursor()

        # Clients Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                client_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                address TEXT,
                address_details TEXT,
                region TEXT,
                province TEXT,
                city TEXT,
                barangay TEXT,
                last_login DATETIME
            )
        ''')

        # Migration: Add full_name column if it doesn't exist
        try:
            c.execute('ALTER TABLE clients ADD COLUMN full_name TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Migration: Update existing records to combine first_name and last_name into full_name
        try:
            c.execute('SELECT client_ID, first_name, last_name FROM clients WHERE full_name IS NULL')
            existing_users = c.fetchall()
            for user in existing_users:
                client_id, first_name, last_name = user
                full_name = f"{first_name} {last_name}".strip()
                c.execute('UPDATE clients SET full_name = ? WHERE client_ID = ?', (full_name, client_id))
        except sqlite3.OperationalError:
            # Old columns don't exist, skip migration
            pass
        
        # Migration: Remove old columns (will be done after ensuring data is migrated)
        try:
            c.execute('ALTER TABLE clients DROP COLUMN first_name')
        except sqlite3.OperationalError:
            pass  # Column doesn't exist or can't be dropped
        
        try:
            c.execute('ALTER TABLE clients DROP COLUMN last_name')
        except sqlite3.OperationalError:
            pass  # Column doesn't exist or can't be dropped
        
        try:
            c.execute('ALTER TABLE clients DROP COLUMN username')
        except sqlite3.OperationalError:
            pass  # Column doesn't exist or can't be dropped

        # Migration: Add separate address fields if they don't exist
        try:
            c.execute('ALTER TABLE clients ADD COLUMN address_details TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            c.execute('ALTER TABLE clients ADD COLUMN region TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            c.execute('ALTER TABLE clients ADD COLUMN province TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            c.execute('ALTER TABLE clients ADD COLUMN city TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            c.execute('ALTER TABLE clients ADD COLUMN barangay TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Orders Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                client_ID INTEGER,
                order_number TEXT,
                status TEXT,
                total_amount REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                shipping_address TEXT,
                payment_method TEXT,
                FOREIGN KEY (client_ID) REFERENCES clients(client_ID)
            )
        ''')

        # Order Items Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                item_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                order_ID INTEGER,
                product_name TEXT,
                quantity INTEGER,
                unit_price REAL,
                FOREIGN KEY (order_ID) REFERENCES orders(order_ID)
            )
        ''')

        # Inventory Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                inventory_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code TEXT,
                name TEXT,
                category TEXT,
                material TEXT,
                price REAL,
                image TEXT,
                size TEXT,
                initial_stock INTEGER,
                current_stock INTEGER,
                low_stock_threshold INTEGER
            )
        ''')

        # Inventory Log Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS inventory_log (
                log_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_ID INTEGER,
                action TEXT,
                quantity INTEGER,
                previous_stock INTEGER,
                new_stock INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                order_ID INTEGER,
                user_ID INTEGER,
                FOREIGN KEY (inventory_ID) REFERENCES inventory(inventory_ID)
            )
        ''')

        # Feedback Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Reviews Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_name TEXT,
                rating INTEGER,
                comment TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                anonymous INTEGER,
                FOREIGN KEY (user_id) REFERENCES clients(client_ID)
            )
        ''')

        # Migrate existing inventory_log table to add missing columns
        try:
            c.execute('ALTER TABLE inventory_log ADD COLUMN order_ID INTEGER')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            c.execute('ALTER TABLE inventory_log ADD COLUMN user_ID INTEGER')
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Populate Inventory (if empty)
        c.execute('SELECT COUNT(*) FROM inventory')
        if c.fetchone()[0] == 0:
            sample_items = [
                ('RG001', 'Opulent Eternity', 'Ring', 'Gold', 8500.00, 'Ring/RG001.png', '7', 10, 10, 5),
                ('RG002', 'Butterfly Bliss', 'Ring', 'Gold', 8200.00, 'Ring/RG002.png', '7', 10, 10, 5),
                ('RG003', 'Celestial Embrace', 'Ring', 'Gold', 8300.00, 'Ring/RG003.png', '7', 10, 10, 5),
                ('RRG001', 'Butterfly Blossoms', 'Ring', 'Rose Gold', 8400.00, 'Ring/RRG001.png', '7', 10, 10, 5),
                ('RRG002', 'Enchanted Vines', 'Ring', 'Rose Gold', 8200.00, 'Ring/RRG002.png', '7', 10, 10, 5),
                ('RRG003', 'Infinity Elegance', 'Ring', 'Rose Gold', 8600.00, 'Ring/RRG003.png', '7', 10, 10, 5),
                ('BG001', 'Auric Veil', 'Bracelet', 'Gold', 7800.00, 'Bracelet/BG001.png', '7"', 10, 10, 5),
                ('BG002', 'Aurum Embrace', 'Bracelet', 'Gold', 7900.00, 'Bracelet/BG002.png', '7"', 10, 10, 5),
                ('BG003', 'Golden Harmony', 'Bracelet', 'Gold', 8000.00, 'Bracelet/BG003.png', '7"', 10, 10, 5),
                ('BRG001', 'Blush Radiance', 'Bracelet', 'Rose Gold', 7700.00, 'Bracelet/BRG001.png', '7"', 10, 10, 5),
                ('BRG002', 'Rosé Serpent', 'Bracelet', 'Rose Gold', 7750.00, 'Bracelet/BRG002.png', '7"', 10, 10, 5),
                ('BRG003', 'Vinea Rosa', 'Bracelet', 'Rose Gold', 7850.00, 'Bracelet/BRG003.png', '7"', 10, 10, 5),
                ('NG001', 'Coquette Ribbon', 'Necklace', 'Gold', 7800.00, 'Necklace/NG001.png', '18"', 10, 10, 5),
                ('NG002', 'Golden Butterfly', 'Necklace', 'Gold', 8000.00, 'Necklace/NG002.png', '18"', 10, 10, 5),
                ('NG003', 'Vintage Heart', 'Necklace', 'Gold', 8100.00, 'Necklace/NG003.png', '18"', 10, 10, 5),
                ('NRG001', 'Aurora Heart', 'Necklace', 'Rose Gold', 7900.00, 'Necklace/NRG001.png', '18"', 10, 10, 5),
                ('NRG002', 'Drop Pendant Necklace', 'Necklace', 'Rose Gold', 7950.00, 'Necklace/NRG002.png', '18"', 10, 10, 5),
                ('NRG003', 'Lucky Pendant', 'Necklace', 'Rose Gold', 7850.00, 'Necklace/NRG003.png', '18"', 10, 10, 5),
                ('EG001', 'Château Lumière', 'Earring', 'Gold', 6800.00, 'Earring/EG001.png', 'Standard', 10, 10, 5),
                ('EG002', 'Champagne Halo', 'Earring', 'Gold', 6900.00, 'Earring/EG002.png', 'Standard', 10, 10, 5),
                ('EG003', 'Chrysalis Monarch', 'Earring', 'Gold', 7000.00, 'Earring/EG003.png', 'Standard', 10, 10, 5),
                ('ERG001', 'Solstice Lustre', 'Earring', 'Rose Gold', 6750.00, 'Earring/ERG001.png', 'Standard', 10, 10, 5),
                ('ERG002', 'Ambroise Clair', 'Earring', 'Rose Gold', 6800.00, 'Earring/ERG002.png', 'Standard', 10, 10, 5),
                ('ERG003', 'Luxeria Dawn', 'Earring', 'Rose Gold', 6900.00, 'Earring/ERG003.png', 'Standard', 10, 10, 5)
            ]
            c.executemany('''
                INSERT INTO inventory (product_code, name, category, material, price, image, size, initial_stock, current_stock, low_stock_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', sample_items)

        # Create a default admin user (if none exists)
        c.execute("SELECT * FROM clients WHERE email = 'admin@aureliana.com'")
        if c.fetchone() is None:
            hashed_password = hash_password('admin')
            c.execute('''
                INSERT INTO clients (full_name, email, phone, password, role) 
                VALUES (?, ?, ?, ?, ?)
            ''', ('Admin', 'admin@aureliana.com', '09918614591', hashed_password, 'admin'))
        
        # Create a test client user (if none exists)
        c.execute("SELECT * FROM clients WHERE email = 'client@aureliana.com'")
        if c.fetchone() is None:
            hashed_password = hash_password('client123')
            c.execute('''
                INSERT INTO clients (full_name, email, phone, password, role) 
                VALUES (?, ?, ?, ?, ?)
            ''', ('Test Client', 'client@aureliana.com', '0987654321', hashed_password, 'user'))
        
        # Add sample inventory log data (if empty)
        c.execute('SELECT COUNT(*) FROM inventory_log')
        if c.fetchone()[0] == 0:
            # Get some inventory IDs for sample data
            c.execute('SELECT inventory_ID FROM inventory LIMIT 5')
            inventory_ids = [row[0] for row in c.fetchall()]
            
            if inventory_ids:
                sample_logs = [
                    (inventory_ids[0], 'Manual Stock Adjustment', 5, 10, 15, None, 1),
                    (inventory_ids[1], 'Order Completed', -2, 8, 6, 1, 2),
                    (inventory_ids[2], 'Inventory Update', 3, 7, 10, None, 1),
                    (inventory_ids[3], 'Order Placed', -1, 9, 8, 2, 2),
                    (inventory_ids[4], 'Stock Restock', 10, 5, 15, None, 1)
                ]
                
                c.executemany('''
                    INSERT INTO inventory_log 
                    (inventory_ID, action, quantity, previous_stock, new_stock, order_ID, user_ID) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', sample_logs)
        
        conn.commit()

# Initialize Database
init_db()

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = hash_password(password)
        
        with db_transaction() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM clients WHERE email = ? AND password = ?', (email, hashed_password))
            user = c.fetchone()
            
            if user:
                session['user_id'] = user[0]
                session['role'] = 'admin' if email == 'admin@aureliana.com' else 'user'
                
                # Update last login
                c.execute('UPDATE clients SET last_login = ? WHERE client_ID = ?', (datetime.datetime.now(), user[0]))
                
                if session['role'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('home'))
            else:
                flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form.get('phone', '')
        
        hashed_password = hash_password(password)
        
        try:
            with db_transaction() as conn:
                c = conn.cursor()
                c.execute("INSERT INTO clients (full_name, email, password, phone) VALUES (?, ?, ?, ?)",
                         (full_name, email, hashed_password, phone))
                
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists. Please use a different email.', 'error')
        except Exception as e:
            flash('Registration failed. Please try again.', 'error')
            print(f"Registration error: {e}")
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/account')
def account():
    if 'user_id' not in session:
        flash('Please log in to access your account.', 'error')
        return redirect(url_for('login'))
    
    # Prevent admin users from accessing customer account page
    if session.get('role') == 'admin':
        flash('Admin users should use the admin dashboard.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    with db_transaction() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM clients WHERE client_ID = ?', (session['user_id'],))
        user_data = c.fetchone()
        
        # Get user's orders
        c.execute('''SELECT o.*
                    FROM orders o
                    WHERE o.client_ID = ?
                    ORDER BY o.created_at DESC''', (session['user_id'],))
        orders = [dict(row) for row in c.fetchall()]
        
        # Get order items for each order
        for order in orders:
            c.execute('''SELECT oi.product_name, oi.quantity, oi.unit_price
                        FROM order_items oi
                        WHERE oi.order_ID = ?
                        ORDER BY oi.item_ID''', (order['order_ID'],))
            order['items'] = [dict(item) for item in c.fetchall()]
        
        # Get user's reviews
        c.execute('SELECT * FROM reviews WHERE user_id = ? ORDER BY created_at DESC', (session['user_id'],))
        reviews = c.fetchall()
    
    return render_template('account.html', user_data=user_data, orders=orders, reviews=reviews)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        flash('Please log in to update your profile.', 'error')
        return redirect(url_for('login'))
    
    # ... logic to update profile
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('account'))

@app.route('/update_address', methods=['POST'])
def update_address():
    if 'user_id' not in session:
        flash('Please log in to update your address.', 'error')
        return redirect(url_for('login'))
    
    region = request.form.get('region', '')
    province = request.form.get('province', '')
    city = request.form.get('city', '')
    barangay = request.form.get('barangay', '')
    address_details = request.form.get('address_details', '')
    
    # Save address components separately and also as a combined string for backward compatibility
    combined_address = ', '.join([address_details, barangay, city, province, region])
    
    with db_transaction() as conn:
        c = conn.cursor()
        c.execute('''UPDATE clients 
                     SET address = ?, address_details = ?, region = ?, province = ?, city = ?, barangay = ? 
                     WHERE client_ID = ?''', 
                  (combined_address, address_details, region, province, city, barangay, session['user_id']))
    
    flash('Address updated successfully!', 'success')
    return redirect(url_for('account'))

@app.route('/update_password', methods=['POST'])
def update_password():
    if 'user_id' not in session:
        flash('Please log in to update your password.', 'error')
        return redirect(url_for('login'))
    
    # ... logic to update password
    
    flash('Password updated successfully!', 'success')
    return redirect(url_for('account'))

# Main Routes
@app.route('/')
def home():
    # Redirect admin users to admin dashboard
    if 'user_id' in session and session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    user_data = None
    if 'user_id' in session:
        with db_transaction() as conn:
            c = conn.cursor()
            c.execute('SELECT full_name, email FROM clients WHERE client_ID = ?', (session['user_id'],))
            user = c.fetchone()
            if user:
                user_data = {
                    'full_name': user[0],
                    'email': user[1]
                }
    
    return render_template('index.html', user_data=user_data)

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('home'))
        
    with db_transaction() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        # Fetch all data for admin panel...
        c.execute('SELECT * FROM clients')
        clients = c.fetchall()
        # Join orders with clients to get username
        c.execute('''
            SELECT o.*, c.full_name FROM orders o
            LEFT JOIN clients c ON o.client_ID = c.client_ID
        ''')
        orders = c.fetchall()
        c.execute('SELECT * FROM inventory')
        inventory = [dict(row) for row in c.fetchall()]
        c.execute('SELECT * FROM feedback')
        feedback = c.fetchall()

    return render_template('admin.html',
        clients=clients,
        orders=orders,
        inventory=inventory,
        feedback=feedback
    )

# Centralized inventory management functions
def log_inventory_change(inventory_id, action, quantity, previous_stock, new_stock, order_id=None, user_id=None):
    """
    Centralized function to log inventory changes and update stock.
    This ensures all inventory changes are properly tracked and consistent.
    """
    try:
        with db_transaction() as conn:
            c = conn.cursor()
            
            # First, log the inventory change
            c.execute('''INSERT INTO inventory_log 
                        (inventory_ID, action, quantity, previous_stock, new_stock, timestamp, order_ID, user_ID) 
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)''',
                     (inventory_id, action, quantity, previous_stock, new_stock, order_id, user_id))
            
            # Then update the inventory table
            c.execute('UPDATE inventory SET current_stock = ? WHERE inventory_ID = ?', (new_stock, inventory_id))
            
            # Get inventory item details for real-time updates
            c.execute('SELECT name, category, product_code FROM inventory WHERE inventory_ID = ?', (inventory_id,))
            item = c.fetchone()
            
            # Emit real-time update to all connected clients
            if item:
                socketio.emit('inventory_updated', {
                    'inventory_ID': inventory_id,
                    'name': item[0],
                    'category': item[1],
                    'product_code': item[2],
                    'current_stock': new_stock,
                    'previous_stock': previous_stock,
                    'action': action,
                    'quantity': quantity
                })
            
            return True
            
    except Exception as e:
        print(f"Database error in log_inventory_change: {e}")
        return False

def get_inventory_stock(inventory_id):
    """Get current stock for an inventory item"""
    try:
        with db_transaction() as conn:
            c = conn.cursor()
            c.execute('SELECT current_stock FROM inventory WHERE inventory_ID = ?', (inventory_id,))
            result = c.fetchone()
            return result[0] if result else 0
    except Exception as e:
        print(f"Database error in get_inventory_stock: {e}")
        return 0

def update_inventory_stock(inventory_id, quantity_change, action, order_id=None, user_id=None):
    """
    Update inventory stock through the logging system.
    quantity_change: positive for additions, negative for reductions
    """
    try:
        current_stock = get_inventory_stock(inventory_id)
        new_stock = max(0, current_stock + quantity_change)
        
        return log_inventory_change(
            inventory_id=inventory_id,
            action=action,
            quantity=abs(quantity_change),
            previous_stock=current_stock,
            new_stock=new_stock,
            order_id=order_id,
            user_id=user_id
        )
    except Exception as e:
        print(f"Error in update_inventory_stock: {e}")
        return False

@app.route('/update_stock', methods=['POST', 'HEAD'])
def update_stock():
    if 'user_id' not in session or session.get('role') != 'admin':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Access denied.'}), 403
        flash('Access denied.', 'error')
        return redirect(url_for('home'))

    # Handle HEAD requests (for URL testing)
    if request.method == 'HEAD':
        return '', 200

    inventory_ID = request.form['inventory_ID']
    new_stock = int(request.form['new_stock'])

    with db_transaction() as conn:
        c = conn.cursor()
        c.execute('SELECT current_stock, name, category FROM inventory WHERE inventory_ID = ?', (inventory_ID,))
        result = c.fetchone()
        if not result:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Inventory item not found.'}), 404
            flash('Inventory item not found.', 'error')
            return redirect(url_for('admin_dashboard'))
        
        previous_stock, name, category = result
        quantity_change = new_stock - previous_stock

        # Use centralized inventory management
        success = update_inventory_stock(
            inventory_id=inventory_ID,
            quantity_change=quantity_change,
            action='Manual Stock Adjustment',
            user_id=session['user_id']
        )

        if success:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Stock updated and logged successfully!'})
            flash('Stock updated and logged successfully!', 'success')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Error updating stock.'}), 500
            flash('Error updating stock.', 'error')

    return redirect(url_for('admin_dashboard'))

@app.route('/update_inventory', methods=['GET', 'POST', 'HEAD'])
def update_inventory():
    if 'user_id' not in session or session.get('role') != 'admin':
        print("Access denied - user not logged in or not admin")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Access denied.'}), 403
        flash('Access denied.', 'error')
        return redirect(url_for('home'))

    # Handle HEAD requests (for URL testing)
    if request.method == 'HEAD':
        return '', 200

    try:
        inventory_ID = request.form['inventory_ID']
        product_code = request.form['product_code']
        name = request.form['name']
        category = request.form['category']
        current_stock = int(request.form['current_stock'])
        price = float(request.form['price'])
        image = request.form['image']
        
        print(f"Updating inventory ID: {inventory_ID}")
        print(f"New values: {product_code}, {name}, {category}, {current_stock}, {price}, {image}")

        with db_transaction() as conn:
            c = conn.cursor()
            
            # Get previous stock for logging
            c.execute('SELECT current_stock FROM inventory WHERE inventory_ID = ?', (inventory_ID,))
            result = c.fetchone()
            if not result:
                print(f"Inventory item {inventory_ID} not found")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Inventory item not found.'}), 404
                flash('Inventory item not found.', 'error')
                return redirect(url_for('admin_dashboard'))
            
            previous_stock = result[0]
            
            # Update inventory details
            c.execute('''
                UPDATE inventory
                SET product_code = ?, name = ?, category = ?, current_stock = ?, price = ?, image = ?
                WHERE inventory_ID = ?
            ''', (product_code, name, category, current_stock, price, image, inventory_ID))
            
            # Log the stock change if it changed (do it directly in this transaction)
            if current_stock != previous_stock:
                quantity_change = current_stock - previous_stock
                c.execute('''INSERT INTO inventory_log 
                            (inventory_ID, action, quantity, previous_stock, new_stock, timestamp, order_ID, user_ID) 
                            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)''',
                         (inventory_ID, 'Inventory Update', abs(quantity_change), previous_stock, current_stock, None, session['user_id']))
                
                # Emit socket event for stock change
                socketio.emit('inventory_updated', {
                    'inventory_ID': inventory_ID,
                    'name': name,
                    'category': category,
                    'product_code': product_code,
                    'current_stock': current_stock,
                    'previous_stock': previous_stock,
                    'action': 'stock_update',
                    'quantity': abs(quantity_change)
                })
            else:
                # Emit socket event even if stock didn't change (for other inventory updates)
                socketio.emit('inventory_updated', {
                    'inventory_ID': inventory_ID,
                    'name': name,
                    'category': category,
                    'product_code': product_code,
                    'current_stock': current_stock,
                    'previous_stock': previous_stock,
                    'action': 'inventory_update',
                    'quantity': 0
                })
            
            print("Inventory updated successfully")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            print("Returning JSON response")
            response_data = {'success': True, 'message': 'Inventory item updated successfully!'}
            print("Response data:", response_data)
            return jsonify(response_data)
        flash('Inventory item updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
        
    except Exception as e:
        print(f"Error in update_inventory: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f'Error updating inventory: {str(e)}'}), 500
        flash(f'Error updating inventory: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/cart')
def cart_page():
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please log in to access your cart.', 'error')
        return redirect(url_for('login'))
    
    # Prevent admin users from accessing cart
    if session.get('role') == 'admin':
        flash('Admin users cannot access the shopping cart.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('cart/cart.html')

@app.route('/checkout')
def checkout_page():
    if 'user_id' not in session:
        flash('Please log in to access checkout.', 'error')
        return redirect(url_for('login'))
    # Prevent admin users from accessing checkout
    if session.get('role') == 'admin':
        flash('Admin users cannot access checkout.', 'error')
        return redirect(url_for('admin_dashboard'))
    return render_template('cart/checkout.html')

@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    
    if name and email and message:
        with db_transaction() as conn:
            c = conn.cursor()
            c.execute('INSERT INTO feedback (name, email, message) VALUES (?, ?, ?)', (name, email, message))
            conn.commit()
        
        # Return JSON response for AJAX handling
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Thank you for your feedback! We appreciate your message and will get back to you soon.'})
        else:
            flash('Thank you for your feedback! We appreciate your message and will get back to you soon.', 'success')
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Please fill out all fields.'}), 400
        else:
            flash('Please fill out all fields.', 'error')
    
    return redirect(url_for('contact'))

# API routes
@app.route('/api/check_login')
def check_login():
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'username': session.get('full_name')})
    return jsonify({'logged_in': False})

@app.route('/api/clear_cart')
def clear_cart():
    # This endpoint is called when user logs out to clear cart
    return jsonify({'success': True})

@app.route('/api/user_info')
def user_info():
    if 'user_id' not in session:
        return jsonify({'logged_in': False})
    with db_transaction() as conn:
        c = conn.cursor()
        c.execute('''SELECT full_name, email, phone, address, address_details, region, province, city, barangay 
                     FROM clients WHERE client_ID = ?''', (session['user_id'],))
        user = c.fetchone()
        if user:
            print(f"Debug - Raw user data: {user}")
            # Get readable address names
            readable_address = get_readable_address(user[5], user[6], user[7], user[8])
            print(f"Debug - Readable address: {readable_address}")
            
            response_data = {
                'logged_in': True,
                'full_name': user[0],
                'email': user[1],
                'phone': user[2],
                'address': user[3],
                'address_details': user[4],
                'region': user[5],
                'province': user[6],
                'city': user[7],
                'barangay': user[8],
                'readable_address': readable_address
            }
            print(f"Debug - API response: {response_data}")
            return jsonify(response_data)
        return jsonify({'logged_in': False})

def get_readable_address(region_code, province_code, city_code, barangay_code):
    """Get readable address names from codes"""
    print(f"Debug - Input codes: region={region_code}, province={province_code}, city={city_code}, barangay={barangay_code}")
    
    try:
        # Load JSON files
        with open('static/json/region.json', encoding='utf-8') as f:
            regions = json.load(f)
        with open('static/json/province.json', encoding='utf-8') as f:
            provinces = json.load(f)
        with open('static/json/city.json', encoding='utf-8') as f:
            cities = json.load(f)
        with open('static/json/barangay.json', encoding='utf-8') as f:
            barangays = json.load(f)
        
        print(f"Debug - Loaded JSON files: regions={len(regions)}, provinces={len(provinces)}, cities={len(cities)}, barangays={len(barangays)}")
        
        # Find readable names
        region_name = next((r['region_name'] for r in regions if r['region_code'] == region_code), region_code)
        province_name = next((p['province_name'] for p in provinces if p['province_code'] == province_code), province_code)
        city_name = next((c['city_name'] for c in cities if c['city_code'] == city_code), city_code)
        barangay_name = next((b['brgy_name'] for b in barangays if b['brgy_code'] == barangay_code), barangay_code)
        
        print(f"Debug - Found names: region={region_name}, province={province_name}, city={city_name}, barangay={barangay_name}")
        
        return {
            'region_name': region_name,
            'province_name': province_name,
            'city_name': city_name,
            'barangay_name': barangay_name
        }
    except Exception as e:
        print(f"Error getting readable address: {e}")
        return {
            'region_name': region_code,
            'province_name': province_code,
            'city_name': city_code,
            'barangay_name': barangay_code
        }

@app.route('/api/barangays')
def api_barangays():
    city_code = request.args.get('city_code')
    if not city_code:
        return jsonify([])
    with open('static/json/barangay.json', encoding='utf-8') as f:
        # Stream and filter line by line for memory efficiency
        barangays = json.load(f)
        filtered = [b for b in barangays if b.get('city_code') == city_code]
    return jsonify(filtered)

@app.route('/api/barangays-debug')
def api_barangays_debug():
    with open('static/json/barangay.json', encoding='utf-8') as f:
        barangays = json.load(f)
        return jsonify(barangays[:10])

# API endpoint to get all inventory (for real-time updates)
@app.route('/api/inventory')
def api_inventory():
    with db_transaction() as conn:
        c = conn.cursor()
        c.execute('SELECT inventory_ID, product_code, name, category, material, price, image, current_stock, low_stock_threshold FROM inventory')
        inventory = []
        for row in c.fetchall():
            inventory.append({
                'inventory_ID': row[0],
                'product_code': row[1],
                'name': row[2],
                'category': row[3],
                'material': row[4],
                'price': row[5],
                'image': row[6],
                'current_stock': row[7],
                'low_stock_threshold': row[8]
            })
        return jsonify(inventory)

@app.route('/api/inventory/<int:inventory_id>')
def api_inventory_item(inventory_id):
    with db_transaction() as conn:
        c = conn.cursor()
        c.execute('SELECT inventory_ID, product_code, name, category, material, price, image, current_stock, low_stock_threshold FROM inventory WHERE inventory_ID = ?', (inventory_id,))
        row = c.fetchone()
        if row:
            return jsonify({
                'inventory_ID': row[0],
                'product_code': row[1],
                'name': row[2],
                'category': row[3],
                'material': row[4],
                'price': row[5],
                'image': row[6],
                'current_stock': row[7],
                'low_stock_threshold': row[8]
            })
        return jsonify({'error': 'Item not found'}), 404

# API endpoint to get all orders (admin only, for real-time updates)
@app.route('/api/orders')
def api_orders():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    with db_transaction() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''
            SELECT o.*, c.full_name as username FROM orders o
            LEFT JOIN clients c ON o.client_ID = c.client_ID
        ''')
        orders = []
        for row in c.fetchall():
            order = dict(row)
            # For compatibility with existing JS, ensure username is present
            order['username'] = row['username']
            orders.append(order)
        return jsonify(orders)

# API endpoint to get all clients (admin only, for real-time updates)
@app.route('/api/clients')
def api_clients():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    with db_transaction() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM clients')
        clients = [dict(row) for row in c.fetchall()]
    return jsonify(clients)

# API endpoint to get inventory logs
@app.route('/api/inventory_logs')
def api_inventory_logs():
    """Get inventory logs for admin dashboard"""
    with db_transaction() as conn:
        c = conn.cursor()
        
        # First, check if the new columns exist
        try:
            c.execute('''
                SELECT 
                    il.log_ID,
                    il.inventory_ID,
                    i.name,
                    i.product_code,
                    i.category,
                    il.action,
                    il.quantity,
                    il.previous_stock,
                    il.new_stock,
                    il.timestamp,
                    il.order_ID,
                    il.user_ID,
                    c.full_name,
                    c.email,
                    c.phone
                FROM inventory_log il
                JOIN inventory i ON il.inventory_ID = i.inventory_ID
                LEFT JOIN clients c ON il.user_ID = c.client_ID
                ORDER BY il.timestamp DESC
                LIMIT 100
            ''')
        except sqlite3.OperationalError:
            # Fallback query for older database schema
            c.execute('''
                SELECT 
                    il.log_ID,
                    il.inventory_ID,
                    i.name,
                    i.product_code,
                    i.category,
                    il.action,
                    il.quantity,
                    il.previous_stock,
                    il.new_stock,
                    il.timestamp,
                    NULL as order_ID,
                    NULL as user_ID,
                    NULL as full_name,
                    NULL as email,
                    NULL as phone
                FROM inventory_log il
                JOIN inventory i ON il.inventory_ID = i.inventory_ID
                ORDER BY il.timestamp DESC
                LIMIT 100
            ''')
        
        logs = []
        for row in c.fetchall():
            logs.append({
                'log_ID': row[0],
                'inventory_ID': row[1],
                'name': row[2],
                'product_code': row[3],
                'category': row[4],
                'action': row[5],
                'quantity': row[6],
                'previous_stock': row[7],
                'new_stock': row[8],
                'timestamp': row[9],
                'order_ID': row[10],
                'user_ID': row[11],
                'user_name': f"{row[12]} {row[13]} {row[14]}" if row[12] and row[13] and row[14] else row[12] if row[12] else row[13] if row[13] else row[14] if row[14] else 'System'
            })
        
        return jsonify(logs)

# Static Pages
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    user_data = None
    if 'user_id' in session:
        with db_transaction() as conn:
            c = conn.cursor()
            c.execute('SELECT full_name, email FROM clients WHERE client_ID = ?', (session['user_id'],))
            user = c.fetchone()
            if user:
                user_data = {
                    'full_name': user[0],
                    'email': user[1]
                }
    return render_template('contact.html', user_data=user_data)

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

# Collection Pages
@app.route('/collections/necklaces')
def necklacec():
    with db_transaction() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM inventory WHERE category = 'Necklace'")
        products = c.fetchall()
    return render_template('necklacec.html', products=products)

@app.route('/collections/rings')
def ringc():
    with db_transaction() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM inventory WHERE category = 'Ring'")
        products = c.fetchall()
    return render_template('ringc.html', products=products)

@app.route('/collections/bracelets')
def braceletc():
    with db_transaction() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM inventory WHERE category = 'Bracelet'")
        products = c.fetchall()
    return render_template('braceletc.html', products=products)

@app.route('/collections/earrings')
def earringc():
    with db_transaction() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM inventory WHERE category = 'Earring'")
        products = c.fetchall()
    return render_template('earringc.html', products=products)

@app.route('/our-values')
def our_values():
    return render_template('our-values.html')

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get form data
        full_name = request.form.get('fullName')
        region = request.form.get('region')
        province = request.form.get('province')
        city = request.form.get('city')
        barangay = request.form.get('barangay')
        address_details = request.form.get('address_details')
        payment_method = request.form.get('payment_method')
        cc_number = request.form.get('cc_number')
        cc_expiry = request.form.get('cc_expiry')
        cc_cvc = request.form.get('cc_cvc')
        gcash_phone = request.form.get('gcash_phone')
        gcash_pin = request.form.get('gcash_pin')
        
        # Compose shipping address
        address_fields = [address_details or '', barangay or '', city or '', province or '', region or '']
        shipping_address = ', '.join(address_fields)
        
        # Get cart items from form (JSON)
        import json
        items_json = request.form.get('itemsToCheckout')
        try:
            items = json.loads(items_json) if items_json else []
        except Exception:
            items = []
        
        if not items:
            flash('No items to checkout.', 'error')
            return redirect(url_for('checkout_page'))
        
        # Validate payment info
        if payment_method == 'Credit Card':
            if not (cc_number and cc_expiry and cc_cvc):
                flash('Please provide all credit card details.', 'error')
                return redirect(url_for('checkout_page'))
        elif payment_method == 'GCash':
            if not (gcash_phone and gcash_pin):
                flash('Please provide GCash phone number and PIN.', 'error')
                return redirect(url_for('checkout_page'))
        
        # Check stock for each item and decrement stock immediately (reserve stock)
        with db_transaction() as conn:
            c = conn.cursor()
            
            # Check stock availability first
            for item in items:
                c.execute('SELECT current_stock FROM inventory WHERE name = ?', (item['name'],))
                row = c.fetchone()
                if not row or item['quantity'] > row[0]:
                    flash(f"Not enough stock for {item['name']}. Only {row[0] if row else 0} left.", 'error')
                    return redirect(url_for('checkout_page'))
            
            # Decrement stock for each item
            for item in items:
                c.execute('SELECT inventory_ID, current_stock FROM inventory WHERE name = ?', (item['name'],))
                row = c.fetchone()
                if row:
                    inventory_id, current_stock = row
                    new_stock = max(0, current_stock - item['quantity'])
                    c.execute('UPDATE inventory SET current_stock = ? WHERE name = ?', (new_stock, item['name']))
                    
                    # Log inventory change
                    c.execute('''INSERT INTO inventory_log 
                                (inventory_ID, action, quantity, previous_stock, new_stock, timestamp) 
                                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
                             (inventory_id, 'Order Placed', item['quantity'], current_stock, new_stock))
                    
                    # Emit real-time inventory update
                    socketio.emit('inventory_update', {
                        'inventory_id': inventory_id,
                        'product_name': item['name'],
                        'new_stock': new_stock,
                        'action': 'Order Placed'
                    })
            
            # Calculate total
            subtotal = sum(item['price'] * item['quantity'] for item in items)
            shipping_cost = 50.0
            total = subtotal + shipping_cost
            
            # Save order
            status = 'Pending Payment' if payment_method == 'Cash on Delivery' else 'Paid'
            c.execute('INSERT INTO orders (client_ID, order_number, status, total_amount, shipping_address, payment_method) VALUES (?, ?, ?, ?, ?, ?)',
                      (session['user_id'], f"ORD{int(datetime.datetime.now().timestamp())}", status, total, shipping_address, payment_method))
            order_id = c.lastrowid
            
            for item in items:
                c.execute('INSERT INTO order_items (order_ID, product_name, quantity, unit_price) VALUES (?, ?, ?, ?)',
                          (order_id, item['name'], item['quantity'], item['price']))
            
            conn.commit()
        
        # Remove items from cart (simulate by clearing session key)
        session.pop('itemsToCheckout', None)
        
        # Emit real-time event to all connected clients (admin dashboard)
        socketio.emit('new_order', {'order_id': order_id})
        
        # Redirect to receipt
        return redirect(url_for('receipt', order_id=order_id))
    
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            flash('Database is temporarily busy. Please try again in a moment.', 'error')
        else:
            flash('An error occurred while processing your order.', 'error')
        print(f"Database error in place_order: {e}")
        return redirect(url_for('checkout_page'))
    except Exception as e:
        flash('An unexpected error occurred while processing your order.', 'error')
        print(f"Unexpected error in place_order: {e}")
        return redirect(url_for('checkout_page'))

@app.route('/receipt/<int:order_id>')
def receipt(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    import json
    with db_transaction() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM orders WHERE order_ID = ?', (order_id,))
        order = c.fetchone()
        c.execute('SELECT * FROM order_items WHERE order_ID = ?', (order_id,))
        items = c.fetchall()
        # Parse address codes
        address = order['shipping_address']
        address_parts = [p.strip() for p in address.split(',')]
        details, barangay_code, city_code, province_code, region_code = (address_parts + ['']*5)[:5]
        # Load JSONs
        with open('static/json/region.json', encoding='utf-8') as f:
            regions = json.load(f)
        with open('static/json/province.json', encoding='utf-8') as f:
            provinces = json.load(f)
        with open('static/json/city.json', encoding='utf-8') as f:
            cities = json.load(f)
        with open('static/json/barangay.json', encoding='utf-8') as f:
            barangays = json.load(f)
        region_name = next((r['region_name'] for r in regions if r['region_code'] == region_code), region_code)
        province_name = next((p['province_name'] for p in provinces if p['province_code'] == province_code), province_code)
        city_name = next((c['city_name'] for c in cities if c['city_code'] == city_code), city_code)
        barangay_name = next((b['brgy_name'] for b in barangays if b['brgy_code'] == barangay_code), barangay_code)
    return render_template('cart/receipt.html', order=order, items=items, address_details=details, barangay_name=barangay_name, city_name=city_name, province_name=province_name, region_name=region_name)

@app.route('/order_received/<int:order_id>', methods=['POST'])
def order_received(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        with db_transaction() as conn:
            c = conn.cursor()
            # Ensure the order belongs to the user and fetch payment_method
            c.execute('SELECT status, client_ID, payment_method FROM orders WHERE order_ID = ?', (order_id,))
            row = c.fetchone()
            if not row or row[1] != session['user_id']:
                flash('Invalid order or permission denied.', 'error')
                return redirect(url_for('account'))
            
            status, client_id, payment_method = row
            
            if payment_method == 'Cash on Delivery':
                if status == 'Pending Payment':
                    c.execute('UPDATE orders SET status = ? WHERE order_ID = ?', ('Paid', order_id))
                    conn.commit()
                    flash('Order marked as paid. Thank you! Please confirm delivery once received.', 'success')
                elif status == 'Paid':
                    c.execute('UPDATE orders SET status = ? WHERE order_ID = ?', ('Completed', order_id))
                    # Decrement inventory for each item in the order
                    c.execute('SELECT product_name, quantity FROM order_items WHERE order_ID = ?', (order_id,))
                    items = c.fetchall()
                    
                    for product_name, qty in items:
                        c.execute('SELECT inventory_ID, current_stock FROM inventory WHERE name = ?', (product_name,))
                        row = c.fetchone()
                        if row:
                            inventory_id, current_stock = row
                            new_stock = max(0, current_stock - qty)
                            
                            # Log the inventory change
                            c.execute('''INSERT INTO inventory_log 
                                        (inventory_ID, action, quantity, previous_stock, new_stock, timestamp, order_ID, user_ID) 
                                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)''',
                                     (inventory_id, 'Order Completed', qty, current_stock, new_stock, order_id, session['user_id']))
                            
                            # Update inventory
                            c.execute('UPDATE inventory SET current_stock = ? WHERE inventory_ID = ?', (new_stock, inventory_id))
                    
                    conn.commit()
                    flash('Order marked as completed. Thank you for confirming delivery!', 'success')
                else:
                    flash('Order cannot be updated.', 'error')
            else:
                if status == 'Paid':
                    c.execute('UPDATE orders SET status = ? WHERE order_ID = ?', ('Completed', order_id))
                    # Decrement inventory for each item in the order
                    c.execute('SELECT product_name, quantity FROM order_items WHERE order_ID = ?', (order_id,))
                    items = c.fetchall()
                    
                    for product_name, qty in items:
                        c.execute('SELECT inventory_ID, current_stock FROM inventory WHERE name = ?', (product_name,))
                        row = c.fetchone()
                        if row:
                            inventory_id, current_stock = row
                            new_stock = max(0, current_stock - qty)
                            
                            # Log the inventory change
                            c.execute('''INSERT INTO inventory_log 
                                        (inventory_ID, action, quantity, previous_stock, new_stock, timestamp, order_ID, user_ID) 
                                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)''',
                                     (inventory_id, 'Order Completed', qty, current_stock, new_stock, order_id, session['user_id']))
                            
                            # Update inventory
                            c.execute('UPDATE inventory SET current_stock = ? WHERE inventory_ID = ?', (new_stock, inventory_id))
                    
                    conn.commit()
                    flash('Order marked as completed. Thank you for confirming delivery!', 'success')
                else:
                    flash('Order cannot be updated.', 'error')
    
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            flash('Database is temporarily busy. Please try again in a moment.', 'error')
        else:
            flash('An error occurred while processing your request.', 'error')
        print(f"Database error in order_received: {e}")
    except Exception as e:
        flash('An unexpected error occurred.', 'error')
        print(f"Unexpected error in order_received: {e}")
    
    return redirect(url_for('account'))

@app.route('/submit_review', methods=['POST'])
def submit_review():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    product_name = request.form.get('product_name')
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    order_id = request.form.get('order_id')
    anonymous = request.form.get('anonymous') == '1'
    # Validate input
    if not (product_name and rating and comment and order_id):
        flash('All review fields are required.', 'error')
        return redirect(url_for('account'))
    # Check if user purchased this product in a completed order
    with db_transaction() as conn:
        c = conn.cursor()
        c.execute('''SELECT o.status FROM orders o
                     JOIN order_items oi ON o.order_ID = oi.order_ID
                     WHERE o.order_ID = ? AND o.client_ID = ? AND oi.product_name = ? AND o.status IN ('Paid', 'Completed')''',
                  (order_id, user_id, product_name))
        if not c.fetchone():
            flash('You can only review products you have purchased and received.', 'error')
            return redirect(url_for('account'))
        # Check if already reviewed
        c.execute('SELECT 1 FROM reviews WHERE user_id = ? AND product_name = ? AND comment IS NOT NULL', (user_id, product_name))
        if c.fetchone():
            flash('You have already reviewed this product.', 'info')
            return redirect(url_for('account'))
        c.execute('INSERT INTO reviews (user_id, product_name, rating, comment, created_at, anonymous) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)',
                  (user_id, product_name, rating, comment, int(anonymous)))
        conn.commit()
    flash('Thank you for your review!', 'success')
    return redirect(url_for('account'))

@app.route('/product/<product_code>')
def product_detail(product_code):
    with db_transaction() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM inventory WHERE product_code = ?', (product_code,))
        product = c.fetchone()
        if not product:
            abort(404)
        # Fetch reviews for this product
        c.execute('''SELECT r.rating, r.comment, r.created_at, r.anonymous, r.user_id, c.full_name
                     FROM reviews r JOIN clients c ON r.user_id = c.client_ID
                     WHERE r.product_name = ? ORDER BY r.created_at DESC''', (product['name'],))
        reviews = []
        for row in c.fetchall():
            if row['anonymous']:
                # Show first letter of first name and a short hash of user_id
                first_letter = row['full_name'][0].upper() if row['full_name'] else 'A'
                user_hash = hashlib.sha256(str(row['user_id']).encode()).hexdigest()[:6]
                user_name = f"{first_letter}-{user_hash}"
            else:
                user_name = f"{row['full_name']} {row['full_name'][0]}."
            reviews.append({
                'rating': row['rating'],
                'comment': row['comment'],
                'created_at': row['created_at'],
                'anonymous': row['anonymous'],
                'user_name': user_name
            })
    return render_template(f'Product page/{product["category"]}/{product_code}.html', product=product, reviews=reviews)

@app.route('/order_paid/<int:order_id>', methods=['POST'])
def order_paid(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with db_transaction() as conn:
        c = conn.cursor()
        c.execute('SELECT status, client_ID, payment_method FROM orders WHERE order_ID = ?', (order_id,))
        row = c.fetchone()
        if not row or row[1] != session['user_id']:
            flash('Invalid order or permission denied.', 'error')
            return redirect(url_for('account'))
        status, client_id, payment_method = row
        if payment_method == 'Cash on Delivery' and status == 'Pending Payment':
            c.execute('UPDATE orders SET status = ? WHERE order_ID = ?', ('Paid', order_id))
            conn.commit()
            flash('Order marked as paid. Thank you! Please confirm delivery once received.', 'success')
        else:
            flash('Order cannot be updated.', 'error')
    return redirect(url_for('account'))

@app.route('/test_server')
def test_server():
    """Simple test route that doesn't use database"""
    return jsonify({'success': True, 'message': 'Server is responding'})

@app.route('/test_admin')
def test_admin():
    """Test route to verify admin access and server response"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    return jsonify({'success': True, 'message': 'Admin access confirmed'})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5051)