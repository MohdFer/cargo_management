-- Cargo Management System Database Schema
-- Complete SQL queries for all 10 tables

-- =============================================
-- 1. USERS TABLE
-- Purpose: Authentication and basic user info for all user types
-- =============================================

CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role ENUM('admin', 'customer', 'employee') NOT NULL,
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- =============================================
-- 2. CUSTOMERS TABLE
-- Purpose: Extended customer profile information
-- =============================================

CREATE TABLE customers (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNIQUE NOT NULL,
    customer_code VARCHAR(20) UNIQUE,
    phone_number VARCHAR(15),
    address TEXT,
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50) DEFAULT 'India',
    postal_code VARCHAR(10),
    registration_date DATE DEFAULT (CURRENT_DATE),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_customer_code (customer_code)
);

-- =============================================
-- 3. EMPLOYEES TABLE
-- Purpose: Employee details and organizational hierarchy
-- =============================================

CREATE TABLE employees (
    employee_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNIQUE NOT NULL,
    employee_code VARCHAR(20) UNIQUE NOT NULL,
    department ENUM('logistics', 'warehouse', 'customer_service', 'management', 'driver') NOT NULL,
    position VARCHAR(50),
    hire_date DATE DEFAULT (CURRENT_DATE),
    manager_id INT,
    phone_number VARCHAR(15),
    salary DECIMAL(10,2),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (manager_id) REFERENCES employees(employee_id),
    INDEX idx_employee_code (employee_code),
    INDEX idx_department (department)
);

-- =============================================
-- 4. CARGO_BOOKINGS TABLE
-- Purpose: Main cargo shipment records
-- =============================================

CREATE TABLE cargo_bookings (
    booking_id INT PRIMARY KEY AUTO_INCREMENT,
    tracking_id VARCHAR(20) UNIQUE NOT NULL,
    customer_id INT NOT NULL,
    sender_name VARCHAR(100) NOT NULL,
    sender_address TEXT NOT NULL,
    sender_phone VARCHAR(15),
    recipient_name VARCHAR(100) NOT NULL,
    recipient_address TEXT NOT NULL,
    recipient_phone VARCHAR(15),
    cargo_description TEXT,
    weight DECIMAL(8,2) NOT NULL,
    dimensions VARCHAR(50),
    cargo_value DECIMAL(10,2),
    booking_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    expected_delivery_date DATE,
    actual_delivery_date DATETIME,
    status ENUM('pending', 'confirmed', 'picked_up', 'in_transit', 'out_for_delivery', 'delivered', 'cancelled') DEFAULT 'pending',
    assigned_employee_id INT,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_status ENUM('unpaid', 'paid', 'refunded') DEFAULT 'unpaid',
    special_instructions TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (assigned_employee_id) REFERENCES employees(employee_id),
    INDEX idx_tracking_id (tracking_id),
    INDEX idx_status (status),
    INDEX idx_booking_date (booking_date)
);

-- =============================================
-- 5. TRACKING_UPDATES TABLE
-- Purpose: Track shipment status changes and location history
-- =============================================

CREATE TABLE tracking_updates (
    update_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    status ENUM('pending', 'confirmed', 'picked_up', 'in_transit', 'at_hub', 'out_for_delivery', 'delivered', 'delivery_failed', 'cancelled') NOT NULL,
    location VARCHAR(100),
    notes TEXT,
    updated_by INT,
    update_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    FOREIGN KEY (booking_id) REFERENCES cargo_bookings(booking_id) ON DELETE CASCADE,
    FOREIGN KEY (updated_by) REFERENCES employees(employee_id),
    INDEX idx_booking_status (booking_id, status),
    INDEX idx_timestamp (update_timestamp)
);

-- =============================================
-- 6. INVOICES TABLE
-- Purpose: Billing and payment management
-- =============================================

CREATE TABLE invoices (
    invoice_id INT PRIMARY KEY AUTO_INCREMENT,
    invoice_number VARCHAR(20) UNIQUE NOT NULL,
    booking_id INT NOT NULL,
    customer_id INT NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    tax_rate DECIMAL(5,2) DEFAULT 18.00,
    tax_amount DECIMAL(10,2) NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    issue_date DATE DEFAULT (CURRENT_DATE),
    due_date DATE,
    payment_status ENUM('unpaid', 'paid', 'overdue', 'cancelled') DEFAULT 'unpaid',
    payment_date DATETIME,
    payment_method ENUM('cash', 'card', 'bank_transfer', 'upi', 'cheque'),
    payment_reference VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES cargo_bookings(booking_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    INDEX idx_invoice_number (invoice_number),
    INDEX idx_payment_status (payment_status)
);

-- =============================================
-- 7. SUPPORT_TICKETS TABLE
-- Purpose: Customer support and complaint management
-- =============================================

CREATE TABLE support_tickets (
    ticket_id INT PRIMARY KEY AUTO_INCREMENT,
    ticket_number VARCHAR(20) UNIQUE NOT NULL,
    customer_id INT NOT NULL,
    booking_id INT,
    subject VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    priority ENUM('low', 'medium', 'high', 'urgent') DEFAULT 'medium',
    category ENUM('billing', 'delivery_issue', 'damaged_goods', 'lost_shipment', 'general_inquiry', 'complaint') NOT NULL,
    status ENUM('open', 'in_progress', 'resolved', 'closed') DEFAULT 'open',
    assigned_to INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL DEFAULT NULL,
    customer_satisfaction ENUM('very_satisfied', 'satisfied', 'neutral', 'dissatisfied', 'very_dissatisfied'),
    resolution_notes TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (booking_id) REFERENCES cargo_bookings(booking_id),
    FOREIGN KEY (assigned_to) REFERENCES employees(employee_id),
    INDEX idx_status (status),
    INDEX idx_priority (priority)
);

-- =============================================
-- 8. SYSTEM_LOGS TABLE
-- Purpose: Audit trail and system activity tracking
-- =============================================

CREATE TABLE system_logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    action VARCHAR(50) NOT NULL,
    table_affected VARCHAR(50),
    record_id INT,
    old_values JSON,
    new_values JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user_action (user_id, action),
    INDEX idx_timestamp (timestamp)
);

-- =============================================
-- 9. NOTIFICATIONS TABLE
-- Purpose: System notifications and alerts
-- =============================================

CREATE TABLE notifications (
    notification_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    booking_id INT,
    title VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    type ENUM('email', 'sms', 'system', 'push') NOT NULL,
    status ENUM('pending', 'sent', 'delivered', 'failed') DEFAULT 'pending',
    priority ENUM('low', 'normal', 'high') DEFAULT 'normal',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    read_at TIMESTAMP,
    email_address VARCHAR(100),
    phone_number VARCHAR(15),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (booking_id) REFERENCES cargo_bookings(booking_id),
    INDEX idx_user_status (user_id, status),
    INDEX idx_type (type)
);

-- =============================================
-- 10. REPORTS TABLE
-- Purpose: Generated reports metadata
-- =============================================

CREATE TABLE reports (
    report_id INT PRIMARY KEY AUTO_INCREMENT,
    report_name VARCHAR(100) NOT NULL,
    report_type ENUM('financial', 'operational', 'customer_activity', 'shipment_volume', 'performance') NOT NULL,
    generated_by INT NOT NULL,
    date_from DATE,
    date_to DATE,
    parameters JSON,
    file_path VARCHAR(255),
    file_size INT,
    format ENUM('pdf', 'excel', 'csv') DEFAULT 'pdf',
    status ENUM('generating', 'completed', 'failed') DEFAULT 'generating',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    download_count INT DEFAULT 0,
    expires_at TIMESTAMP,
    FOREIGN KEY (generated_by) REFERENCES users(user_id),
    INDEX idx_report_type (report_type),
    INDEX idx_generated_by (generated_by)
);

