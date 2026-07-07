-- ============================================================
--  11:11:11 EVOXU — Full Database Schema
--  Run this in MySQL Workbench to create the complete database
--  Engine: MySQL 8.0 | Charset: utf8mb4
-- ============================================================

DROP DATABASE IF EXISTS evoxu_db;
CREATE DATABASE evoxu_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE evoxu_db;

-- ============================================================
--  1. AUTH_USER  (Django built-in user table)
--     Every reseller has one linked auth_user login account
-- ============================================================
CREATE TABLE auth_user (
  id           INT            NOT NULL AUTO_INCREMENT,
  password     VARCHAR(128)   NOT NULL,
  last_login   DATETIME(6)        NULL,
  is_superuser TINYINT(1)     NOT NULL DEFAULT 0,
  username     VARCHAR(150)   NOT NULL,
  first_name   VARCHAR(150)   NOT NULL DEFAULT '',
  last_name    VARCHAR(150)   NOT NULL DEFAULT '',
  email        VARCHAR(254)   NOT NULL DEFAULT '',
  is_staff     TINYINT(1)     NOT NULL DEFAULT 0,
  is_active    TINYINT(1)     NOT NULL DEFAULT 1,
  date_joined  DATETIME(6)    NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_auth_user_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Login credentials for resellers and admin users';

-- ============================================================
--  2. RESELLERS_RESELLER  (Core reseller profiles)
--     Two types: retail (physical store) / influencer (social)
--     ID format: RTSE-0001 (retail), INSE-0001 (influencer)
--     Code format: AV001, SB001, BH001  (used in referral URLs)
--     Referral URL: http://127.0.0.1:8000/{code}-ref
-- ============================================================
CREATE TABLE resellers_reseller (
  id               BIGINT         NOT NULL AUTO_INCREMENT,
  user_id          INT            NOT NULL,

  -- Identity
  name             VARCHAR(200)   NOT NULL,
  phone            VARCHAR(20)    NOT NULL DEFAULT '',
  reseller_code    VARCHAR(20)    NOT NULL COMMENT 'Short code used in QR URL, e.g. AV001',
  reseller_id      VARCHAR(20)    NOT NULL COMMENT 'Formatted ID: RTSE-0001 / INSE-0001',
  reseller_type    VARCHAR(20)    NOT NULL DEFAULT 'retail'
                     COMMENT 'Values: retail | influencer',

  -- Referral
  referral_link    VARCHAR(500)   NOT NULL COMMENT 'Full QR scan URL',
  qr_image         VARCHAR(100)   NOT NULL DEFAULT '' COMMENT 'Path to QR code PNG',

  -- Commission
  commission_rate  DECIMAL(10,2)  NOT NULL DEFAULT 100.00
                     COMMENT 'Fixed commission per order in ₹',
  is_active        TINYINT(1)     NOT NULL DEFAULT 1,
  created_at       DATETIME(6)    NOT NULL,

  -- Retail-specific fields
  address          LONGTEXT           NULL COMMENT 'Store / business address',
  city             VARCHAR(100)   NOT NULL DEFAULT '',
  state            VARCHAR(100)   NOT NULL DEFAULT '',
  pincode          VARCHAR(10)    NOT NULL DEFAULT '',
  address_proof    VARCHAR(100)       NULL COMMENT 'Uploaded address proof document path',

  -- Influencer-specific fields
  platform         VARCHAR(50)    NOT NULL DEFAULT '' COMMENT 'Instagram / YouTube / etc.',
  social_handle    VARCHAR(200)   NOT NULL DEFAULT '',
  follower_count   VARCHAR(50)    NOT NULL DEFAULT '',
  profile_url      VARCHAR(500)   NOT NULL DEFAULT '',

  PRIMARY KEY (id),
  UNIQUE KEY uq_reseller_code    (reseller_code),
  UNIQUE KEY uq_reseller_id      (reseller_id),
  UNIQUE KEY uq_reseller_user_id (user_id),
  CONSTRAINT fk_reseller_user
    FOREIGN KEY (user_id) REFERENCES auth_user(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Reseller profiles — retail stores and influencers';

-- ============================================================
--  3. RESELLERS_QRSCAN  (QR scan tracking)
--     Every time a customer scans a reseller QR code,
--     one row is added here for analytics
-- ============================================================
CREATE TABLE resellers_qrscan (
  id          BIGINT       NOT NULL AUTO_INCREMENT,
  reseller_id BIGINT       NOT NULL,
  ip_address  CHAR(39)         NULL COMMENT 'IPv4 or IPv6',
  user_agent  LONGTEXT     NOT NULL DEFAULT '',
  scanned_at  DATETIME(6)  NOT NULL,
  PRIMARY KEY (id),
  KEY idx_qrscan_reseller (reseller_id),
  KEY idx_qrscan_date     (scanned_at),
  CONSTRAINT fk_qrscan_reseller
    FOREIGN KEY (reseller_id) REFERENCES resellers_reseller(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='One row per QR code scan — used for reseller analytics';

-- ============================================================
--  4. RESELLERS_RESELLERPAYOUT  (Commission payout records)
--     Tracks all commission payments to resellers
--     Status: pending → processing → paid
-- ============================================================
CREATE TABLE resellers_resellerpayout (
  id           BIGINT         NOT NULL AUTO_INCREMENT,
  reseller_id  BIGINT         NOT NULL,
  amount       DECIMAL(10,2)  NOT NULL,
  status       VARCHAR(20)    NOT NULL DEFAULT 'pending'
                 COMMENT 'Values: pending | processing | paid',
  period       VARCHAR(50)    NOT NULL COMMENT 'e.g. May 2025',
  dates        VARCHAR(100)   NOT NULL DEFAULT '' COMMENT 'e.g. 01 May – 31 May 2025',
  requested_at DATETIME(6)    NOT NULL,
  paid_at      DATETIME(6)        NULL,
  PRIMARY KEY (id),
  KEY idx_payout_reseller (reseller_id),
  KEY idx_payout_status   (status),
  CONSTRAINT fk_payout_reseller
    FOREIGN KEY (reseller_id) REFERENCES resellers_reseller(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Commission payout history per reseller';

-- ============================================================
--  5. STORE_PRODUCT  (Product catalogue)
--     12 ritual perfume oil products
--     for_gender: male | female | combo
-- ============================================================
CREATE TABLE store_product (
  id          BIGINT         NOT NULL AUTO_INCREMENT,
  name        VARCHAR(200)   NOT NULL COMMENT 'Product code: KLEOMA, MYSTRA, etc.',
  intent      VARCHAR(200)   NOT NULL COMMENT 'e.g. Love & Attraction',
  description LONGTEXT       NOT NULL DEFAULT '',
  price       DECIMAL(10,2)  NOT NULL,
  for_gender  VARCHAR(10)    NOT NULL COMMENT 'Values: male | female | combo',
  emoji       VARCHAR(10)    NOT NULL DEFAULT '',
  in_stock    TINYINT(1)     NOT NULL DEFAULT 1,
  PRIMARY KEY (id),
  KEY idx_product_gender (for_gender),
  KEY idx_product_stock  (in_stock)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Ritual perfume oil product catalogue';

-- ============================================================
--  6. STORE_CUSTOMER  (Customer records)
--     referred_by links to the reseller whose QR was scanned
--     One customer can only be referred once (first scan wins)
-- ============================================================
CREATE TABLE store_customer (
  id             BIGINT        NOT NULL AUTO_INCREMENT,
  name           VARCHAR(200)  NOT NULL,
  email          VARCHAR(254)  NOT NULL,
  phone          VARCHAR(20)   NOT NULL DEFAULT '',
  referred_by_id BIGINT            NULL COMMENT 'Reseller who referred this customer',
  created_at     DATETIME(6)   NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_customer_email (email),
  KEY idx_customer_reseller (referred_by_id),
  CONSTRAINT fk_customer_reseller
    FOREIGN KEY (referred_by_id) REFERENCES resellers_reseller(id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Customer accounts — linked to referring reseller';

-- ============================================================
--  7. STORE_ORDER  (Orders)
--     reseller_id = who referred the customer (NULL = direct)
--     commission_amount = fixed ₹100 per order (or custom rate)
--     order_number format: {RESCODE}-{MMDD}-{4digits}
--     e.g. AV001-0602-3847
-- ============================================================
CREATE TABLE store_order (
  id                BIGINT         NOT NULL AUTO_INCREMENT,
  order_number      VARCHAR(30)    NOT NULL,
  customer_id       BIGINT         NOT NULL,
  reseller_id       BIGINT             NULL COMMENT 'NULL = direct sale, no referral',
  total_amount      DECIMAL(10,2)  NOT NULL,
  commission_amount DECIMAL(10,2)  NOT NULL DEFAULT 100.00,
  status            VARCHAR(20)    NOT NULL DEFAULT 'pending'
                      COMMENT 'Values: pending | processing | delivered | cancelled',
  notes             LONGTEXT       NOT NULL DEFAULT '',
  created_at        DATETIME(6)    NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_order_number      (order_number),
  KEY idx_order_customer          (customer_id),
  KEY idx_order_reseller          (reseller_id),
  KEY idx_order_status            (status),
  KEY idx_order_date              (created_at),
  CONSTRAINT fk_order_customer
    FOREIGN KEY (customer_id) REFERENCES store_customer(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_order_reseller
    FOREIGN KEY (reseller_id) REFERENCES resellers_reseller(id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Customer orders — attributed to reseller for commission tracking';

-- ============================================================
--  8. STORE_ORDERITEM  (Order line items)
--     One row per product per order
--     unit_price captured at time of order (not live price)
-- ============================================================
CREATE TABLE store_orderitem (
  id         BIGINT         NOT NULL AUTO_INCREMENT,
  order_id   BIGINT         NOT NULL,
  product_id BIGINT         NOT NULL,
  quantity   INT UNSIGNED   NOT NULL DEFAULT 1,
  unit_price DECIMAL(10,2)  NOT NULL COMMENT 'Price at time of purchase',
  PRIMARY KEY (id),
  KEY idx_orderitem_order   (order_id),
  KEY idx_orderitem_product (product_id),
  CONSTRAINT fk_orderitem_order
    FOREIGN KEY (order_id) REFERENCES store_order(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_orderitem_product
    FOREIGN KEY (product_id) REFERENCES store_product(id)
    ON DELETE CASCADE,
  CONSTRAINT chk_orderitem_qty CHECK (quantity >= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Individual product lines within an order';

-- ============================================================
--  SEED DATA — Products (12 ritual oils)
-- ============================================================
INSERT INTO store_product (name, intent, description, price, for_gender, emoji, in_stock) VALUES
('KLEOMA',    'Love & Attraction',   'A ritual-infused attar to support emotional connection, attraction, and presence. Velvety, warm, and floral.',           1234.00, 'male',   '🌹', 1),
('KLINFON',   'Relaxation & Calm',   'Supports calm presence and smooth transition into rest. Herbal and grounding — a sacred oil for stillness.',              1234.00, 'male',   '🌿', 0),
('MYSTRA',    'Financial Clarity',   'For financial clarity, balance, and mindful decision-making. Opens with citrus and saffron, grounded by oud.',            1234.00, 'male',   '⚖️', 1),
('SHREEMSRI', 'Wealth & Prosperity', 'A sacred oil for those walking the path of meaningful wealth creation. Golden saffron, cinnamon, smoky musk.',            1234.00, 'male',   '👑', 1),
('SUKCE',     'Success & Achievement','A sensory anchor for entrepreneurs, leaders, and creators. Lavender, saffron, jasmine, oud, amber.',                    1234.00, 'male',   '🔥', 1),
('KAMAVYA',   'Attraction & Love',   'Romantic and magnetic. Sweet almond, jasmine sambac, crystal tuberose, cocoa.',                                           1234.00, 'female', '💫', 1),
('KLINFON',   'Relaxation & Calm',   'Encourages ease, softness, and balanced rhythm. Lavender, lemon, saffron, jasmine, oud.',                               1234.00, 'female', '🌸', 1),
('HREMAAN',   'Financial Clarity',   'A sacred anchor for clarity in financial thinking. Lavender, lemon, caraway, saffron, jasmine, oud.',                   1234.00, 'female', '💎', 1),
('SHRIVAA',   'Wealth & Prosperity', 'For those walking the path of conscious prosperity. Golden saffron, cinnamon, smoky musk, patchouli.',                  1234.00, 'female', '🌺', 1),
('YCNEX',     'Confidence & Success','A sensory anchor for the woman who leads. Citrus, saffron, cinnamon, vetiver, sandalwood, oud.',                        1234.00, 'female', '✨', 1),
('KLINFON Combo', 'Relaxation — Him & Her', 'Two 10ml Roll-Ons. Male + Female formulations. The complete KLINFON ritual set.',                                2345.00, 'combo',  '🎁', 1),
('Love Combo','Love & Attraction — Him & Her','KLEOMA (Male) + KAMAVYA (Female). Two 10ml Roll-Ons. The sacred love pairing.',                               2345.00, 'combo',  '💝', 1);

-- ============================================================
--  USEFUL VIEWS
-- ============================================================

-- Sales breakdown by reseller
CREATE OR REPLACE VIEW v_reseller_sales AS
SELECT
  r.reseller_id                                    AS reseller_id,
  r.name                                           AS reseller_name,
  r.reseller_code                                  AS code,
  r.reseller_type                                  AS type,
  COUNT(DISTINCT o.id)                             AS total_orders,
  COALESCE(SUM(o.total_amount), 0)                 AS total_revenue,
  COALESCE(SUM(o.commission_amount), 0)            AS total_commission,
  COUNT(DISTINCT c.id)                             AS total_customers,
  COUNT(DISTINCT qs.id)                            AS total_qr_scans
FROM resellers_reseller r
LEFT JOIN store_order    o  ON o.reseller_id    = r.id
LEFT JOIN store_customer c  ON c.referred_by_id = r.id
LEFT JOIN resellers_qrscan qs ON qs.reseller_id = r.id
GROUP BY r.id;

-- Orders with full details
CREATE OR REPLACE VIEW v_order_details AS
SELECT
  o.order_number,
  o.created_at                                     AS order_date,
  o.status,
  c.name                                           AS customer_name,
  c.email                                          AS customer_email,
  r.name                                           AS reseller_name,
  r.reseller_id                                    AS reseller_id,
  r.reseller_code                                  AS reseller_code,
  o.total_amount,
  o.commission_amount,
  GROUP_CONCAT(p.name ORDER BY p.name SEPARATOR ', ') AS products
FROM store_order o
JOIN store_customer c   ON c.id = o.customer_id
LEFT JOIN resellers_reseller r ON r.id = o.reseller_id
JOIN store_orderitem oi ON oi.order_id = o.id
JOIN store_product p    ON p.id = oi.product_id
GROUP BY o.id;

-- Product sales by reseller
CREATE OR REPLACE VIEW v_product_sales_by_reseller AS
SELECT
  r.name                  AS reseller_name,
  r.reseller_id           AS reseller_id,
  p.name                  AS product_name,
  p.for_gender            AS gender,
  SUM(oi.quantity)        AS units_sold,
  SUM(oi.unit_price * oi.quantity) AS revenue
FROM store_orderitem oi
JOIN store_order o      ON o.id = oi.order_id
JOIN store_product p    ON p.id = oi.product_id
LEFT JOIN resellers_reseller r ON r.id = o.reseller_id
GROUP BY r.id, p.id
ORDER BY r.name, units_sold DESC;

-- ============================================================
--  USEFUL QUERIES (run these in Workbench to see live data)
-- ============================================================

/*
-- All resellers with order counts:
SELECT * FROM v_reseller_sales;

-- Full order details:
SELECT * FROM v_order_details ORDER BY order_date DESC LIMIT 20;

-- Product sales by reseller:
SELECT * FROM v_product_sales_by_reseller;

-- Total summary:
SELECT
  COUNT(*) AS total_orders,
  SUM(total_amount) AS total_revenue,
  SUM(commission_amount) AS total_commission,
  COUNT(DISTINCT customer_id) AS unique_customers
FROM store_order;

-- Orders by reseller (quick count):
SELECT
  COALESCE(r.name, 'Direct Sale') AS reseller,
  COUNT(*) AS orders,
  SUM(o.total_amount) AS revenue
FROM store_order o
LEFT JOIN resellers_reseller r ON r.id = o.reseller_id
GROUP BY o.reseller_id
ORDER BY orders DESC;
*/
