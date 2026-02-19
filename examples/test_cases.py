"""
Example test cases for Enterprise UI Automation Platform.
"""

# Example 1: LG E-commerce Flow
lg_ecommerce_test = """
Navigate to https://www.lg.com/in
Click Air Solutions
Click Split AC
Click the first product
Click Buy Now
"""

# Example 2: Simple Login Flow
simple_login_test = """
Go to https://example.com
Click Login
Type test@example.com in Email
Type password123 in Password
Click Submit
Wait for Dashboard
"""

# Example 3: Search and Filter
search_filter_test = """
Navigate to https://example.com
Type laptop in Search
Click Search button
Wait for Results
Click Price filter
Click Apply filters
"""

# Example 4: Form Filling
form_filling_test = """
Go to https://example.com/contact
Type John Doe in Name
Type john@example.com in Email
Type 1234567890 in Phone
Type This is a test message in Message
Click Send
Wait for Confirmation
"""

# Example 5: Multi-step Navigation
multi_step_nav = """
Navigate to https://example.com
Click Products
Click Electronics
Click Laptops
Click First laptop
Click Add to Cart
Click Checkout
"""
