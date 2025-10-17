import sqlite3
import os
import hashlib
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'supersecretkey'

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Database Setup
def init_db():
    with sqlite3.connect('aureliana.db') as conn:
        c = conn.cursor()

        # Clients Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                client_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                address TEXT,
                last_login DATETIME
            )
        ''')

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
                FOREIGN KEY (inventory_ID) REFERENCES inventory(inventory_ID)
            )
        ''')

        # Feedback Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

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
        c.execute("SELECT * FROM clients WHERE username = 'admin'")
        if c.fetchone() is None:
            hashed_password = hash_password('admin')
            c.execute('''
                INSERT INTO clients (first_name, last_name, email, phone, username, password, role) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('Admin', 'Admin', 'admin@aureliana.com', '09918614591', 'admin', hashed_password, 'admin'))
        
        # Create a test client user (if none exists)
        c.execute("SELECT * FROM clients WHERE username = 'client'")
        if c.fetchone() is None:
            hashed_password = hash_password('client123')
            c.execute('''
                INSERT INTO clients (first_name, last_name, email, phone, username, password, role) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('Test', 'Client', 'client@aureliana.com', '0987654321', 'client', hashed_password, 'user'))
        
        conn.commit()

# Initialize Database
init_db()

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)
        
        with sqlite3.connect('aureliana.db') as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM clients WHERE username = ? AND password = ?', (username, hashed_password))
            user = c.fetchone()
            
            if user:
                session['user_id'] = user[0]
                session['username'] = user[5]
                session['role'] = user[7]
                
                c.execute('UPDATE clients SET last_login = ? WHERE client_ID = ?', (datetime.datetime.now(), user[0]))
                conn.commit()
                
                flash('Login successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return redirect(url_for('register'))
            
        hashed_password = hash_password(password)

        try:
            with sqlite3.connect('aureliana.db') as conn:
                c = conn.cursor()
                c.execute("INSERT INTO clients (first_name, last_name, email, phone, username, password, role, last_login) VALUES (?, ?, ?, ?, ?, ?, 'user', ?)",
                          (first_name, last_name, email, phone, username, hashed_password, datetime.datetime.now()))
                conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists.', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Prevent admin users from accessing customer account page
    if session.get('role') == 'admin':
        flash('Admin users should use the admin dashboard.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    with sqlite3.connect('aureliana.db') as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Fetch user data
        c.execute('SELECT * FROM clients WHERE client_ID = ?', (session['user_id'],))
        user = c.fetchone()
        
        if user is None:
            session.clear()
            return redirect(url_for('login'))
            
        # Fetch user's orders
        c.execute('''
            SELECT * FROM orders 
            WHERE client_ID = ? 
            ORDER BY created_at DESC
        ''', (session['user_id'],))
        orders_data = c.fetchall()
        
        orders = []
        for order_row in orders_data:
            order = dict(order_row)
            c.execute('''
                SELECT * FROM order_items 
                WHERE order_ID = ?
            ''', (order['order_ID'],))
            order['items'] = [dict(item) for item in c.fetchall()]
            orders.append(order)
        print("orders type:", type(orders), "orders value:", orders)
            
    return render_template('account.html', user=user, orders=orders)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # ... logic to update profile
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('account'))

@app.route('/update_address', methods=['POST'])
def update_address():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    region = request.form.get('region', '')
    province = request.form.get('province', '')
    city = request.form.get('city', '')
    barangay = request.form.get('barangay', '')
    address_details = request.form.get('address_details', '')
    # Save as a single string for now: details, barangay, city, province, region
    address = ', '.join([address_details, barangay, city, province, region])
    with sqlite3.connect('aureliana.db') as conn:
        c = conn.cursor()
        c.execute('UPDATE clients SET address = ? WHERE client_ID = ?', (address, session['user_id']))
        conn.commit()
    flash('Address updated successfully!', 'success')
    return redirect(url_for('account'))

@app.route('/update_password', methods=['POST'])
def update_password():
    if 'user_id' not in session:
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
    
    with sqlite3.connect('aureliana.db') as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM inventory')
        products = c.fetchall()
    return render_template('index.html', products=products)

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('home'))
        
    with sqlite3.connect('aureliana.db') as conn:
        c = conn.cursor()
        # Fetch all data for admin panel...
        c.execute('SELECT * FROM clients')
        clients = c.fetchall()
        c.execute('SELECT * FROM orders')
        orders = c.fetchall()
        c.execute('SELECT * FROM inventory')
        inventory = c.fetchall()
        c.execute('SELECT * FROM feedback')
        feedback = c.fetchall()
        c.execute('SELECT log_ID, inventory_ID, action, quantity, previous_stock, new_stock, timestamp FROM inventory_log ORDER BY timestamp DESC')
        inventory_logs = c.fetchall()

    return render_template('admin.html',
        clients=clients,
        orders=orders,
        inventory=inventory,
        feedback=feedback,
        inventory_logs=inventory_logs
    )

@app.route('/update_stock', methods=['POST'])
def update_stock():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('home'))

    inventory_ID = request.form['inventory_ID']
    new_stock = int(request.form['new_stock'])

    with sqlite3.connect('aureliana.db') as conn:
        c = conn.cursor()
        c.execute('SELECT current_stock FROM inventory WHERE inventory_ID = ?', (inventory_ID,))
        previous_stock = c.fetchone()[0]

        c.execute('UPDATE inventory SET current_stock = ? WHERE inventory_ID = ?', (new_stock, inventory_ID))
        c.execute('''
            INSERT INTO inventory_log (inventory_ID, action, quantity, previous_stock, new_stock)
            VALUES (?, ?, ?, ?, ?)
        ''', (inventory_ID, 'adjust', abs(new_stock - previous_stock), previous_stock, new_stock))

        conn.commit()

    flash('Stock updated and logged successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/cart')
def cart_page():
    # Prevent admin users from accessing cart
    if 'user_id' in session and session.get('role') == 'admin':
        flash('Admin users cannot access the shopping cart.', 'error')
        return redirect(url_for('admin_dashboard'))
    return render_template('cart/cart.html')

@app.route('/checkout')
def checkout_page():
    if 'user_id' not in session:
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
    subject = request.form.get('subject')
    message = request.form.get('message')
    if name and email and subject and message:
        with sqlite3.connect('aureliana.db') as conn:
            c = conn.cursor()
            c.execute('INSERT INTO feedback (name, email, subject, message) VALUES (?, ?, ?, ?)', (name, email, subject, message))
            conn.commit()
        flash('Thank you for your feedback!', 'success')
    else:
        flash('Please fill out all fields.', 'error')
    return redirect(url_for('contact'))

# API routes
@app.route('/api/check_login')
def check_login():
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'username': session.get('username')})
    return jsonify({'logged_in': False})

@app.route('/api/clear_cart')
def clear_cart():
    # This endpoint is called when user logs out to clear cart
    return jsonify({'success': True})

@app.route('/api/user_info')
def user_info():
    if 'user_id' not in session:
        return jsonify({'logged_in': False})
    with sqlite3.connect('aureliana.db') as conn:
        c = conn.cursor()
        c.execute('SELECT first_name, last_name, email, phone, address FROM clients WHERE client_ID = ?', (session['user_id'],))
        user = c.fetchone()
        if not user:
            return jsonify({'logged_in': False})
        first_name, last_name, email, phone, address = user
        # Parse structured address
        address_details = barangay = city = province = region = ''
        if address:
            parts = [p.strip() for p in address.split(',')]
            if len(parts) == 5:
                address_details, barangay, city, province, region = parts
        return jsonify({
            'logged_in': True,
            'full_name': f"{first_name} {last_name}",
            'address_details': address_details,
            'barangay': barangay,
            'city': city,
            'province': province,
            'region': region,
            'email': email,
            'phone': phone
        })

@app.route('/api/barangays')
def api_barangays():
    city_code = request.args.get('city_code')
    if not city_code:
        return jsonify([])
    import json
    with open('static/json/barangay.json', encoding='utf-8') as f:
        # Stream and filter line by line for memory efficiency
        barangays = json.load(f)
        filtered = [b for b in barangays if b.get('city_code') == city_code]
    return jsonify(filtered)

@app.route('/api/barangays-debug')
def api_barangays_debug():
    import json
    with open('static/json/barangay.json', encoding='utf-8') as f:
        barangays = json.load(f)
        return jsonify(barangays[:10])

# Static Pages
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

# Collection Pages
@app.route('/collections/necklaces')
def necklacec():
    with sqlite3.connect('aureliana.db') as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM inventory WHERE category = 'Necklace'")
        products = c.fetchall()
    return render_template('necklacec.html', products=products)

@app.route('/collections/rings')
def ringc():
    with sqlite3.connect('aureliana.db') as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM inventory WHERE category = 'Ring'")
        products = c.fetchall()
    return render_template('ringc.html', products=products)

@app.route('/collections/bracelets')
def braceletc():
    with sqlite3.connect('aureliana.db') as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM inventory WHERE category = 'Bracelet'")
        products = c.fetchall()
    return render_template('braceletc.html', products=products)

@app.route('/collections/earrings')
def earringc():
    with sqlite3.connect('aureliana.db') as conn:
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
    # Calculate total using DB prices
    subtotal = 0
    db_items = []
    with sqlite3.connect('aureliana.db') as conn:
        c = conn.cursor()
        for item in items:
            c.execute('SELECT price FROM inventory WHERE name = ?', (item['name'],))
            row = c.fetchone()
            if not row:
                continue  # skip if not found
            db_price = row[0]
            subtotal += db_price * item['quantity']
            db_items.append({
                'name': item['name'],
                'quantity': item['quantity'],
                'price': db_price
            })
    shipping_cost = 50.0
    total = subtotal + shipping_cost
    # Save order
    with sqlite3.connect('aureliana.db') as conn:
        c = conn.cursor()
        c.execute('INSERT INTO orders (client_ID, order_number, status, total_amount, shipping_address, payment_method) VALUES (?, ?, ?, ?, ?, ?)',
                  (session['user_id'], f"ORD{int(datetime.datetime.now().timestamp())}", 'Paid', total, shipping_address, payment_method))
        order_id = c.lastrowid
        for item in db_items:
            c.execute('INSERT INTO order_items (order_ID, product_name, quantity, unit_price) VALUES (?, ?, ?, ?)',
                      (order_id, item['name'], item['quantity'], item['price']))
            # Decrease stock in inventory
            c.execute('UPDATE inventory SET current_stock = current_stock - ? WHERE name = ?', (item['quantity'], item['name']))
        conn.commit()
    # Remove items from cart (simulate by clearing session key)
    session.pop('itemsToCheckout', None)
    # Redirect to receipt
    return redirect(url_for('receipt', order_id=order_id))

@app.route('/receipt/<int:order_id>')
def receipt(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with sqlite3.connect('aureliana.db') as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM orders WHERE order_ID = ?', (order_id,))
        order = c.fetchone()
        c.execute('SELECT * FROM order_items WHERE order_ID = ?', (order_id,))
        items = c.fetchall()
    return render_template('cart/receipt.html', order=order, items=items)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)