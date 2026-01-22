// Cart data stored in memory
let cart = [];

// Toggle mobile menu
function toggleMobileMenu() {
    const menu = document.querySelector('.menu');
    const signupIn = document.querySelector('.signup-in');
    const menuToggle = document.querySelector('.menu-toggle');
    
    menu.classList.toggle('active');
    signupIn.classList.toggle('active');
    menuToggle.classList.toggle('active');
}

// Search functionality
function searchItems() {
    const searchInput = document.getElementById('searchBar').value.toLowerCase();
    const menuItems = document.querySelectorAll('.menu-item');
    const menuCategories = document.querySelectorAll('.menu-category');
    
    menuCategories.forEach(category => {
        let hasVisibleItems = false;
        const items = category.querySelectorAll('.menu-item');
        
        items.forEach(item => {
            const itemName = item.getAttribute('data-name');
            if (itemName.includes(searchInput)) {
                item.style.display = 'block';
                hasVisibleItems = true;
            } else {
                item.style.display = 'none';
            }
        });
        
        if (hasVisibleItems) {
            category.style.display = 'block';
        } else {
            category.style.display = 'none';
        }
    });
}

// Add to cart
function addToCart(button) {
    const menuItem = button.closest('.menu-item');
    const itemName = menuItem.querySelector('h4').textContent;
    const itemPrice = parseInt(menuItem.getAttribute('data-price'));
    const itemImage = menuItem.querySelector('img').src;
    
    const existingItem = cart.find(item => item.name === itemName);
    
    if (existingItem) {
        existingItem.quantity++;
    } else {
        cart.push({
            name: itemName,
            price: itemPrice,
            image: itemImage,
            quantity: 1
        });
    }
    
    updateCartUI();
    
    // Visual feedback
    button.innerHTML = '<i class="fa fa-check"></i> Added';
    button.style.background = '#27ae60';
    
    setTimeout(() => {
        button.innerHTML = '<i class="fa fa-plus"></i> Add';
        button.style.background = '#B98C00';
    }, 1000);
}

// Update cart UI
function updateCartUI() {
    const cartCount = document.getElementById('cartCount');
    const cartItems = document.getElementById('cartItems');
    const subtotalElement = document.getElementById('subtotal');
    const taxElement = document.getElementById('tax');
    const cartTotal = document.getElementById('cartTotal');
    
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    cartCount.textContent = totalItems;
    
    if (cart.length === 0) {
        cartItems.innerHTML = '<p class="empty-cart">Your cart is empty</p>';
        subtotalElement.textContent = '₹0';
        taxElement.textContent = '₹0';
        cartTotal.textContent = '₹0';
        return;
    }
    
    cartItems.innerHTML = '';
    let subtotal = 0;
    
    cart.forEach((item, index) => {
        subtotal += item.price * item.quantity;
        
        const cartItemDiv = document.createElement('div');
        cartItemDiv.className = 'cart-item';
        cartItemDiv.innerHTML = `
            <img src="${item.image}" alt="${item.name}" class="cart-item-img">
            <div class="cart-item-details">
                <div class="cart-item-name">${item.name}</div>
                <div class="cart-item-price">₹${item.price} × ${item.quantity} = ₹${item.price * item.quantity}</div>
                <div class="cart-item-controls">
                    <div class="cart-item-quantity">
                        <button onclick="updateCartItemQuantity(${index}, -1)">-</button>
                        <span>${item.quantity}</span>
                        <button onclick="updateCartItemQuantity(${index}, 1)">+</button>
                    </div>
                    <button class="remove-item" onclick="removeCartItem(${index})">
                        <i class="fa fa-trash"></i> Remove
                    </button>
                </div>
            </div>
        `;
        cartItems.appendChild(cartItemDiv);
    });
    
    const tax = Math.round(subtotal * 0.05);
    const total = subtotal + tax;
    
    subtotalElement.textContent = `₹${subtotal}`;
    taxElement.textContent = `₹${tax}`;
    cartTotal.textContent = `₹${total}`;
}

// Update cart item quantity
function updateCartItemQuantity(index, change) {
    if (cart[index]) {
        cart[index].quantity += change;
        if (cart[index].quantity <= 0) {
            cart.splice(index, 1);
        }
        updateCartUI();
    }
}

// Remove cart item
function removeCartItem(index) {
    cart.splice(index, 1);
    updateCartUI();
}

// Toggle cart sidebar
function toggleCart() {
    const cartSidebar = document.getElementById('cartSidebar');
    const cartOverlay = document.getElementById('cartOverlay');
    
    cartSidebar.classList.toggle('active');
    cartOverlay.classList.toggle('active');
    
    if (cartSidebar.classList.contains('active')) {
        document.body.style.overflow = 'hidden';
    } else {
        document.body.style.overflow = 'auto';
    }
}

// Show address modal
function showAddressModal() {
    const modal = document.getElementById('addressModal');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

// Close address modal
function closeAddressModal() {
    const modal = document.getElementById('addressModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Place order function
function placeOrder() {
    if (cart.length === 0) {
        alert('Your cart is empty! Please add items to place an order.');
        return;
    }
    
    showAddressModal();
}

// Confirm order with address
async function confirmOrder() {
    const name = document.getElementById('customerName').value.trim();
    const phone = document.getElementById('customerPhone').value.trim();
    const addressLine = document.getElementById('addressLine').value.trim();
    const city = document.getElementById('city').value.trim();
    const pincode = document.getElementById('pincode').value.trim();
    
    if (!name || !phone || !addressLine || !city || !pincode) {
        alert('Please fill all address fields!');
        return;
    }
    
    if (phone.length !== 10 || !/^\d+$/.test(phone)) {
        alert('Please enter a valid 10-digit phone number!');
        return;
    }
    
    if (pincode.length !== 6 || !/^\d+$/.test(pincode)) {
        alert('Please enter a valid 6-digit pincode!');
        return;
    }
    
    const fullAddress = `${name}, ${phone}, ${addressLine}, ${city} - ${pincode}`;
    
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const tax = Math.round(subtotal * 0.05);
    const total = subtotal + tax;
    
    // Prepare order data
    const orderData = {
        cart_items: cart,
        total_amount: total,
        address: fullAddress
    };
    
    try {
        // Show loading state
        const confirmBtn = document.querySelector('.confirm-order-btn');
        const originalText = confirmBtn.innerHTML;
        confirmBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Processing...';
        confirmBtn.disabled = true;
        
        // Send order to server
        const response = await fetch('/place_order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(orderData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Success message
            alert(`✅ ${result.message}\n\nOrder ID: #${result.order_id}\n\nA confirmation email has been sent to your registered email address.\n\nEstimated delivery: 30-40 minutes`);
            
            // Clear cart
            cart = [];
            updateCartUI();
            closeAddressModal();
            toggleCart();
            
            // Reset form
            document.getElementById('addressForm').reset();
        } else {
            alert(`❌ ${result.message}`);
        }
        
        // Reset button
        confirmBtn.innerHTML = originalText;
        confirmBtn.disabled = false;
        
    } catch (error) {
        console.error('Order error:', error);
        alert('❌ Failed to place order. Please try again or contact support.');
        
        // Reset button
        const confirmBtn = document.querySelector('.confirm-order-btn');
        confirmBtn.innerHTML = '<i class="fa fa-check-circle"></i> Confirm Order';
        confirmBtn.disabled = false;
    }
}

// Close mobile menu when clicking outside
document.addEventListener('click', function(event) {
    const menu = document.querySelector('.menu');
    const signupIn = document.querySelector('.signup-in');
    const menuToggle = document.querySelector('.menu-toggle');
    
    if (menu.classList.contains('active') && 
        !menu.contains(event.target) && 
        !menuToggle.contains(event.target) &&
        !signupIn.contains(event.target)) {
        toggleMobileMenu();
    }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    updateCartUI();
    
    // Close modal when clicking outside
    const modal = document.getElementById('addressModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeAddressModal();
            }
        });
    }
});