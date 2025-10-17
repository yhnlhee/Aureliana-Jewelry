// script.js

// This ensures the main cart-related JavaScript runs only after the entire HTML document is loaded.
document.addEventListener('DOMContentLoaded', () => {
    // Selectors for elements on the cart page (index.html)
    const selectAllCheckboxes = document.querySelectorAll('#selectAllProducts, #selectAllBottom');
    const productListContainer = document.getElementById('product-list');
    const selectedItemCountSpan = document.getElementById('selected-item-count');
    const totalSelectedItemsSpan = document.getElementById('total-selected-items');
    const overallTotalDisplay = document.getElementById('overall-total');
    const loadingMessage = document.getElementById('loading-message');
    const deleteSelectedButton = document.querySelector('.delete-selected-btn');
    const checkoutButton = document.getElementById('checkoutButton'); // Get the checkout button

    // --- Client-Side Cart Storage and Management ---
    const CART_STORAGE_KEY = 'cart';
    const CHECKOUT_ITEMS_STORAGE_KEY = 'aureliana_checkout_items'; // New key for items going to checkout

    function getCartItems() {
        try {
            const cartJson = localStorage.getItem(CART_STORAGE_KEY);
            return cartJson ? JSON.parse(cartJson) : [];
        } catch (e) {
            console.error("Error reading cart from localStorage:", e);
            return [];
        }
    }

    function saveCartItems(cart) {
        try {
            localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
        } catch (e) {
            console.error("Error saving cart to localStorage:", e);
        }
    }

    // Function to "fetch" products (now from localStorage) and display them in the cart
    function fetchProducts() {
        loadingMessage.textContent = 'Loading jewelry items...';
        loadingMessage.style.display = 'block';

        const cartItems = getCartItems();
        renderProducts(cartItems);

        loadingMessage.style.display = 'none'; // Hide loading message
    }

    // Function to dynamically render products into the cart
    function renderProducts(products) {
        productListContainer.innerHTML = ''; // Clear existing content
        if (products.length === 0) {
            productListContainer.innerHTML = `<p class="text-center text-gray-500 py-8">Your cart is empty.</p>`;
            return;
        }

        products.forEach(product => {
            const productItemDiv = document.createElement('div');
            productItemDiv.className = 'product-item py-4 border-b border-gray-100 grid grid-cols-12 gap-4 items-center';
            productItemDiv.dataset.productId = product.id; // Use only the product ID

            // Use 'image' and 'price' fields
            const displayImageUrl = product.image; // Use as is

            productItemDiv.innerHTML = `
                <div class="col-span-6 flex items-center">
                    <input type="checkbox" class="product-checkbox form-checkbox h-4 w-4 text-shopee-orange rounded-sm focus:ring-0 mr-2">
                    <img src="${displayImageUrl}" alt="${product.name}" class="w-20 h-20 object-cover rounded-md mr-4">
                    <div class="flex-grow">
                        <p class="text-sm font-medium text-gray-800">${product.name}</p>
                        <p class="text-xs text-gray-500 mt-1">${product.description || ''}</p>
                        ${product.material ? `<p class="text-xs text-gray-500 mt-1">Material: ${product.material}</p>` : ''}
                        ${product.gemstone ? `<p class="text-xs text-gray-500 mt-1">Gemstone: ${product.gemstone}</p>` : ''}
                        ${product.size ? `<p class="text-xs text-gray-500 mt-1">Size: ${product.size}</p>` : ''}
                        ${product.store_name ? `<div class="text-xs text-shopee-orange mt-2 flex items-center"><i class="fas fa-store-alt mr-1"></i> ${product.store_name}</div>` : ''}
                    </div>
                </div>
                <div class="col-span-2 text-center hidden md:block text-gray-700">₱${product.price.toLocaleString('en-US')}</div>
                <div class="col-span-1 flex items-center justify-center">
                    <div class="flex items-center border border-gray-300 rounded-md">
                        <button class="quantity-btn w-6 h-6 flex items-center justify-center text-gray-600 hover:bg-gray-100 rounded-l-md" data-action="decrease">-</button>
                        <input type="text" value="${product.quantity}" class="quantity-input w-8 text-center border-x border-gray-300 text-sm py-1 focus:outline-none" data-unit-price="${product.price}">
                        <button class="quantity-btn w-6 h-6 flex items-center justify-center text-gray-600 hover:bg-gray-100 rounded-r-md" data-action="increase">+</button>
                    </div>
                </div>
                <div class="col-span-2 text-center total-price text-shopee-orange font-bold text-lg">₱${(product.price * product.quantity).toLocaleString('en-US')}</div>
                <div class="col-span-1 text-center text-gray-500 text-sm flex flex-col items-center">
                    <button class="delete-btn hover:text-red-500 mb-1">Delete</button>
                    <button class="find-similar-btn hover:text-shopee-orange">Find Similar</button>
                </div>
            `;
            productListContainer.appendChild(productItemDiv);
        });
        updateCartTotals(); // Initial total calculation after rendering
    }

    // Function to calculate and update cart totals and counts
    function updateCartTotals() {
        let totalItemsSelected = 0;
        let overallTotalPrice = 0;
        const currentProductCheckboxes = document.querySelectorAll('.product-checkbox');

        currentProductCheckboxes.forEach(checkbox => {
            if (checkbox.checked) {
                totalItemsSelected++;
                const productItem = checkbox.closest('.product-item');
                const quantityInput = productItem.querySelector('.quantity-input');
                // Ensure unitPrice is parsed correctly, it might be a string
                const unitPrice = parseFloat(quantityInput.dataset.unitPrice);
                const quantity = parseInt(quantityInput.value);
                overallTotalPrice += unitPrice * quantity;
            }
        });

        // Update display elements
        selectedItemCountSpan.textContent = totalItemsSelected;
        totalSelectedItemsSpan.textContent = totalItemsSelected;
        overallTotalDisplay.textContent = `₱${overallTotalPrice.toLocaleString('en-US')}`;

        // Sync "Select All" checkboxes
        const allProductsChecked = currentProductCheckboxes.length > 0 && totalItemsSelected === currentProductCheckboxes.length;
        selectAllCheckboxes.forEach(checkbox => {
            checkbox.checked = allProductsChecked;
        });
    }

    // --- Event Delegation for dynamically created elements on the cart page ---
    productListContainer.addEventListener('click', (event) => {
        const target = event.target;

        // Handle quantity buttons
        if (target.classList.contains('quantity-btn')) {
            const button = target;
            const action = button.dataset.action;
            const quantityInput = button.parentElement.querySelector('.quantity-input');
            let quantity = parseInt(quantityInput.value);
            const unitPrice = parseFloat(quantityInput.dataset.unitPrice);
            const productItem = quantityInput.closest('.product-item');
            const productId = productItem.dataset.productId;

            if (action === 'decrease' && quantity > 1) {
                quantity--;
            } else if (action === 'increase') {
                quantity++;
            }

            quantityInput.value = quantity;
            const totalPriceElement = productItem.querySelector('.total-price');
            totalPriceElement.textContent = `₱${(unitPrice * quantity).toLocaleString('en-US')}`;

            // Update quantity in localStorage
            let cart = getCartItems();
            const itemIndex = cart.findIndex(item => item.id === productId);
            if (itemIndex !== -1) {
                cart[itemIndex].quantity = quantity;
                saveCartItems(cart);
            }
            updateCartTotals();
        }

        // Handle delete buttons
        if (target.classList.contains('delete-btn')) {
            const productItem = target.closest('.product-item');
            if (productItem) {
                const productId = productItem.dataset.productId;
                deleteCartItem(productId, productItem);
            }
        }

        // Handle "Find Similar" buttons
        if (target.classList.contains('find-similar-btn')) {
            showMessage('"Find Similar" feature is coming soon!', 'info');
        }
    });

    // Event listener for product list container to handle changes on quantity input fields
    productListContainer.addEventListener('change', (event) => {
        if (event.target.classList.contains('quantity-input')) {
            let quantity = parseInt(event.target.value);
            if (isNaN(quantity) || quantity < 1) {
                quantity = 1; // Default to 1 if invalid
            }
            event.target.value = quantity;

            const unitPrice = parseFloat(event.target.dataset.unitPrice);
            const productItem = event.target.closest('.product-item');
            const combinedProductId = productItem.dataset.productId; // Use combined ID for lookup

            const totalPriceElement = productItem.querySelector('.total-price');
            totalPriceElement.textContent = `₱${(unitPrice * quantity).toLocaleString('en-US')}`;

            // Update quantity in localStorage
            let cart = getCartItems();
            const itemIndex = cart.findIndex(item => `${item.id}-${item.size}` === combinedProductId);
            if (itemIndex !== -1) {
                cart[itemIndex].quantity = quantity;
                saveCartItems(cart);
            }
            updateCartTotals();
        }

        // Handle individual product checkboxes
        if (event.target.classList.contains('product-checkbox')) {
            updateCartTotals();
        }
    });

    // Function to delete a single cart item from localStorage
    function deleteCartItem(productId, productItemElement) {
        // Using showConfirm for better UX instead of native confirm()
        showConfirm('Are you sure you want to delete this item?', () => {
            let cart = getCartItems();
            const initialLength = cart.length;
            cart = cart.filter(item => item.id !== productId);

            if (cart.length < initialLength) {
                saveCartItems(cart);
                productItemElement.remove(); // Remove from DOM
                updateCartTotals(); // Recalculate totals
                showMessage('Item deleted successfully!', 'success');
            } else {
                showMessage('Item not found in cart.', 'error');
            }
        });
    }

    // Event Listeners for Select All Checkboxes
    selectAllCheckboxes.forEach(selectAllCheckbox => {
        selectAllCheckbox.addEventListener('change', (event) => {
            const isChecked = event.target.checked;
            document.querySelectorAll('.product-checkbox').forEach(checkbox => {
                checkbox.checked = isChecked;
            });
            updateCartTotals();
        });
    });

    // Event listener for "Delete Selected" button
    deleteSelectedButton.addEventListener('click', () => {
        const selectedProductItems = Array.from(document.querySelectorAll('.product-checkbox:checked'))
                                       .map(checkbox => checkbox.closest('.product-item'));

        if (selectedProductItems.length === 0) {
            showMessage('No items selected for deletion.', 'info');
            return;
        }

        showConfirm('Are you sure you want to delete the selected items?', () => {
            let cart = getCartItems();
            let deletedCount = 0;
            
            selectedProductItems.forEach(itemElement => {
                const productId = itemElement.dataset.productId;
                const foundIndex = cart.findIndex(item => item.id === productId);
                if (foundIndex !== -1) {
                    cart.splice(foundIndex, 1); // Remove item from array
                    itemElement.remove(); // Remove from DOM
                    deletedCount++;
                }
            });

            saveCartItems(cart); // Save the updated cart
            updateCartTotals(); // Recalculate totals

            if (deletedCount > 0) {
                showMessage(`${deletedCount} selected items deleted successfully!`, 'success');
            } else {
                showMessage('No selected items were found to delete.', 'warning');
            }
        });
    });

    // Ensure checkout button always collects checked items, including after select all
    if (checkoutButton) {
        checkoutButton.addEventListener('click', () => {
            const selectedItemsForCheckout = [];
            document.querySelectorAll('.product-checkbox:checked').forEach(checkbox => {
                const productItemElement = checkbox.closest('.product-item');
                const productId = productItemElement.dataset.productId;
                const cart = getCartItems();
                const itemInCart = cart.find(item => item.id === productId);
                if (itemInCart) {
                    selectedItemsForCheckout.push(itemInCart);
                }
            });
            if (selectedItemsForCheckout.length > 0) {
                localStorage.setItem(CHECKOUT_ITEMS_STORAGE_KEY, JSON.stringify(selectedItemsForCheckout));
                window.location.href = 'checkout.html';
            } else {
                showMessage('Please select at least one item to checkout.', 'info');
            }
        });
    }

    // Generic message box function for notifications (replaces alert/confirm)
    function showMessage(message, type = 'info') {
        const messageBox = document.createElement('div');
        messageBox.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        let bgColor = 'bg-gray-700';
        let textColor = 'text-white';
        if (type === 'success') {
            bgColor = 'bg-green-500';
        } else if (type === 'error') {
            bgColor = 'bg-red-500';
        } else if (type === 'warning') {
            bgColor = 'bg-yellow-500';
        } else if (type === 'info') {
            bgColor = 'bg-blue-500'; // Added info specific color
        }


        messageBox.innerHTML = `
            <div class="bg-white p-6 rounded-lg shadow-xl text-center max-w-sm w-full">
                <p class="text-lg font-semibold mb-4 ${textColor} ${bgColor} p-2 rounded-md">${message}</p>
                <button class="bg-shopee-orange text-white px-4 py-2 rounded-md hover:bg-shopee-dark-orange close-message-box">OK</button>
            </div>
        `;
        document.body.appendChild(messageBox);
        messageBox.querySelector('.close-message-box').addEventListener('click', () => {
            messageBox.remove();
        });
    }

    // Generic confirmation box function
    function showConfirm(message, onConfirm) {
        const confirmBox = document.createElement('div');
        confirmBox.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        confirmBox.innerHTML = `
            <div class="bg-white p-6 rounded-lg shadow-xl text-center max-w-sm w-full">
                <p class="text-lg font-semibold mb-4">${message}</p>
                <div class="flex justify-center space-x-4">
                    <button class="bg-red-500 text-white px-4 py-2 rounded-md hover:bg-red-600 confirm-btn">Yes</button>
                    <button class="bg-gray-300 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-400 cancel-btn">Cancel</button>
                </div>
            </div>
        `;
        document.body.appendChild(confirmBox);

        confirmBox.querySelector('.confirm-btn').addEventListener('click', () => {
            confirmBox.remove();
            onConfirm();
        });

        confirmBox.querySelector('.cancel-btn').addEventListener('click', () => {
            confirmBox.remove();
        });
    }

    // Initial fetch and rendering of products when the cart page loads
    fetchProducts();
}); // End of DOMContentLoaded for cart page logic

// =========================================================================
// Functions and Listeners for Product Detail Pages (e.g., BG001.html, BRG003.html)
// These are outside DOMContentLoaded because they should be available globally
// when script.js is loaded on any page that uses them.
// =========================================================================

// Global function to handle adding items to cart from product detail pages
// This function will now directly manage localStorage.
async function addToCart(productId, productName, unitPrice, imageUrl, quantity) {
    // Optional attributes: retrieve from data-attributes or elements
    const addToCartButton = document.querySelector('.add-to-cart-btn');
    const description = addToCartButton?.dataset.productDescription || '';
    const material = addToCartButton?.dataset.productMaterial || '';
    const selectedSizeElement = document.getElementById('size');
    const size = selectedSizeElement ? selectedSizeElement.value : '';

    const newItem = {
        id: productId,
        name: productName,
        unit_price: parseFloat(unitPrice),
        image_url: imageUrl, // This path is relative to the server root for storage
        quantity: parseInt(quantity),
        description: description,
        material: material,
        size: size,
        store_name: 'Aureliana Jewelry' // Default store name
    };

    let cart = JSON.parse(localStorage.getItem('aureliana_cart')) || [];

    // Check if the item (with same ID) is already in the cart
    const existingItemIndex = cart.findIndex(item => item.id === newItem.id);

    if (existingItemIndex !== -1) {
        // If item exists, add the new quantity to the existing quantity
        cart[existingItemIndex].quantity += newItem.quantity;
        showMessage(`${productName} quantity updated in cart!`, 'success');
    } else {
        // If item doesn't exist, add it as a new item
        cart.push(newItem);
        showMessage(`${productName} added to cart!`, 'success');
    }

    localStorage.setItem('aureliana_cart', JSON.stringify(cart));

    // Optional: Log to console to confirm it was added
    console.log(`${productName} added to cart! Current cart:`, cart);
}

// Quantity control for product pages (these elements are direct descendants of the body)
// These listeners will be active on product pages where script.js is included.
const decreaseBtn = document.getElementById('decrease');
const increaseBtn = document.getElementById('increase');
const quantityInput = document.getElementById('quantity');

// FIX: Wrap these event listeners in a conditional check
// to ensure the elements exist before trying to add listeners.
// This prevents the "Cannot read properties of null" error when script.js is loaded
// on pages (like cart/index.html) that don't have these specific buttons.
if (decreaseBtn && increaseBtn && quantityInput) {
    decreaseBtn.addEventListener('click', () => {
        let currentValue = parseInt(quantityInput.value);
        if (currentValue > 1) {
            quantityInput.value = currentValue - 1;
        }
    });

    increaseBtn.addEventListener('click', () => {
        let currentValue = parseInt(quantityInput.value);
        quantityInput.value = currentValue + 1;
    });
}


// Add to Cart functionality for product detail pages
// This specifically targets the button with class 'add-to-cart-btn' on product pages.
const addToCartButton = document.querySelector('.add-to-cart-btn');

// This part already has a check 'if (addToCartButton)', which is good.
if (addToCartButton) {
    addToCartButton.addEventListener('click', () => {
        const productId = addToCartButton.dataset.productId;
        const productName = addToCartButton.dataset.productName;
        const unitPrice = parseFloat(addToCartButton.dataset.productPrice); // Make sure it's a number
        const imageUrl = addToCartButton.dataset.productImage;
        const quantity = parseInt(quantityInput.value);

        // Call the global addToCart function
        addToCart(productId, productName, unitPrice, imageUrl, quantity);
    });
}