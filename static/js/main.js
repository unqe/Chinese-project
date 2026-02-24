/* =========================================================================
   Despair Chinese — Main JavaScript
   Features: auto-dismiss alerts, AJAX basket add, navbar scroll effect,
             delivery/payment toggles, qty controls, star picker
========================================================================= */

document.addEventListener('DOMContentLoaded', function () {

    // -----------------------------------------------------------------------
    // Auto-dismiss alerts after 4 seconds
    // -----------------------------------------------------------------------
    const alerts = document.querySelectorAll('.alert.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 4000);
    });

    // -----------------------------------------------------------------------
    // Navbar shadow on scroll
    // -----------------------------------------------------------------------
    const nav = document.getElementById('main-nav');
    if (nav) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 30) {
                nav.style.boxShadow = '0 4px 24px rgba(0,0,0,0.6)';
            } else {
                nav.style.boxShadow = 'none';
            }
        }, { passive: true });
    }

    // -----------------------------------------------------------------------
    // AJAX Basket Add (from menu card quick-add buttons)
    // -----------------------------------------------------------------------
    document.querySelectorAll('[data-ajax-basket]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const btn = form.querySelector('[type=submit]');
            if (btn) { btn.disabled = true; }

            const formData = new FormData(form);
            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    // Update basket badge counters
                    document.querySelectorAll('.basket-badge, #basket-count').forEach(function (el) {
                        el.textContent = data.count;
                        el.style.display = data.count > 0 ? 'flex' : 'none';
                    });
                    // Animate the button
                    if (btn) {
                        const original = btn.innerHTML;
                        btn.innerHTML = '<i class="fa-solid fa-check"></i>';
                        btn.style.background = '#27ae60';
                        setTimeout(function () {
                            btn.innerHTML = original;
                            btn.style.background = '';
                            btn.disabled = false;
                        }, 1400);
                    }
                }
            })
            .catch(function () {
                if (btn) { btn.disabled = false; }
            });
        });
    });

    // -----------------------------------------------------------------------
    // Checkout: Delivery / Collection toggle
    // -----------------------------------------------------------------------
    const deliveryCards = document.querySelectorAll('.delivery-option-card');
    const deliveryRadios = document.querySelectorAll('input[name="delivery_type"]');
    const addressBlock = document.getElementById('address-block');

    function syncDeliveryUI(value) {
        deliveryCards.forEach(function (card) {
            card.classList.toggle('active', card.dataset.value === value);
        });
        if (addressBlock) {
            if (value === 'delivery') {
                addressBlock.style.display = 'block';
            } else {
                addressBlock.style.display = 'none';
            }
        }
    }

    deliveryCards.forEach(function (card) {
        card.addEventListener('click', function () {
            const target = document.getElementById('id_delivery_type_' + card.dataset.value) ||
                           document.querySelector('input[name="delivery_type"][value="' + card.dataset.value + '"]');
            if (target) { target.checked = true; target.dispatchEvent(new Event('change')); }
            syncDeliveryUI(card.dataset.value);
        });
    });

    deliveryRadios.forEach(function (radio) {
        radio.addEventListener('change', function () {
            syncDeliveryUI(this.value);
        });
        if (radio.checked) { syncDeliveryUI(radio.value); }
    });

    // -----------------------------------------------------------------------
    // Checkout: Payment method toggle
    // -----------------------------------------------------------------------
    const paymentCards = document.querySelectorAll('.payment-option-card');
    const paymentRadios = document.querySelectorAll('input[name="payment_method"]');
    const cardFieldsBlock = document.getElementById('card-fields-block');

    function syncPaymentUI(value) {
        paymentCards.forEach(function (card) {
            card.classList.toggle('active', card.dataset.value === value);
        });
        if (cardFieldsBlock) {
            cardFieldsBlock.style.display = (value === 'card') ? 'block' : 'none';
        }
    }

    paymentCards.forEach(function (card) {
        card.addEventListener('click', function () {
            const target = document.querySelector('input[name="payment_method"][value="' + card.dataset.value + '"]');
            if (target) { target.checked = true; target.dispatchEvent(new Event('change')); }
            syncPaymentUI(card.dataset.value);
        });
    });

    paymentRadios.forEach(function (radio) {
        radio.addEventListener('change', function () { syncPaymentUI(this.value); });
        if (radio.checked) { syncPaymentUI(radio.value); }
    });

    // -----------------------------------------------------------------------
    // Qty control (item detail page ± buttons)
    // -----------------------------------------------------------------------
    const qtyMinus = document.querySelector('.qty-btn[data-action="minus"]');
    const qtyPlus  = document.querySelector('.qty-btn[data-action="plus"]');
    const qtyInput = document.querySelector('.qty-input');

    if (qtyInput) {
        if (qtyMinus) {
            qtyMinus.addEventListener('click', function () {
                const v = parseInt(qtyInput.value, 10);
                if (v > 1) { qtyInput.value = v - 1; }
            });
        }
        if (qtyPlus) {
            qtyPlus.addEventListener('click', function () {
                const v = parseInt(qtyInput.value, 10);
                if (v < 99) { qtyInput.value = v + 1; }
            });
        }
    }

    // -----------------------------------------------------------------------
    // Star picker (review form) — clicking a label sets the hidden input
    // -----------------------------------------------------------------------
    const starLabels = document.querySelectorAll('.star-label');
    const ratingInput = document.getElementById('id_rating');

    starLabels.forEach(function (label, idx) {
        label.addEventListener('click', function () {
            // star-picker uses flex-direction: row-reverse, so idx 0 = 5 stars
            const value = starLabels.length - idx;
            if (ratingInput) { ratingInput.value = value; }
            starLabels.forEach(function (l, i) {
                const icon = l.querySelector('i');
                if (icon) {
                    if (i >= idx) {
                        icon.style.color = 'var(--gold)';
                    } else {
                        icon.style.color = '#3a2a1a';
                    }
                }
            });
        });
    });

    // Pre-fill stars if editing an existing review
    if (ratingInput && ratingInput.value) {
        const preVal = parseInt(ratingInput.value, 10);
        starLabels.forEach(function (l, i) {
            const icon = l.querySelector('i');
            if (icon) {
                const starVal = starLabels.length - i;
                icon.style.color = starVal <= preVal ? 'var(--gold)' : '#3a2a1a';
            }
        });
    }

    // -----------------------------------------------------------------------
    // Mobile category tabs scroll-active sync (menu page)
    // -----------------------------------------------------------------------
    const menuSections = document.querySelectorAll('[data-menu-section]');
    const catNavLinks  = document.querySelectorAll('.category-nav-link, .cat-tab-mobile');

    if (menuSections.length && catNavLinks.length) {
        const observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    const slug = entry.target.dataset.menuSection;
                    catNavLinks.forEach(function (link) {
                        link.classList.toggle('active', link.dataset.section === slug);
                    });
                }
            });
        }, { rootMargin: '-20% 0px -60% 0px', threshold: 0 });

        menuSections.forEach(function (sec) { observer.observe(sec); });

        // Click — smooth scroll
        catNavLinks.forEach(function (link) {
            link.addEventListener('click', function (e) {
                const slug = link.dataset.section;
                const target = document.querySelector('[data-menu-section="' + slug + '"]');
                if (target) {
                    e.preventDefault();
                    const offset = 90;
                    const top = target.getBoundingClientRect().top + window.scrollY - offset;
                    window.scrollTo({ top: top, behavior: 'smooth' });
                }
            });
        });
    }

});
