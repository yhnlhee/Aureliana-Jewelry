# Aureliana Jewelry - Database System Documentation

## Overview
The Aureliana Jewelry website now uses a comprehensive multi-database system to handle user authentication, orders, inventory management, and contact messages. This system ensures data integrity, security, and scalability for the jewelry business.

## Database Architecture

### 1. **users.db** - User Authentication & Profiles
**Purpose**: Manages user accounts, authentication, and profile information.

**Tables**:
- `users`
  - `id` (PRIMARY KEY)
  - `username` (UNIQUE)
  - `email` (UNIQUE)
  - `password_hash` (SHA-256 encrypted)
  - `full_name`
  - `phone`
  - `address`
  - `created_at`

**Features**:
- Secure password hashing using SHA-256
- Unique username and email constraints
- User profile management
- Session-based authentication

### 2. **orders.db** - Order Management
**Purpose**: Tracks customer orders, order items, and order status.

**Tables**:
- `orders`
  - `id` (PRIMARY KEY)
  - `user_id` (FOREIGN KEY → users.id)
  - `order_number` (UNIQUE, auto-generated)
  - `total_amount`
  - `status` (pending, processing, shipped, delivered, cancelled)
  - `shipping_address`
  - `payment_method`
  - `created_at`

- `order_items`
  - `id` (PRIMARY KEY)
  - `order_id` (FOREIGN KEY → orders.id)
  - `product_id`
  - `product_name`
  - `quantity`
  - `unit_price`

**Features**:
- Auto-generated order numbers (format: ORD-YYYYMMDD-XXXX)
- Order status tracking
- Detailed order item records
- Payment method tracking

### 3. **inventory.db** - Inventory Management
**Purpose**: Manages product inventory, stock levels, and inventory tracking.

**Tables**:
- `inventory`
  - `id` (PRIMARY KEY)
  - `product_id`
  - `product_name`
  - `category` (necklace, ring, bracelet, earring)
  - `material` (18K Gold, 18K Rose Gold, etc.)
  - `gemstone` (Diamond, Pearl, Sapphire, etc.)
  - `unit_price`
  - `image_url`
  - `size`
  - `stock_quantity`
  - `reorder_level`
  - `last_updated`

- `inventory_log`
  - `id` (PRIMARY KEY)
  - `product_id`
  - `action` (add, remove, adjust)
  - `quantity`
  - `previous_stock`
  - `new_stock`
  - `timestamp`

**Features**:
- Real-time stock tracking
- Low stock alerts (reorder level)
- Inventory change logging
- Product categorization

### 4. **contact.db** - Contact Form Management
**Purpose**: Stores and manages customer contact form submissions.

**Tables**:
- `contact_messages`
  - `id` (PRIMARY KEY)
  - `name`
  - `email`
  - `subject`
  - `message`
  - `status` (unread, read, replied)
  - `created_at`

**Features**:
- Message status tracking
- Customer inquiry management
- Timestamp tracking

## Security Features

### Authentication System
- **Password Security**: SHA-256 hashing for password storage
- **Session Management**: Flask session-based authentication
- **Login Required Decorator**: Protects routes that require authentication
- **Secure Logout**: Clears all session data

### Data Protection
- **SQL Injection Prevention**: Parameterized queries
- **Input Validation**: Form validation and sanitization
- **Session Security**: Secure session management

## User Flow

### 1. **Registration Process**
1. User visits `/register`
2. Fills out registration form (username, email, password, full name)
3. System validates input and checks for duplicates
4. Password is hashed and stored in `users.db`
5. User is redirected to login page

### 2. **Login Process**
1. User visits `/login`
2. Enters username and password
3. System verifies credentials against `users.db`
4. If valid, creates session and redirects to home page
5. If invalid, shows error message

### 3. **Shopping Process**
1. **Browse Products**: Users can view products without login
2. **Add to Cart**: Requires login (`@login_required`)
3. **Check Inventory**: System checks `inventory.db` for stock availability
4. **Place Order**: Creates order in `orders.db` and updates inventory

### 4. **Order Management**
1. **Order Creation**: Generates unique order number
2. **Inventory Update**: Automatically reduces stock quantities
3. **Order Tracking**: Admin can view and manage orders
4. **Status Updates**: Track order progress

## Admin Features

### Admin Dashboard (`/admin`)
- **Orders Management**: View all orders, status, and details
- **Inventory Management**: Monitor stock levels and product information
- **Contact Messages**: View and manage customer inquiries
- **User Management**: View registered users

### Database Management
- **Real-time Monitoring**: Live updates of inventory and orders
- **Low Stock Alerts**: Automatic notifications for reorder levels
- **Order Tracking**: Complete order history and status

## API Endpoints

### Authentication
- `POST /login` - User login
- `POST /register` - User registration
- `GET /logout` - User logout

### Shopping
- `POST /add_to_cart` - Add item to cart (requires login)
- `POST /place_order` - Place order (requires login)

### Contact
- `POST /contact` - Submit contact form

## Database Relationships

```
users (1) ←→ (many) orders
orders (1) ←→ (many) order_items
inventory (1) ←→ (many) inventory_log
```

## File Structure

```
Aureliana Jewelry/
├── app.py                 # Main Flask application
├── users.db              # User authentication database
├── orders.db             # Order management database
├── inventory.db          # Inventory management database
├── contact.db            # Contact messages database
├── populate_inventory.py # Script to populate inventory
├── templates/
│   ├── login.html        # Login page
│   ├── register.html     # Registration page
│   ├── admin.html        # Admin dashboard
│   └── ...               # Other templates
└── DATABASE_SYSTEM.md    # This documentation
```

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install flask
   ```

2. **Initialize Databases**:
   ```bash
   python app.py
   ```
   (Databases are automatically created on first run)

3. **Populate Inventory**:
   ```bash
   python populate_inventory.py
   ```

4. **Run the Application**:
   ```bash
   python app.py
   ```

## Security Considerations

- **Password Hashing**: All passwords are hashed using SHA-256
- **Session Security**: Secure session management with random secret keys
- **SQL Injection Prevention**: All database queries use parameterized statements
- **Input Validation**: Form inputs are validated and sanitized
- **Access Control**: Protected routes require authentication

## Future Enhancements

1. **Email Verification**: Add email verification for new registrations
2. **Password Reset**: Implement password reset functionality
3. **Admin Roles**: Add different admin permission levels
4. **Payment Integration**: Integrate payment gateways
5. **Order Notifications**: Email notifications for order status changes
6. **Inventory Alerts**: Automated low stock notifications
7. **Analytics**: Sales and inventory analytics dashboard

## Maintenance

### Regular Tasks
- Monitor database sizes and performance
- Backup databases regularly
- Review and clean old contact messages
- Update inventory reorder levels
- Monitor failed login attempts

### Database Backups
```bash
# Backup all databases
sqlite3 users.db ".backup users_backup.db"
sqlite3 orders.db ".backup orders_backup.db"
sqlite3 inventory.db ".backup inventory_backup.db"
sqlite3 contact.db ".backup contact_backup.db"
```

This comprehensive database system provides a solid foundation for the Aureliana Jewelry e-commerce platform, ensuring data integrity, security, and scalability for future growth. 