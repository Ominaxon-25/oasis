/**
 * OASIS - Restaurant Reservation System (Tashkent)
 * Core JavaScript with Multilingual Support (EN, UZ, RU)
 */

(function () {
  'use strict';

  // Storage Keys
  const STORAGE_KEY = 'oasis_reservations';
  const PARTNER_STORAGE_KEY = 'oasis_restaurant_leads';
  const LANG_STORAGE_KEY = 'oasis_lang';

  // State
  let currentLang = localStorage.getItem(LANG_STORAGE_KEY) || 'en';
  let currentReservationDraft = null;

  // DOM Elements
  const searchForm = document.getElementById('searchForm');
  const searchArea = document.getElementById('searchArea');
  const searchDate = document.getElementById('searchDate');
  const searchTime = document.getElementById('searchTime');
  const searchGuests = document.getElementById('searchGuests');
  const activeFilterBadge = document.getElementById('activeFilterBadge');

  const reservationModal = document.getElementById('reservationModal');
  const bookingStageForm = document.getElementById('bookingStageForm');
  const bookingStageVerification = document.getElementById('bookingStageVerification');
  const bookingStageConfirmed = document.getElementById('bookingStageConfirmed');
  const reservationForm = document.getElementById('reservationForm');
  const resRestaurant = document.getElementById('resRestaurant');
  const resDate = document.getElementById('resDate');
  const resTime = document.getElementById('resTime');
  const resGuests = document.getElementById('resGuests');
  const resName = document.getElementById('resName');
  const resPhone = document.getElementById('resPhone');
  const resSpecial = document.getElementById('resSpecial');

  const digit1 = document.getElementById('digit1');
  const digit2 = document.getElementById('digit2');
  const digit3 = document.getElementById('digit3');
  const digit4 = document.getElementById('digit4');
  const codeErrorMsg = document.getElementById('codeErrorMsg');

  const confirmedRefCode = document.getElementById('confirmedRefCode');
  const confirmedRestaurant = document.getElementById('confirmedRestaurant');
  const confirmedDate = document.getElementById('confirmedDate');
  const confirmedTime = document.getElementById('confirmedTime');
  const confirmedGuests = document.getElementById('confirmedGuests');
  const confirmedSeating = document.getElementById('confirmedSeating');

  const partnerModal = document.getElementById('partnerModal');
  const partnerForm = document.getElementById('partnerForm');
  const partnerSuccess = document.getElementById('partnerSuccess');

  const drawerOverlay = document.getElementById('drawerOverlay');
  const savedBookingsList = document.getElementById('savedBookingsList');
  const myBookingsBtn = document.getElementById('myBookingsBtn');
  const headerBookingCount = document.getElementById('headerBookingCount');

  const mobileMenuToggle = document.getElementById('mobileMenuToggle');
  const mobileNavDrawer = document.getElementById('mobileNavDrawer');
  const toastMsg = document.getElementById('toastMsg');

  // =========================================================================
  // 1. Multilingual Translation Engine
  // =========================================================================
  function t(key, params) {
    const dict = (window.OASIS_TRANSLATIONS && window.OASIS_TRANSLATIONS[currentLang]) 
      || (window.OASIS_TRANSLATIONS && window.OASIS_TRANSLATIONS.en) 
      || {};
    let text = dict[key] || (window.OASIS_TRANSLATIONS && window.OASIS_TRANSLATIONS.en && window.OASIS_TRANSLATIONS.en[key]) || key;
    if (params) {
      Object.keys(params).forEach(p => {
        text = text.replace(new RegExp(`\\{${p}\\}`, 'g'), params[p]);
      });
    }
    return text;
  }

  window.changeLanguage = function (lang) {
    if (!window.OASIS_TRANSLATIONS || !window.OASIS_TRANSLATIONS[lang]) return;
    currentLang = lang;
    try {
      localStorage.setItem(LANG_STORAGE_KEY, lang);
    } catch (e) {
      console.warn('LocalStorage lang save issue:', e);
    }
    document.documentElement.lang = lang;
    applyTranslations();
  };

  function applyTranslations() {
    // 1. Update text nodes with data-i18n
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const translation = t(key);
      if (translation && translation !== key) {
        el.innerHTML = translation;
      }
    });

    // 2. Update placeholder attributes with data-i18n-placeholder
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      const translation = t(key);
      if (translation && translation !== key) {
        el.placeholder = translation;
      }
    });

    // 3. Update active state on language switcher buttons
    document.querySelectorAll('.lang-btn').forEach(btn => {
      if (btn.getAttribute('data-lang') === currentLang) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // 4. Update dynamic labels
    renderBookingsDrawer();
  }

  // =========================================================================
  // 2. Date Constraints: Only from tomorrow onwards
  // =========================================================================
  function getTomorrowDateString() {
    const now = new Date();
    const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    const yyyy = tomorrow.getFullYear();
    const mm = String(tomorrow.getMonth() + 1).padStart(2, '0');
    const dd = String(tomorrow.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  }

  function initDatePickers() {
    const minDate = getTomorrowDateString();
    
    // Search date picker
    if (searchDate) {
      searchDate.setAttribute('min', minDate);
      searchDate.value = minDate;
      searchDate.addEventListener('change', function () {
        if (this.value < minDate) {
          showToast(t('toast_date_err'));
          this.value = minDate;
        }
      });
    }

    // Reservation modal date picker
    if (resDate) {
      resDate.setAttribute('min', minDate);
      resDate.value = minDate;
      resDate.addEventListener('change', function () {
        if (this.value < minDate) {
          showToast(t('toast_date_err'));
          this.value = minDate;
        }
      });
    }
  }

  // =========================================================================
  // 3. Search & Filter
  // =========================================================================
  window.handleSearchSubmit = function (event) {
    if (event) event.preventDefault();

    const selectedArea = searchArea.value;
    const cards = document.querySelectorAll('.restaurant-card');
    let visibleCount = 0;

    cards.forEach(card => {
      const cardArea = card.getAttribute('data-area');
      if (selectedArea === 'all' || cardArea === selectedArea) {
        card.style.display = 'flex';
        visibleCount++;
      } else {
        card.style.display = 'none';
      }
    });

    if (activeFilterBadge) {
      if (selectedArea !== 'all') {
        const areaName = searchArea.options[searchArea.selectedIndex].text;
        activeFilterBadge.textContent = t('showing_filter', { area: areaName, count: visibleCount });
        activeFilterBadge.style.display = 'inline';
      } else {
        activeFilterBadge.style.display = 'none';
      }
    }

    // Smooth scroll to restaurants section
    const exploreSection = document.getElementById('explore');
    if (exploreSection) {
      exploreSection.scrollIntoView({ behavior: 'smooth' });
    }

    showToast(t('toast_found', { count: visibleCount, guests: searchGuests.value }));
  };

  // =========================================================================
  // 4. Reservation Modal Flow
  // =========================================================================
  window.openReservationModal = function (restaurantName, timeSlot) {
    // Reset stages
    bookingStageForm.style.display = 'block';
    bookingStageVerification.style.display = 'none';
    bookingStageConfirmed.style.display = 'none';
    codeErrorMsg.textContent = '';
    clearDigitInputs();

    // Set restaurant
    if (restaurantName && resRestaurant) {
      resRestaurant.value = restaurantName;
    }

    // Set date from search bar or tomorrow
    const minDate = getTomorrowDateString();
    if (searchDate && searchDate.value >= minDate) {
      resDate.value = searchDate.value;
    } else {
      resDate.value = minDate;
    }

    // Set time
    if (timeSlot && resTime) {
      resTime.value = timeSlot;
    } else if (searchTime && resTime) {
      resTime.value = searchTime.value;
    }

    // Set guests
    if (searchGuests && resGuests) {
      resGuests.value = searchGuests.value;
    }

    reservationModal.classList.add('active');
    document.body.style.overflow = 'hidden';
  };

  window.closeReservationModal = function () {
    reservationModal.classList.remove('active');
    document.body.style.overflow = '';
  };

  window.backToFormStage = function () {
    bookingStageVerification.style.display = 'none';
    bookingStageForm.style.display = 'block';
  };

  window.handleReservationSubmit = function (event) {
    event.preventDefault();

    const selectedSeating = document.querySelector('input[name="resSeating"]:checked')?.value || 'Indoor';

    currentReservationDraft = {
      restaurant: resRestaurant.value,
      date: resDate.value,
      time: resTime.value,
      guests: resGuests.value,
      seating: selectedSeating,
      name: resName.value.trim(),
      phone: resPhone.value.trim(),
      special: resSpecial.value.trim(),
      createdAt: new Date().toISOString()
    };

    // Transition to verification stage
    bookingStageForm.style.display = 'none';
    bookingStageVerification.style.display = 'block';
    clearDigitInputs();
    if (digit1) digit1.focus();
  };

  // 4-digit input logic
  const digitInputs = [digit1, digit2, digit3, digit4];
  digitInputs.forEach((input, idx) => {
    if (!input) return;

    input.addEventListener('input', (e) => {
      const val = e.target.value.replace(/[^0-9]/g, '');
      e.target.value = val ? val.slice(-1) : '';

      if (val && idx < digitInputs.length - 1) {
        digitInputs[idx + 1].focus();
      }

      // Auto submit if all 4 digits filled
      const fullCode = digitInputs.map(i => i.value).join('');
      if (fullCode.length === 4) {
        verifyCode(fullCode);
      }
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !e.target.value && idx > 0) {
        digitInputs[idx - 1].focus();
      }
    });

    input.addEventListener('paste', (e) => {
      e.preventDefault();
      const pasted = (e.clipboardData || window.clipboardData).getData('text').trim();
      if (/^\d{4}$/.test(pasted)) {
        pasted.split('').forEach((char, i) => {
          if (digitInputs[i]) digitInputs[i].value = char;
        });
        verifyCode(pasted);
      }
    });
  });

  function clearDigitInputs() {
    digitInputs.forEach(i => { if (i) i.value = ''; });
  }

  window.handleCodeSubmit = function (event) {
    if (event) event.preventDefault();
    const enteredCode = digitInputs.map(i => i.value).join('');
    verifyCode(enteredCode);
  };

  function verifyCode(code) {
    if (code === '1234') {
      codeErrorMsg.textContent = '';
      completeBooking();
    } else {
      codeErrorMsg.textContent = t('verif_err');
      clearDigitInputs();
      if (digit1) digit1.focus();
    }
  }

  function generateReservationCode() {
    const randomDigits = Math.floor(1000 + Math.random() * 9000);
    return `OAS-${randomDigits}`;
  }

  function completeBooking() {
    if (!currentReservationDraft) return;

    const refCode = generateReservationCode();
    currentReservationDraft.refCode = refCode;

    // Save to localStorage
    saveReservationToStorage(currentReservationDraft);

    // Populate confirmation display
    confirmedRefCode.textContent = refCode;
    confirmedRestaurant.textContent = currentReservationDraft.restaurant;
    
    // Format friendly date
    const [y, m, d] = currentReservationDraft.date.split('-');
    const localeMap = { en: 'en-US', uz: 'uz-UZ', ru: 'ru-RU' };
    const locale = localeMap[currentLang] || 'en-US';
    const formattedDate = new Date(y, m - 1, d).toLocaleDateString(locale, {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    });
    confirmedDate.textContent = formattedDate;
    confirmedTime.textContent = currentReservationDraft.time;
    
    const guestUnit = Number(currentReservationDraft.guests) === 1 ? t('guest_word') : t('guests_word');
    confirmedGuests.textContent = `${currentReservationDraft.guests} ${guestUnit}`;
    confirmedSeating.textContent = t(`seating_${currentReservationDraft.seating.toLowerCase()}`) || currentReservationDraft.seating;

    // Switch stage
    bookingStageVerification.style.display = 'none';
    bookingStageConfirmed.style.display = 'block';

    updateBookingCountBadge();
    showToast(t('toast_confirmed', { restaurant: currentReservationDraft.restaurant }));
  }

  // =========================================================================
  // 5. LocalStorage & Bookings Drawer
  // =========================================================================
  function getSavedReservations() {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      console.warn('LocalStorage access issue:', e);
      return [];
    }
  }

  function saveReservationToStorage(item) {
    const list = getSavedReservations();
    list.unshift(item);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    } catch (e) {
      console.warn('LocalStorage save issue:', e);
    }
  }

  function removeReservationFromStorage(refCode) {
    let list = getSavedReservations();
    list = list.filter(item => item.refCode !== refCode);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    } catch (e) {
      console.warn('LocalStorage remove issue:', e);
    }
    updateBookingCountBadge();
    renderBookingsDrawer();
    showToast(t('toast_removed'));
  }

  function updateBookingCountBadge() {
    const count = getSavedReservations().length;
    if (headerBookingCount) {
      headerBookingCount.textContent = count;
      headerBookingCount.style.display = count > 0 ? 'inline-flex' : 'none';
    }
  }

  function renderBookingsDrawer() {
    const list = getSavedReservations();
    if (!savedBookingsList) return;

    if (list.length === 0) {
      savedBookingsList.innerHTML = `
        <div class="empty-bookings-notice">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--gold); margin-bottom: 1rem;"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
          <p style="font-weight: 600; color: var(--dark); margin-bottom: 0.35rem;">${t('drawer_empty_title')}</p>
          <p style="font-size: 0.88rem;">${t('drawer_empty_text')}</p>
        </div>
      `;
      return;
    }

    const cancelText = t('btn_cancel');
    savedBookingsList.innerHTML = list.map(item => `
      <div class="saved-booking-item">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <h4>${escapeHtml(item.restaurant)}</h4>
          <button type="button" onclick="window.cancelReservation('${item.refCode}')" style="color: var(--text-muted); font-size: 0.75rem; text-decoration: underline;" title="${cancelText}">${cancelText}</button>
        </div>
        <div class="saved-booking-code">${escapeHtml(item.refCode)} · Confirmed</div>
        <div class="saved-booking-meta">
          <span>📅 ${escapeHtml(item.date)} at ${escapeHtml(item.time)}</span>
          <span>👥 ${escapeHtml(item.guests)} (${escapeHtml(t(`seating_${(item.seating || '').toLowerCase()}`) || item.seating)})</span>
          <span>👤 ${escapeHtml(item.name)} (${escapeHtml(item.phone)})</span>
        </div>
      </div>
    `).join('');
  }

  window.openBookingsDrawer = function () {
    renderBookingsDrawer();
    drawerOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  };

  window.closeBookingsDrawer = function () {
    drawerOverlay.classList.remove('active');
    document.body.style.overflow = '';
  };

  window.cancelReservation = function (refCode) {
    if (confirm(t('cancel_confirm'))) {
      removeReservationFromStorage(refCode);
    }
  };

  // =========================================================================
  // 6. For Restaurants Partner Modal
  // =========================================================================
  window.openPartnerModal = function () {
    partnerForm.style.display = 'block';
    partnerSuccess.style.display = 'none';
    partnerForm.reset();
    partnerModal.classList.add('active');
    document.body.style.overflow = 'hidden';
  };

  window.closePartnerModal = function () {
    partnerModal.classList.remove('active');
    document.body.style.overflow = '';
  };

  window.handlePartnerSubmit = function (event) {
    event.preventDefault();

    const lead = {
      restaurant: document.getElementById('partnerRestaurantName').value.trim(),
      name: document.getElementById('partnerContactName').value.trim(),
      phone: document.getElementById('partnerPhone').value.trim(),
      submittedAt: new Date().toISOString()
    };

    // Save lead to localStorage
    try {
      const leads = JSON.parse(localStorage.getItem(PARTNER_STORAGE_KEY) || '[]');
      leads.push(lead);
      localStorage.setItem(PARTNER_STORAGE_KEY, JSON.stringify(leads));
    } catch (e) {
      console.warn('LocalStorage lead save error:', e);
    }

    // Switch to success state
    partnerForm.style.display = 'none';
    partnerSuccess.style.display = 'block';
  };

  // =========================================================================
  // 7. Generic Info Modal (Terms / Privacy)
  // =========================================================================
  window.showModalInfo = function (type) {
    const modal = document.getElementById('infoModal');
    if (type === 'privacy') {
      document.getElementById('infoModalTitle').textContent = t('privacy_title');
      document.getElementById('infoModalContent').textContent = t('privacy_text');
    } else if (type === 'terms') {
      document.getElementById('infoModalTitle').textContent = t('terms_title');
      document.getElementById('infoModalContent').textContent = t('terms_text');
    }
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  };

  window.closeInfoModal = function () {
    document.getElementById('infoModal').classList.remove('active');
    document.body.style.overflow = '';
  };

  // =========================================================================
  // 8. Toast Helper
  // =========================================================================
  let toastTimer = null;
  function showToast(msg) {
    if (!toastMsg) return;
    toastMsg.textContent = msg;
    toastMsg.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastMsg.classList.remove('show');
    }, 3200);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // =========================================================================
  // 9. Initialization
  // =========================================================================
  document.addEventListener('DOMContentLoaded', () => {
    // Initialize date constraints
    initDatePickers();
    
    // Apply saved or default language
    applyTranslations();
    
    // Badge
    updateBookingCountBadge();

    // My Bookings button click
    if (myBookingsBtn) {
      myBookingsBtn.addEventListener('click', openBookingsDrawer);
    }

    // Mobile nav toggle
    if (mobileMenuToggle && mobileNavDrawer) {
      mobileMenuToggle.addEventListener('click', () => {
        mobileNavDrawer.classList.toggle('active');
      });

      // Close mobile drawer when clicking any nav link
      mobileNavDrawer.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
          mobileNavDrawer.classList.remove('active');
        });
      });
    }

    // Close modals on Esc key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeReservationModal();
        closePartnerModal();
        closeBookingsDrawer();
        closeInfoModal();
      }
    });

    // Close modals when clicking backdrop
    [reservationModal, partnerModal, document.getElementById('infoModal')].forEach(modal => {
      if (modal) {
        modal.addEventListener('click', (e) => {
          if (e.target === modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
          }
        });
      }
    });
  });

})();
