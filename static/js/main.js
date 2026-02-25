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
    // Site announcement banner — dismiss after 12 s or on close click
    // -----------------------------------------------------------------------
    var announcementBar  = document.getElementById('site-announcement');
    var announcementClose = document.getElementById('announcement-close');
    if (announcementBar) {
        function slideUpAnnouncement() {
            announcementBar.style.transition = 'opacity .5s, max-height .6s, padding .6s';
            announcementBar.style.opacity    = '0';
            announcementBar.style.maxHeight  = '0';
            announcementBar.style.paddingTop    = '0';
            announcementBar.style.paddingBottom = '0';
            announcementBar.style.overflow   = 'hidden';
        }
        setTimeout(slideUpAnnouncement, 12000);
        if (announcementClose) {
            announcementClose.addEventListener('click', slideUpAnnouncement);
        }
    }

    // -----------------------------------------------------------------------
    // Password reveal toggle — auto-applied to every password input on the page
    // -----------------------------------------------------------------------
    document.querySelectorAll('input[type="password"]').forEach(function (input) {
        if (input.dataset.pwWrapped) return;          // don't double-apply
        input.dataset.pwWrapped = '1';

        // Wrap input in a relative container
        var wrap = document.createElement('div');
        wrap.style.cssText = 'position:relative;width:100%;display:block;';
        input.parentNode.insertBefore(wrap, input);
        wrap.appendChild(input);
        input.style.paddingRight = '2.5rem';

        // Build the eye button
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'pw-toggle';
        btn.tabIndex  = -1;
        btn.setAttribute('aria-label', 'Show or hide password');
        btn.innerHTML = '<i class="fas fa-eye-slash"></i>';  // slashed = currently hidden
        btn.style.cssText = [
            'position:absolute',
            'top:50%',
            'right:.65rem',
            'transform:translateY(-50%)',
            'background:none',
            'border:none',
            'color:#9a8870',
            'cursor:pointer',
            'padding:.2rem',
            'font-size:.85rem',
            'z-index:10',
            'line-height:1',
            'transition:color .2s'
        ].join(';') + ';';

        btn.addEventListener('click', function () {
            var show = input.type === 'password';
            input.type    = show ? 'text' : 'password';
            // eye = visible now; eye-slash = hidden now
            btn.innerHTML = show ? '<i class="fas fa-eye"></i>' : '<i class="fas fa-eye-slash"></i>';
            btn.style.color = show ? '#d4a017' : '#9a8870';
        });

        wrap.appendChild(btn);
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

    // -----------------------------------------------------------------------
    // Cookie / GDPR consent banner
    // -----------------------------------------------------------------------
    const cookieBanner  = document.getElementById('cookie-banner');
    const cookieAccept  = document.getElementById('cookie-accept');
    const cookieDecline = document.getElementById('cookie-decline');

    if (cookieBanner) {
        const consent = localStorage.getItem('cookie_consent');
        if (!consent) {
            // Show banner after a short delay so it doesn't flash immediately
            setTimeout(function () { cookieBanner.style.display = 'block'; }, 800);
        }
        if (cookieAccept) {
            cookieAccept.addEventListener('click', function () {
                localStorage.setItem('cookie_consent', 'accepted');
                cookieBanner.style.display = 'none';
            });
        }
        if (cookieDecline) {
            cookieDecline.addEventListener('click', function () {
                localStorage.setItem('cookie_consent', 'declined');
                cookieBanner.style.display = 'none';
            });
        }
    }

});
