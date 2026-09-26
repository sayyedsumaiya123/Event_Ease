// EventEase — Main JavaScript

document.addEventListener('DOMContentLoaded', function () {

  // ── Navbar scroll effect ──
  const navbar = document.getElementById('mainNavbar');
  if (navbar) {
    window.addEventListener('scroll', () => {
      navbar.classList.toggle('scrolled', window.scrollY > 20);
    });
  }

  // ── Auto-dismiss alerts ──
  const alerts = document.querySelectorAll('.animated-message');
  alerts.forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // ── Animate numbers on scroll ──
  const animateNumber = (el) => {
    const target = parseInt(el.textContent.replace(/,/g, ''));
    if (isNaN(target)) return;
    let start = 0;
    const duration = 1200;
    const step = (timestamp) => {
      if (!start) start = timestamp;
      const progress = Math.min((timestamp - start) / duration, 1);
      el.textContent = Math.floor(progress * target).toLocaleString();
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };

  const statsObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const numbers = entry.target.querySelectorAll('.stat-value, .stat-number, .asc-value, .dsc-value');
        numbers.forEach(animateNumber);
        statsObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });

  document.querySelectorAll('.stats-bar, .admin-stat-card, .dashboard-stat-card').forEach(el => {
    statsObserver.observe(el);
  });

  // ── Event card hover glow ──
  document.querySelectorAll('.event-card').forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      card.style.setProperty('--mouse-x', x + '%');
      card.style.setProperty('--mouse-y', y + '%');
    });
  });

  // ── Smooth scroll for anchor links ──
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ── Filter form auto-submit on select change ──
  const filterForm = document.getElementById('filterForm');
  if (filterForm) {
    filterForm.querySelectorAll('select').forEach(select => {
      select.addEventListener('change', () => filterForm.submit());
    });
  }

  // ── Confirm delete ──
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', (e) => {
      if (!confirm(el.dataset.confirm)) e.preventDefault();
    });
  });

  // ── Tooltip initialization ──
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'));
  tooltipTriggerList.forEach(el => {
    new bootstrap.Tooltip(el, { trigger: 'hover' });
  });

  // ── Page load animation ──
  document.body.classList.add('loaded');

  console.log('%c EventEase DevOps Project ', 'background: linear-gradient(135deg, #6366f1, #ec4899); color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;');
  console.log('Stack: Django + PostgreSQL + Docker + Jenkins + Prometheus + Grafana');
});
