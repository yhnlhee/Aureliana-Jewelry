document.addEventListener('DOMContentLoaded', () => {
    const checkoutButton = document.getElementById('checkoutButton');

    if (checkoutButton) {
        checkoutButton.addEventListener('click', () => {
            fetch('/api/check_login')
                .then(response => response.json())
                .then(data => {
                    if (data.logged_in) {
                        const selectedItems = document.querySelectorAll('.product-item input[type="checkbox"]:checked');
                        if (selectedItems.length > 0) {
                            let itemsToCheckout = [];
                            selectedItems.forEach(checkbox => {
                                const productItem = checkbox.closest('.product-item');
                                const name = productItem.querySelector('.font-medium').textContent;
                                const priceText = productItem.querySelector('.text-gray-600').textContent;
                                const price = parseFloat(priceText.replace('₱', '').replace(',', ''));
                                const quantity = parseInt(productItem.querySelector('.quantity-input').value);
                                const image = productItem.querySelector('img').src;
                                itemsToCheckout.push({ name, price, quantity, image });
                            });
                            localStorage.setItem('itemsToCheckout', JSON.stringify(itemsToCheckout));
                            window.location.href = '/checkout';
                        } else {
                            alert('Please select items to check out.');
                        }
                    } else {
                        alert('Please log in to proceed to checkout.');
                        window.location.href = '/login';
                    }
                })
                .catch(error => {
                    console.error('Error checking login status:', error);
                    alert('An error occurred. Please try again.');
                });
        });
    }

    // Address autofill logic using JSON files (full hierarchy)
    const regionSelect = document.getElementById('region');
    const provinceSelect = document.getElementById('province');
    const citySelect = document.getElementById('city');
    const barangaySelect = document.getElementById('barangay');
    const addressDetails = document.getElementById('address_details');

    // Helper to populate a select
    function populateSelect(select, items, placeholder) {
        select.innerHTML = `<option value="">${placeholder}</option>`;
        items.forEach(item => {
            const opt = document.createElement('option');
            opt.value = item.code || item;
            opt.textContent = item.name || item;
            select.appendChild(opt);
        });
        select.disabled = false;
    }

    // Load regions
    fetch('/static/json/region.json').then(r => r.json()).then(regions => {
        populateSelect(regionSelect, regions, 'Select Region');
    });

    regionSelect && regionSelect.addEventListener('change', function() {
        provinceSelect.disabled = true; citySelect.disabled = true; barangaySelect.disabled = true;
        provinceSelect.innerHTML = citySelect.innerHTML = barangaySelect.innerHTML = '';
        if (!this.value) return;
        fetch('/static/json/province.json').then(r => r.json()).then(provinces => {
            const filtered = provinces.filter(p => p.region_code === this.value);
            populateSelect(provinceSelect, filtered, 'Select Province');
        });
    });
    provinceSelect && provinceSelect.addEventListener('change', function() {
        citySelect.disabled = true; barangaySelect.disabled = true;
        citySelect.innerHTML = barangaySelect.innerHTML = '';
        if (!this.value) return;
        fetch('/static/json/city.json').then(r => r.json()).then(cities => {
            const filtered = cities.filter(c => c.province_code === this.value);
            populateSelect(citySelect, filtered, 'Select City/Municipality');
        });
    });
    citySelect && citySelect.addEventListener('change', function() {
        barangaySelect.disabled = true;
        barangaySelect.innerHTML = '';
        if (!this.value) return;
        fetch('/static/json/barangay.json').then(r => r.json()).then(barangays => {
            const filtered = barangays.filter(b => b.city_code === this.value);
            populateSelect(barangaySelect, filtered, 'Select Barangay');
        });
    });
    barangaySelect && barangaySelect.addEventListener('change', function() {
        // Optionally do something on barangay select
    });

    // Autofill from user info if logged in
    fetch('/api/user_info')
        .then(response => response.json())
        .then(data => {
            if (data.logged_in && data.address) {
                // Try to parse address into region, province, city, barangay, details
                // This requires the address to be saved in a structured way
                // For now, leave as manual selection for usability
            }
        });
});