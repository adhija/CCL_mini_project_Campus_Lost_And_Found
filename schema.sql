-- schema.sql — MySQL database schema for Campus Lost & Found Portal
-- AWS Service: Amazon RDS (MySQL 8.0)
-- Run this on your RDS instance to create the tables.

CREATE DATABASE IF NOT EXISTS lostfound
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE lostfound;

-- Users table: students and admins
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'admin') NOT NULL DEFAULT 'student'
) ENGINE=InnoDB;

-- Items table: lost and found items
CREATE TABLE IF NOT EXISTS items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status ENUM('LOST', 'FOUND', 'CLAIMED') NOT NULL DEFAULT 'LOST',
    category VARCHAR(100) NOT NULL DEFAULT 'General',
    location VARCHAR(150) NOT NULL DEFAULT 'Campus Grounds & Parking',
    verification_question VARCHAR(255) DEFAULT '',
    photo_key VARCHAR(512),
    reported_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reported_by) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Claims table: claim requests on items
CREATE TABLE IF NOT EXISTS claims (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NOT NULL,
    claimed_by INT NOT NULL,
    message TEXT NOT NULL,
    verification_answer TEXT DEFAULT '',
    status ENUM('PENDING', 'APPROVED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY (claimed_by) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

