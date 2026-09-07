/**
 * OASIS - Restaurant Reservation System (Tashkent)
 * MVP Core JavaScript
 */

(function () {
  'use strict';

  // State
  let currentReservationDraft = null;
  const STORAGE_KEY = 'oasis_reservations';
  const PARTNER_STORAGE_KEY = 'oasis_restaurant_leads';

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
  // 1. Date Constraints: Only from tomorrow onwards
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
          showToast('Bookings can only be made from tomorrow.');
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
          showToast('Bookings can only be made from tomorrow.');
          this.value = minDate;
        }
      });
    }
  }

  // =========================================================================
  // 2. Search & Filter
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
        activeFilterBadge.textContent = `Showing: ${selectedArea} (${visibleCount})`;
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

    showToast(`Found ${visibleCount} available restaurants for ${searchGuests.value} guests.`);
  };

  // =========================================================================
  // 3. Reservation Modal Flow
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
      codeErrorMsg.textContent = 'Invalid code. For demo, please enter 1234';
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
    const formattedDate = new Date(y, m - 1, d).toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    });
    confirmedDate.textContent = formattedDate;
    confirmedTime.textContent = currentReservationDraft.time;
    confirmedGuests.textContent = `${currentReservationDraft.guests} ${Number(currentReservationDraft.guests) === 1 ? 'Guest' : 'Guests'}`;
    confirmedSeating.textContent = currentReservationDraft.seating;

    // Switch stage
    bookingStageVerification.style.display = 'none';
    bookingStageConfirmed.style.display = 'block';

    updateBookingCountBadge();
    showToast(`Table confirmed at ${currentReservationDraft.restaurant}!`);
  }

  // =========================================================================
  // 4. LocalStorage & Bookings Drawer
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
    showToast('Reservation removed.');
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
          <p style="font-weight: 600; color: var(--dark); margin-bottom: 0.35rem;">No active reservations</p>
          <p style="font-size: 0.88rem;">When you book a table with Oasis, your confirmed reservations will appear here.</p>
        </div>
      `;
      return;
    }

    savedBookingsList.innerHTML = list.map(item => `
      <div class="saved-booking-item">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <h4>${escapeHtml(item.restaurant)}</h4>
          <button type="button" onclick="window.cancelReservation('${item.refCode}')" style="color: var(--text-muted); font-size: 0.75rem; text-decoration: underline;" title="Cancel this booking">Cancel</button>
        </div>
        <div class="saved-booking-code">${escapeHtml(item.refCode)} · Confirmed</div>
        <div class="saved-booking-meta">
          <span>📅 ${escapeHtml(item.date)} at ${escapeHtml(item.time)}</span>
          <span>👥 ${escapeHtml(item.guests)} Guests (${escapeHtml(item.seating)})</span>
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
    if (confirm('Cancel this table reservation?')) {
      removeReservationFromStorage(refCode);
    }
  };

  // =========================================================================
  // 5. For Restaurants Partner Modal
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
  // 6. Generic Info Modal (Terms / Privacy)
  // =========================================================================
  window.showModalInfo = function (title, text) {
    const modal = document.getElementById('infoModal');
    document.getElementById('infoModalTitle').textContent = title;
    document.getElementById('infoModalContent').textContent = text;
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  };

  window.closeInfoModal = function () {
    document.getElementById('infoModal').classList.remove('active');
    document.body.style.overflow = '';
  };

  // =========================================================================
  // 7. Toast Helper
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
  // 8. Event Listeners Initialization
  // =========================================================================
  document.addEventListener('DOMContentLoaded', () => {
    initDatePickers();
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
    [reservationModal, partnerModal].forEach(modal => {
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
